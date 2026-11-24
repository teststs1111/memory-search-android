plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "jp.teststs1111.memorysearch"
    compileSdk = 35

    defaultConfig {
        applicationId = "jp.teststs1111.memorysearch"
        minSdk = 26
        targetSdk = 35
        versionCode = 8
        versionName = "0.8.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // Reuse the original Chapter 1 reference image without modifying it.
    sourceSets.getByName("main").assets.srcDir("../reference/chapter_01")
    // Reference OCR diagnostics are included only in debug builds.
    sourceSets.getByName("debug").assets.srcDir("../reference/chapter_05")

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("com.google.mlkit:text-recognition-japanese:16.0.1")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
