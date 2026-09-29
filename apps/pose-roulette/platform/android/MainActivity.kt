package space.phenotype.pose

import android.content.ContentValues
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.view.KeyEvent
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.segmentation.subject.SubjectSegmentation
import com.google.mlkit.vision.segmentation.subject.SubjectSegmenterOptions
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream

class MainActivity: FlutterActivity() {
    private val channelName = "space.phenotype.pose/native"
    private var channel: MethodChannel? = null
    private var cameraActive = false

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
        channel!!.setMethodCallHandler { call, result ->
            when (call.method) {
                "cameraActive" -> {
                    cameraActive = call.argument<Boolean>("active") ?: false
                    result.success(true)
                }
                "saveMedia" -> {
                    val path = call.argument<String>("path")
                    val video = call.argument<Boolean>("video") ?: false
                    if (path == null) result.error("ARG", "Missing path", null)
                    else try { save(path, video); result.success(true) }
                    catch (e: Exception) { result.error("SAVE", e.message, null) }
                }
                "matte" -> {
                    val input = call.argument<String>("input")
                    val output = call.argument<String>("output")
                    if (input == null || output == null) result.error("ARG","Missing matte path",null)
                    else qualityMatte(input, output, result)
                }
                "recap" -> result.error("RECAP_PENDING", "Native recap encoder is not initialized in this build.", null)
                "cancelRecap" -> result.success(true)
                else -> result.notImplemented()
            }
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (cameraActive && (keyCode == KeyEvent.KEYCODE_VOLUME_UP || keyCode == KeyEvent.KEYCODE_VOLUME_DOWN)) {
            channel?.invokeMethod("shutter", null)
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    private fun qualityMatte(input: String, output: String, reply: MethodChannel.Result) {
        try {
            val options = SubjectSegmenterOptions.Builder()
                .enableForegroundBitmap()
                .build()
            val segmenter = SubjectSegmentation.getClient(options)
            val image = InputImage.fromFilePath(this, Uri.fromFile(File(input)))
            segmenter.process(image)
                .addOnSuccessListener { segmented ->
                    try {
                        val bitmap = segmented.foregroundBitmap
                            ?: throw IllegalStateException("Subject segmentation returned no bitmap")
                        FileOutputStream(output).use { stream ->
                            if (!bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, stream)) {
                                throw IllegalStateException("Could not encode subject mask")
                            }
                        }
                        reply.success(output)
                    } catch (e: Exception) {
                        reply.error("MATTE", e.message, null)
                    } finally {
                        segmenter.close()
                    }
                }
                .addOnFailureListener { e ->
                    segmenter.close()
                    reply.error("MATTE", e.message, null)
                }
        } catch (e: Exception) {
            reply.error("MATTE", e.message, null)
        }
    }

    private fun save(path: String, video: Boolean) {
        val file = File(path)
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, file.name)
            put(MediaStore.MediaColumns.MIME_TYPE, if (video) "video/mp4" else if (file.extension.lowercase()=="png") "image/png" else "image/jpeg")
            if (Build.VERSION.SDK_INT >= 29) {
                put(MediaStore.MediaColumns.RELATIVE_PATH, if (video) "Movies/Pose Roulette" else "Pictures/Pose Roulette")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
        }
        val collection = if (video) MediaStore.Video.Media.EXTERNAL_CONTENT_URI else MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        val uri = contentResolver.insert(collection, values) ?: error("Could not create MediaStore item")
        contentResolver.openOutputStream(uri)?.use { out -> FileInputStream(file).use { it.copyTo(out) } } ?: error("Could not open MediaStore output")
        if (Build.VERSION.SDK_INT >= 29) {
            values.clear(); values.put(MediaStore.MediaColumns.IS_PENDING, 0); contentResolver.update(uri, values, null, null)
        }
    }
}
