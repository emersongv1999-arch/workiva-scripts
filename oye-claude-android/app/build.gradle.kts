import java.net.URI
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Modelo pequeño de español de Vosk (https://alphacephei.com/vosk/models)
val voskModelName = "vosk-model-small-es-0.42"
val voskModelUrl = "https://alphacephei.com/vosk/models/$voskModelName.zip"
val voskAssetsDir = file("src/main/assets/model-es")

// En GitHub Actions el número de ejecución sirve como versionCode, así cada APK
// nuevo se instala encima del anterior sin desinstalar.
val buildNumber = System.getenv("GITHUB_RUN_NUMBER")?.toIntOrNull() ?: 1

android {
    namespace = "com.emersongv.oyeclaude"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.emersongv.oyeclaude"
        minSdk = 26
        targetSdk = 35
        versionCode = buildNumber
        versionName = "1.0.$buildNumber"
        buildConfigField("String", "VOSK_MODEL", "\"$voskModelName\"")
        ndk {
            // Teléfonos reales: ARM. Quita el filtro si quieres probar en un emulador x86.
            abiFilters += listOf("arm64-v8a", "armeabi-v7a")
        }
    }

    signingConfigs {
        // Llave fija incluida en el repo para que las actualizaciones se instalen
        // encima de la versión anterior. Solo para uso personal (sideload).
        create("shared") {
            storeFile = file("oyeclaude.keystore")
            storePassword = "oyeclaude"
            keyAlias = "oyeclaude"
            keyPassword = "oyeclaude"
        }
    }

    buildTypes {
        getByName("debug") {
            signingConfig = signingConfigs.getByName("shared")
        }
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("shared")
        }
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    packaging {
        // Extrae las .so al instalar (Vosk las carga vía JNA).
        jniLibs.useLegacyPackaging = true
    }

    lint {
        checkReleaseBuilds = false
        abortOnError = false
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.17.0")
    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("com.google.android.material:material:1.13.0")
    implementation("com.alphacephei:vosk-android:0.3.75@aar")
    implementation("net.java.dev.jna:jna:5.18.1@aar")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20250517")
}

// Descarga y descomprime el modelo en assets/model-es si todavía no está.
val downloadVoskModel by tasks.registering {
    group = "vosk"
    description = "Descarga $voskModelName en src/main/assets/model-es"
    onlyIf { !File(voskAssetsDir, "am/final.mdl").exists() }
    doLast {
        val workDir = layout.buildDirectory.dir("vosk").get().asFile
        val zip = File(workDir, "$voskModelName.zip")
        if (!zip.exists()) {
            workDir.mkdirs()
            logger.lifecycle("Descargando $voskModelUrl …")
            val tmp = File(workDir, "$voskModelName.zip.part")
            URI(voskModelUrl).toURL().openStream().use { input ->
                tmp.outputStream().use { output -> input.copyTo(output) }
            }
            tmp.renameTo(zip)
        }
        val unzipped = File(workDir, "unzipped")
        unzipped.deleteRecursively()
        copy {
            from(zipTree(zip))
            into(unzipped)
        }
        val modelRoot = File(unzipped, voskModelName)
        check(File(modelRoot, "am/final.mdl").exists()) { "El zip del modelo no tiene la estructura esperada" }
        voskAssetsDir.deleteRecursively()
        modelRoot.copyRecursively(voskAssetsDir, overwrite = true)
        logger.lifecycle("Modelo Vosk listo en $voskAssetsDir")
    }
}

tasks.named("preBuild") {
    dependsOn(downloadVoskModel)
}
