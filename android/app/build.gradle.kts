import java.util.Properties
import java.io.FileInputStream

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    id("com.google.gms.google-services")
}

// load release signing config from android/key.properties (not committed)
val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    namespace = "com.carekw.care_mobile"
    compileSdk = 36
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // flutter_local_notifications schedules with java.time, which needs
        // desugaring to run on the older API levels we still support.
        isCoreLibraryDesugaringEnabled = true
    }

    defaultConfig {
        // The Play Console listing was created as "care.app", and a published
        // package name can never change — so this MUST stay care.app.
        // (`namespace` above is only the internal Kotlin/R package and is
        // intentionally left as com.carekw.care_mobile.)
        applicationId = "care.app"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // نقتصر على arm64-v8a (APK + AAB): مكتبات flutter_webrtc/mlkit الأصلية
        // تُحشر لكل المعماريات فتتضخّم الحزمة فوق 100MB (حدّ GitHub). arm64 يغطّي
        // ~99% من الأجهزة. نستخدم .add() لا += (الأخيرة تعدّل نسخة فلا تؤثّر).
        ndk {
            abiFilters.clear()
            abiFilters.add("arm64-v8a")
        }
    }

    signingConfigs {
        create("release") {
            if (keystorePropertiesFile.exists()) {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                storeFile = rootProject.file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
            }
        }
    }

    buildTypes {
        release {
            // R8 otherwise fails on ML Kit script recognisers we do not bundle
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            signingConfig = if (keystorePropertiesFile.exists())
                signingConfigs.getByName("release") else signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

// Google Play requires every native library to support 16 KB memory pages.
// mobile_scanner 5.x pulls old MLKit + CameraX whose .so files are aligned to
// 4 KB (libbarhopper_v3.so, libimage_processing_util_jni.so); these newer
// releases ship 16 KB-aligned binaries. Gradle resolves to the highest version,
// so declaring them here upgrades what the plugin brings in.
dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")
    implementation("androidx.camera:camera-core:1.4.2")
    implementation("androidx.camera:camera-camera2:1.4.2")
    implementation("androidx.camera:camera-lifecycle:1.4.2")
    implementation("androidx.camera:camera-view:1.4.2")
}

flutter {
    source = "../.."
}
