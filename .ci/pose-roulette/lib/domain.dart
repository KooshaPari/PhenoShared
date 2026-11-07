import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

const tau = pi * 2;
double wrapAngle(double x) => (x % tau + tau) % tau;
double landingAngle(int index, int count) => wrapAngle(-(index + .5) * tau / count);
double spinTravel(double start, double target) => tau * 5 + wrapAngle(target - start);
String uniqueId() => '${DateTime.now().microsecondsSinceEpoch}-${Random.secure().nextInt(1 << 30)}';

Future<ui.Image> decodePicture(Uint8List bytes, {int maxSide = 2000}) async {
  final buffer = await ui.ImmutableBuffer.fromUint8List(bytes);
  ui.ImageDescriptor? descriptor;
  ui.Codec? codec;
  try {
    descriptor = await ui.ImageDescriptor.encoded(buffer);
    if (descriptor.width * descriptor.height > 100000000) {
      throw const FormatException('Image dimensions are too large.');
    }
    final scale = min(1.0, maxSide / max(descriptor.width, descriptor.height));
    codec = await descriptor.instantiateCodec(
      targetWidth: max(1, (descriptor.width * scale).round()),
      targetHeight: max(1, (descriptor.height * scale).round()),
    );
    return (await codec.getNextFrame()).image;
  } finally {
    codec?.dispose(); descriptor?.dispose(); buffer.dispose();
  }
}
Future<ui.Image> pictureFile(String path, {int maxSide = 2000}) async =>
    decodePicture(await File(path).readAsBytes(), maxSide: maxSide);
Future<Uint8List> pngBytes(ui.Image image) async {
  final data = await image.toByteData(format: ui.ImageByteFormat.png);
  if (data == null) throw StateError('The image could not be encoded.');
  return data.buffer.asUint8List();
}
Future<void> copyOriginal(File source, File destination) async {
  await source.copy(destination.path);
  if (await source.length() != await destination.length()) {
    await destination.delete();
    throw const FileSystemException('The original photo was not copied completely.');
  }
}

class PosePoint {
  const PosePoint(this.x,this.y,this.z,this.confidence);
  final double x,y,z,confidence;
  Map<String,dynamic> json()=>{'x':x,'y':y,'z':z,'confidence':confidence};
  factory PosePoint.fromJson(Map<String,dynamic> j)=>PosePoint(
    (j['x'] as num).toDouble(),(j['y'] as num).toDouble(),
    (j['z'] as num? ?? 0).toDouble(),(j['confidence'] as num? ?? 1).toDouble());
}

class PosePreparation {
  PosePreparation({this.ready=false,this.stage='Queued',this.quality='none',this.error,
    Map<String,PosePoint>? landmarks,int? updatedAt})
      : landmarks=landmarks??{},updatedAt=updatedAt??DateTime.now().millisecondsSinceEpoch;
  bool ready;
  String stage,quality;
  String? error;
  Map<String,PosePoint> landmarks;
  int updatedAt;
  Map<String,dynamic> json()=>{'ready':ready,'stage':stage,'quality':quality,'error':error,
    'updatedAt':updatedAt,'landmarks':landmarks.map((k,v)=>MapEntry(k,v.json()))};
  factory PosePreparation.fromJson(Object? raw){
    if(raw is! Map)return PosePreparation();
    final j=Map<String,dynamic>.from(raw);
    final points=<String,PosePoint>{};
    if(j['landmarks'] is Map){
      for(final entry in (j['landmarks'] as Map).entries){
        if(entry.value is Map)points['${entry.key}']=PosePoint.fromJson(Map<String,dynamic>.from(entry.value));
      }
    }
    return PosePreparation(ready:j['ready']==true,stage:j['stage'] as String? ?? 'Queued',
      quality:j['quality'] as String? ?? 'none',error:j['error'] as String?,
      landmarks:points,updatedAt:j['updatedAt'] as int?);
  }
}

class Pose {
  Pose(this.id, this.name, this.path, {this.used = false, this.maskPath, PosePreparation? prep})
    : prep=prep??PosePreparation();
  final String id, path;
  String name;
  bool used;
  String? maskPath;
  PosePreparation prep;
  Map<String, dynamic> json() => {'id':id,'name':name,'used':used,'masked':maskPath != null,'prep':prep.json()};
}
class Draw {
  Draw({required this.winnerId, required this.wheelPath, required this.start,
    required this.travel, required this.target});
  final String winnerId, wheelPath;
  final double start, travel, target;
  Map<String, dynamic> json() => {'winnerId':winnerId,'wheelPath':wheelPath,
    'start':start,'travel':travel,'target':target};
  factory Draw.fromJson(Map<String,dynamic> j) => Draw(winnerId:j['winnerId'],
    wheelPath:j['wheelPath'],start:(j['start'] as num).toDouble(),
    travel:(j['travel'] as num).toDouble(),target:(j['target'] as num).toDouble());
}
class Shot {
  Shot(this.path, this.referencePath, this.poseName, this.draw);
  final String path, referencePath, poseName;
  final Draw? draw;
  Map<String,dynamic> json() => {'path':path,'referencePath':referencePath,'poseName':poseName,'draw':draw?.json()};
  factory Shot.fromJson(Map<String,dynamic> j) => Shot(j['path'],j['referencePath'],j['poseName'],
    j['draw'] == null ? null : Draw.fromJson(Map<String,dynamic>.from(j['draw'])));
}

class Deck extends ChangeNotifier {
  final List<Pose> poses = [];
  late Directory directory;
  bool noRepeats = true;
  int round = 1;
  String? lastId;
  Draw? lastDraw;
  Shot? lastShot;
  Future<void> _saving = Future.value();
  List<Pose> get eligible => noRepeats ? poses.where((p) => !p.used).toList() : List.of(poses);
  Pose? get selected => poses.where((p) => p.id == lastId).firstOrNull;
  String get root => directory.path;
  Future<void> load() async {
    directory = Directory('${(await getApplicationSupportDirectory()).path}/pose-roulette');
    await directory.create(recursive:true);
    final file = File('$root/deck.json');
    if (!await file.exists()) return;
    final j = jsonDecode(await file.readAsString()) as Map<String,dynamic>;
    noRepeats = j['noRepeats'] != false; round = (j['round'] as int? ?? 1).clamp(1,99999);
    lastId = j['lastId'];
    for (final p in (j['poses'] as List? ?? [])) {
      final id = p['id'] as String;
      if (!RegExp(r'^[0-9-]+$').hasMatch(id)) continue;
      final path = '$root/$id.png';
      if (!await File(path).exists()) continue;
      final mask = '$root/$id-mask.png';
      poses.add(Pose(id,p['name'] as String? ?? 'Pose',path,used:p['used'] == true,
        maskPath:p['masked'] == true && await File(mask).exists() ? mask : null,
        prep:PosePreparation.fromJson(p['prep'])));
    }
    if (j['lastDraw'] != null) lastDraw = Draw.fromJson(Map<String,dynamic>.from(j['lastDraw']));
    if (j['lastShot'] != null) {
      final shot = Shot.fromJson(Map<String,dynamic>.from(j['lastShot']));
      if (await File(shot.path).exists()) lastShot = shot;
    }
    notifyListeners();
  }
  Future<void> save() {
    final snapshot = jsonEncode({'version':1,'poses':poses.map((p)=>p.json()).toList(),
      'noRepeats':noRepeats,'round':round,'lastId':lastId,'lastDraw':lastDraw?.json(),'lastShot':lastShot?.json()});
    _saving = _saving.catchError((Object _) {}).then((_) async {
      final temporary = File('$root/deck.json.tmp');
      await temporary.writeAsString(snapshot,flush:true);
      await temporary.rename('$root/deck.json');
    });
    notifyListeners();
    return _saving;
  }
  Future<Pose> addReference(Uint8List bytes, String name) async {
    if (poses.length >= 200) throw StateError('This deck is limited to 200 poses.');
    if (bytes.length > 40 * 1024 * 1024) throw StateError('Reference exceeds 40 MB.');
    final image = await decodePicture(bytes);
    final id = uniqueId(), path = '$root/$id.png';
    try { await File(path).writeAsBytes(await pngBytes(image)); } finally { image.dispose(); }
    final pose = Pose(id,name,path); poses.add(pose); return pose;
  }
  Future<void> setMask(Pose pose, Uint8List bytes) async {
    final path = '$root/${pose.id}-mask.png';
    await File(path).writeAsBytes(bytes,flush:true); pose.maskPath = path; await save();
  }
  Future<void> resetRound() async { for(final p in poses) { p.used = false; } round++; await save(); }
  Future<void> remove(Pose pose) async {
    poses.remove(pose); if(lastId == pose.id) lastId = null;
    // Reference bytes are retained for the last photo's optional recap.
    await save();
  }
  Future<Shot> keepShot(String source, Pose pose, Draw? draw) async {
    var extension = source.split('.').last.toLowerCase();
    if (!['jpg','jpeg','png','heic','heif','webp'].contains(extension)) extension = 'jpg';
    final file = File('$root/photo-${uniqueId()}.$extension');
    await copyOriginal(File(source), file);
    final shot = Shot(file.path,pose.path,pose.name,draw?.winnerId == pose.id ? draw : null);
    lastShot = shot; await save(); return shot;
  }
  Future<File> exportDeck() async {
    final list = <Map<String,dynamic>>[];
    for(final pose in poses) {
      list.add({'name':pose.name,'used':pose.used,
        'image':'data:image/png;base64,${base64Encode(await File(pose.path).readAsBytes())}',
        if(pose.maskPath != null) 'mask':'data:image/png;base64,${base64Encode(await File(pose.maskPath!).readAsBytes())}',
        'preparation':pose.prep.json()});
    }
    final json = jsonEncode({'format':'pose-roulette','version':1,'noRepeats':noRepeats,
      'round':round,'lastIndex':poses.indexWhere((p)=>p.id == lastId),'photos':list});
    if (utf8.encode(json).length > 150 * 1024 * 1024) throw StateError('Export exceeds 150 MB. Split the deck.');
    final file = File('${(await getTemporaryDirectory()).path}/pose-deck-${uniqueId()}.json');
    await file.writeAsString(json); return file;
  }
  Future<int> importDeck(File file) async {
    if(await file.length() > 150 * 1024 * 1024) throw StateError('Deck exceeds 150 MB.');
    final j = jsonDecode(await file.readAsString());
    if(j is! Map || j['format'] != 'pose-roulette' || j['version'] != 1 || j['photos'] is! List) {
      throw const FormatException('Select an exported Pose Roulette JSON deck.');
    }
    final entries = j['photos'] as List;
    if(entries.length + poses.length > 200) throw StateError('Import would exceed 200 poses.');
    final empty = poses.isEmpty;
    var added = 0;
    for(var i=0;i<entries.length;i++) {
      final e = entries[i];
      if(e is! Map || e['name'] is! String || e['image'] is! String) continue;
      try {
        final uri = UriData.parse(e['image'] as String);
        if(!['image/png','image/jpeg','image/webp'].contains(uri.mimeType)) continue;
        final pose = await addReference(uri.contentAsBytes(),e['name']);
        if(empty) pose.used = e['used'] == true;
        if(e['mask'] is String && (e['mask'] as String).length < 16000000) {
          final mask = UriData.parse(e['mask']);
          if(mask.mimeType == 'image/png') {
            final im = await decodePicture(mask.contentAsBytes(),maxSide:1280);
            try { await setMask(pose,await pngBytes(im)); } finally { im.dispose(); }
          }
        }
        if(e['preparation'] is Map){
          final imported=PosePreparation.fromJson(e['preparation']);
          pose.prep.landmarks=imported.landmarks;
          pose.prep.ready=pose.maskPath!=null && imported.ready;
          pose.prep.stage=pose.prep.ready?'Imported ready':'Queued';
          pose.prep.quality=pose.prep.ready?imported.quality:'none';
        }
        if(empty && j['lastIndex'] == i) lastId = pose.id;
        added++;
      } catch (_) { /* Invalid entries do not discard valid ones. Count is reported. */ }
    }
    if(empty) { noRepeats = j['noRepeats'] != false; round = (j['round'] is int ? j['round'] as int : 1).clamp(1,99999); }
    await save(); return added;
  }
}
