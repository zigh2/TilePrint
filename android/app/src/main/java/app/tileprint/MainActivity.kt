package app.tileprint

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.core.content.IntentCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.tileprint.ui.EditorScreen
import app.tileprint.ui.EmptyScreen
import app.tileprint.ui.TilePrintTheme

class MainActivity : ComponentActivity() {
    private val vm: EditorViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        if (savedInstanceState == null) handleIntent(intent)
        setContent { TilePrintTheme { AppRoot() } }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    /** "Open with" and "Share to" from other apps. */
    private fun handleIntent(intent: Intent?) {
        val uri: Uri? = when (intent?.action) {
            Intent.ACTION_VIEW -> intent.data
            Intent.ACTION_SEND -> IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java)
            else -> null
        }
        uri?.let(vm::openUri)
    }

    @Composable
    private fun AppRoot() {
        val state by vm.state.collectAsStateWithLifecycle()
        var pendingTiled by remember { mutableStateOf(true) }

        val openDoc = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri -> uri?.let(vm::openUri) }
        val createDoc = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { uri ->
            uri?.let { vm.export(it, pendingTiled) }
        }
        val pick = { openDoc.launch(arrayOf("application/pdf", "image/*")) }

        if (state.source == null) {
            EmptyScreen(loading = state.loading, onPick = pick)
        } else {
            EditorScreen(
                state = state, vm = vm, onPickFile = pick,
                onExport = { tiled ->
                    pendingTiled = tiled
                    val base = state.source?.name?.substringBeforeLast('.') ?: "poster"
                    createDoc.launch("${base}_${if (tiled) "tiles" else "full"}.pdf")
                },
                onShare = {
                    state.export.savedUri?.let { uri ->
                        val send = Intent(Intent.ACTION_SEND).apply {
                            type = "application/pdf"
                            putExtra(Intent.EXTRA_STREAM, uri)
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        }
                        startActivity(Intent.createChooser(send, getString(R.string.share)))
                    }
                },
            )
        }
    }
}
