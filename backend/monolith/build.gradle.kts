group = "ru.team42.monolith"

plugins {
    alias(libs.plugins.springBoot)
    alias(libs.plugins.jib)
}

dependencies {
    // Core modules
    implementation(project(":core:common-data"))
    implementation(project(":core:web-common"))
    implementation(project(":core:kafka-common"))
    implementation(project(":core:security-common"))

    // Web
    implementation(libs.spring.boot.starter.webmvc)
    implementation(libs.spring.boot.starter.actuator)
    implementation(libs.springdoc.webmvc)

    // Security
    implementation(libs.spring.boot.starter.security)

    // Database
    implementation(libs.spring.boot.starter.validation)
    runtimeOnly(libs.postgresql)
    implementation(libs.spring.boot.starter.data.jpa)

    // Annotation processors
    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)
    implementation(libs.mapstruct)
    annotationProcessor(libs.mapstruct.processor)

    // Testing
    testImplementation(libs.spring.security.test)
}
