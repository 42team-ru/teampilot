group = "ru.team42.backend.web_common"

plugins {
    id("java-library")
}

dependencies {
    api(libs.spring.boot.autoconfigure)

    implementation(libs.springdoc.webmvc)

    compileOnly(libs.spring.boot.starter.web)
    compileOnly(libs.spring.boot.starter.validation)
    compileOnly(libs.spring.data.commons)
    compileOnly(libs.spring.security.web)

    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)
}
