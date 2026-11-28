package app.tileprint.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SectionCard(title: String, icon: ImageVector, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Icon(icon, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                Text(title, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
            }
            content()
        }
    }
}

@Composable
fun FieldLabel(text: String) {
    Text(text, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@Composable
fun <T> Segmented(options: List<Pair<T, String>>, selected: T, onSelect: (T) -> Unit, modifier: Modifier = Modifier) {
    SingleChoiceSegmentedButtonRow(modifier.fillMaxWidth()) {
        options.forEachIndexed { index, (value, label) ->
            SegmentedButton(
                selected = value == selected,
                onClick = { onSelect(value) },
                shape = SegmentedButtonDefaults.itemShape(index, options.size),
                icon = {},
            ) { Text(label, fontSize = 12.5.sp, maxLines = 1) }
        }
    }
}

@Composable
fun SwitchRow(title: String, subtitle: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f)) {
            Text(title, fontWeight = FontWeight.Medium, fontSize = 14.sp)
            Text(subtitle, fontSize = 11.5.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, lineHeight = 15.sp)
        }
        Switch(checked = checked, onCheckedChange = onChange, enabled = enabled)
    }
}

/** A length field shown in [unitLabel]; [valuePt] is the model value, [toUnit]/[fromUnit] convert. */
@Composable
fun NumberField(
    label: String, valuePt: Double, unitLabel: String, toUnit: (Double) -> Double, fromUnit: (Double) -> Double,
    onCommit: (Double) -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, allowZero: Boolean = false,
) {
    val shown = format(toUnit(valuePt))
    var text by remember { mutableStateOf(shown) }
    var focused by remember { mutableStateOf(false) }
    if (!focused && text != shown) text = shown            // follow external changes (undo, aspect lock, unit switch)

    fun commit() {
        val v = parseDecimal(text)
        if (v != null && (v > 0 || (allowZero && v == 0.0))) onCommit(fromUnit(v)) else text = shown
    }
    OutlinedTextField(
        value = text,
        onValueChange = { text = it },
        label = { Text(label) },
        suffix = { Text(unitLabel, fontSize = 12.sp) },
        singleLine = true,
        enabled = enabled,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal, imeAction = ImeAction.Done),
        keyboardActions = KeyboardActions(onDone = { commit() }),
        modifier = modifier.onFocusChanged { f ->
            if (focused && !f.isFocused) commit()
            focused = f.isFocused
        },
    )
}

private fun format(v: Double): String {
    val r = Math.round(v * 100) / 100.0
    return if (r == Math.floor(r)) r.toLong().toString() else r.toString()
}

private fun parseDecimal(s: String): Double? =
    s.map { c -> if (c in '٠'..'٩') '0' + (c - '٠') else if (c == '٫' || c == ',') '.' else c }
        .joinToString("").trim().toDoubleOrNull()

class DropItem(val value: String, val label: String)
class DropGroup(val title: String?, val items: List<DropItem>)

@Composable
fun DropdownField(selectedLabel: String, groups: List<DropGroup>, onSelect: (String) -> Unit, modifier: Modifier = Modifier) {
    var open by remember { mutableStateOf(false) }
    Box(modifier.fillMaxWidth()) {
        OutlinedButton(onClick = { open = true }, modifier = Modifier.fillMaxWidth().height(48.dp)) {
            Text(selectedLabel, modifier = Modifier.weight(1f), maxLines = 1)
            Icon(Icons.Filled.ArrowDropDown, null)
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            groups.forEachIndexed { gi, g ->
                if (gi > 0) HorizontalDivider()
                g.title?.let {
                    Text(it, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp))
                }
                g.items.forEach { item ->
                    DropdownMenuItem(text = { Text(item.label) }, onClick = { open = false; onSelect(item.value) })
                }
            }
        }
    }
}

@Composable
fun VSpace(h: Int) = Spacer(Modifier.height(h.dp))

@Composable
fun FooterNameField(value: String, onCommit: (String) -> Unit) {
    var text by remember(value) { mutableStateOf(value) }
    var focused by remember { mutableStateOf(false) }
    OutlinedTextField(
        value = text,
        onValueChange = { text = it.take(120) },
        label = { Text(androidx.compose.ui.res.stringResource(app.tileprint.R.string.footer_name)) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
        keyboardActions = KeyboardActions(onDone = { onCommit(text.trim()) }),
        modifier = Modifier.fillMaxWidth().onFocusChanged { f ->
            if (focused && !f.isFocused) onCommit(text.trim())
            focused = f.isFocused
        },
    )
}
