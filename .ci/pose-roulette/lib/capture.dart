import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart' as mlpose;
import 'domain.dart';
import 'guide.dart';
import 'native.dart';
import 'pose_fit.dart';

class CapturePage extends StatefulWidget{
  const CapturePage({super.key,required this.deck,required this.pose,required this.draw,required this.initialMirror});
  final Deck deck;final Pose pose;final Draw? draw;final bool initialMirror;
  @override State<CapturePage> createState()=>_CapturePageState();
}
class _CapturePageState extends State<CapturePage> with WidgetsBindingObserver{
  CameraController? controller;List<CameraDescription> cameras=[];int cameraIndex=0,generation=0,maskGeneration=0;
  ui.Image? source,mask;bool opening=false,shooting=false,maskBusy=false,mirror=false;
  final mlpose.PoseDetector livePose=mlpose.PoseDetector(options:mlpose.PoseDetectorOptions(
    mode:mlpose.PoseDetectionMode.stream,model:mlpose.PoseDetectionModel.base));
  bool poseInFlight=false;int lastPoseMs=0;FitResult? fit;Map<String,PosePoint> livePoints={};
  String coachMode='standard',loadedMaskPath='';
  double x=0,y=0,scale=1,angle=0,opacity=.28,dim=.35,blur=5;
  double baseScale=1,baseAngle=0,zoom=1,minZoom=1,maxZoom=1,exposure=0,minExposure=0,maxExposure=0;
  Offset focal=Offset.zero;String mode='outline',message='Starting native camera…';int timer=0,countdown=0;
  FlashMode flash=FlashMode.off;StreamSubscription<MethodCall>? subscription;
  @override void initState(){
    super.initState();mirror=widget.initialMirror;WidgetsBinding.instance.addObserver(this);
    widget.deck.addListener(syncPreparedAssets);
    subscription=Native.events.stream.listen((e){if(e.method=='shutter')capture();});
    Native.cameraActive(true);initialize();
  }
  Future<void> initialize()async{
    try{
      source=await pictureFile(widget.pose.path);
      await syncPreparedAssets();
      cameras=await availableCameras();
      if(cameras.isEmpty)throw StateError('No camera was reported by the device.');
      final back=cameras.indexWhere((c)=>c.lensDirection==CameraLensDirection.back);cameraIndex=max(0,back);
      if(mounted)await openCamera();
    }catch(e){if(mounted)setState(()=>message='Camera unavailable: $e. Go back to attach a stock-camera original.');}
  }
  Future<void> openCamera()async{
    if(cameras.isEmpty||!mounted)return;final token=++generation;
    setState(()=>opening=true);
    final old=controller;controller=null;await old?.dispose();
    final next=CameraController(cameras[cameraIndex],ResolutionPreset.max,enableAudio:false,
      imageFormatGroup:Platform.isAndroid?ImageFormatGroup.nv21:ImageFormatGroup.bgra8888);
    try{
      await next.initialize();
      if(!mounted||generation!=token){await next.dispose();return;}
      await next.setFlashMode(FlashMode.off);
      final limits=await Future.wait([next.getMinZoomLevel(),next.getMaxZoomLevel(),next.getMinExposureOffset(),next.getMaxExposureOffset()]);
      if(!mounted||generation!=token){await next.dispose();return;}
      setState((){
        controller=next;minZoom=limits[0];maxZoom=min(limits[1],12);zoom=1.0.clamp(minZoom,maxZoom);
        minExposure=limits[2];maxExposure=limits[3];exposure=0;flash=FlashMode.off;
        message='Native still capture · maximum requested resolution. This is not a video-frame screenshot.';
      });
      await next.setZoomLevel(zoom);
      await next.startImageStream((image)=>onPoseFrame(next,image,token));
    }catch(e){await next.dispose();if(mounted&&generation==token)setState(()=>message='Could not start this camera: $e');}
    finally{if(mounted&&generation==token)setState(()=>opening=false);}
  }
  @override void didChangeAppLifecycleState(AppLifecycleState state){
    final c=controller;
    if(state==AppLifecycleState.inactive&&c!=null&&c.value.isInitialized&&!shooting){
      generation++;controller=null;c.dispose();if(mounted)setState(()=>message='Camera paused.');
    }else if(state==AppLifecycleState.resumed&&controller==null&&!opening&&!shooting&&cameras.isNotEmpty){openCamera();}
  }
  @override void dispose(){
    generation++;maskGeneration++;WidgetsBinding.instance.removeObserver(this);widget.deck.removeListener(syncPreparedAssets);subscription?.cancel();
    Native.cameraActive(false);controller?.dispose();livePose.close();source?.dispose();mask?.dispose();super.dispose();
  }
  void report(Object e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('$e')));}
  Future<void> capture()async{
    final c=controller;if(c==null||!c.value.isInitialized||shooting||opening)return;
    setState(()=>shooting=true);final token=generation;
    try{
      for(var remaining=timer;remaining>0;remaining--){
        if(!mounted||generation!=token)return;setState(()=>countdown=remaining);await Future<void>.delayed(const Duration(seconds:1));
      }
      if(!mounted||generation!=token)return;setState(()=>countdown=0);HapticFeedback.mediumImpact();
      if(c.value.isStreamingImages)await c.stopImageStream();
      final file=await c.takePicture();
      final shot=await widget.deck.keepShot(file.path,widget.pose,widget.draw);
      if(mounted)Navigator.pop(context,shot);
    }catch(e){report(e);}
    finally{if(mounted)setState((){shooting=false;countdown=0;});}
  }
  Future<void> syncPreparedAssets()async{
    final path=widget.pose.maskPath;
    if(path==null||path==loadedMaskPath||!await File(path).exists())return;
    try{
      final fresh=await pictureFile(path,maxSide:1280);
      if(!mounted){fresh.dispose();return;}
      final old=mask;setState((){mask=fresh;loadedMaskPath=path;mode='outline';
        message=widget.pose.prep.quality=='native-quality'?'Detailed local guide ready.':'Fast guide ready; quality refinement continues in the background.';});old?.dispose();
    }catch(_){}
  }

  mlpose.InputImage? inputFromCamera(CameraController c,CameraImage image){
    var sensor=c.description.sensorOrientation;
    if(Platform.isAndroid){
      const orientations=<DeviceOrientation,int>{
        DeviceOrientation.portraitUp:0,DeviceOrientation.landscapeLeft:90,
        DeviceOrientation.portraitDown:180,DeviceOrientation.landscapeRight:270};
      final compensation=orientations[c.value.deviceOrientation]??0;
      sensor=c.description.lensDirection==CameraLensDirection.front
        ?(sensor+compensation)%360:(sensor-compensation+360)%360;
    }
    final rotation=mlpose.InputImageRotationValue.fromRawValue(sensor);
    final format=mlpose.InputImageFormatValue.fromRawValue(image.format.raw);
    if(rotation==null||format==null||image.planes.length!=1)return null;
    if(Platform.isAndroid&&format!=mlpose.InputImageFormat.nv21)return null;
    if(Platform.isIOS&&format!=mlpose.InputImageFormat.bgra8888)return null;
    final plane=image.planes.first;
    return mlpose.InputImage.fromBytes(bytes:plane.bytes,metadata:mlpose.InputImageMetadata(
      size:Size(image.width.toDouble(),image.height.toDouble()),rotation:rotation,
      format:format,bytesPerRow:plane.bytesPerRow));
  }

  Future<void> onPoseFrame(CameraController c,CameraImage image,int token)async{
    if(poseInFlight||shooting||coachMode=='off'||generation!=token||!mounted)return;
    final now=DateTime.now().millisecondsSinceEpoch;if(now-lastPoseMs<115)return;
    final input=inputFromCamera(c,image);if(input==null)return;
    poseInFlight=true;lastPoseMs=now;
    try{
      final results=await livePose.processImage(input);
      if(!mounted||generation!=token)return;
      if(results.isEmpty){setState(()=>fit=null);return;}
      final pose=results.first;
      final rotated=c.description.sensorOrientation==90||c.description.sensorOrientation==270;
      final logicalW=(rotated?image.height:image.width).toDouble(),logicalH=(rotated?image.width:image.height).toDouble();
      final points=<String,PosePoint>{};
      for(final landmark in pose.landmarks.values){
        var nx=(landmark.x/logicalW).clamp(-.5,1.5),ny=(landmark.y/logicalH).clamp(-.5,1.5);
        if(c.description.lensDirection==CameraLensDirection.front)nx=1-nx;
        points[landmark.type.name]=PosePoint(nx,ny,landmark.z/max(logicalW,logicalH),landmark.likelihood.clamp(0,1));
      }
      final target=transformReference(widget.pose.prep.landmarks,x:x,y:y,scale:scale,angle:angle,mirror:mirror);
      final result=target.isEmpty?null:comparePoses(target,points);
      setState((){livePoints=points;fit=result;});
    }catch(_){if(mounted)setState(()=>fit=null);}
    finally{poseInFlight=false;}
  }

  Future<void> buildMask({Rect? crop})async{
    if(source==null||maskBusy)return;final token=++maskGeneration;
    setState((){maskBusy=true;message=Platform.isIOS?'Apple Vision is finding the person locally…':'Native ONNX Runtime is building the person matte locally…';});
    final scratch=<File>[];
    try{
      var input=widget.pose.path;
      if(crop!=null){
        final s=source!,r=Rect.fromLTWH(crop.left*s.width,crop.top*s.height,crop.width*s.width,crop.height*s.height);
        final recorder=ui.PictureRecorder();Canvas(recorder).drawImageRect(s,r,Rect.fromLTWH(0,0,r.width,r.height),Paint());
        final picture=recorder.endRecording(),im=await picture.toImage(max(1,r.width.round()),max(1,r.height.round()));picture.dispose();
        final file=File('${widget.deck.root}/crop-${uniqueId()}.png');scratch.add(file);
        try{await file.writeAsBytes(await pngBytes(im));}finally{im.dispose();}input=file.path;
      }
      final file=File('${widget.deck.root}/mask-work-${uniqueId()}.png');scratch.add(file);
      await Native.matte(input,file.path,quality:'quality');
      if(!mounted||token!=maskGeneration)return;
      var result=await pictureFile(file.path,maxSide:1280);
      if(crop!=null){
        final s=source!,factor=min(1.0,1280/max(s.width,s.height)),w=(s.width*factor).round(),h=(s.height*factor).round();
        final recorder=ui.PictureRecorder();Canvas(recorder).drawImageRect(result,
          Rect.fromLTWH(0,0,result.width.toDouble(),result.height.toDouble()),
          Rect.fromLTWH(crop.left*w,crop.top*h,crop.width*w,crop.height*h),Paint());
        final picture=recorder.endRecording(),full=await picture.toImage(w,h);picture.dispose();result.dispose();result=full;
      }
      final bytes=await pngBytes(result);
      await widget.deck.setMask(widget.pose,bytes);
      if(!mounted||token!=maskGeneration){result.dispose();return;}
      final old=mask;setState((){mask=result;mode='outline';message='Local person mask ready. Check hands, clothing and gaps; Edit can correct mistakes.';});old?.dispose();
    }catch(e){if(mounted&&token==maskGeneration)setState(()=>message='AI mask failed: $e. Edit remains available without AI.');}
    finally{
      for(final f in scratch){try{if(await f.exists())await f.delete();}catch(_) {}}
      if(mounted&&token==maskGeneration)setState(()=>maskBusy=false);
    }
  }
  Future<void> edit()async{
    final s=source;if(s==null||maskBusy)return;
    final result=await Navigator.push<MaskEditResult>(context,MaterialPageRoute(builder:(_)=>MaskEditor(source:s,mask:mask)));
    if(!mounted||result==null)return;
    if(result.crop!=null){await buildMask(crop:result.crop);return;}
    if(result.png!=null){
      await widget.deck.setMask(widget.pose,result.png!);widget.pose.prep.quality='manual';widget.pose.prep.stage='Ready';widget.pose.prep.ready=true;await widget.deck.save();final image=await decodePicture(result.png!,maxSide:1280);
      if(!mounted){image.dispose();return;}final old=mask;setState((){mask=image;mode='outline';message='Your corrected mask is saved with the reference.';});old?.dispose();
    }
  }
  Widget range(String title,double value,double low,double high,ValueChanged<double> change)=>Row(children:[
    SizedBox(width:82,child:Text(title)),Expanded(child:Slider(value:value.clamp(low,high),min:low,max:high,
      label:value.toStringAsFixed(1),onChanged:change))]);
  Widget controls()=>SingleChildScrollView(padding:const EdgeInsets.fromLTRB(14,4,14,12),child:Column(children:[
    Text(message,textAlign:TextAlign.center,style:Theme.of(context).textTheme.bodySmall),
    const SizedBox(height:8),
    SegmentedButton<String>(segments:const [
      ButtonSegment(value:'minimal',label:Text('Minimal')),
      ButtonSegment(value:'standard',label:Text('Standard')),
      ButtonSegment(value:'coach',label:Text('Coach')),
      ButtonSegment(value:'off',label:Text('Off'))],
      selected:{coachMode},onSelectionChanged:(s)=>setState(()=>coachMode=s.first)),
    const SizedBox(height:8),
    Row(children:[Expanded(child:FilledButton.tonal(onPressed:maskBusy||source==null?null:()=>buildMask(),
      child:Text(maskBusy?'Building guide…':'Build AI guide'))),const SizedBox(width:8),
      OutlinedButton(onPressed:maskBusy||source==null?null:edit,child:const Text('Edit / crop'))]),
    Row(mainAxisAlignment:MainAxisAlignment.spaceBetween,children:[
      IconButton(tooltip:'Change camera',onPressed:shooting||opening||cameras.length<2?null:(){cameraIndex=(cameraIndex+1)%cameras.length;openCamera();},icon:const Icon(Icons.cameraswitch)),
      DropdownButton<int>(value:timer,items:[0,3,10].map((n)=>DropdownMenuItem(value:n,child:Text(n==0?'No timer':'${n}s timer'))).toList(),onChanged:shooting?null:(v)=>setState(()=>timer=v!)),
      FilledButton(onPressed:shooting||opening||controller==null?null:capture,
        style:FilledButton.styleFrom(shape:const CircleBorder(),padding:const EdgeInsets.all(19)),
        child:Icon(shooting?Icons.hourglass_bottom:Icons.camera,size:32)),
      IconButton(tooltip:'Flash ${flash.name}',onPressed:controller==null?null:()async{
        final next=flash==FlashMode.off?FlashMode.auto:flash==FlashMode.auto?FlashMode.always:FlashMode.off;
        try{await controller!.setFlashMode(next);if(mounted)setState(()=>flash=next);}catch(e){report(e);}
      },icon:Icon(flash==FlashMode.off?Icons.flash_off:flash==FlashMode.auto?Icons.flash_auto:Icons.flash_on))]),
    ExpansionTile(title:const Text('Guide and camera controls'),children:[
      DropdownButton<String>(value:mode,items:const [DropdownMenuItem(value:'outline',child:Text('Focus outline')),
        DropdownMenuItem(value:'cutout',child:Text('Focus cutout')),DropdownMenuItem(value:'ghost',child:Text('Whole reference')),
        DropdownMenuItem(value:'off',child:Text('Guide off'))],onChanged:(v)=>setState(()=>mode=v!)),
      range('Trace',opacity,0,1,(v)=>setState(()=>opacity=v)),
      range('Outside dim',dim,0,.8,(v)=>setState(()=>dim=v)),
      range('Outside blur',blur,0,12,(v)=>setState(()=>blur=v)),
      range('Guide size',scale,.25,3,(v)=>setState(()=>scale=v)),
      range('Rotation',angle,-pi,pi,(v)=>setState(()=>angle=v)),
      if(maxZoom>minZoom)range('Lens zoom',zoom,minZoom,maxZoom,(v)async{setState(()=>zoom=v);try{await controller?.setZoomLevel(v);}catch(e){report(e);}}),
      if(maxExposure>minExposure)range('Exposure',exposure,minExposure,maxExposure,(v)async{setState(()=>exposure=v);try{await controller?.setExposureOffset(v);}catch(e){report(e);}}),
      Row(mainAxisAlignment:MainAxisAlignment.spaceEvenly,children:[
        TextButton.icon(onPressed:()=>setState(()=>mirror=!mirror),icon:const Icon(Icons.flip),label:const Text('Mirror guide')),
        TextButton(onPressed:()=>setState((){x=0;y=0;scale=1;angle=0;}),child:const Text('Reset alignment'))]),
      const Padding(padding:EdgeInsets.all(8),child:Text('Drag, pinch and rotate the reference. Tap the live image to focus. Android volume keys act as a shutter only on this screen. Guides never enter the original photo.',textAlign:TextAlign.center))
    ])
  ]));
  Widget preview()=>LayoutBuilder(builder:(context,c){
    final cam=controller,s=source;
    if(cam==null||!cam.value.isInitialized)return Center(child:Column(mainAxisSize:MainAxisSize.min,children:[
      if(opening)const CircularProgressIndicator(),Text(opening?'Opening camera…':'Camera paused / unavailable'),
      TextButton(onPressed:opening?null:openCamera,child:const Text('Retry camera'))]));
    final portrait=MediaQuery.orientationOf(context)==Orientation.portrait;
    final ratio=portrait?1/cam.value.aspectRatio:cam.value.aspectRatio;
    final w=min(c.maxWidth,c.maxHeight*ratio),h=w/ratio;
    return Center(child:SizedBox(width:w,height:h,child:ClipRect(child:Stack(fit:StackFit.expand,children:[
      CameraPreview(cam),
      if(s!=null)GuideLayer(source:s,mask:mask,mode:mode,opacity:opacity,dim:dim,blur:blur,
        x:x,y:y,scale:scale,angle:angle,mirror:mirror,signalColor:coachMode=='off'?null:(fit==null?Colors.grey:HSVColor.fromAHSV(1,fit!.score*1.2,.78,.95).toColor())),
      if(coachMode=='coach'&&livePoints.isNotEmpty)CustomPaint(painter:LiveSkeletonPainter(livePoints,fit)),
      if(coachMode!='off')Positioned(top:12,right:12,left:12,child:FitHud(
        result:fit,mode:coachMode,preparing:widget.pose.prep.landmarks.isEmpty)),
      GestureDetector(behavior:HitTestBehavior.opaque,
        onTapUp:(d)async{try{final point=Offset((d.localPosition.dx/w).clamp(0.0,1.0),(d.localPosition.dy/h).clamp(0.0,1.0));
          await cam.setFocusPoint(point);await cam.setExposurePoint(point);HapticFeedback.selectionClick();}catch(e){report(e);}},
        onScaleStart:(d){focal=d.localFocalPoint;baseScale=scale;baseAngle=angle;},
        onScaleUpdate:(d){setState((){x+=(d.localFocalPoint.dx-focal.dx)/w;y+=(d.localFocalPoint.dy-focal.dy)/h;
          focal=d.localFocalPoint;scale=(baseScale*d.scale).clamp(.25,3.0);angle=(baseAngle+d.rotation).clamp(-pi,pi);});}),
      if(countdown>0)Center(child:Text('$countdown',style:const TextStyle(fontSize:100,fontWeight:FontWeight.bold,shadows:[Shadow(blurRadius:12)])))
    ]))));
  });
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Match the pose')),
    body:SafeArea(child:LayoutBuilder(builder:(context,c){
      if(c.maxWidth>c.maxHeight)return Row(children:[Expanded(child:preview()),SizedBox(width:min(370,c.maxWidth*.44),child:controls())]);
      return Column(children:[Expanded(child:preview()),SizedBox(height:min(330,c.maxHeight*.43),child:controls())]);
    })));
}


class FitHud extends StatelessWidget{
  const FitHud({super.key,required this.result,required this.mode,required this.preparing});
  final FitResult? result;final String mode;final bool preparing;
  @override Widget build(BuildContext context){
    final r=result,score=r?.score??0;
    final color=r==null?Colors.grey:HSVColor.fromAHSV(1,score*1.2,.78,.95).toColor();
    final hint=preparing?'Preparing pose model…':(r?.hint??'Step into frame');
    return IgnorePointer(child:Align(alignment:Alignment.topCenter,child:Container(
      constraints:const BoxConstraints(maxWidth:360),
      padding:mode=='minimal'?const EdgeInsets.all(7):const EdgeInsets.symmetric(horizontal:10,vertical:7),
      decoration:BoxDecoration(color:Colors.black45,borderRadius:BorderRadius.circular(999),
        border:Border.all(color:color.withValues(alpha:.55))),
      child:mode=='minimal'
        ? SizedBox(width:12,height:12,child:DecoratedBox(decoration:BoxDecoration(color:color,shape:BoxShape.circle)))
        : Row(mainAxisSize:MainAxisSize.min,children:[
            Container(width:10,height:10,decoration:BoxDecoration(color:color,shape:BoxShape.circle)),
            const SizedBox(width:7),
            if(r!=null)...[Text('${r.score}',style:TextStyle(fontSize:12,fontWeight:FontWeight.w800,color:color)),const SizedBox(width:6)],
            Flexible(child:Text(hint,maxLines:1,overflow:TextOverflow.ellipsis,
              style:const TextStyle(fontSize:11,fontWeight:FontWeight.w700))),
            if(mode=='coach'&&r!=null)...[const SizedBox(width:7),
              Text('P${r.shape} F${r.framing}',style:Theme.of(context).textTheme.labelSmall)]
          ])
    )));
  }
}

class LiveSkeletonPainter extends CustomPainter{
  LiveSkeletonPainter(this.points,this.fit);
  final Map<String,PosePoint> points;final FitResult? fit;
  @override void paint(Canvas canvas,Size size){
    for(final bone in fitBones){
      final a=points[bone[0]],b=points[bone[1]];if(a==null||b==null||a.confidence<.35||b.confidence<.35)continue;
      final q=min(fit?.perJoint[bone[0]]??.4,fit?.perJoint[bone[1]]??.4);
      final color=HSVColor.fromAHSV(.95,q*120,.82,.98).toColor();
      canvas.drawLine(Offset(a.x*size.width,a.y*size.height),Offset(b.x*size.width,b.y*size.height),
        Paint()..color=color..strokeWidth=4..strokeCap=StrokeCap.round);
    }
    for(final e in points.entries){
      if(e.value.confidence<.45)continue;final q=fit?.perJoint[e.key]??.4;
      canvas.drawCircle(Offset(e.value.x*size.width,e.value.y*size.height),4,
        Paint()..color=HSVColor.fromAHSV(.95,q*120,.82,.98).toColor());
    }
  }
  @override bool shouldRepaint(covariant LiveSkeletonPainter old)=>true;
}
