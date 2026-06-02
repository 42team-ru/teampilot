rootProject.name = "backend"

pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
        maven("https://packages.confluent.io/maven/")
    }
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
        maven("https://packages.confluent.io/maven/")
    }
}

include("monolith")
include("core")
include("core:common-data")
include("core:logging-common")
include("core:kafka-common")
include("core:security-common")
include("core:web-common")
include("core:s3-common")
