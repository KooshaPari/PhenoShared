from pathlib import Path
import shutil, subprocess, sys, re, os

src=Path(__file__).resolve().parents[1]
target=Path(sys.argv[1]).resolve()
if target.exists(): shutil.rmtree(target)
subprocess.run([
    "flutter","create","--platforms=android,ios","--org","space.phenotype",
    "--project-name","pose_roulette","--empty",str(target)
],check=True)

shutil.copy2(src/"pubspec.yaml",target/"pubspec.yaml")
shutil.rmtree(target/"lib")
shutil.copytree(src/"lib",target/"lib")
if (src/"test").exists():
    shutil.rmtree(target/"test",ignore_errors=True)
    shutil.copytree(src/"test",target/"test")

# Android: Pixel target, minSdk 24 for subject segmentation, modern camera + ML Kit.
gradle=target/"android/app/build.gradle.kts"
g=gradle.read_text()
g=re.sub(r"minSdk\s*=\s*flutter\.minSdkVersion","minSdk = 24",g)
g=g.replace('applicationId = "space.phenotype.pose_roulette"','applicationId = "space.phenotype.pose"')
g=g.replace('namespace = "space.phenotype.pose_roulette"','namespace = "space.phenotype.pose"')
if 'play-services-mlkit-subject-segmentation' not in g:
    g += '\n\ndependencies {\n    implementation("com.google.android.gms:play-services-mlkit-subject-segmentation:16.0.0-beta1")\n}\n'
gradle.write_text(g)
manifest=target/"android/app/src/main/AndroidManifest.xml"
m=manifest.read_text()
m=m.replace("<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">",
'''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.CAMERA"/>
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES"/>
    <uses-permission android:name="android.permission.READ_MEDIA_VIDEO"/>''')
m=m.replace('<application\n        android:label="pose_roulette"', '<application\n        android:label="Pose Roulette"')
m=m.replace("</application>",'''        <meta-data
            android:name="com.google.mlkit.vision.DEPENDENCIES"
            android:value="subject_segment" />
    </application>''')
manifest.write_text(m)

# iOS: direct camera and photo-library save, iOS 16+ to keep the native stack simple.
plist=target/"ios/Runner/Info.plist"
p=plist.read_text()
insert='''\n\t<key>NSCameraUsageDescription</key>\n\t<string>Pose Roulette uses the camera to line you up with the selected pose and take your photo.</string>\n\t<key>NSPhotoLibraryUsageDescription</key>\n\t<string>Pose Roulette lets you attach an original from your photo library.</string>\n\t<key>NSPhotoLibraryAddUsageDescription</key>\n\t<string>Pose Roulette saves the clean photo and optional recap when you ask.</string>\n'''
p=p.replace("\n</dict>\n</plist>",insert+"\n</dict>\n</plist>")
plist.write_text(p)
pbx=target/"ios/Runner.xcodeproj/project.pbxproj"
x=pbx.read_text().replace("PRODUCT_BUNDLE_IDENTIFIER = space.phenotype.poseRoulette;","PRODUCT_BUNDLE_IDENTIFIER = space.phenotype.pose;")
x=re.sub(r"IPHONEOS_DEPLOYMENT_TARGET = [0-9.]+;","IPHONEOS_DEPLOYMENT_TARGET = 16.0;",x)
pbx.write_text(x)

# Podfile platform target may be commented in a fresh Flutter project.
pod=target/"ios/Podfile"
if pod.exists():
    q=pod.read_text()
    q=re.sub(r"# platform :ios, '[^']+'","platform :ios, '16.0'",q)
    pod.write_text(q)

# Native bridge files are copied after flutter create so generation cannot overwrite them.
android_bridge=src/"platform/android/MainActivity.kt"
if android_bridge.exists():
    dest=target/"android/app/src/main/kotlin/space/phenotype/pose/MainActivity.kt"
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Remove generated package tree to avoid a second MainActivity.
    old=target/"android/app/src/main/kotlin/space/phenotype/pose_roulette/MainActivity.kt"
    if old.exists(): old.unlink()
    shutil.copy2(android_bridge,dest)
    recap=src/"platform/android/RecapRenderer.kt"
    if recap.exists(): shutil.copy2(recap,dest.parent/"RecapRenderer.kt")
ios_bridge=src/"platform/ios/AppDelegate.swift"
if ios_bridge.exists():
    shutil.copy2(ios_bridge,target/"ios/Runner/AppDelegate.swift")
    recap=src/"platform/ios/RecapRenderer.swift"
    if recap.exists(): shutil.copy2(recap,target/"ios/Runner/RecapRenderer.swift")
print(target)
