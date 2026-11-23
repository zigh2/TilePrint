package app.tileprint.ui

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Redo
import androidx.compose.material.icons.automirrored.outlined.Undo
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.FileDownload
import androidx.compose.material.icons.outlined.FitScreen
import androidx.compose.material.icons.outlined.FolderOpen
import androidx.compose.material.icons.outlined.GridView
import androidx.compose.material.icons.outlined.KeyboardArrowDown
import androidx.compose.material.icons.outlined.KeyboardArrowUp
import androidx.compose.material.icons.outlined.OpenWith
import androidx.compose.material.icons.outlined.PictureAsPdf
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FilledTonalIconToggleButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import app.tileprint.EditorViewModel
import app.tileprint.R
import app.tileprint.UiState
import app.tileprint.core.Paper
import app.tileprint.engine.PdfExporter
import app.tileprint.engine.Region
import kotlinx.coroutines.delay
import kotlin.math.max
import kotlin.math.min

@Composable
fun EmptyScreen(loading: Boolean, onPick: () -> Unit) {
    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).padding(24.dp), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp),
            modifier = Modifier.width(420.dp)) {
            Surface(shape = RoundedCornerShape(24.dp), color = MaterialTheme.colorScheme.primary, modifier = Modifier.size(84.dp)) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(Icons.Outlined.GridView, null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(40.dp))
                }
            }
            Text(stringResource(R.string.empty_title), fontSize = 24.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
            Text(stringResource(R.string.empty_text), color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
            if (loading) CircularProgressIndicator()
            else Button(onClick = onPick) {
                Icon(Icons.Outlined.FolderOpen, null, Modifier.padding(end = 8.dp))
                Text(stringResource(R.string.choose_file))
            }
            Text(stringResource(R.string.formats), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditorScreen(
    state: UiState, vm: EditorViewModel,
    onPickFile: () -> Unit, onExport: (tiled: Boolean) -> Unit, onShare: () -> Unit,
) {
    val job = state.job
    var view by remember { mutableStateOf<ViewTransform?>(null) }
    var fitScale by remember { mutableStateOf(1f) }
    var canvasSize by remember { mutableStateOf(IntSize.Zero) }
    var region by remember { mutableStateOf<Region?>(null) }
    var regionRev by remember { mutableIntStateOf(-1) }
    var sheetNumber by remember { mutableStateOf<Int?>(null) }
    var settingsOpen by remember { mutableStateOf(false) }
    var exportMenu by remember { mutableStateOf(false) }
    val snack = remember { SnackbarHostState() }
    val ctx = LocalContext.current

    // refit when the poster size, the canvas or the page changes
    LaunchedEffect(job?.posterW, job?.posterH, canvasSize, state.settings.pageIndex, state.source?.name) {
        if (job != null && canvasSize.width > 0) {
            val v = fitView(canvasSize.width.toFloat(), canvasSize.height.toFloat(), job)
            view = v; fitScale = v.scale
        }
    }
    // crisp re-render of the visible part when zoomed past the base image's resolution
    LaunchedEffect(view, state.rev, canvasSize) {
        val v = view; val j = job; val ov = state.overview
        if (v == null || j == null || ov == null || canvasSize.width == 0) return@LaunchedEffect
        delay(250)
        val pl = j.placement
        val x0 = max(max(-v.tx / v.scale, pl.x.toFloat()), 0f)
        val y0 = max(max(-v.ty / v.scale, pl.y.toFloat()), 0f)
        val x1 = min(min((canvasSize.width - v.tx) / v.scale, (pl.x + pl.width).toFloat()), j.posterW.toFloat())
        val y1 = min(min((canvasSize.height - v.ty) / v.scale, (pl.y + pl.height).toFloat()), j.posterH.toFloat())
        if (x1 - x0 < 1f || y1 - y0 < 1f) { region = null; return@LaunchedEffect }
        val have = ov.width / pl.width
        if (v.scale <= have * 1.15) { region = null; return@LaunchedEffect }
        val r = vm.region(x0.toDouble(), y0.toDouble(), (x1 - x0).toDouble(), (y1 - y0).toDouble(), min(2800f, (x1 - x0) * v.scale).toInt())
        region = r; regionRev = state.rev
    }
    // messages (errors and "saved")
    LaunchedEffect(state.message) {
        val m = state.message ?: return@LaunchedEffect
        val text = ctx.getString(m.resId) + (m.arg?.let { ": $it" } ?: "")
        val offerShare = m.resId == R.string.saved && state.export.savedUri != null
        val res = snack.showSnackbar(text, actionLabel = if (offerShare) ctx.getString(R.string.share) else null)
        vm.consumeMessage()
        if (res == SnackbarResult.ActionPerformed) onShare()
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snack) },
        topBar = {
            TopAppBar(
                title = { Text(state.source?.name ?: "", maxLines = 1, fontSize = 16.sp) },
                actions = {
                    IconButton(onClick = vm::undo, enabled = state.canUndo) { Icon(Icons.AutoMirrored.Outlined.Undo, stringResource(R.string.undo)) }
                    IconButton(onClick = vm::redo, enabled = state.canRedo) { Icon(Icons.AutoMirrored.Outlined.Redo, stringResource(R.string.redo)) }
                    FilledTonalIconToggleButton(checked = state.moveMode, onCheckedChange = vm::setMoveMode) {
                        Icon(Icons.Outlined.OpenWith, stringResource(R.string.move_content))
                    }
                    IconButton(onClick = { job?.let { view = fitView(canvasSize.width.toFloat(), canvasSize.height.toFloat(), it) } }) {
                        Icon(Icons.Outlined.FitScreen, stringResource(R.string.fit_view))
                    }
                    IconButton(onClick = onPickFile) { Icon(Icons.Outlined.FolderOpen, stringResource(R.string.open_file)) }
                    Box {
                        IconButton(onClick = { exportMenu = true }, enabled = job != null) { Icon(Icons.Outlined.FileDownload, stringResource(R.string.export)) }
                        DropdownMenu(expanded = exportMenu, onDismissRequest = { exportMenu = false }) {
                            if (job != null) {
                                val u = state.settings.unit
                                DropdownMenuItem(
                                    leadingIcon = { Icon(Icons.Outlined.GridView, null) },
                                    text = {
                                        Column {
                                            Text(stringResource(R.string.export_tiled), fontWeight = FontWeight.SemiBold)
                                            Text(stringResource(R.string.export_tiled_desc, job.printed, state.settings.paper), fontSize = 12.sp,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        }
                                    },
                                    onClick = { exportMenu = false; onExport(true) })
                                val tooBig = max(job.posterW, job.posterH) > PdfExporter.MAX_PAGE_PT
                                DropdownMenuItem(
                                    enabled = !tooBig,
                                    leadingIcon = { Icon(Icons.Outlined.PictureAsPdf, null) },
                                    text = {
                                        Column {
                                            Text(stringResource(R.string.export_full), fontWeight = FontWeight.SemiBold)
                                            Text(if (tooBig) stringResource(R.string.too_big)
                                            else stringResource(R.string.export_full_desc, fmtLen(u.fromPt(job.posterW)), fmtLen(u.fromPt(job.posterH)), unitText(u)),
                                                fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        }
                                    },
                                    onClick = { exportMenu = false; onExport(false) })
                                if (state.export.savedUri != null) {
                                    DropdownMenuItem(leadingIcon = { Icon(Icons.Outlined.Share, null) },
                                        text = { Text(stringResource(R.string.share)) }, onClick = { exportMenu = false; onShare() })
                                }
                            }
                        }
                    }
                },
            )
        },
    ) { inner ->
        BoxWithConstraints(Modifier.padding(inner).fillMaxSize()) {
            val wide = maxWidth >= 840.dp
            val canvasArea: @Composable (Modifier) -> Unit = { mod ->
                Box(mod.onSizeChanged { canvasSize = it }.background(MaterialTheme.colorScheme.surfaceVariant)) {
                    val v = view
                    if (v != null && job != null) {
                        PreviewCanvas(
                            state = state, view = v, fitScale = fitScale, region = region, regionRev = regionRev,
                            onView = { view = it },
                            onTapTile = { t -> vm.select(t?.key) },
                            onOpenTile = { t ->
                                val pp = job.layout.plan(job.skip, state.settings.numbering).firstOrNull { it.tile.key == t.key }
                                if (pp != null) sheetNumber = pp.number
                            },
                            onMoveContent = vm::moveContent,
                        )
                        InfoChips(state, Modifier.align(Alignment.TopStart).padding(10.dp))
                        Text(
                            stringResource(if (state.moveMode) R.string.move_hint else R.string.hint_gestures),
                            fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center,
                            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = if (wide) 12.dp else 84.dp, start = 12.dp, end = 12.dp),
                        )
                    }
                    if (state.loading) CircularProgressIndicator(Modifier.align(Alignment.Center))
                }
            }
            if (wide) {
                Row(Modifier.fillMaxSize()) {
                    Column(Modifier.width(390.dp).fillMaxHeight().verticalScroll(rememberScrollState()).padding(12.dp)) {
                        SettingsPanel(state, vm, onPickFile)
                    }
                    canvasArea(Modifier.weight(1f).fillMaxHeight())
                }
            } else {
                canvasArea(Modifier.fillMaxSize())
                ExtendedFloatingActionButton(
                    onClick = { settingsOpen = true },
                    icon = { Icon(Icons.Outlined.Settings, null) },
                    text = { Text(stringResource(R.string.settings)) },
                    modifier = Modifier.align(Alignment.BottomEnd).padding(16.dp),
                )
            }
        }
    }

    if (settingsOpen) {
        ModalBottomSheet(onDismissRequest = { settingsOpen = false }, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(Modifier.verticalScroll(rememberScrollState()).padding(start = 16.dp, end = 16.dp, bottom = 24.dp)) {
                SettingsPanel(state, vm, onPickFile)
            }
        }
    }
    sheetNumber?.let { n -> SheetPreviewDialog(n, state, vm, onNumber = { sheetNumber = it }, onDismiss = { sheetNumber = null }) }

    if (state.export.running) {
        AlertDialog(
            onDismissRequest = {}, confirmButton = {},
            title = { Text(stringResource(R.string.writing_pdf)) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    val total = max(state.export.total, 1)
                    LinearProgressIndicator(progress = { state.export.done.toFloat() / total }, modifier = Modifier.fillMaxWidth())
                    Text(stringResource(R.string.sheets_done, state.export.done, state.export.total), fontSize = 13.sp)
                }
            },
        )
    }
}

@Composable
private fun InfoChips(state: UiState, modifier: Modifier) {
    val j = state.job ?: return
    val u = state.settings.unit
    Surface(modifier, shape = RoundedCornerShape(12.dp), tonalElevation = 3.dp, shadowElevation = 3.dp,
        color = MaterialTheme.colorScheme.surface) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(stringResource(R.string.chip_sheets, j.layout.rows, j.layout.cols, j.sheets) +
                (if (j.printed != j.sheets) "  ·  " + stringResource(R.string.chip_print, j.printed) else ""),
                fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
            Text("${fmtLen(u.fromPt(j.posterW))} × ${fmtLen(u.fromPt(j.posterH))} ${unitText(u)}  ·  ×${"%.2f".format(java.util.Locale.US, j.scale)}  ·  ${state.settings.paper}",
                fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            j.dpi?.let { d ->
                val low = d < 150
                Text(stringResource(if (low) R.string.dpi_low else R.string.dpi_ok, Math.round(d).toInt()), fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold, color = if (low) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary)
            }
        }
    }
}

@Composable
private fun SheetPreviewDialog(number: Int, state: UiState, vm: EditorViewModel, onNumber: (Int) -> Unit, onDismiss: () -> Unit) {
    val job = state.job ?: run { onDismiss(); return }
    val plan = remember(job, state.settings.numbering) { job.layout.plan(job.skip, state.settings.numbering) }
    val page = plan.firstOrNull { it.number == number } ?: run { onDismiss(); return }
    val byLabel = remember(plan) { plan.associate { it.label to it.number } }
    var bmp by remember(number, state.rev) { mutableStateOf<Bitmap?>(null) }
    LaunchedEffect(number, state.rev) { bmp = vm.sheetPreview(number) }

    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(Modifier.fillMaxSize().padding(12.dp), shape = RoundedCornerShape(20.dp), color = MaterialTheme.colorScheme.surface) {
            Column {
                Row(Modifier.fillMaxWidth().padding(start = 16.dp, end = 4.dp, top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(stringResource(R.string.sheet_title, page.label), fontWeight = FontWeight.Bold, fontSize = 17.sp)
                        Text(stringResource(R.string.sheet_sub, page.tile.row + 1, page.tile.col + 1, page.number, page.total),
                            fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    fun go(dir: String) = page.neighbors[dir]?.let { byLabel[it] }?.let(onNumber)
                    IconButton(onClick = { go("left") }, enabled = "left" in page.neighbors) { Icon(Icons.AutoMirrored.Outlined.ArrowBack, null) }
                    IconButton(onClick = { go("up") }, enabled = "up" in page.neighbors) { Icon(Icons.Outlined.KeyboardArrowUp, null) }
                    IconButton(onClick = { go("down") }, enabled = "down" in page.neighbors) { Icon(Icons.Outlined.KeyboardArrowDown, null) }
                    IconButton(onClick = { go("right") }, enabled = "right" in page.neighbors) { Icon(Icons.AutoMirrored.Outlined.ArrowForward, null) }
                    IconButton(onClick = onDismiss) { Icon(Icons.Outlined.Close, stringResource(R.string.close)) }
                }
                Box(Modifier.weight(1f).fillMaxWidth().background(MaterialTheme.colorScheme.surfaceVariant).padding(8.dp), contentAlignment = Alignment.Center) {
                    val b = bmp
                    if (b == null) CircularProgressIndicator()
                    else Image(b.asImageBitmap(), null, contentScale = ContentScale.Fit, modifier = Modifier.fillMaxSize())
                }
            }
        }
    }
}

private fun fmtLen(v: Double): String {
    val r = Math.round(v * 10) / 10.0
    return if (r == Math.floor(r)) r.toLong().toString() else r.toString()
}

@Composable
private fun unitText(u: Paper.Unit) = stringResource(when (u) {
    Paper.Unit.MM -> R.string.unit_mm
    Paper.Unit.CM -> R.string.unit_cm
    Paper.Unit.IN -> R.string.unit_in
})
