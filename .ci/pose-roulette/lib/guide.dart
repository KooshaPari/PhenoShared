import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'domain.dart';

Matrix4 guideTransform(Size size, ui.Image image, double x, double y, double scale, double angle, bool mirror) {
  final fit=min(size.width/image.width,size.height/image.height)*scale;
  return Matrix4.identity()..translate(size.width*(.5+x),size.height*(.5+y))
    ..rotateZ(angle)..scale(mirror?-fit:fit,fit)..translate(-image.width/2,-image.height/2);
}
class GuideLayer extends StatelessWidget {
  const GuideLayer({super.key,required this.source,required this.mask,required this.mode,
    required this.opacity,required this.dim,required this.blur,required this.x,required this.y,
    required this.scale,required this.angle,required this.mirror,this.signalColor});
  final ui.Image source;final ui.Image? mask;final String mode;
  final double opacity,dim,blur,x,y,scale,angle;final bool mirror;final Color? signalColor;
  @override Widget build(BuildContext context)=>IgnorePointer(child:LayoutBuilder(builder:(context,c){
    final size=Size(c.maxWidth,c.maxHeight),matte=mask;
    if(mode=='off')return const SizedBox.expand();
    return Stack(fit:StackFit.expand,children:[
      if(matte!=null&&(mode=='outline'||mode=='cutout'))ClipRect(child:ShaderMask(
        blendMode:BlendMode.dstOut,
        shaderCallback:(_)=>ui.ImageShader(matte,TileMode.decal,TileMode.decal,
          guideTransform(size,matte,x,y,scale,angle,mirror).storage),
        child:BackdropFilter(filter:ui.ImageFilter.blur(sigmaX:blur,sigmaY:blur),
          child:ColoredBox(color:Colors.black.withValues(alpha:dim))))),
      CustomPaint(painter:_GuidePainter(source,matte,mode,opacity,x,y,scale,angle,mirror,signalColor))
    ]);
  }));
}
class _GuidePainter extends CustomPainter {
  _GuidePainter(this.source,this.mask,this.mode,this.opacity,this.x,this.y,this.scale,this.angle,this.mirror,this.signalColor);
  final ui.Image source;final ui.Image? mask;final String mode;
  final double opacity,x,y,scale,angle;final bool mirror;final Color? signalColor;
  @override void paint(Canvas canvas,Size size){
    final rect=Rect.fromLTWH(0,0,source.width.toDouble(),source.height.toDouble());
    final m=mask;
    canvas.save();canvas.transform(guideTransform(size,source,x,y,scale,angle,mirror).storage);
    canvas.saveLayer(rect.inflate(12),Paint()..color=Colors.white.withValues(alpha:opacity));
    if(m==null||mode=='ghost'){
      canvas.drawImage(source,Offset.zero,Paint()..filterQuality=FilterQuality.medium);
    }else{
      final mr=Rect.fromLTWH(0,0,m.width.toDouble(),m.height.toDouble());
      if(mode=='cutout'){
        canvas.drawImage(source,Offset.zero,Paint());
        canvas.drawImageRect(m,mr,rect,Paint()..blendMode=BlendMode.dstIn..filterQuality=FilterQuality.medium);
      }else{
        canvas.drawImageRect(m,mr,rect,Paint()
          ..colorFilter=ColorFilter.mode(signalColor??const Color(0xffeed4ff),BlendMode.srcIn)
          ..imageFilter=ui.ImageFilter.dilate(radiusX:4,radiusY:4));
        canvas.drawImageRect(m,mr,rect,Paint()..blendMode=BlendMode.dstOut);
      }
    }
    canvas.restore();canvas.restore();
  }
  @override bool shouldRepaint(covariant _GuidePainter old)=>true;
}
class MaskEditResult {
  MaskEditResult({this.png,this.crop});
  final Uint8List? png;final Rect? crop;
}
class _Stroke {
  _Stroke(this.erase,this.radius);final bool erase;final double radius;final List<Offset> points=[];
}
Rect containedRect(Size size,ui.Image source){
  final fit=min(size.width/source.width,size.height/source.height);
  return Rect.fromCenter(center:Offset(size.width/2,size.height/2),width:source.width*fit,height:source.height*fit);
}
void paintMatte(Canvas canvas,Size size,ui.Image? base,List<_Stroke> strokes){
  final rect=Offset.zero&size;
  canvas.saveLayer(rect,Paint());
  if(base!=null)canvas.drawImageRect(base,Rect.fromLTWH(0,0,base.width.toDouble(),base.height.toDouble()),rect,Paint());
  for(final stroke in strokes){
    if(stroke.points.isEmpty)continue;
    final p=Paint()..color=Colors.white..style=PaintingStyle.stroke..strokeCap=StrokeCap.round
      ..strokeJoin=StrokeJoin.round..strokeWidth=stroke.radius*max(size.width,size.height)*2
      ..blendMode=stroke.erase?BlendMode.clear:BlendMode.srcOver;
    final path=Path()..moveTo(stroke.points.first.dx*size.width,stroke.points.first.dy*size.height);
    for(final point in stroke.points.skip(1)){path.lineTo(point.dx*size.width,point.dy*size.height);}
    if(stroke.points.length==1){canvas.drawCircle(Offset(stroke.points[0].dx*size.width,stroke.points[0].dy*size.height),p.strokeWidth/2,p..style=PaintingStyle.fill);}
    else{canvas.drawPath(path,p);}
  }
  canvas.restore();
}
class MaskEditor extends StatefulWidget {
  const MaskEditor({super.key,required this.source,required this.mask});
  final ui.Image source;final ui.Image? mask;
  @override State<MaskEditor> createState()=>_MaskEditorState();
}
class _MaskEditorState extends State<MaskEditor>{
  final strokes=<_Stroke>[];String tool='keep';double brush=.025;Rect? crop;Offset? cropStart;
  bool saving=false,cleared=false;Size stage=Size.zero;
  Offset point(Offset local){
    final r=containedRect(stage,widget.source);
    return Offset(((local.dx-r.left)/r.width).clamp(0.0,1.0),((local.dy-r.top)/r.height).clamp(0.0,1.0));
  }
  Future<void> apply()async{
    if(tool=='crop'){
      if(crop==null||crop!.width<.04||crop!.height<.04)return;
      Navigator.pop(context,MaskEditResult(crop:crop));return;
    }
    setState(()=>saving=true);
    try{
      final fit=min(1.0,1280/max(widget.source.width,widget.source.height));
      final w=max(1,(widget.source.width*fit).round()),h=max(1,(widget.source.height*fit).round());
      final recorder=ui.PictureRecorder();
      paintMatte(Canvas(recorder),Size(w.toDouble(),h.toDouble()),cleared?null:widget.mask,strokes);
      final picture=recorder.endRecording(),im=await picture.toImage(w,h);picture.dispose();
      final bytes=await pngBytes(im);im.dispose();
      if(mounted)Navigator.pop(context,MaskEditResult(png:bytes));
    }catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('$e')));}
    finally{if(mounted)setState(()=>saving=false);}
  }
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Refine the person mask')),
    body:SafeArea(child:Column(children:[
      Expanded(child:LayoutBuilder(builder:(context,c){stage=Size(c.maxWidth,c.maxHeight);return GestureDetector(
        onPanStart:saving?null:(d){final p=point(d.localPosition);setState((){
          if(tool=='crop'){cropStart=p;crop=Rect.fromPoints(p,p);}else{strokes.add(_Stroke(tool=='erase',brush)..points.add(p));}
        });},
        onPanUpdate:saving?null:(d){final p=point(d.localPosition);setState((){
          if(tool=='crop'&&cropStart!=null){crop=Rect.fromPoints(cropStart!,p);}else if(strokes.isNotEmpty){strokes.last.points.add(p);}
        });},
        onTapDown:saving?null:(d){if(tool!='crop')setState(()=>strokes.add(_Stroke(tool=='erase',brush)..points.add(point(d.localPosition))));},
        child:CustomPaint(size:stage,painter:_EditorPainter(widget.source,cleared?null:widget.mask,strokes,crop)));
      })),
      Padding(padding:const EdgeInsets.all(12),child:Column(children:[
        const Text('Purple is included. Keep hands and clothing; erase gaps and background.'),
        SegmentedButton<String>(segments:const [ButtonSegment(value:'keep',label:Text('Keep')),
          ButtonSegment(value:'erase',label:Text('Erase')),ButtonSegment(value:'crop',label:Text('Crop for AI'))],
          selected:{tool},onSelectionChanged:saving?null:(s)=>setState(()=>tool=s.first)),
        if(tool!='crop')Row(children:[const Text('Brush'),Expanded(child:Slider(min:.004,max:.10,value:brush,label:'${(brush*100).round()}%',onChanged:(v)=>setState(()=>brush=v)))]),
        Row(mainAxisAlignment:MainAxisAlignment.spaceEvenly,children:[
          TextButton(onPressed:saving||strokes.isEmpty?null:()=>setState(()=>strokes.removeLast()),child:const Text('Undo')),
          TextButton(onPressed:saving?null:()=>setState((){cleared=false;strokes.clear();crop=null;}),child:const Text('Reset')),
          TextButton(onPressed:saving?null:()=>setState((){cleared=true;strokes.clear();}),child:const Text('Clear'))]),
        SizedBox(width:double.infinity,child:FilledButton(onPressed:saving?null:apply,
          child:Text(saving?'Saving…':tool=='crop'?'Run AI on this crop':'Use this corrected guide'))),
        if(tool=='crop')const Text('Drag a box around the person. This changes AI input only, never the photo.')
      ]))])));
}
class _EditorPainter extends CustomPainter{
  _EditorPainter(this.source,this.base,this.strokes,this.crop);
  final ui.Image source;final ui.Image? base;final List<_Stroke> strokes;final Rect? crop;
  @override void paint(Canvas canvas,Size size){
    final rect=containedRect(size,source);
    canvas.drawImageRect(source,Rect.fromLTWH(0,0,source.width.toDouble(),source.height.toDouble()),rect,Paint());
    canvas.drawRect(rect,Paint()..color=Colors.black38);
    canvas.save();canvas.translate(rect.left,rect.top);
    canvas.saveLayer(Offset.zero&rect.size,Paint()..colorFilter=const ColorFilter.mode(Color(0x77da9cff),BlendMode.srcIn));
    paintMatte(canvas,rect.size,base,strokes);canvas.restore();
    if(crop!=null)canvas.drawRect(Rect.fromLTWH(crop!.left*rect.width,crop!.top*rect.height,crop!.width*rect.width,crop!.height*rect.height),
      Paint()..color=Colors.amber..style=PaintingStyle.stroke..strokeWidth=2);
    canvas.restore();
  }
  @override bool shouldRepaint(covariant _EditorPainter old)=>true;
}
