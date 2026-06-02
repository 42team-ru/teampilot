group = "ru.team42.backend.room_common"

plugins {
    id("java-library")
}

dependencies {
    api(libs.spring.boot.autoconfigure)

    compileOnly(libs.spring.boot.starter.websocket)
    compileOnly(libs.spring.boot.starter.web)
    compileOnly(libs.spring.boot.starter.security)
    compileOnly(libs.jackson.databind)

    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    testCompileOnly(libs.lombok)
    testAnnotationProcessor(libs.lombok)
}
