import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';
import 'domain.dart';
import 'native.dart';

class ReviewPage extends StatefulWidget{
  const ReviewPage({super.key,required this.shot,required this.root});
  final Shot shot;final String root;
  @override State<ReviewPage> createState()=>_ReviewPageState();
}
class _ReviewPageState extends State<ReviewPage> with WidgetsBindingObserver{
  bool busy=false,encoding=false;double progress=0;String? video;String details='Original kept in this app.';
  StreamSubscription<MethodCall>? subscription;
  @override void initState(){super.initState();WidgetsBinding.instance.addObserver(this);
    subscription=Native.events.stream.listen((event){
      if(event.method=='recapProgress'&&mounted&&encoding)setState(()=>progress=(event.arguments as num).toDouble());
    });inspect();}
  Future<void> inspect()async{
    final size=await File(widget.shot.path).length();
    if(mounted)setState(()=>details='Original · ${(size/1048576).toStringAsFixed(1)} MB · kept in this app');
  }
  void notice(Object text){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('$text')));}
  @override void dispose(){subscription?.cancel();WidgetsBinding.instance.removeObserver(this);if(encoding)Native.cancelRecap();super.dispose();}
  @override void didChangeAppLifecycleState(AppLifecycleState state){
    if(state==AppLifecycleState.paused&&encoding){Native.cancelRecap();notice('Video export cancelled when the app went into the background. The original is safe.');}
  }
  Future<void> save(String path,{bool isVideo=false})async{
    setState(()=>busy=true);
    try{await Native.saveMedia(path,video:isVideo);notice(isVideo?'Video saved separately to your photo library.':'Original photo saved to your photo library.');}
    catch(e){notice(e);}finally{if(mounted)setState(()=>busy=false);}
  }
  Future<void> share(String path)async{
    try{await SharePlus.instance.share(ShareParams(files:[XFile(path)],title:'Pose Roulette'));}catch(e){notice(e);}
  }
  Future<void> createRecap()async{
    final draw=widget.shot.draw;if(draw==null||encoding)return;
    setState((){encoding=true;progress=0;});
    try{
      if(!await File(draw.wheelPath).exists())throw StateError('The original wheel snapshot is unavailable; a different spin will not be substituted.');
      final path=await Native.recap({'wheel':draw.wheelPath,'reference':widget.shot.referencePath,
        'photo':widget.shot.path,'start':draw.start,'travel':draw.travel,'target':draw.target,
        'output':'${widget.root}/recap-${uniqueId()}.mp4'});
      if(mounted)setState(()=>video=path);
    }catch(e){notice(e);}finally{if(mounted)setState(()=>encoding=false);}
  }
  @override Widget build(BuildContext context)=>PopScope(canPop:!encoding,child:Scaffold(
    appBar:AppBar(title:const Text('Your photo')),
    body:SafeArea(child:Column(children:[
      Expanded(child:InteractiveViewer(child:Image.file(File(widget.shot.path),fit:BoxFit.contain,cacheWidth:1600))),
      ConstrainedBox(constraints:BoxConstraints(maxHeight:MediaQuery.sizeOf(context).height*.47),child:SingleChildScrollView(
        padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
          Text(widget.shot.poseName,style:Theme.of(context).textTheme.titleMedium),Text(details),
          const SizedBox(height:10),Row(children:[
            Expanded(child:FilledButton.icon(onPressed:busy?null:()=>save(widget.shot.path),icon:const Icon(Icons.save_alt),label:const Text('Save original'))),
            const SizedBox(width:8),IconButton(tooltip:'Share original',onPressed:()=>share(widget.shot.path),icon:const Icon(Icons.ios_share))]),
          ExpansionTile(tilePadding:EdgeInsets.zero,title:const Text('Optional: spin → pose → photo video'),children:[
            const Text('A separate 6.4-second, 720 × 1280 H.264 MP4. Replays the saved draw, shows its reference, then cuts to this photo. No microphone. Your original is not resized or overwritten.'),
            const SizedBox(height:10),
            if(widget.shot.draw==null)const Text('This reference was not selected by a recorded spin. No replacement spin will be invented.'),
            if(encoding)...[LinearProgressIndicator(value:progress),Text('${(progress*100).round()}%'),
              TextButton(onPressed:Native.cancelRecap,child:const Text('Cancel video export'))]
            else FilledButton.tonal(onPressed:widget.shot.draw==null?null:createRecap,child:Text(video==null?'Make recap video':'Make another recap')),
            if(video!=null)...[const SizedBox(height:8),const Text('MP4 ready. Save or share it as a second file.'),
              Wrap(spacing:8,children:[OutlinedButton(onPressed:busy?null:()=>save(video!,isVideo:true),child:const Text('Save video')),
                OutlinedButton.icon(onPressed:()=>share(video!),icon:const Icon(Icons.ios_share),label:const Text('Share video'))])]
          ])
        ])))
    ]))));
}
