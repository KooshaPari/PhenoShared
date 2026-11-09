import 'dart:math';
import 'domain.dart';

class FitResult {
  const FitResult({required this.score,required this.shape,required this.framing,
    required this.hint,required this.perJoint,required this.visible,required this.total});
  final int score,shape,framing,visible,total;
  final String hint;
  final Map<String,double> perJoint;
}

const fitBones=<List<String>>[
  ['leftShoulder','rightShoulder'],['leftShoulder','leftElbow'],['leftElbow','leftWrist'],
  ['rightShoulder','rightElbow'],['rightElbow','rightWrist'],['leftShoulder','leftHip'],
  ['rightShoulder','rightHip'],['leftHip','rightHip'],['leftHip','leftKnee'],['leftKnee','leftAnkle'],
  ['rightHip','rightKnee'],['rightKnee','rightAnkle']
];

const _important=<String>[
  'nose','leftShoulder','rightShoulder','leftElbow','rightElbow','leftWrist','rightWrist',
  'leftHip','rightHip','leftKnee','rightKnee','leftAnkle','rightAnkle'
];

String _friendly(String key)=>key.replaceAllMapped(RegExp(r'([A-Z])'),(m)=>' ${m.group(1)!.toLowerCase()}');

Map<String,PosePoint> transformReference(Map<String,PosePoint> source,{
  required double x,required double y,required double scale,required double angle,required bool mirror,
}) {
  final out=<String,PosePoint>{},cs=cos(angle),sn=sin(angle);
  for(final e in source.entries){
    var px=e.value.x-.5,py=e.value.y-.5;
    if(mirror)px=-px;
    px*=scale;py*=scale;
    final rx=px*cs-py*sn,ry=px*sn+py*cs;
    out[e.key]=PosePoint(.5+x+rx,.5+y+ry,e.value.z,e.value.confidence);
  }
  return out;
}

PosePoint? _center(Map<String,PosePoint> p,String a,String b){
  final x=p[a],y=p[b];if(x==null||y==null||x.confidence<.35||y.confidence<.35)return null;
  return PosePoint((x.x+y.x)/2,(x.y+y.y)/2,(x.z+y.z)/2,min(x.confidence,y.confidence));
}
double _dist(PosePoint a,PosePoint b)=>sqrt(pow(a.x-b.x,2)+pow(a.y-b.y,2));
double _clamp01(double x)=>x.clamp(0.0,1.0);
Map<String,PosePoint>? _local(Map<String,PosePoint> p){
  final hip=_center(p,'leftHip','rightHip'),shoulder=_center(p,'leftShoulder','rightShoulder');
  if(hip==null||shoulder==null)return null;
  final torso=max(.04,_dist(hip,shoulder));
  return {for(final e in p.entries) if(e.value.confidence>.35)
    e.key:PosePoint((e.value.x-hip.x)/torso,(e.value.y-hip.y)/torso,e.value.z/torso,e.value.confidence)};
}
RectStats? _stats(Map<String,PosePoint> p){
  final v=p.values.where((q)=>q.confidence>.35).toList();if(v.length<4)return null;
  final minX=v.map((e)=>e.x).reduce(min),maxX=v.map((e)=>e.x).reduce(max),
    minY=v.map((e)=>e.y).reduce(min),maxY=v.map((e)=>e.y).reduce(max);
  return RectStats((minX+maxX)/2,(minY+maxY)/2,max(.01,maxX-minX),max(.01,maxY-minY));
}
class RectStats{const RectStats(this.cx,this.cy,this.w,this.h);final double cx,cy,w,h;}

FitResult comparePoses(Map<String,PosePoint> target,Map<String,PosePoint> live){
  final a=_local(target),b=_local(live),sa=_stats(target),sb=_stats(live);
  if(a==null||b==null||sa==null||sb==null)return const FitResult(
    score:0,shape:0,framing:0,hint:'Step fully into frame — shoulders and hips are needed.',perJoint:{},visible:0,total:13);
  var weighted=0.0,weights=0.0;final per=<String,double>{};
  String worst='';double worstErr=-1;
  for(final key in _important){
    final x=a[key],y=b[key];if(x==null||y==null)continue;
    final confidence=min(target[key]!.confidence,live[key]!.confidence);
    if(confidence<.4)continue;
    final err=sqrt(pow(x.x-y.x,2)+pow(x.y-y.y,2))*.72 + (x.z-y.z).abs()*.10;
    final jointScore=_clamp01(1-err/1.15);
    per[key]=jointScore;
    final weight=(key.contains('Shoulder')||key.contains('Hip'))?1.3:1.0;
    weighted+=jointScore*confidence*weight;weights+=confidence*weight;
    if(err>worstErr){worstErr=err;worst=key;}
  }
  final visible=per.length;
  if(visible<6)return FitResult(score:0,shape:0,framing:0,
    hint:'Show more of your body — at least shoulders, hips and limbs.',perJoint:per,visible:visible,total:_important.length);
  final shape=(100*(weighted/max(weights,.001))).round().clamp(0,100);
  final centerError=sqrt(pow(sa.cx-sb.cx,2)+pow(sa.cy-sb.cy,2));
  final sizeRatio=((sb.h/sa.h)-1).abs();
  final framing=(100*_clamp01(1-centerError/0.28-sizeRatio/0.75)).round().clamp(0,100);
  final score=(shape*.78+framing*.22).round().clamp(0,100);

  String hint='Hold it — you are lined up.';
  final dx=sa.cx-sb.cx,dy=sa.cy-sb.cy,ratio=sb.h/sa.h;
  if(dx.abs()>.055) hint=dx>0?'Move right →':'← Move left';
  else if(dy.abs()>.065) hint=dy>0?'Move down a little ↓':'Move up a little ↑';
  else if(ratio<.82) hint='Step closer';
  else if(ratio>1.20) hint='Step back';
  else if(worst.isNotEmpty&&worstErr>.22){
    final t=target[worst]!,l=live[worst]!;
    final ddx=t.x-l.x,ddy=t.y-l.y;
    final part=_friendly(worst);
    if(ddx.abs()>ddy.abs())hint=ddx>0?'Move your $part right →':'Move your $part left ←';
    else hint=ddy>0?'Lower your $part ↓':'Raise your $part ↑';
  } else if(score<85) hint='Fine-tune the outline';
  return FitResult(score:score,shape:shape,framing:framing,hint:hint,perJoint:per,visible:visible,total:_important.length);
}
