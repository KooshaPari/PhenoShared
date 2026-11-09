import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:share_plus/share_plus.dart';
import 'domain.dart';
import 'native.dart';
import 'capture.dart';
import 'review.dart';
import 'preprocess.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized(); Native.initialize();
  runApp(const PoseApp());
}
class PoseApp extends StatelessWidget {
  const PoseApp({super.key});
  @override Widget build(BuildContext context) => MaterialApp(
    title:'Pose Roulette',debugShowCheckedModeBanner:false,
    theme:ThemeData(brightness:Brightness.dark,useMaterial3:true,
      colorScheme:ColorScheme.fromSeed(seedColor:const Color(0xffcfb4f4),brightness:Brightness.dark),
      scaffoldBackgroundColor:const Color(0xff121015),
      filledButtonTheme:FilledButtonThemeData(style:FilledButton.styleFrom(minimumSize:const Size(48,52))),
      sliderTheme:const SliderThemeData(showValueIndicator:ShowValueIndicator.always)),
    home:const Home());
}
void inform(BuildContext context, Object message) {
  if(!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(message.toString())));
}
Future<void> shareFile(String path, String title) async {
  await SharePlus.instance.share(ShareParams(files:[XFile(path)],title:title));
}

class Home extends StatefulWidget {
  const Home({super.key});
  @override State<Home> createState()=>_HomeState();
}
class _HomeState extends State<Home> with SingleTickerProviderStateMixin {
  final deck=Deck(); final images=<String,ui.Image>{};
  late final AnimationController animation;
  late final PosePreprocessor preprocessor;
  List<Pose> wheelPoses=[];
  double rotation=0,start=0,travel=0;
  bool ready=false,busy=false,spinning=false;
  @override void initState() {
    super.initState();
    preprocessor=PosePreprocessor(deck);
    animation=AnimationController(vsync:this,duration:const Duration(milliseconds:3400))
      ..addListener(()=>setState(()=>rotation=start+travel*(1-pow(1-animation.value,4))));
    deck.addListener(changed); load();
  }
  void changed(){if(mounted)setState((){});}
  Future<void> load() async {
    try { await deck.load(); rotation=deck.lastDraw?.target??0; await thumbnails(); preprocessor.start(); }
    catch(e){if(mounted)inform(context,'Saved deck could not fully load: $e');}
    if(mounted)setState(()=>ready=true);
  }
  Future<void> thumbnails() async {
    for(final p in deck.poses) {
      if(images.containsKey(p.id))continue;
      try { images[p.id]=await pictureFile(p.path,maxSide:180); } catch(_) {}
    }
    if(mounted)setState(()=>wheelPoses=deck.eligible.isEmpty?List.of(deck.poses):deck.eligible);
  }
  @override void dispose() {
    deck.removeListener(changed); preprocessor.dispose(); deck.dispose(); animation.dispose();
    for(final image in images.values){image.dispose();}
    super.dispose();
  }
  Future<void> add() async {
    if(busy||spinning)return; setState(()=>busy=true);
    var count=0;
    try {
      final picks=await ImagePicker().pickMultiImage(maxWidth:2000,maxHeight:2000,imageQuality:95);
      final added=<Pose>[];
      for(final file in picks){final pose=await deck.addReference(await file.readAsBytes(),file.name);added.add(pose);count++;}
      await deck.save(); await thumbnails();
      for(final pose in added)preprocessor.enqueue(pose);
      if(mounted&&count>0)inform(context,'Added $count references.');
    }catch(e){await deck.save();await thumbnails();if(mounted)inform(context,'Added $count. $e');}
    finally{if(mounted)setState(()=>busy=false);}
  }
  Future<void> menu(String action) async {
    if(busy||spinning)return;setState(()=>busy=true);
    try {
      if(action=='import') {
        final selected=await FilePicker.platform.pickFiles(type:FileType.custom,allowedExtensions:['json']);
        final path=selected?.files.single.path;
        if(path!=null){final added=await deck.importDeck(File(path));await thumbnails();preprocessor.start();if(mounted)inform(context,'Imported $added valid references. Preprocessing continues in the background.');}
      } else if(action=='export') {
        final file=await deck.exportDeck();await shareFile(file.path,'Pose Roulette deck');
      } else if(action=='round') { await deck.resetRound();await thumbnails(); }
    }catch(e){if(mounted)inform(context,e);}
    finally{if(mounted)setState(()=>busy=false);}
  }
  Future<void> spin() async {
    if(!ready||busy||spinning||deck.poses.isEmpty)return;
    setState(()=>spinning=true);
    try {
      if(deck.noRepeats&&deck.eligible.isEmpty)await deck.resetRound();
      final pool=deck.eligible;final index=Random.secure().nextInt(pool.length),winner=pool[index];
      setState(()=>wheelPoses=List.of(pool));
      final recorder=ui.PictureRecorder();
      WheelPainter(pool,images).paint(Canvas(recorder),const Size(800,800));
      final picture=recorder.endRecording(),bitmap=await picture.toImage(800,800);
      picture.dispose();final wheelPath='${deck.root}/spin-${uniqueId()}.png';
      try{await File(wheelPath).writeAsBytes(await pngBytes(bitmap));}finally{bitmap.dispose();}
      start=wrapAngle(rotation);final target=landingAngle(index,pool.length);travel=spinTravel(start,target);
      final draw=Draw(winnerId:winner.id,wheelPath:wheelPath,start:start,travel:travel,target:target);
      winner.used=true;deck.lastId=winner.id;deck.lastDraw=draw;await deck.save();
      if(!mounted)return;
      animation.duration=Duration(milliseconds:MediaQuery.of(context).disableAnimations?1:3400);
      await animation.forward(from:0).orCancel;
      if(!mounted)return;setState(()=>rotation=target);HapticFeedback.selectionClick();
      await show(winner);
    }on TickerCanceled{/* Selection was already persisted. */}
    catch(e){if(mounted)inform(context,e);}
    finally{if(mounted)setState(()=>spinning=false);}
  }
  Future<void> show(Pose pose) async {
    await Navigator.of(context).push(MaterialPageRoute(builder:(_)=>PosePage(deck:deck,pose:pose,
      draw:deck.lastDraw?.winnerId==pose.id?deck.lastDraw:null)));
    if(mounted)await thumbnails();
  }
  Future<void> remove(Pose pose) async {
    final yes=await showDialog<bool>(context:context,builder:(c)=>AlertDialog(
      title:const Text('Remove this reference?'),content:Text(pose.name),actions:[
        TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('Keep')),
        FilledButton(onPressed:()=>Navigator.pop(c,true),child:const Text('Remove'))]));
    if(yes==true){await deck.remove(pose);images.remove(pose.id)?.dispose();await thumbnails();}
  }
  @override Widget build(BuildContext context) {
    final locked=!ready||busy||spinning;
    return Scaffold(appBar:AppBar(title:const Text('Pose Roulette'),actions:[
      PopupMenuButton<String>(enabled:!locked,onSelected:menu,itemBuilder:(_)=>[
        const PopupMenuItem(value:'import',child:Text('Import Vercel / native deck')),
        const PopupMenuItem(value:'export',child:Text('Export / share deck')),
        const PopupMenuItem(value:'round',child:Text('Start a fresh round'))])]),
      body:SafeArea(child:LayoutBuilder(builder:(context,constraints)=>SingleChildScrollView(
        padding:const EdgeInsets.fromLTRB(20,8,20,32),child:Center(child:ConstrainedBox(
        constraints:const BoxConstraints(maxWidth:680),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
          Text('A little chance. A new pose.',style:Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height:8),
          Text('${deck.poses.length} references · round ${deck.round} · saved on this phone'),
          const SizedBox(height:12),
          SizedBox(height:min(constraints.maxWidth-40,360),child:Stack(alignment:Alignment.center,children:[
            Semantics(label:'Pose wheel',child:Transform.rotate(angle:rotation,child:CustomPaint(
              size:const Size(360,360),painter:WheelPainter(wheelPoses,images)))),
            Positioned(top:0,child:Icon(Icons.arrow_drop_down,size:46,color:Theme.of(context).colorScheme.primary)),
            FilledButton(onPressed:locked||deck.poses.isEmpty?null:spin,child:Text(spinning?'Spinning…':'SPIN'))])),
          const SizedBox(height:12),
          FilledButton.icon(onPressed:locked?null:add,icon:const Icon(Icons.add_photo_alternate_outlined),
            label:Text(busy?'Working…':'Add photos')),
          SwitchListTile.adaptive(contentPadding:EdgeInsets.zero,title:const Text('No repeats until the round ends'),
            value:deck.noRepeats,onChanged:locked?null:(v)async{deck.noRepeats=v;await deck.save();await thumbnails();}),
          if(deck.selected!=null)OutlinedButton.icon(onPressed:locked?null:()=>show(deck.selected!),
            icon:const Icon(Icons.person_outline),label:Text('Selected: ${deck.selected!.name}',maxLines:1,overflow:TextOverflow.ellipsis)),
          if(deck.lastShot!=null)TextButton.icon(onPressed:locked?null:()=>Navigator.push(context,MaterialPageRoute(
            builder:(_)=>ReviewPage(shot:deck.lastShot!,root:deck.root))),icon:const Icon(Icons.photo_outlined),label:const Text('Last photo / optional recap')),
          const SizedBox(height:12),
          if(deck.poses.isEmpty)const Padding(padding:EdgeInsets.all(20),child:Text(
            'Add your own pose references, spin, then use the native camera or attach an original from your usual Camera app. No account or photo server.',textAlign:TextAlign.center)),
          GridView.builder(shrinkWrap:true,physics:const NeverScrollableScrollPhysics(),itemCount:deck.poses.length,
            gridDelegate:SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount:constraints.maxWidth>580?5:3,
              mainAxisSpacing:10,crossAxisSpacing:10,childAspectRatio:.75),
            itemBuilder:(context,index){final p=deck.poses[index];return InkWell(
              onTap:locked?null:()=>show(p),onLongPress:locked?null:()=>remove(p),
              child:ClipRRect(borderRadius:BorderRadius.circular(14),child:Stack(fit:StackFit.expand,children:[
                Image.file(File(p.path),fit:BoxFit.cover,cacheWidth:240),
                if(p.used)const Positioned(top:6,left:6,child:CircleAvatar(radius:13,child:Icon(Icons.check,size:18))),
                Positioned(left:6,bottom:34,child:Container(
                  padding:const EdgeInsets.symmetric(horizontal:7,vertical:4),
                  decoration:BoxDecoration(color:p.prep.quality=='native-quality'?Colors.green.shade800:Colors.black54,borderRadius:BorderRadius.circular(9)),
                  child:Text(p.prep.ready?(p.prep.quality=='native-quality'?'READY+':'READY'):'PREP',style:const TextStyle(fontSize:10,fontWeight:FontWeight.w700)))),
                Positioned(right:0,top:0,child:IconButton(tooltip:'Remove reference',onPressed:locked?null:()=>remove(p),
                  icon:const Icon(Icons.close,size:20),style:IconButton.styleFrom(backgroundColor:Colors.black38))),
                Align(alignment:Alignment.bottomCenter,child:Container(width:double.infinity,color:Colors.black54,
                  padding:const EdgeInsets.all(6),child:Text(p.name,maxLines:1,overflow:TextOverflow.ellipsis)))])));}),
          const SizedBox(height:20),Text(
            'Preprocessing never blocks the wheel. Fast guides land first; quality refinement keeps running in the background. '
            'If you reach a pose before a feature is ready, that feature catches up there.',
            textAlign:TextAlign.center,style:Theme.of(context).textTheme.bodySmall),
          const SizedBox(height:8),
          const Text('Native preview · Pixel 9 Pro XL / iPhone 17 Pro Max targets\nCamera quality and hardware features depend on actual device support.',textAlign:TextAlign.center)
        ])))))));
  }
}

class WheelPainter extends CustomPainter {
  WheelPainter(this.poses,this.images);
  final List<Pose> poses;final Map<String,ui.Image> images;
  static const colors=[Color(0xffefb8a2),Color(0xffd9deb9),Color(0xffcfc7e1),Color(0xfff2d89f),Color(0xffbdcfc5),Color(0xffc4d0e0)];
  @override void paint(Canvas canvas,Size size){
    final center=Offset(size.width/2,size.height/2),radius=min(size.width,size.height)/2-12;
    final rect=Rect.fromCircle(center:center,radius:radius),n=max(poses.length,1);
    for(var i=0;i<n;i++){
      final path=Path()..moveTo(center.dx,center.dy)..arcTo(rect,-pi/2+i*tau/n,tau/n,false)..close();
      canvas.save();canvas.clipPath(path);canvas.drawRect(rect,Paint()..color=colors[i%colors.length]);
      final image=poses.isEmpty?null:images[poses[i].id];
      if(image!=null){final a=Rect.fromLTWH(0,0,image.width.toDouble(),image.height.toDouble());
        canvas.drawImageRect(image,a,rect,Paint()..color=const Color(0xd9ffffff)..filterQuality=FilterQuality.medium);}
      canvas.restore();canvas.drawPath(path,Paint()..color=Colors.black38..style=PaintingStyle.stroke..strokeWidth=1.5);
    }
    canvas.drawCircle(center,radius,Paint()..color=const Color(0xffd4bddf)..style=PaintingStyle.stroke..strokeWidth=5);
  }
  @override bool shouldRepaint(covariant WheelPainter old)=>true;
}
class PosePage extends StatefulWidget {
  const PosePage({super.key,required this.deck,required this.pose,required this.draw});
  final Deck deck;final Pose pose;final Draw? draw;
  @override State<PosePage> createState()=>_PosePageState();
}
class _PosePageState extends State<PosePage>{
  bool mirror=false,busy=false;
  Future<void> attach(ImageSource source)async{
    setState(()=>busy=true);
    try{
      final file=await ImagePicker().pickImage(source:source,requestFullMetadata:false);
      if(file==null)return;
      final shot=await widget.deck.keepShot(file.path,widget.pose,widget.draw);
      if(mounted)await review(shot);
    }catch(e){if(mounted)inform(context,e);}finally{if(mounted)setState(()=>busy=false);}
  }
  Future<void> review(Shot shot)async=>Navigator.push(context,MaterialPageRoute(
    builder:(_)=>ReviewPage(shot:shot,root:widget.deck.root)));
  Future<void> camera()async{
    final shot=await Navigator.push<Shot>(context,MaterialPageRoute(builder:(_)=>CapturePage(
      deck:widget.deck,pose:widget.pose,draw:widget.draw,initialMirror:mirror)));
    if(shot!=null&&mounted)await review(shot);
  }
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:Text(widget.pose.name)),
    body:SafeArea(child:Column(children:[
      Expanded(child:InteractiveViewer(child:Transform.flip(flipX:mirror,child:Image.file(File(widget.pose.path),fit:BoxFit.contain)))),
      Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        Row(mainAxisAlignment:MainAxisAlignment.center,children:[
          TextButton.icon(onPressed:()=>setState(()=>mirror=!mirror),icon:const Icon(Icons.flip),label:const Text('Mirror guide')),
          TextButton(onPressed:busy?null:()=>attach(ImageSource.camera),child:const Text('System camera'))]),
        FilledButton.icon(onPressed:busy?null:camera,icon:const Icon(Icons.camera_alt),label:const Text('Take photo with this pose')),
        const SizedBox(height:8),OutlinedButton.icon(onPressed:busy?null:()=>attach(ImageSource.gallery),
          icon:const Icon(Icons.add_photo_alternate),label:const Text('Attach an original from Camera')),
        const SizedBox(height:6),const Text('Guides never appear in the saved original. A recap video is optional afterward.',textAlign:TextAlign.center)
      ]))])));
}
