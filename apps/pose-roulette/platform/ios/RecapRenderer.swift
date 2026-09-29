import Foundation
import Flutter
import UIKit
import AVFoundation
import CoreVideo

final class RecapRenderer {
  private let channel: FlutterMethodChannel
  private let lock = NSLock()
  private var cancelled = false

  init(channel: FlutterMethodChannel) { self.channel = channel }

  func cancel() {
    lock.lock(); cancelled = true; lock.unlock()
  }

  private func isCancelled() -> Bool {
    lock.lock(); defer { lock.unlock() }
    return cancelled
  }

  func render(_ args: [String:Any], reply: @escaping FlutterResult) {
    lock.lock(); cancelled = false; lock.unlock()
    DispatchQueue.global(qos: .userInitiated).async {
      do {
        let output = try self.encode(args)
        DispatchQueue.main.async { reply(output) }
      } catch is CancellationError {
        DispatchQueue.main.async {
          reply(FlutterError(code:"RECAP_CANCELLED", message:"Video export cancelled. The original photo was not changed.", details:nil))
        }
      } catch {
        DispatchQueue.main.async {
          reply(FlutterError(code:"RECAP", message:error.localizedDescription, details:nil))
        }
      }
    }
  }

  private func required(_ args:[String:Any], _ key:String) throws -> String {
    guard let value=args[key] as? String else {
      throw NSError(domain:"PoseRoulette",code:10,userInfo:[NSLocalizedDescriptionKey:"Missing \(key)"])
    }
    return value
  }

  private func image(_ path:String) throws -> UIImage {
    guard let image=UIImage(contentsOfFile:path) else {
      throw NSError(domain:"PoseRoulette",code:11,userInfo:[NSLocalizedDescriptionKey:"Could not decode \(URL(fileURLWithPath:path).lastPathComponent)"])
    }
    return image
  }

  private func palette(_ style:String) -> [UIColor] {
    switch style {
    case "editorial":
      return [UIColor(red:246/255,green:241/255,blue:230/255,alpha:1),
              UIColor(red:24/255,green:22/255,blue:21/255,alpha:1),
              UIColor(red:189/255,green:63/255,blue:51/255,alpha:1),
              UIColor(red:35/255,green:34/255,blue:31/255,alpha:1)]
    case "chaos":
      return [UIColor(red:18/255,green:10/255,blue:26/255,alpha:1),.white,
              UIColor(red:214/255,green:1,blue:72/255,alpha:1),
              UIColor(red:1,green:73/255,blue:179/255,alpha:1)]
    default:
      return [UIColor(red:17/255,green:14/255,blue:22/255,alpha:1),.white,
              UIColor(red:218/255,green:177/255,blue:247/255,alpha:1),
              UIColor(red:184/255,green:1,blue:122/255,alpha:1)]
    }
  }

  private func easeOut(_ t:CGFloat) -> CGFloat {
    let x=max(0,min(1,t)); return 1-pow(1-x,4)
  }
  private func smooth(_ t:CGFloat) -> CGFloat {
    let x=max(0,min(1,t)); return x*x*(3-2*x)
  }

  private func containRect(_ image:UIImage, _ box:CGRect, scale:CGFloat=1) -> CGRect {
    let s=image.size
    let k=min(box.width/s.width,box.height/s.height)*scale
    let w=s.width*k,h=s.height*k
    return CGRect(x:box.midX-w/2,y:box.midY-h/2,width:w,height:h)
  }
  private func coverRect(_ image:UIImage, _ box:CGRect, scale:CGFloat=1) -> CGRect {
    let s=image.size
    let k=max(box.width/s.width,box.height/s.height)*scale
    let w=s.width*k,h=s.height*k
    return CGRect(x:box.midX-w/2,y:box.midY-h/2,width:w,height:h)
  }

  private func fill(_ color:UIColor, rect:CGRect) {
    color.setFill(); UIBezierPath(rect:rect).fill()
  }
  private func rounded(_ color:UIColor, rect:CGRect, radius:CGFloat, alpha:CGFloat=1) {
    color.withAlphaComponent(alpha).setFill(); UIBezierPath(roundedRect:rect,cornerRadius:radius).fill()
  }
  private func text(_ value:String, x:CGFloat, y:CGFloat, size:CGFloat, color:UIColor,
                    centered:Bool=false, bold:Bool=true, alpha:CGFloat=1) {
    let font=bold ? UIFont.systemFont(ofSize:size,weight:.heavy) : UIFont.systemFont(ofSize:size,weight:.medium)
    let attrs:[NSAttributedString.Key:Any]=[.font:font,.foregroundColor:color.withAlphaComponent(alpha)]
    if centered {
      let width=(value as NSString).size(withAttributes:attrs).width
      (value as NSString).draw(at:CGPoint(x:x-width/2,y:y),withAttributes:attrs)
    } else {
      (value as NSString).draw(at:CGPoint(x:x,y:y),withAttributes:attrs)
    }
  }

  private func sticker(_ value:String, cx:CGFloat, cy:CGFloat, colors:[UIColor], rotation:CGFloat=0, scale:CGFloat=1) {
    guard let ctx=UIGraphicsGetCurrentContext() else { return }
    let font=UIFont.systemFont(ofSize:28*scale,weight:.black)
    let attrs:[NSAttributedString.Key:Any]=[.font:font,.foregroundColor:colors[0]]
    let tw=(value as NSString).size(withAttributes:attrs).width
    let w=tw+38*scale,h=54*scale
    ctx.saveGState();ctx.translateBy(x:cx,y:cy);ctx.rotate(by:rotation * .pi/180)
    rounded(colors[2],rect:CGRect(x:-w/2,y:-h/2,width:w,height:h),radius:18*scale)
    (value as NSString).draw(at:CGPoint(x:-tw/2,y:-font.lineHeight/2+3*scale),withAttributes:attrs)
    ctx.restoreGState()
  }

  private func drawContain(_ image:UIImage, box:CGRect, alpha:CGFloat=1, scale:CGFloat=1) {
    image.draw(in:containRect(image,box,scale:scale),blendMode:.normal,alpha:alpha)
  }
  private func drawCover(_ image:UIImage, box:CGRect, alpha:CGFloat=1, scale:CGFloat=1) {
    guard let ctx=UIGraphicsGetCurrentContext() else { return }
    ctx.saveGState();ctx.clip(to:box)
    image.draw(in:coverRect(image,box,scale:scale),blendMode:.normal,alpha:alpha)
    ctx.restoreGState()
  }

  private func drawFrame(_ ctx:CGContext, wheel:UIImage, reference:UIImage, photo:UIImage,
                         frame:Int, fps:Int, start:Double, travel:Double, style:String,
                         width:CGFloat, height:CGFloat) {
    ctx.saveGState()
    ctx.translateBy(x:0,y:height);ctx.scaleBy(x:1,y:-1)
    UIGraphicsPushContext(ctx)
    defer { UIGraphicsPopContext(); ctx.restoreGState() }

    let t=CGFloat(frame)/CGFloat(fps)
    let colors=palette(style)
    fill(colors[0],rect:CGRect(x:0,y:0,width:width,height:height))

    for i in 0...5 {
      let yy=(CGFloat(i)*260+t*95).truncatingRemainder(dividingBy:1500)-100
      rounded(colors[2],rect:CGRect(x:-80,y:yy,width:width+160,height:70),radius:35,alpha:0.07)
    }

    if t < 2.55 {
      let p=max(0,min(1,t/2.55))
      text("POSE ROULETTE",x:42,y:50,size:24,color:colors[1],alpha:0.78)
      text(style=="chaos" ? "WHO GETS PICKED?" : "SPIN / MATCH / SHOOT",x:42,y:91,size:15,color:colors[1],bold:false,alpha:0.48)
      let cx=width/2,cy=height*0.48,size:CGFloat=560
      for g in stride(from:3,through:1,by:-1) {
        let gp=max(0,p-CGFloat(g)*0.012)
        let a=CGFloat(start+travel*Double(easeOut(gp)))
        ctx.saveGState();ctx.translateBy(x:cx,y:cy);ctx.rotate(by:a)
        drawContain(wheel,box:CGRect(x:-size/2,y:-size/2,width:size,height:size),alpha:0.10)
        ctx.restoreGState()
      }
      let a=CGFloat(start+travel*Double(easeOut(p)))
      let pulse=1+0.035*sin(p*18)
      ctx.saveGState();ctx.translateBy(x:cx,y:cy);ctx.rotate(by:a);ctx.scaleBy(x:pulse,y:pulse)
      drawContain(wheel,box:CGRect(x:-size/2,y:-size/2,width:size,height:size))
      ctx.restoreGState()
      let pointer=UIBezierPath();pointer.move(to:CGPoint(x:cx,y:cy-size/2-8));pointer.addLine(to:CGPoint(x:cx-24,y:cy-size/2-48));pointer.addLine(to:CGPoint(x:cx+24,y:cy-size/2-48));pointer.close()
      colors[3].setFill();pointer.fill()
      if t>0.35 {
        sticker(style=="editorial" ? "random is the brief" : "LET IT PICK",cx:width/2,cy:height*0.82,colors:colors,rotation:-3+sin(t*5)*2,scale:0.9)
      }
    } else if t < 3.55 {
      let p=smooth((t-2.55)/1.0)
      if t<2.68 { fill(.white.withAlphaComponent(max(0,min(0.82,(2.68-t)/0.13*0.82))),rect:CGRect(x:0,y:0,width:width,height:height)) }
      let box=CGRect(x:58,y:128,width:width-116,height:height-246)
      let sc=0.84+0.16*p
      ctx.saveGState();ctx.translateBy(x:width/2,y:height/2);ctx.scaleBy(x:sc,y:sc);ctx.translateBy(x:-width/2,y:-height/2)
      rounded(colors[1],rect:box.insetBy(dx:-10,dy:-10),radius:34,alpha:0.14)
      drawContain(reference,box:box)
      ctx.restoreGState()
      sticker(style=="editorial" ? "SELECTED" : "POSE LOCKED",cx:width/2,cy:112,colors:colors,rotation:style=="chaos" ? 5 : -2)
      text("match the shape, then make it yours",x:width/2,y:height-78,size:18,color:colors[1],centered:true,bold:false,alpha:0.78)
    } else if t < 3.82 {
      let p=(t-3.55)/0.27
      let shift=p*width*1.4
      drawCover(reference,box:CGRect(x:-shift,y:0,width:width,height:height),scale:1.03)
      drawCover(photo,box:CGRect(x:width-shift,y:0,width:width,height:height),scale:1.02)
      for i in 0...4 {
        fill(colors[2].withAlphaComponent((1-p)*0.47),rect:CGRect(x:0,y:height*(0.13+CGFloat(i)*0.17),width:width,height:height*0.012))
      }
    } else {
      let p=max(0,min(1,(t-3.82)/(6.40-3.82)))
      drawCover(photo,box:CGRect(x:0,y:0,width:width,height:height),scale:1+0.055*smooth(p))
      for i in 0...12 {
        let a=CGFloat(i)/12
        fill(UIColor.black.withAlphaComponent(0.012+0.12*a*a),rect:CGRect(x:0,y:height*(0.44+a*0.56),width:width,height:height*0.06))
      }
      let pop=smooth(min(1,p*5))
      sticker(style=="editorial" ? "FINAL FRAME" : style=="chaos" ? "NAILED IT" : "SHOT ✓",cx:126,cy:height-176,colors:colors,rotation:-4,scale:0.82+0.18*pop)
      text("POSE ROULETTE",x:42,y:height-94,size:20,color:.white,alpha:0.88)
      text("spin → pose → photo",x:42,y:height-60,size:14,color:.white,bold:false,alpha:0.63)
      if style=="chaos" {
        colors[3].setFill()
        for i in 0...8 {
          let xx=(width*0.12+CGFloat(i)*73).truncatingRemainder(dividingBy:width)
          let yy=(height*0.16+CGFloat(i)*119).truncatingRemainder(dividingBy:height)
          UIBezierPath(ovalIn:CGRect(x:xx-4-CGFloat(i%3)*2,y:yy-4-CGFloat(i%3)*2,width:8+CGFloat(i%3)*4,height:8+CGFloat(i%3)*4)).fill()
        }
      }
    }
  }

  private func encode(_ args:[String:Any]) throws -> String {
    let wheelPath=try required(args,"wheel"),referencePath=try required(args,"reference"),photoPath=try required(args,"photo"),output=try required(args,"output")
    let start=(args["start"] as? NSNumber)?.doubleValue ?? 0
    let travel=(args["travel"] as? NSNumber)?.doubleValue ?? Double.pi*10
    let style=args["style"] as? String ?? "snap"
    let wheel=try image(wheelPath),reference=try image(referencePath),photo=try image(photoPath)

    let url=URL(fileURLWithPath:output);try? FileManager.default.removeItem(at:url)
    let width=720,height=1280,fps:Int32=24,frames=Int(6.4*Double(fps))
    let writer=try AVAssetWriter(outputURL:url,fileType:.mp4)
    let settings:[String:Any]=[
      AVVideoCodecKey:AVVideoCodecType.h264,
      AVVideoWidthKey:width,AVVideoHeightKey:height,
      AVVideoCompressionPropertiesKey:[
        AVVideoAverageBitRateKey:4_500_000,
        AVVideoProfileLevelKey:AVVideoProfileLevelH264HighAutoLevel,
        AVVideoMaxKeyFrameIntervalKey:Int(fps)
      ]
    ]
    let input=AVAssetWriterInput(mediaType:.video,outputSettings:settings)
    input.expectsMediaDataInRealTime=false
    let attrs:[String:Any]=[
      kCVPixelBufferPixelFormatTypeKey as String:kCVPixelFormatType_32BGRA,
      kCVPixelBufferWidthKey as String:width,
      kCVPixelBufferHeightKey as String:height,
      kCVPixelBufferIOSurfacePropertiesKey as String:[:]
    ]
    let adaptor=AVAssetWriterInputPixelBufferAdaptor(assetWriterInput:input,sourcePixelBufferAttributes:attrs)
    guard writer.canAdd(input) else { throw NSError(domain:"PoseRoulette",code:12,userInfo:[NSLocalizedDescriptionKey:"Video writer rejected input"]) }
    writer.add(input)
    guard writer.startWriting() else { throw writer.error ?? NSError(domain:"PoseRoulette",code:13,userInfo:[NSLocalizedDescriptionKey:"Could not start video writer"]) }
    writer.startSession(atSourceTime:.zero)

    for frame in 0..<frames {
      if isCancelled() { throw CancellationError() }
      while !input.isReadyForMoreMediaData {
        if isCancelled() { throw CancellationError() }
        Thread.sleep(forTimeInterval:0.002)
      }
      guard let pool=adaptor.pixelBufferPool else { throw NSError(domain:"PoseRoulette",code:14,userInfo:[NSLocalizedDescriptionKey:"Video pixel-buffer pool unavailable"]) }
      var maybe:CVPixelBuffer?
      guard CVPixelBufferPoolCreatePixelBuffer(nil,pool,&maybe)==kCVReturnSuccess,let buffer=maybe else {
        throw NSError(domain:"PoseRoulette",code:15,userInfo:[NSLocalizedDescriptionKey:"Could not allocate video frame"])
      }
      CVPixelBufferLockBaseAddress(buffer,[])
      guard let base=CVPixelBufferGetBaseAddress(buffer) else { CVPixelBufferUnlockBaseAddress(buffer,[]);throw NSError(domain:"PoseRoulette",code:16,userInfo:[NSLocalizedDescriptionKey:"Could not access video frame"]) }
      let bytes=CVPixelBufferGetBytesPerRow(buffer)
      guard let ctx=CGContext(data:base,width:width,height:height,bitsPerComponent:8,bytesPerRow:bytes,space:CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo:CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue) else {
        CVPixelBufferUnlockBaseAddress(buffer,[]);throw NSError(domain:"PoseRoulette",code:17,userInfo:[NSLocalizedDescriptionKey:"Could not create video canvas"])
      }
      drawFrame(ctx,wheel:wheel,reference:reference,photo:photo,frame:frame,fps:Int(fps),start:start,travel:travel,style:style,width:CGFloat(width),height:CGFloat(height))
      CVPixelBufferUnlockBaseAddress(buffer,[])
      let time=CMTime(value:Int64(frame),timescale:fps)
      if !adaptor.append(buffer,withPresentationTime:time) {
        throw writer.error ?? NSError(domain:"PoseRoulette",code:18,userInfo:[NSLocalizedDescriptionKey:"Could not append video frame"])
      }
      if frame % 12 == 0 {
        let progress=Double(frame)/Double(frames)
        DispatchQueue.main.async { self.channel.invokeMethod("recapProgress",arguments:progress) }
      }
    }
    input.markAsFinished()
    let semaphore=DispatchSemaphore(value:0)
    writer.finishWriting { semaphore.signal() }
    semaphore.wait()
    if isCancelled() { try? FileManager.default.removeItem(at:url);throw CancellationError() }
    guard writer.status == .completed else {
      throw writer.error ?? NSError(domain:"PoseRoulette",code:19,userInfo:[NSLocalizedDescriptionKey:"Video writer did not finish"])
    }
    DispatchQueue.main.async { self.channel.invokeMethod("recapProgress",arguments:1.0) }
    return output
  }
}
