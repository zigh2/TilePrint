package app.tileprint.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.AspectRatio
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.LockOpen
import androidx.compose.material.icons.outlined.OpenWith
import androidx.compose.material.icons.outlined.Print
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material3.FilledTonalIconToggleButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.tileprint.EditorViewModel
import app.tileprint.R
import app.tileprint.UiState
import app.tileprint.core.Paper
import app.tileprint.core.ScaleMode
import app.tileprint.core.Settings

@Composable
fun SettingsPanel(state: UiState, vm: EditorViewModel, onChangeFile: () -> Unit, modifier: Modifier = Modifier) {
    val s = state.settings
    val unit = s.unit
    val src = state.source
    val job = state.job
    val unitLabel = unitName(unit)

    Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        // ---- source
        SectionCard(stringResource(R.string.source), Icons.Outlined.Description) {
            if (src != null) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Column(Modifier.weight(1f)) {
                        Text(src.name, fontWeight = FontWeight.SemiBold, maxLines = 1)
                        val (w, h) = src.sizes[s.pageIndex.coerceIn(0, src.pageCount - 1)]
                        Text("${fmt(unit.fromPt(w))} × ${fmt(unit.fromPt(h))} $unitLabel" +
                            (src.pixelW?.let { " · $it×${src.pixelH} px" } ?: ""),
                            fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    TextButton(onClick = onChangeFile) { Text(stringResource(R.string.change)) }
                }
                if (src.pageCount > 1) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { vm.setPage(s.pageIndex - 1) }, enabled = s.pageIndex > 0) {
                            Icon(Icons.AutoMirrored.Outlined.ArrowBack, null)
                        }
                        Text(stringResource(R.string.page_label, s.pageIndex + 1, src.pageCount), Modifier.weight(1f),
                            fontWeight = FontWeight.SemiBold, fontSize = 14.sp, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
                        IconButton(onClick = { vm.setPage(s.pageIndex + 1) }, enabled = s.pageIndex < src.pageCount - 1) {
                            Icon(Icons.AutoMirrored.Outlined.ArrowForward, null)
                        }
                    }
                }
            }
            FieldLabel(stringResource(R.string.units))
            Segmented(
                listOf(Paper.Unit.MM to stringResource(R.string.unit_mm), Paper.Unit.CM to stringResource(R.string.unit_cm),
                    Paper.Unit.IN to stringResource(R.string.unit_in)),
                unit, { u -> vm.update { it.copy(unit = u) } })
        }

        // ---- final size
        SectionCard(stringResource(R.string.final_size), Icons.Outlined.AspectRatio) {
            FieldLabel(stringResource(R.string.size))
            val custom = s.posterPreset == "Custom"
            val isoA = Paper.presetOrder.filter { it.length == 2 && it[0] == 'A' }
            val isoB = Paper.presetOrder.filter { it.length == 2 && it[0] == 'B' }
            val us = Paper.presetOrder.filter { it !in isoA && it !in isoB }
            fun item(n: String): DropItem {
                val (w, h) = Paper.sizesPt.getValue(n)
                return DropItem(n, "$n — ${fmt(unit.fromPt(w))} × ${fmt(unit.fromPt(h))} $unitLabel")
            }
            DropdownField(
                if (custom) stringResource(R.string.custom) else item(s.posterPreset).label,
                listOf(DropGroup(stringResource(R.string.group_iso_a), isoA.map(::item)),
                    DropGroup(stringResource(R.string.group_iso_b), isoB.map(::item)),
                    DropGroup(stringResource(R.string.group_us), us.map(::item)),
                    DropGroup(null, listOf(DropItem("Custom", stringResource(R.string.custom))))),
                vm::choosePreset)
            if (custom) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    NumberField(stringResource(R.string.width), s.posterW, unitLabel, unit::fromPt, unit::toPt,
                        { vm.setPosterSize(it, null) }, Modifier.weight(1f))
                    FilledTonalIconToggleButton(checked = s.lockAspect, onCheckedChange = { c -> vm.update { it.copy(lockAspect = c) } }) {
                        Icon(if (s.lockAspect) Icons.Outlined.Lock else Icons.Outlined.LockOpen, stringResource(R.string.keep_ratio))
                    }
                    NumberField(stringResource(R.string.height), s.posterH, unitLabel, unit::fromPt, unit::toPt,
                        { vm.setPosterSize(null, it) }, Modifier.weight(1f))
                }
            } else {
                FieldLabel(stringResource(R.string.orientation))
                Segmented(orientOptions(), s.posterOrient, { o -> vm.update { it.copy(posterOrient = o) } })
            }
            FieldLabel(stringResource(R.string.scaling))
            Segmented(
                listOf(ScaleMode.FIT to stringResource(R.string.fit), ScaleMode.FILL to stringResource(R.string.fill),
                    ScaleMode.STRETCH to stringResource(R.string.stretch)),
                s.scaleMode, { m -> vm.update { it.copy(scaleMode = m) } })
            OutlinedButton(onClick = vm::resetPosition, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Outlined.OpenWith, null, Modifier.padding(end = 8.dp))
                Text(stringResource(R.string.reset_position))
            }
            job?.dpi?.let { dpi ->
                val low = dpi < 150
                Column {
                    Text(stringResource(if (low) R.string.dpi_low else R.string.dpi_ok, Math.round(dpi).toInt()),
                        fontWeight = FontWeight.SemiBold,
                        color = if (low) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary)
                    if (low) Text(stringResource(R.string.dpi_low_d), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        // ---- printer paper
        SectionCard(stringResource(R.string.printer_paper), Icons.Outlined.Print) {
            FieldLabel(stringResource(R.string.paper))
            fun pitem(n: String): DropItem {
                val (w, h) = Paper.sizesPt.getValue(n)
                return DropItem(n, "$n — ${fmt(unit.fromPt(w))} × ${fmt(unit.fromPt(h))} $unitLabel")
            }
            val isoA = Paper.presetOrder.filter { it.length == 2 && it[0] == 'A' }
            val isoB = Paper.presetOrder.filter { it.length == 2 && it[0] == 'B' }
            val us = Paper.presetOrder.filter { it !in isoA && it !in isoB }
            DropdownField(pitem(s.paper).label,
                listOf(DropGroup(stringResource(R.string.group_iso_a), isoA.map(::pitem)),
                    DropGroup(stringResource(R.string.group_iso_b), isoB.map(::pitem)),
                    DropGroup(stringResource(R.string.group_us), us.map(::pitem))),
                { n -> vm.update { it.copy(paper = n) } })
            FieldLabel(stringResource(R.string.orientation))
            Segmented(orientOptions(), s.paperOrient, { o -> vm.update { it.copy(paperOrient = o) } })
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NumberField(stringResource(R.string.margin), s.margin, unitLabel, unit::fromPt, unit::toPt,
                    { v -> vm.update { it.copy(margin = v) } }, Modifier.weight(1f))
                NumberField(stringResource(R.string.arrow_band), s.header, unitLabel, unit::fromPt, unit::toPt,
                    { v -> vm.update { it.copy(header = v) } }, Modifier.weight(1f))
            }
            NumberField(stringResource(R.string.overlap), s.overlap, unitLabel, unit::fromPt, unit::toPt,
                { v -> vm.update { it.copy(overlap = v) } }, Modifier.fillMaxWidth(), allowZero = true)
            Text(stringResource(if (s.overlap < 0.01) R.string.overlap_hint_0 else R.string.overlap_hint_n),
                fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            FieldLabel(stringResource(R.string.numbering))
            Segmented(listOf("seq" to stringResource(R.string.num_seq), "rc" to stringResource(R.string.num_rc)),
                s.numbering, { n -> vm.update { it.copy(numbering = n) } })
        }

        // ---- options
        SectionCard(stringResource(R.string.sheet_details), Icons.Outlined.Tune) {
            SwitchRow(stringResource(R.string.smart_cut), stringResource(R.string.smart_cut_d), s.smartCut) { v -> vm.update { it.copy(smartCut = v) } }
            SwitchRow(stringResource(R.string.skip_blank), stringResource(R.string.skip_blank_d), s.skipBlank) { v -> vm.update { it.copy(skipBlank = v) } }
            SwitchRow(stringResource(R.string.crop_marks), stringResource(R.string.crop_marks_d), s.cropMarks) { v -> vm.update { it.copy(cropMarks = v) } }
            SwitchRow(stringResource(R.string.overlap_ticks), stringResource(R.string.overlap_ticks_d), s.overlapTicks, enabled = s.overlap >= 0.01) { v -> vm.update { it.copy(overlapTicks = v) } }
            SwitchRow(stringResource(R.string.footer), stringResource(R.string.footer_d), s.footer) { v -> vm.update { it.copy(footer = v) } }
            SwitchRow(stringResource(R.string.scale_ruler), stringResource(R.string.scale_ruler_d), s.scaleBar) { v -> vm.update { it.copy(scaleBar = v) } }
            SwitchRow(stringResource(R.string.blank_backs), stringResource(R.string.blank_backs_d), s.blankBacks) { v -> vm.update { it.copy(blankBacks = v) } }
            FooterNameField(s.footerText) { t -> vm.update { it.copy(footerText = t) } }
        }
    }
}

@Composable
private fun orientOptions() = listOf(
    Settings.Orient.AUTO to stringResource(R.string.auto),
    Settings.Orient.PORTRAIT to stringResource(R.string.portrait),
    Settings.Orient.LANDSCAPE to stringResource(R.string.landscape),
)

@Composable
private fun unitName(u: Paper.Unit) = stringResource(when (u) {
    Paper.Unit.MM -> R.string.unit_mm
    Paper.Unit.CM -> R.string.unit_cm
    Paper.Unit.IN -> R.string.unit_in
})

private fun fmt(v: Double): String {
    val r = Math.round(v * 100) / 100.0
    return if (r == Math.floor(r)) r.toLong().toString() else r.toString()
}
