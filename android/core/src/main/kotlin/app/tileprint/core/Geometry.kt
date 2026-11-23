package app.tileprint.core

import kotlin.math.max
import kotlin.math.min

/** Result of [sourceTransform]: the PDF `cm` matrix plus the clip rectangle, all in page space. */
class SourcePlacement(val a: Double, val b: Double, val c: Double, val d: Double, val e: Double, val f: Double,
                      val clipX: Double, val clipY: Double, val clipW: Double, val clipH: Double)

/**
 * Where the imported source page lands on a sheet.
 *
 * The page is imported as a Form XObject whose /Rotate has been reset to 0, so the form is the
 * *unrotated* page; [rotation] (0/90/180/270, clockwise as displayed) is applied here, because the
 * library's own rotation handling distorts 90/270 pages.
 *
 * [ox],[oy],[w0],[h0] = origin and size of the unrotated form's BBox after its /Matrix.
 * The poster point ([tx],[ty]) (y down) lands at the frame's top-left; the frame is
 * (frameX0, frameY0)-(frameX1, frameY1) in page space (y up).
 */
fun sourceTransform(rotation: Int, ox: Double, oy: Double, w0: Double, h0: Double, pl: Placement,
                    posterW: Double, posterH: Double, frame: DoubleArray, tx: Double, ty: Double): SourcePlacement {
    val x0 = frame[0]; val y0 = frame[1]; val x1 = frame[2]; val y1 = frame[3]
    val rot = ((rotation % 360) + 360) % 360
    val hDisp = if (rot == 90 || rot == 270) w0 else h0            // height of the page as displayed
    // displayed point (a, b) = [m11 m12; m21 m22] * (u - ox, v - oy) + (m13, m23)
    val (m11, m12, m13, m21, m22, m23) = when (rot) {
        90 -> doubleArrayOf(0.0, 1.0, 0.0, -1.0, 0.0, w0)
        180 -> doubleArrayOf(-1.0, 0.0, w0, 0.0, -1.0, h0)
        270 -> doubleArrayOf(0.0, -1.0, h0, 1.0, 0.0, 0.0)
        else -> doubleArrayOf(1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    }
    val e0 = x0 + pl.x - tx                                  // displayed -> page: X = sx*a + e0, Y = sy*b + f0
    val f0 = y1 - pl.y + ty - hDisp * pl.sy
    val cx1 = min(x1, x0 + posterW - tx)
    val cy0 = max(y0, y1 - (posterH - ty))
    return SourcePlacement(
        a = pl.sx * m11, b = pl.sy * m21, c = pl.sx * m12, d = pl.sy * m22,
        e = pl.sx * (m13 - m11 * ox - m12 * oy) + e0,
        f = pl.sy * (m23 - m21 * ox - m22 * oy) + f0,
        clipX = x0, clipY = cy0, clipW = cx1 - x0, clipH = y1 - cy0)
}

private operator fun DoubleArray.component6() = this[5]
