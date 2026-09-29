import Flutter
import UIKit
import Photos
import Vision
import CoreImage

@main
@objc class AppDelegate: FlutterAppDelegate {
  private let channelName = "space.phenotype.pose/native"
  private let ciContext = CIContext(options: [.cacheIntermediates: false])

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    let controller = window?.rootViewController as! FlutterViewController
    let channel = FlutterMethodChannel(name: channelName, binaryMessenger: controller.binaryMessenger)
    channel.setMethodCallHandler { [weak self] call, result in
      guard let self else { result(FlutterError(code:"APP",message:"App unavailable",details:nil)); return }
      switch call.method {
      case "cameraActive": result(true)
      case "saveMedia":
        guard let args = call.arguments as? [String:Any], let path=args["path"] as? String else {
          result(FlutterError(code:"ARG",message:"Missing path",details:nil)); return
        }
        self.saveMedia(path:path, video:(args["video"] as? Bool) ?? false, result:result)
      case "matte":
        guard let args = call.arguments as? [String:Any],
              let input=args["input"] as? String, let output=args["output"] as? String else {
          result(FlutterError(code:"ARG",message:"Missing matte path",details:nil)); return
        }
        self.qualityMatte(input:input, output:output, result:result)
      case "recap":
        result(FlutterError(code:"RECAP_PENDING",message:"Native recap encoder is not initialized in this build.",details:nil))
      case "cancelRecap": result(true)
      default: result(FlutterMethodNotImplemented)
      }
    }
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  private func qualityMatte(input:String, output:String, result:@escaping FlutterResult) {
    DispatchQueue.global(qos:.userInitiated).async {
      do {
        let request = VNGeneratePersonSegmentationRequest()
        request.qualityLevel = .accurate
        request.outputPixelFormat = kCVPixelFormatType_OneComponent8
        let handler = VNImageRequestHandler(url: URL(fileURLWithPath: input), options: [:])
        try handler.perform([request])
        guard let pixel = request.results?.first?.pixelBuffer else {
          throw NSError(domain:"PoseRoulette",code:1,userInfo:[NSLocalizedDescriptionKey:"Vision found no person mask"])
        }
        var mask = CIImage(cvPixelBuffer: pixel)
        if let filter = CIFilter(name:"CIMaskToAlpha") {
          filter.setValue(mask, forKey:kCIInputImageKey)
          if let out = filter.outputImage { mask = out }
        }
        guard let cg = self.ciContext.createCGImage(mask, from: mask.extent),
              let data = UIImage(cgImage:cg).pngData() else {
          throw NSError(domain:"PoseRoulette",code:2,userInfo:[NSLocalizedDescriptionKey:"Could not encode Vision mask"])
        }
        try data.write(to:URL(fileURLWithPath:output),options:.atomic)
        DispatchQueue.main.async { result(output) }
      } catch {
        DispatchQueue.main.async { result(FlutterError(code:"MATTE",message:error.localizedDescription,details:nil)) }
      }
    }
  }

  private func saveMedia(path:String, video:Bool, result:@escaping FlutterResult) {
    PHPhotoLibrary.requestAuthorization(for: .addOnly) { status in
      guard status == .authorized || status == .limited else {
        result(FlutterError(code:"PHOTO_PERMISSION",message:"Photo-library add permission was not granted.",details:nil)); return
      }
      PHPhotoLibrary.shared().performChanges({
        if video { PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: URL(fileURLWithPath:path)) }
        else { PHAssetChangeRequest.creationRequestForAssetFromImage(atFileURL: URL(fileURLWithPath:path)) }
      }) { ok,error in
        if ok { result(true) }
        else { result(FlutterError(code:"SAVE",message:error?.localizedDescription ?? "Save failed",details:nil)) }
      }
    }
  }
}
