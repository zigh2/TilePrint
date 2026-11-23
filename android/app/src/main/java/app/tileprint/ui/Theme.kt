package app.tileprint.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Light = lightColorScheme(
    primary = Color(0xFF2B62F0), onPrimary = Color.White,
    primaryContainer = Color(0xFFE9EFFF), onPrimaryContainer = Color(0xFF0B2A7A),
    secondaryContainer = Color(0xFFE9EFFF), onSecondaryContainer = Color(0xFF0B2A7A),
    background = Color(0xFFF3F4F7), surface = Color(0xFFFFFFFF),
    surfaceVariant = Color(0xFFEEF0F4), onSurface = Color(0xFF121722), onSurfaceVariant = Color(0xFF5A6275),
    outline = Color(0xFFCFD4DC), outlineVariant = Color(0xFFE2E5EA),
    error = Color(0xFFD6362B),
)
private val Dark = darkColorScheme(
    primary = Color(0xFF6F97FF), onPrimary = Color(0xFF0B1226),
    primaryContainer = Color(0xFF1C2C5A), onPrimaryContainer = Color(0xFFD9E3FF),
    secondaryContainer = Color(0xFF1C2C5A), onSecondaryContainer = Color(0xFFD9E3FF),
    background = Color(0xFF0D1016), surface = Color(0xFF151A23),
    surfaceVariant = Color(0xFF1F2530), onSurface = Color(0xFFE9EDF5), onSurfaceVariant = Color(0xFF9AA3B7),
    outline = Color(0xFF3A4457), outlineVariant = Color(0xFF252C3A),
    error = Color(0xFFFF6B5E),
)

@Composable
fun TilePrintTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) Dark else Light, content = content)
}
