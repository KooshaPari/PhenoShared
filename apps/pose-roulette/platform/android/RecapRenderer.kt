package space.phenotype.pose

import android.graphics.*
import android.media.*
import android.os.Handler
import android.os.Looper
import android.view.Surface
import io.flutter.plugin.common.MethodChannel
import java.io.File
import kotlin.math.*

class RecapRenderer(private val channel: MethodChannel) {
    @Volatile private var cancelled = false
    fun cancel() { cancelled = true }

    fun render(args: Map<String, Any?>, reply: MethodChannel.Result) {
        cancelled = false
        Thread {
            try {
                val wheel = required(args, "wheel")
                val reference = required(args, "reference")
                val photo = required(args, "photo")
                val output = required(args, "output")
                val start = (args["start"] as? Number)?.toDouble() ?: 0.0
                val travel = (args["travel"] as? Number)?.toDouble() ?: (Math.PI * 10)
                val style = args["style"] as? String ?: "snap"
                encode(wheel, reference, photo, output, start, travel, style)
                main { reply.success(output) }
            } catch (e: java.util.concurrent.CancellationException) {
                main { reply.error("RECAP_CANCELLED", "Video export cancelled. The photo was not changed.", null) }
            } catch (e: Exception) {
                main { reply.error("RECAP", e.message ?: "Video export failed", null) }
            }
        }.start()
    }

    private fun required(args: Map<String, Any?>, key: String) =
        args[key] as? String ?: throw IllegalArgumentException("Missing $key")

    private fun main(block: () -> Unit) = Handler(Looper.getMainLooper()).post(block)

    private fun decode(path: String, maxSide: Int = 1800): Bitmap {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(path, bounds)
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / sample > maxSide * 2) sample *= 2
        val opts = BitmapFactory.Options().apply {
            inSampleSize = sample
            inPreferredConfig = Bitmap.Config.ARGB_8888
        }
        val bitmap = BitmapFactory.decodeFile(path, opts)
            ?: throw IllegalArgumentException("Could not decode ${File(path).name}")
        if (max(bitmap.width, bitmap.height) <= maxSide) return bitmap
        val k = maxSide.toFloat() / max(bitmap.width, bitmap.height)
        val scaled = Bitmap.createScaledBitmap(bitmap, max(1, (bitmap.width*k).roundToInt()), max(1, (bitmap.height*k).roundToInt()), true)
        if (scaled !== bitmap) bitmap.recycle()
        return scaled
    }

    private fun palette(style: String): IntArray = when(style) {
        "editorial" -> intArrayOf(Color.rgb(246,241,230), Color.rgb(24,22,21), Color.rgb(189,63,51), Color.rgb(35,34,31))
        "chaos" -> intArrayOf(Color.rgb(18,10,26), Color.WHITE, Color.rgb(214,255,72), Color.rgb(255,73,179))
        else -> intArrayOf(Color.rgb(17,14,22), Color.WHITE, Color.rgb(218,177,247), Color.rgb(184,255,122))
    }

    private fun easeOut(t: Float): Float = 1f - (1f-t.coerceIn(0f,1f)).pow(4)
    private fun smooth(t: Float): Float { val x=t.coerceIn(0f,1f); return x*x*(3f-2f*x) }

    private fun drawContain(c: Canvas, bmp: Bitmap, box: RectF, paint: Paint, scale: Float = 1f) {
        val k = min(box.width()/bmp.width, box.height()/bmp.height)*scale
        val w=bmp.width*k; val h=bmp.height*k
        val dst=RectF(box.centerX()-w/2, box.centerY()-h/2, box.centerX()+w/2, box.centerY()+h/2)
        c.drawBitmap(bmp,null,dst,paint)
    }
    private fun drawCover(c: Canvas, bmp: Bitmap, box: RectF, paint: Paint, scale: Float = 1f) {
        val k = max(box.width()/bmp.width, box.height()/bmp.height)*scale
        val w=bmp.width*k; val h=bmp.height*k
        val dst=RectF(box.centerX()-w/2, box.centerY()-h/2, box.centerX()+w/2, box.centerY()+h/2)
        c.save(); c.clipRect(box); c.drawBitmap(bmp,null,dst,paint); c.restore()
    }
    private fun rounded(c: Canvas, rect: RectF, radius: Float, color: Int, alpha: Int = 255) {
        c.drawRoundRect(rect,radius,radius,Paint(Paint.ANTI_ALIAS_FLAG).apply{this.color=color;this.alpha=alpha})
    }
    private fun text(c: Canvas, value: String, x: Float, y: Float, size: Float, color: Int, align: Paint.Align = Paint.Align.LEFT, bold: Boolean = true, alpha: Int = 255) {
        c.drawText(value,x,y,Paint(Paint.ANTI_ALIAS_FLAG).apply{
            textSize=size;this.color=color;textAlign=align;this.alpha=alpha
            typeface=Typeface.create("sans-serif",if(bold)Typeface.BOLD else Typeface.NORMAL)
        })
    }
    private fun sticker(c: Canvas, value:String, cx:Float, cy:Float, colors:IntArray, rotation:Float=0f, scale:Float=1f){
        val p=Paint(Paint.ANTI_ALIAS_FLAG).apply{textSize=28f*scale;typeface=Typeface.create("sans-serif",Typeface.BOLD)}
        val w=p.measureText(value)+38f*scale;val h=54f*scale
        c.save();c.translate(cx,cy);c.rotate(rotation)
        rounded(c,RectF(-w/2,-h/2,w/2,h/2),18f*scale,colors[2])
        text(c,value,0f,10f*scale,28f*scale,colors[0],Paint.Align.CENTER,true)
        c.restore()
    }

    private fun drawFrame(canvas: Canvas, wheel:Bitmap, ref:Bitmap, photo:Bitmap, frame:Int, fps:Int, start:Double, travel:Double, style:String){
        val t=frame.toFloat()/fps
        val colors=palette(style); val w=canvas.width.toFloat();val h=canvas.height.toFloat()
        canvas.drawColor(colors[0])
        val imagePaint=Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        val bg=Paint(Paint.ANTI_ALIAS_FLAG).apply{color=colors[2];alpha=18}
        for(i in 0..5){
            val yy=((i*260f + t*95f)%1500f)-100f
            canvas.drawRoundRect(RectF(-80f,yy,w+80f,yy+70f),35f,35f,bg)
        }

        if(t < 2.55f){
            val p=(t/2.55f).coerceIn(0f,1f)
            text(canvas,"POSE ROULETTE",42f,78f,24f,colors[1],bold=true,alpha=185)
            text(canvas,if(style=="chaos")"WHO GETS PICKED?" else "SPIN / MATCH / SHOOT",42f,116f,15f,colors[1],bold=false,alpha=120)
            val cx=w/2;val cy=h*.48f;val size=560f
            for(g in 3 downTo 1){
                val gp=max(0f,p-g*.012f)
                val a=(start+travel*easeOut(gp))*180.0/Math.PI
                canvas.save();canvas.translate(cx,cy);canvas.rotate(a.toFloat())
                imagePaint.alpha=25
                drawContain(canvas,wheel,RectF(-size/2,-size/2,size/2,size/2),imagePaint)
                canvas.restore()
            }
            val a=(start+travel*easeOut(p))*180.0/Math.PI
            val pulse=1f+.035f*sin(p*18f)
            canvas.save();canvas.translate(cx,cy);canvas.rotate(a.toFloat());canvas.scale(pulse,pulse)
            imagePaint.alpha=255;drawContain(canvas,wheel,RectF(-size/2,-size/2,size/2,size/2),imagePaint);canvas.restore()
            val pointer=Path().apply{moveTo(cx,cy-size/2-8);lineTo(cx-24,cy-size/2-48);lineTo(cx+24,cy-size/2-48);close()}
            canvas.drawPath(pointer,Paint(Paint.ANTI_ALIAS_FLAG).apply{color=colors[3]})
            if(t>.35f) sticker(canvas,if(style=="editorial")"random is the brief" else "LET IT PICK",w/2,h*.82f,colors,-3f+sin(t*5f)*2f,.9f)
        } else if(t < 3.55f){
            val p=smooth((t-2.55f)/1f)
            if(t<2.68f) canvas.drawColor(Color.argb(((2.68f-t)/.13f*210).roundToInt().coerceIn(0,210),255,255,255))
            val box=RectF(58f,128f,w-58f,h-118f)
            val sc=.84f+.16f*p
            canvas.save();canvas.translate(w/2,h/2);canvas.scale(sc,sc);canvas.translate(-w/2,-h/2)
            rounded(canvas,RectF(box.left-10,box.top-10,box.right+10,box.bottom+10),34f,colors[1],35)
            drawContain(canvas,ref,box,imagePaint)
            canvas.restore()
            sticker(canvas,if(style=="editorial")"SELECTED" else "POSE LOCKED",w/2,112f,colors,if(style=="chaos")5f else -2f,1f)
            text(canvas,"match the shape, then make it yours",w/2,h-62f,18f,colors[1],Paint.Align.CENTER,false,190)
        } else if(t < 3.82f){
            val p=(t-3.55f)/.27f
            val shift=p*w*1.4f
            imagePaint.alpha=255
            drawCover(canvas,ref,RectF(-shift,0f,w-shift,h),imagePaint,1.03f)
            drawCover(canvas,photo,RectF(w-shift,0f,2*w-shift,h),imagePaint,1.02f)
            val streak=Paint().apply{color=colors[2];alpha=(120*(1-p)).roundToInt()}
            for(i in 0..4)canvas.drawRect(0f,h*(.13f+i*.17f),w, h*(.14f+i*.17f),streak)
        } else {
            val p=((t-3.82f)/(6.40f-3.82f)).coerceIn(0f,1f)
            val zoom=1f+.055f*smooth(p)
            imagePaint.alpha=255
            drawCover(canvas,photo,RectF(0f,0f,w,h),imagePaint,zoom)
            val shade=Paint().apply{shader=LinearGradient(0f,h*.55f,0f,h,Color.TRANSPARENT,Color.argb(175,0,0,0),Shader.TileMode.CLAMP)}
            canvas.drawRect(0f,h*.45f,w,h,shade)
            val pop=smooth(min(1f,p*5f))
            sticker(canvas,if(style=="editorial")"FINAL FRAME" else if(style=="chaos")"NAILED IT" else "SHOT ✓",126f,h-176f,colors,-4f,.82f+.18f*pop)
            text(canvas,"POSE ROULETTE",42f,h-76f,20f,Color.WHITE,bold=true,alpha=225)
            text(canvas,"spin → pose → photo",42f,h-43f,14f,Color.WHITE,bold=false,alpha=160)
            if(style=="chaos"){
                val spark=Paint(Paint.ANTI_ALIAS_FLAG).apply{color=colors[3]}
                for(i in 0..8){val xx=(w*.12f+i*73f)%w;val yy=(h*.16f+i*119f)%h;canvas.drawCircle(xx,yy,4f+(i%3)*2f,spark)}
            }
        }
    }

    private fun encode(wheelPath:String, referencePath:String, photoPath:String, output:String, start:Double, travel:Double, style:String){
        File(output).delete()
        val wheel=decode(wheelPath,1000);val ref=decode(referencePath);val photo=decode(photoPath)
        val width=720;val height=1280;val fps=24;val frames=(6.4f*fps).roundToInt()
        val format=MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC,width,height).apply{
            setInteger(MediaFormat.KEY_COLOR_FORMAT,MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
            setInteger(MediaFormat.KEY_BIT_RATE,4_500_000)
            setInteger(MediaFormat.KEY_FRAME_RATE,fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL,1)
        }
        val codec=MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        codec.configure(format,null,null,MediaCodec.CONFIGURE_FLAG_ENCODE)
        val surface:Surface=codec.createInputSurface()
        val muxer=MediaMuxer(output,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        val info=MediaCodec.BufferInfo();var track=-1;var started=false;var eos=false
        codec.start()
        fun drain(end:Boolean){
            while(true){
                val index=codec.dequeueOutputBuffer(info,if(end)10000 else 0)
                if(index==MediaCodec.INFO_TRY_AGAIN_LATER){if(!end)return else if(eos)return}
                else if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED){
                    if(started)throw IllegalStateException("Encoder format changed twice")
                    track=muxer.addTrack(codec.outputFormat);muxer.start();started=true
                }else if(index>=0){
                    val data=codec.getOutputBuffer(index)?:throw IllegalStateException("Encoder returned no buffer")
                    if(info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG !=0)info.size=0
                    if(info.size>0){
                        if(!started)throw IllegalStateException("Muxer not started")
                        data.position(info.offset);data.limit(info.offset+info.size);muxer.writeSampleData(track,data,info)
                    }
                    eos=info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM !=0
                    codec.releaseOutputBuffer(index,false)
                    if(eos)return
                }
            }
        }
        val startNs=System.nanoTime()
        try{
            for(frame in 0 until frames){
                if(cancelled)throw java.util.concurrent.CancellationException()
                val canvas=surface.lockCanvas(null)
                try{drawFrame(canvas,wheel,ref,photo,frame,fps,start,travel,style)}
                finally{surface.unlockCanvasAndPost(canvas)}
                drain(false)
                if(frame%12==0)main{channel.invokeMethod("recapProgress",frame.toDouble()/frames)}
                val wanted=startNs+((frame+1)*1_000_000_000L/fps)
                val remain=wanted-System.nanoTime()
                if(remain>0)Thread.sleep(remain/1_000_000L,(remain%1_000_000L).toInt())
            }
            codec.signalEndOfInputStream()
            while(!eos)drain(true)
            main{channel.invokeMethod("recapProgress",1.0)}
        }finally{
            try{codec.stop()}catch(_:Exception){};codec.release();surface.release()
            try{if(started)muxer.stop()}catch(_:Exception){};muxer.release()
            wheel.recycle();ref.recycle();photo.recycle()
            if(cancelled)File(output).delete()
        }
    }
}
