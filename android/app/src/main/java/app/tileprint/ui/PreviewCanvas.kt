package app.tileprint.ui

import android.graphics.Paint
import android.graphics.RectF
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculateCentroid
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChanged
import app.tileprint.UiState
import app.tileprint.core.Job
import app.tileprint.core.Tile
import app.tileprint.engine.Region
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

data class ViewTransform(val scale: Float, val tx: Float, val ty: Float)

/** Fit the whole poster into a canvas of [w] x [h] pixels. */
fun fitView(w: Float, h: Float, job: Job): ViewTransform {
    val pad = min(w, h) * 0.08f
    val s = max(1e-4f, min((w - 2 * pad) / job.posterW.toFloat(), (h - 2 * pad) / job.posterH.toFloat()))
    return ViewTransform(s, (w - job.posterW.toFloat() * s) / 2, (h - job.posterH.toFloat() * s) / 2)
}

fun tileAt(job: Job, wx: Double, wy: Double): Tile? {
    if (wx < 0 || wy < 0 || wx > job.posterW || wy > job.posterH) return null
    var best: Tile? = null
    var bd = -1.0
    for (t in job.layout.tiles()) {
        if (wx >= t.x && wx <= t.x + t.w && wy >= t.y && wy <= t.y + t.h) {
            val d = minOf(wx - t.x, t.x + t.w - wx, wy - t.y, t.y + t.h - wy)
            if (d > bd) { bd = d; best = t }
        }
    }
    return best
}

@Composable
fun PreviewCanvas(
    state: UiState,
    view: ViewTransform,
    fitScale: Float,
    region: Region?,
    regionRev: Int,
    onView: (ViewTransform) -> Unit,
    onTapTile: (Tile?) -> Unit,
    onOpenTile: (Tile) -> Unit,
    onMoveContent: (Double, Double) -> Unit,
    modifier: Modifier = Modifier,
) {
    val job = state.job
    val accent = MaterialTheme.colorScheme.primary.toArgb()
    val onAccent = MaterialTheme.colorScheme.onPrimary.toArgb()
    val dark = MaterialTheme.colorScheme.background.toArgb().let { (it and 0xFF) < 0x40 }
    val paints = remember { Paints() }
    var dragOffset by remember { mutableStateOf(Offset.Zero) }       // live content drag, in poster points
    val curView by rememberUpdatedState(view)
    val curOnView by rememberUpdatedState(onView)
    val curJob by rememberUpdatedState(job)
    val curMove by rememberUpdatedState(state.moveMode)
    val curFit by rememberUpdatedState(fitScale)
    val curTap by rememberUpdatedState(onTapTile)
    val curOpen by rememberUpdatedState(onOpenTile)
    val curMoveCb by rememberUpdatedState(onMoveContent)

    fun toWorld(o: Offset) = ((o.x - curView.tx) / curView.scale).toDouble() to ((o.y - curView.ty) / curView.scale).toDouble()

    Canvas(
        modifier
            .fillMaxSize()
            .pointerInput(Unit) {
                detectTapGestures(
                    onTap = { o -> curJob?.let { j -> toWorld(o).let { (x, y) -> curTap(tileAt(j, x, y)) } } },
                    onDoubleTap = { o -> curJob?.let { j -> toWorld(o).let { (x, y) -> tileAt(j, x, y)?.let(curOpen) } } },
                )
            }
            .pointerInput(Unit) {
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    var pastSlop = false
                    var total = Offset.Zero
                    var maxPointers = 1
                    var drag = Offset.Zero
                    do {
                        val event = awaitPointerEvent()
                        val pressed = event.changes.count { it.pressed }
                        maxPointers = max(maxPointers, pressed)
                        val zoom = event.calculateZoom()
                        val pan = event.calculatePan()
                        val centroid = event.calculateCentroid()
                        if (!pastSlop) {
                            total += pan
                            if (total.getDistance() > viewConfiguration.touchSlop || abs(1f - zoom) > 0.02f || pressed > 1) pastSlop = true
                        }
                        if (pastSlop && pressed > 0) {
                            val v = curView
                            if (curMove && maxPointers == 1) {
                                drag += pan / v.scale
                                dragOffset = drag
                            } else {
                                val ns = (v.scale * zoom).coerceIn(curFit * 0.25f, max(curFit * 120f, 12f))
                                val f = ns / v.scale
                                if (centroid != Offset.Unspecified) {
                                    curOnView(ViewTransform(ns, centroid.x - (centroid.x - v.tx) * f + pan.x, centroid.y - (centroid.y - v.ty) * f + pan.y))
                                }
                            }
                            event.changes.forEach { if (it.positionChanged()) it.consume() }
                        }
                    } while (event.changes.any { it.pressed })
                    if (curMove && maxPointers == 1 && drag != Offset.Zero) curMoveCb(drag.x.toDouble(), drag.y.toDouble())
                    dragOffset = Offset.Zero
                }
            },
    ) {
        val j = job ?: return@Canvas
        val pw = j.posterW.toFloat()
        val ph = j.posterH.toFloat()
        val pl = j.placement
        val sc = view.scale
        val px = 1f / sc
        drawIntoCanvas { canvas ->
            val nc = canvas.nativeCanvas
            nc.save()
            nc.translate(view.tx, view.ty)
            nc.scale(sc, sc)

            // paper with a soft shadow
            for (i in 1..7) {
                paints.fill.color = android.graphics.Color.argb(if (dark) 40 else 14, 0, 0, 0)
                nc.drawRect(-i * px, (5 - i) * px + i * px, pw + i * px, ph + (5 + i) * px, paints.fill)
            }
            paints.fill.color = android.graphics.Color.WHITE
            nc.drawRect(0f, 0f, pw, ph, paints.fill)

            // content (live drag offset while moving)
            nc.save()
            nc.clipRect(0f, 0f, pw, ph)
            state.overview?.let { bmp ->
                val dx = dragOffset.x
                val dy = dragOffset.y
                nc.drawBitmap(bmp, null, RectF(pl.x.toFloat() + dx, pl.y.toFloat() + dy,
                    (pl.x + pl.width).toFloat() + dx, (pl.y + pl.height).toFloat() + dy), paints.bitmap)
            }
            if (region != null && regionRev == state.rev && dragOffset == Offset.Zero) {
                nc.drawBitmap(region.bitmap, null, RectF(region.x.toFloat(), region.y.toFloat(),
                    (region.x + region.w).toFloat(), (region.y + region.h).toFloat()), paints.bitmap)
            }
            nc.restore()

            // overlap strips
            val fw = j.layout.frameW.toFloat()
            val fh = j.layout.frameH.toFloat()
            paints.fill.color = android.graphics.Color.argb(52, 255, 150, 0)
            val xs = j.layout.xs
            val ys = j.layout.ys
            for (i in 1 until xs.size) nc.drawRect(xs[i].toFloat(), 0f, min((xs[i - 1] + fw).toFloat(), pw), ph, paints.fill)
            for (i in 1 until ys.size) nc.drawRect(0f, ys[i].toFloat(), pw, min((ys[i - 1] + fh).toFloat(), ph), paints.fill)

            // skipped tiles dimmed, selected tile tinted
            for (t in j.layout.tiles()) {
                if (t.key in j.skip) {
                    paints.fill.color = android.graphics.Color.argb(if (dark) 110 else 45, 20, 28, 46)
                    nc.drawRect(t.x.toFloat(), t.y.toFloat(), min((t.x + t.w).toFloat(), pw), min((t.y + t.h).toFloat(), ph), paints.fill)
                }
                if (t.key == state.selected) {
                    paints.fill.color = (accent and 0x00FFFFFF) or (0x33 shl 24)
                    nc.drawRect(t.x.toFloat(), t.y.toFloat(), min((t.x + t.w).toFloat(), pw), min((t.y + t.h).toFloat(), ph), paints.fill)
                }
            }

            // tile frames (never leave the poster)
            nc.save()
            nc.clipRect(-2 * px, -2 * px, pw + 2 * px, ph + 2 * px)
            paints.stroke.color = accent
            paints.stroke.strokeWidth = 1.5f * px
            for (t in j.layout.tiles()) {
                nc.drawRect(t.x.toFloat(), t.y.toFloat(), (t.x + t.w).toFloat(), (t.y + t.h).toFloat(), paints.stroke)
            }
            nc.restore()

            // sheet numbers: constant on-screen size
            val labels = j.layout.plan(j.skip, state.settings.numbering).associate { it.tile.key to it.label }
            for (t in j.layout.tiles()) {
                val minSide = min(t.w, t.h).toFloat()
                if (minSide * sc < 64f) continue
                val fs = min(24f, max(11f, minSide * 0.075f * sc)) / sc
                val skipped = t.key in j.skip
                val label = if (skipped) "–" else labels[t.key] ?: continue
                paints.text.textSize = fs
                val tw = paints.text.measureText(label)
                val ph2 = fs * 1.55f
                val pw2 = max(ph2, tw + fs * 1.1f)
                val x = t.x.toFloat() + fs * 0.5f
                val y = t.y.toFloat() + fs * 0.5f
                paints.fill.color = if (skipped) android.graphics.Color.rgb(138, 147, 166) else accent
                nc.drawRoundRect(x, y, x + pw2, y + ph2, ph2 / 2, ph2 / 2, paints.fill)
                paints.text.color = if (skipped) android.graphics.Color.WHITE else onAccent
                nc.drawText(label, x + pw2 / 2, y + ph2 / 2 - (paints.text.ascent() + paints.text.descent()) / 2, paints.text)
            }

            // poster outline
            paints.stroke.color = if (dark) android.graphics.Color.argb(70, 255, 255, 255) else android.graphics.Color.argb(90, 16, 24, 40)
            paints.stroke.strokeWidth = px
            nc.drawRect(0f, 0f, pw, ph, paints.stroke)
            nc.restore()
        }
    }
}

private class Paints {
    val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    val bitmap = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG).apply { isFilterBitmap = true }
    val text = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textAlign = Paint.Align.CENTER
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }
}
