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
        versionCode = 6
        versionName = "0.6.0"
    }

    // Reuse the original Chapter 1 reference image without modifying it.
    sourceSets.getByName("main").assets.srcDir("../reference/chapter_01")

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
}
