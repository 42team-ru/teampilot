group = "ru.team42.monolith"

plugins {
    alias(libs.plugins.springBoot)
    alias(libs.plugins.jib)
}

dependencies {
    implementation(project(":core:common-data"))
    implementation(project(":core:web-common"))

    // Web
    implementation(libs.spring.boot.starter.webmvc)
    implementation(libs.spring.boot.starter.actuator)
    implementation(libs.springdoc.webmvc)

    // Security
    implementation(libs.spring.boot.starter.security)
    implementation(libs.spring.boot.starter.security.oauth2.client)
    implementation(libs.bouncycastle.bcprov)

    // Database
    implementation(libs.spring.boot.starter.flyway)
    implementation(libs.flyway.database.postgresql)
    implementation(libs.spring.boot.starter.validation)
    runtimeOnly(libs.postgresql)
    implementation(libs.spring.boot.starter.data.jpa)

    // Annotation processors
    implementation(libs.mapstruct)
    annotationProcessor(libs.mapstruct.processor)

    // Testing
    testImplementation(libs.spring.security.test)
}
