group = "ru.team42.backend.s3_common"

plugins {
    id("java-library")
}

dependencies {
    api(libs.aws.s3)
    api(project(":core:common-data"))

    compileOnly(libs.spring.boot.starter.data.jpa)
    compileOnly(libs.spring.boot.autoconfigure)
    compileOnly(libs.spring.boot.starter)
    annotationProcessor(libs.spring.boot.configuration.processor)

    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)
}
