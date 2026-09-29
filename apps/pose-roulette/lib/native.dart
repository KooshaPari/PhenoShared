import 'dart:async';
import 'package:flutter/services.dart';

class Native {
  static const channel = MethodChannel('space.phenotype.pose/native');
  static final events = StreamController<MethodCall>.broadcast();
  static void initialize() {
    channel.setMethodCallHandler((call) async { events.add(call); });
  }
  static Future<String> matte(String input, String output, {String quality='quality'}) async {
    final result = await channel.invokeMethod<String>('matte', {'input':input,'output':output,'quality':quality});
    if(result == null) throw StateError('The native person-mask request returned no image.');
    return result;
  }
  static Future<void> saveMedia(String path, {bool video = false}) async {
    final result = await channel.invokeMethod<bool>('saveMedia',{'path':path,'video':video});
    if(result != true) throw StateError('The system did not confirm saving this file.');
  }
  static Future<String> recap(Map<String,dynamic> input) async {
    final result = await channel.invokeMethod<String>('recap',input);
    if(result == null) throw StateError('The encoder returned no video.');
    return result;
  }
  static Future<void> cancelRecap() async => channel.invokeMethod<void>('cancelRecap');
  static Future<void> cameraActive(bool active) async => channel.invokeMethod<void>('cameraActive',{'active':active});
}
