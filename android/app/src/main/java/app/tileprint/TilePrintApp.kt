package app.tileprint

import android.app.Application
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader

class TilePrintApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // PDFBox spills big documents to temp files: point it at the app cache (the default is not writable here)
        System.setProperty("java.io.tmpdir", cacheDir.absolutePath)
        PDFBoxResourceLoader.init(applicationContext)
    }
}
