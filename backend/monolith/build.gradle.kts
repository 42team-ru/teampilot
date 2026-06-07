group = "ru.team42.monolith"

plugins {
    alias(libs.plugins.springBoot)
    alias(libs.plugins.jib)
    alias(libs.plugins.openapi.generator)
}

dependencies {
    // Core modules
    implementation(project(":core:common-data"))
    implementation(project(":core:web-common"))
    implementation(project(":core:kafka-common"))
    implementation(project(":core:kafka-proto-common"))
    implementation(project(":core:security-common"))
    implementation(project(":core:s3-common"))

    // Web
    implementation(libs.spring.boot.starter.webmvc)
    implementation(libs.spring.boot.starter.websocket)
    implementation(libs.spring.boot.starter.actuator)
    implementation(libs.springdoc.webmvc)
    implementation(libs.spring.boot.starter.webflux)

    // Security
    implementation(libs.spring.boot.starter.security)
    implementation(libs.jjwt.api)
    runtimeOnly(libs.jjwt.impl)
    runtimeOnly(libs.jjwt.jackson)

    // Database
    implementation(libs.spring.boot.starter.validation)
    runtimeOnly(libs.postgresql)
    implementation(libs.spring.boot.starter.data.jpa)

    // Annotation processors
    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)
    implementation(libs.mapstruct)
    annotationProcessor(libs.mapstruct.processor)

    // HTML parsing
    implementation("org.jsoup:jsoup:1.17.2")

    // Testing
    testImplementation(libs.spring.security.test)
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

openApiGenerate {
    generatorName.set("java")
    inputSpec.set("$projectDir/src/main/resources/openapi/yougile.json")
    outputDir.set("${layout.buildDirectory.get()}/generated/openapi")
    apiPackage.set("ru.team42.monolith.client.yougile.api")
    modelPackage.set("ru.team42.monolith.client.yougile.model")
    validateSpec.set(false)
    skipValidateSpec.set(true)
    schemaMappings.set(
        mapOf(
            "location" to "String"
        )
    )
    configOptions.set(
        mapOf(
            "library" to "webclient",
            "useJakartaEe" to "true",
            "useSpringBoot3" to "false",
            "serializationLibrary" to "jackson",
            "openApiNullable" to "false",
            "useSpringBoot4" to "true",
        )
    )
}

sourceSets {
    main {
        java {
            srcDir("${layout.buildDirectory.get()}/generated/openapi/src/main/java")
        }
    }
}

tasks.compileJava {
    dependsOn(tasks.openApiGenerate)
}
