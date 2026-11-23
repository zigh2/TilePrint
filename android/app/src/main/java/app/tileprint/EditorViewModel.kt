package app.tileprint

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import androidx.annotation.StringRes
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.tileprint.core.Job
import app.tileprint.core.Paper
import app.tileprint.core.PosterRaster
import app.tileprint.core.Placement
import app.tileprint.core.Settings
import app.tileprint.core.buildJob
import app.tileprint.data.SourceDoc
import app.tileprint.data.SourceException
import app.tileprint.data.SourceLoader
import app.tileprint.engine.OverlayOptions
import app.tileprint.engine.PdfExporter
import app.tileprint.engine.Region
import app.tileprint.engine.RenderEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Locale
import kotlinx.coroutines.Job as CoroutineJob

/** One-shot message for a snackbar: a string resource and an optional argument (e.g. an error detail). */
data class UiMessage(@StringRes val resId: Int, val arg: String? = null)

data class ExportUi(
    val running: Boolean = false,
    val done: Int = 0,
    val total: Int = 0,
    val savedUri: Uri? = null,
)

data class UiState(
    val source: SourceDoc? = null,
    val settings: Settings = Settings(),
    val job: Job? = null,
    val overview: Bitmap? = null,
    val rev: Int = 0,                       // bumps whenever the layout/placement changes (invalidates crisp regions)
    val canUndo: Boolean = false,
    val canRedo: Boolean = false,
    val loading: Boolean = false,
    val message: UiMessage? = null,
    val selected: Pair<Int, Int>? = null,
    val moveMode: Boolean = false,
    val export: ExportUi = ExportUi(),
) {
    val language: String get() = if (Locale.getDefault().language == "ar") "ar" else "en"
}

class EditorViewModel(app: Application) : AndroidViewModel(app) {
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private var engine: RenderEngine? = null
    private val history = ArrayList<Settings>()
    private var pos = 0
    private var jobTask: CoroutineJob? = null
    private var rasterKey: List<Any>? = null
    private var raster: PosterRaster? = null

    private fun ctx() = getApplication<Application>()

    // ---------------------------------------------------------------- source
    fun openUri(uri: Uri) {
        if (_state.value.export.running) return
        viewModelScope.launch {
            _state.update { it.copy(loading = true) }
            try {
                val (doc, eng) = withContext(Dispatchers.IO) {
                    val d = SourceLoader.load(ctx(), uri)
                    d to RenderEngine(d.file)
                }
                engine?.close()
                engine = eng
                rasterKey = null
                val settings = _state.value.settings.copy(pageIndex = 0, offsetX = 0.0, offsetY = 0.0)
                history.clear(); history.add(settings); pos = 0
                val overview = withContext(Dispatchers.Default) { eng.overview(doc.info(0), 0) }
                _state.update { it.copy(source = doc, settings = settings, overview = overview, selected = null,
                    loading = false, job = null) }
                rebuild()
                syncHistoryFlags()
            } catch (e: SourceException) {
                _state.update { it.copy(loading = false, message = UiMessage(e.resId)) }
            } catch (e: Throwable) {
                _state.update { it.copy(loading = false, message = UiMessage(R.string.error_generic, e.message)) }
            }
        }
    }

    fun setPage(index: Int) {
        val doc = _state.value.source ?: return
        val i = index.coerceIn(0, doc.pageCount - 1)
        viewModelScope.launch {
            val s = _state.value.settings.copy(pageIndex = i, offsetX = 0.0, offsetY = 0.0)
            val ov = withContext(Dispatchers.Default) { engine?.overview(doc.info(i), i) }
            _state.update { it.copy(overview = ov ?: it.overview) }
            commit(s)
        }
    }

    // ---------------------------------------------------------------- settings
    /** Apply a change, record it for undo, and rebuild the layout. */
    fun update(change: (Settings) -> Settings) {
        val cur = _state.value.settings
        val next = change(cur)
        if (next != cur) commit(next)
    }

    /** Custom poster size with the aspect lock: editing one side recomputes the other. */
    fun setPosterSize(widthPt: Double?, heightPt: Double?) {
        val cur = _state.value.settings
        val src = _state.value.source?.sizes?.getOrNull(cur.pageIndex)
        update { s ->
            var w = widthPt ?: s.posterW
            var h = heightPt ?: s.posterH
            if (s.lockAspect && src != null) {
                if (widthPt != null) h = w * src.second / src.first else if (heightPt != null) w = h * src.first / src.second
            }
            s.copy(posterW = w.coerceIn(10.0, 14400.0 * 40), posterH = h.coerceIn(10.0, 14400.0 * 40))
        }
    }

    /** Selecting "Custom" starts from the current poster size. */
    fun choosePreset(name: String) {
        val job = _state.value.job
        update { s ->
            if (name == "Custom" && s.posterPreset != "Custom" && job != null) s.copy(posterPreset = name, posterW = job.posterW, posterH = job.posterH)
            else s.copy(posterPreset = name)
        }
    }

    fun moveContent(dxPt: Double, dyPt: Double) = update { it.copy(offsetX = it.offsetX + dxPt, offsetY = it.offsetY + dyPt) }
    fun resetPosition() = update { it.copy(offsetX = 0.0, offsetY = 0.0) }
    fun setMoveMode(on: Boolean) = _state.update { it.copy(moveMode = on) }
    fun select(tile: Pair<Int, Int>?) = _state.update { it.copy(selected = tile) }
    fun consumeMessage() = _state.update { it.copy(message = null) }

    fun undo() {
        if (pos > 0) { pos--; applyHistory() }
    }

    fun redo() {
        if (pos < history.size - 1) { pos++; applyHistory() }
    }

    private fun applyHistory() {
        val s = history[pos]
        val doc = _state.value.source
        viewModelScope.launch {
            if (doc != null && s.pageIndex != _state.value.settings.pageIndex) {
                val ov = withContext(Dispatchers.Default) { engine?.overview(doc.info(s.pageIndex), s.pageIndex) }
                _state.update { it.copy(overview = ov ?: it.overview) }
            }
            _state.update { it.copy(settings = s) }
            rebuild()
            syncHistoryFlags()
        }
    }

    private fun commit(s: Settings) {
        while (history.size > pos + 1) history.removeAt(history.size - 1)
        history.add(s); pos = history.size - 1
        _state.update { it.copy(settings = s) }
        syncHistoryFlags()
        rebuild()
    }

    private fun syncHistoryFlags() = _state.update { it.copy(canUndo = pos > 0, canRedo = pos < history.size - 1) }

    // ---------------------------------------------------------------- layout job
    private fun rebuild() {
        val doc = _state.value.source ?: return
        val s = _state.value.settings
        val eng = engine ?: return
        jobTask?.cancel()
        jobTask = viewModelScope.launch(Dispatchers.Default) {
            try {
                val job = buildJob(doc.info(s.pageIndex), s) { pl, pw, ph -> rasterFor(eng, s.pageIndex, pl, pw, ph) }
                _state.update { it.copy(job = job, rev = it.rev + 1) }
            } catch (e: IllegalArgumentException) {              // e.g. margins leave no printable area
                _state.update { it.copy(job = null, message = UiMessage(R.string.error_generic, e.message)) }
            }
        }
    }

    /** The poster raster is the costly part: reuse it while only tile settings change. */
    private fun rasterFor(eng: RenderEngine, page: Int, pl: Placement, pw: Double, ph: Double): PosterRaster {
        val key = listOf(page, pl.x.round2(), pl.y.round2(), pl.width.round2(), pl.height.round2(), pw.round2(), ph.round2())
        if (key != rasterKey || raster == null) {
            raster = eng.posterRaster(page, pl, pw, ph)
            rasterKey = key
        }
        return raster!!
    }

    private fun Double.round2() = Math.round(this * 100) / 100.0

    // ---------------------------------------------------------------- preview images
    suspend fun region(rx: Double, ry: Double, rw: Double, rh: Double, outPx: Int): Region? = withContext(Dispatchers.Default) {
        val eng = engine ?: return@withContext null
        val job = _state.value.job ?: return@withContext null
        eng.region(_state.value.settings.pageIndex, job.placement, rx, ry, rw, rh, outPx)
    }

    private fun overlayOptions(job: Job, s: Settings, name: String) = OverlayOptions(
        numbering = s.numbering, cropMarks = s.cropMarks, overlapTicks = s.overlapTicks, footer = s.footer,
        scaleBar = s.scaleBar, imperialBar = s.unit == Paper.Unit.IN,
        footerName = s.footerText.ifBlank { name },
        scaleText = if (Math.abs(job.placement.sx - job.placement.sy) < 1e-6) "%.2f".format(Locale.US, job.placement.sx) else "",
        language = _state.value.language)

    suspend fun sheetPreview(number: Int): Bitmap? = withContext(Dispatchers.IO) {
        val st = _state.value
        val doc = st.source ?: return@withContext null
        val job = st.job ?: return@withContext null
        runCatching {
            PdfExporter.sheetPreview(ctx(), doc, st.settings.pageIndex, job, overlayOptions(job, st.settings, doc.name), number)
        }.getOrNull()
    }

    // ---------------------------------------------------------------- export
    fun export(uri: Uri, tiled: Boolean) {
        val st = _state.value
        val doc = st.source ?: return
        val job = st.job ?: return
        if (st.export.running) return
        _state.update { it.copy(export = ExportUi(running = true, total = job.sheets)) }
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val out = ctx().contentResolver.openOutputStream(uri, "w") ?: error("cannot write")
                out.buffered().use { stream ->
                    if (tiled) {
                        PdfExporter.exportTiled(ctx(), doc, st.settings.pageIndex, job, overlayOptions(job, st.settings, doc.name),
                            stream, st.settings.blankBacks) { i, n -> _state.update { it.copy(export = it.export.copy(done = i, total = n)) } }
                    } else PdfExporter.exportFull(doc, st.settings.pageIndex, job, stream)
                }
                _state.update { it.copy(export = ExportUi(savedUri = uri), message = UiMessage(R.string.saved)) }
            } catch (e: Throwable) {
                _state.update { it.copy(export = ExportUi(), message = UiMessage(R.string.error_generic, e.message)) }
            }
        }
    }

    override fun onCleared() {
        engine?.close()
        super.onCleared()
    }
}
