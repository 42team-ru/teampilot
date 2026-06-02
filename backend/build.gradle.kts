import io.spring.gradle.dependencymanagement.dsl.DependencyManagementExtension

plugins {
    java
    idea
    alias(libs.plugins.springBoot) apply false
    alias(libs.plugins.dependencyManagement) apply false
    alias(libs.plugins.jib) apply false
}

subprojects {
    apply(plugin = "java")
    apply(plugin = "io.spring.dependency-management")
    apply(plugin = "idea")

    the<DependencyManagementExtension>().apply {
        imports {
            mavenBom(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)
        }
    }
    java {
        toolchain {
            languageVersion = JavaLanguageVersion.of(rootProject.libs.versions.java.get())
        }
    }

    configurations {
        compileOnly {
            extendsFrom(configurations.annotationProcessor.get())
        }
    }

    dependencies {
        // Annotation Processors
        compileOnly(rootProject.libs.lombok)
        annotationProcessor(rootProject.libs.lombok)
    }

    tasks.withType<Test> {
        useJUnitPlatform()
    }

    configurations.all {
        exclude(group = "io.swagger.core.v3", module = "swagger-annotations")
    }

    plugins.withId("com.google.cloud.tools.jib") {
        configure<com.google.cloud.tools.jib.gradle.JibExtension> {
            from {
                image = "eclipse-temurin:25-jre-alpine"
            }
            to {
                image = "ghcr.io/42team-ru/${project.name}:latest"
            }
            container {
                jvmFlags = listOf("-Xms256m", "-Xmx512m")
            }
        }
    }

    group = "ru.team42.backend"
    version = "0.0.1-SNAPSHOT"
}

tasks.test {
    useJUnitPlatform()
}