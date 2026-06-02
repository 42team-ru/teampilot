group = "ru.team42.backend.logging_common"

plugins {
    id("java-library")
}

dependencies {
    api(libs.logstash.logback.encoder)
    api(libs.loki4j)
    api(libs.spring.boot.starter.actuator)
    api(libs.micrometer.registry.prometheus)

    api(libs.spring.boot.starter.aspectj)

    api(libs.spring.boot.autoconfigure)

    compileOnly(libs.spring.boot.starter.web)

    compileOnly(libs.spring.boot.starter.webflux)

    compileOnly(libs.spring.security.web)

    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)
}