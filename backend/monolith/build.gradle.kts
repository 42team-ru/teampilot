group = "ru.team42.monolith"

plugins {
    alias(libs.plugins.springBoot)
    alias(libs.plugins.jib)
}

dependencies {
    implementation(project(":core:common-data"))
    implementation(project(":core:web-common"))
    implementation(project(":core:kafka-common"))

    // Web
    implementation(libs.spring.boot.starter.webmvc)
    implementation(libs.spring.boot.starter.actuator)
    implementation(libs.springdoc.webmvc)

    // Security
    implementation(libs.spring.boot.starter.security)
    implementation(libs.spring.boot.starter.security.oauth2.client)
    implementation(libs.spring.boot.starter.oauth2.resource.server)
    implementation(libs.bouncycastle.bcprov)

    // Core modules
    implementation(project(":core:kafka-common"))
    implementation(project(":core:security-common"))

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
