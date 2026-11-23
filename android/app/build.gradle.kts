import java.io.File

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Version comes from the repo-level VERSION file (the same one the desktop release uses).
val versionText = File(rootDir.parentFile, "VERSION").takeIf { it.exists() }?.readText()?.trim() ?: "0.0.1"
val versionParts = versionText.split(".").mapNotNull { it.toIntOrNull() } + listOf(0, 0, 0)

android {
    namespace = "app.tileprint"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.tileprint"
        minSdk = 26
        targetSdk = 35
        versionName = versionText
        versionCode = versionParts[0] * 10000 + versionParts[1] * 100 + versionParts[2]
    }

    // Release signing: set TP_KEYSTORE (+ TP_KEYSTORE_PASSWORD, TP_KEY_ALIAS, TP_KEY_PASSWORD) to use your own key.
    // Without them the APK is signed with the debug key: installable, but updates need the same key each time.
    val keystore = System.getenv("TP_KEYSTORE")
    signingConfigs {
        if (!keystore.isNullOrBlank() && File(keystore).exists()) {
            create("release") {
                storeFile = File(keystore)
                storePassword = System.getenv("TP_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("TP_KEY_ALIAS")
                keyPassword = System.getenv("TP_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
    packaging {
        resources.excludes += setOf("/META-INF/{AL2.0,LGPL2.1}", "/META-INF/DEPENDENCIES", "/META-INF/LICENSE*", "/META-INF/NOTICE*")
    }
    androidResources {
        // English and Arabic only: keeps the APK small
        localeFilters += listOf("en", "ar")
    }
}

dependencies {
    implementation(project(":core"))

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.exifinterface:exifinterface:1.3.7")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    // Vector-preserving PDF composition (imports a page once as a Form XObject, like pikepdf on the desktop)
    implementation("com.tom-roush:pdfbox-android:2.0.27.0")
}
