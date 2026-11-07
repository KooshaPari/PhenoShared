import 'dart:collection';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart' as mlpose;
import 'package:google_mlkit_selfie_segmentation/google_mlkit_selfie_segmentation.dart' as mlseg;
import 'domain.dart';
import 'native.dart';

class PosePreprocessor {
  PosePreprocessor(this.deck)
      : _fastPose = mlpose.PoseDetector(options: mlpose.PoseDetectorOptions(
          mode: mlpose.PoseDetectionMode.single, model: mlpose.PoseDetectionModel.base)),
        _qualityPose = mlpose.PoseDetector(options: mlpose.PoseDetectorOptions(
          mode: mlpose.PoseDetectionMode.single, model: mlpose.PoseDetectionModel.accurate)),
        _fastMask = mlseg.SelfieSegmenter(mode: mlseg.SegmenterMode.single, enableRawSizeMask: true);

  final Deck deck;
  final mlpose.PoseDetector _fastPose, _qualityPose;
  final mlseg.SelfieSegmenter _fastMask;
  final Queue<Pose> _fastQueue = Queue<Pose>(), _qualityQueue = Queue<Pose>();
  final Set<String> _fastQueued = {}, _qualityQueued = {};
  bool _fastRunning=false,_qualityRunning=false,_disposed=false;

  int get fastPending => _fastQueue.length + (_fastRunning ? 1 : 0);
  int get qualityPending => _qualityQueue.length + (_qualityRunning ? 1 : 0);

  void start() {
    for (final pose in deck.poses) {
      if (!pose.prep.ready || pose.prep.landmarks.isEmpty || pose.maskPath == null) enqueue(pose);
      else if (pose.prep.quality != 'native-quality' && pose.prep.quality != 'manual') _enqueueQuality(pose);
    }
  }

  void enqueue(Pose pose) {
    if (_disposed || _fastQueued.contains(pose.id)) return;
    _fastQueued.add(pose.id);
    pose.prep.stage='Queued';
    pose.prep.error=null;
    pose.prep.updatedAt=DateTime.now().millisecondsSinceEpoch;
    _fastQueue.add(pose);
    deck.save();
    _pumpFast();
  }

  Future<void> _pumpFast() async {
    if (_fastRunning || _disposed) return;
    _fastRunning=true;
    try {
      while (_fastQueue.isNotEmpty && !_disposed) {
        final pose=_fastQueue.removeFirst();
        _fastQueued.remove(pose.id);
        if (!deck.poses.contains(pose)) continue;
        await _fast(pose);
        if (deck.poses.contains(pose)) _enqueueQuality(pose);
      }
    } finally {
      _fastRunning=false;
      _pumpQuality();
    }
  }

  void _enqueueQuality(Pose pose) {
    if (_disposed || _qualityQueued.contains(pose.id) || pose.prep.quality=='manual') return;
    _qualityQueued.add(pose.id);
    _qualityQueue.add(pose);
    _pumpQuality();
  }

  Future<void> _pumpQuality() async {
    if (_qualityRunning || _disposed) return;
    // Fast-first: every new reference gets a usable guide before expensive refinement starts.
    if (_fastRunning || _fastQueue.isNotEmpty) return;
    _qualityRunning=true;
    try {
      while (_qualityQueue.isNotEmpty && !_disposed) {
        if (_fastRunning || _fastQueue.isNotEmpty) break;
        final pose=_qualityQueue.removeFirst();
        _qualityQueued.remove(pose.id);
        if (!deck.poses.contains(pose) || pose.prep.quality=='manual') continue;
        await _quality(pose);
      }
    } finally {
      _qualityRunning=false;
      if (_fastQueue.isEmpty && _qualityQueue.isNotEmpty && !_disposed) {
        Future<void>.delayed(const Duration(milliseconds:80),_pumpQuality);
      }
    }
  }

  Future<Map<String,PosePoint>> _landmarks(mlpose.PoseDetector detector, String path, int width, int height) async {
    final poses=await detector.processImage(mlpose.InputImage.fromFilePath(path));
    if (poses.isEmpty) return {};
    mlpose.Pose best=poses.first;
    var bestVisible=-1;
    for (final pose in poses) {
      final visible=pose.landmarks.values.where((p)=>p.likelihood>.55).length;
      if (visible>bestVisible) { best=pose; bestVisible=visible; }
    }
    final points=<String,PosePoint>{};
    for (final landmark in best.landmarks.values) {
      points[landmark.type.name]=PosePoint(
        (landmark.x/width).clamp(-.5,1.5),
        (landmark.y/height).clamp(-.5,1.5),
        landmark.z/max(width,height),
        landmark.likelihood.clamp(0,1));
    }
    return points;
  }

  Future<Uint8List> _maskPng(mlseg.SegmentationMask mask) async {
    final w=mask.width,h=mask.height;
    final raw=Uint8List(w*h*4);
    for(var i=0;i<w*h;i++){
      final a=(mask.confidences[i].clamp(0.0,1.0)*255).round();
      final o=i*4; raw[o]=255;raw[o+1]=255;raw[o+2]=255;raw[o+3]=a;
    }
    final buffer=await ui.ImmutableBuffer.fromUint8List(raw);
    final descriptor=ui.ImageDescriptor.raw(buffer,width:w,height:h,pixelFormat:ui.PixelFormat.rgba8888,rowBytes:w*4);
    final codec=await descriptor.instantiateCodec();
    try {
      final image=(await codec.getNextFrame()).image;
      try { return await pngBytes(image); } finally { image.dispose(); }
    } finally {
      codec.dispose();descriptor.dispose();buffer.dispose();
    }
  }

  Future<void> _fast(Pose pose) async {
    pose.prep.stage='Fast guide';
    pose.prep.updatedAt=DateTime.now().millisecondsSinceEpoch;
    await deck.save();
    String? problem;
    try {
      final image=await pictureFile(pose.path,maxSide:2200);
      final w=image.width,h=image.height; image.dispose();
      Map<String,PosePoint> points={};
      try { points=await _landmarks(_fastPose,pose.path,w,h); }
      catch(e){ problem='Pose: $e'; }
      try {
        final mask=await _fastMask.processImage(mlseg.InputImage.fromFilePath(pose.path));
        if(mask!=null){
          await deck.setMask(pose,await _maskPng(mask));
        } else {
          problem=[problem,'Fast cutout unavailable'].whereType<String>().join(' · ');
        }
      } catch(e) {
        problem=[problem,'Cutout: $e'].whereType<String>().join(' · ');
      }
      pose.prep.landmarks=points;
      pose.prep.ready=true; // Never hold the wheel hostage. Whole-reference overlay is always usable.
      pose.prep.quality=pose.maskPath==null?'original':'fast';
      pose.prep.stage=pose.maskPath==null?'Ready · original overlay':'Ready · refining';
      pose.prep.error=problem;
      pose.prep.updatedAt=DateTime.now().millisecondsSinceEpoch;
      await deck.save();
    } catch(e) {
      pose.prep.ready=true;
      pose.prep.quality='original';
      pose.prep.stage='Ready · preprocessing degraded';
      pose.prep.error='$e';
      pose.prep.updatedAt=DateTime.now().millisecondsSinceEpoch;
      await deck.save();
    }
  }

  Future<void> _quality(Pose pose) async {
    if (_disposed || !deck.poses.contains(pose)) return;
    pose.prep.stage='Ready · background quality pass';
    pose.prep.updatedAt=DateTime.now().millisecondsSinceEpoch;
    await deck.save();
    String? warning=pose.prep.error;
    final image=await pictureFile(pose.path,maxSide:2200);
    final w=image.width,h=image.height;image.dispose();
    try {
      final accurate=await _landmarks(_qualityPose,pose.path,w,h);
      if(accurate.isNotEmpty) pose.prep.landmarks=accurate;
    } catch(e) {
      warning=[warning,'Accurate pose: $e'].whereType<String>().join(' · ');
    }
    try {
      final output='${deck.root}/${pose.id}-mask-quality.png';
      final generated=await Native.matte(pose.path,output,quality:'quality');
      if(await File(generated).exists()){
        final stable='${deck.root}/${pose.id}-mask.png';
        await File(generated).copy(stable);
        pose.maskPath=stable;
        pose.prep.quality='native-quality';
      }
    } catch(e) {
      warning=[warning,'Quality cutout: $e'].whereType<String>().join(' · ');
    }
    pose.prep.ready=true;
    pose.prep.stage='Ready';
    pose.prep.error=warning;
    pose.prep.updatedAt=DateTime.now().millisecondsSinceEpoch;
    await deck.save();
  }

  Future<void> dispose() async {
    _disposed=true;_fastQueue.clear();_qualityQueue.clear();
    await _fastPose.close();await _qualityPose.close();await _fastMask.close();
  }
}
