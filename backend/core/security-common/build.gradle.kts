group = "ru.team42.backend.security_common"

plugins {
    id("java-library")
}

dependencies {
    api(libs.spring.boot.autoconfigure)
    api(libs.spring.boot.starter.security)

    compileOnly(libs.spring.boot.starter.web)

    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)
}
