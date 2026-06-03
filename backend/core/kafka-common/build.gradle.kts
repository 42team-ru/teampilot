group = "ru.team42.backend.kafka_common"

plugins {
    id("java-library")
}

dependencies {
    api(libs.spring.kafka)

    api(libs.spring.boot.kafka)
    compileOnly(libs.spring.boot.autoconfigure)
    compileOnly(libs.spring.boot.starter)
    annotationProcessor(libs.spring.boot.configuration.processor)

    api(libs.jackson.databind)

    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)
}