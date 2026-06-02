group = "ru.team42.backend.grpc_common"


plugins {
    id("java-library")
    alias(libs.plugins.protobuf)
}


dependencies {
    // Protobuf + gRPC runtime
    api(libs.protobuf.java)
    api(libs.protobuf.java.util)
    api(libs.grpc.protobuf)
    api(libs.grpc.stub)
    api(libs.grpc.services)          // health check
    api(libs.grpc.netty.shaded)
    api(libs.confluent.protobuf.serializer)
    // @javax.annotation.Generated на сгенерированных классах
    compileOnly(libs.javax.annotation.api)


    // Spring Boot autoconfiguration
    compileOnly(libs.spring.boot.autoconfigure)
    compileOnly(libs.spring.boot.starter)
    annotationProcessor(libs.spring.boot.configuration.processor)


    compileOnly(libs.lombok)
    annotationProcessor(libs.lombok)
}


protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:${libs.versions.protobuf.get()}"
    }
    plugins {
        create("grpc") {
            artifact = "io.grpc:protoc-gen-grpc-java:${libs.versions.grpc.get()}"
        }
    }
    generateProtoTasks {
        all().forEach { task ->
            task.builtins {
                named("java")
            }
            task.plugins {
                create("grpc")
            }
        }
    }
}
