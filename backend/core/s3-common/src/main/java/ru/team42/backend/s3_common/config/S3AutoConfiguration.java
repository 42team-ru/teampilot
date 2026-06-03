package ru.team42.backend.s3_common.config;

import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import ru.team42.backend.s3_common.service.S3Service;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3Configuration;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

import java.net.URI;

@AutoConfiguration
@ConditionalOnClass(S3Client.class)
@EnableConfigurationProperties(S3Properties.class)
public class S3AutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public S3Client s3Client(S3Properties props) {
        var credentials = StaticCredentialsProvider.create(
                AwsBasicCredentials.create(props.getAccessKey(), props.getSecretKey()));

        var builder = S3Client.builder()
                .region(Region.of(props.getRegion()))
                .credentialsProvider(credentials)
                .serviceConfiguration(S3Configuration.builder()
                        .pathStyleAccessEnabled(true)
                        .build());

        if (props.getEndpoint() != null && !props.getEndpoint().isBlank()) {
            builder.endpointOverride(URI.create(props.getEndpoint()));
        }

        return builder.build();
    }

    @Bean
    @ConditionalOnMissingBean
    public S3Presigner s3Presigner(S3Properties props) {
        var credentials = StaticCredentialsProvider.create(
                AwsBasicCredentials.create(props.getAccessKey(), props.getSecretKey()));

        var builder = S3Presigner.builder()
                .region(Region.of(props.getRegion()))
                .credentialsProvider(credentials)
                .serviceConfiguration(S3Configuration.builder()
                        .pathStyleAccessEnabled(true)
                        .build());

        String presignEndpoint = (props.getPresignedEndpoint() != null && !props.getPresignedEndpoint().isBlank())
                ? props.getPresignedEndpoint()
                : props.getEndpoint();
        if (presignEndpoint != null && !presignEndpoint.isBlank()) {
            builder.endpointOverride(URI.create(presignEndpoint));
        }

        return builder.build();
    }

    @Bean
    @ConditionalOnMissingBean
    public S3Service s3Service(S3Client s3Client, S3Presigner s3Presigner, S3Properties props) {
        return new S3Service(s3Client, s3Presigner, props.getPresignedUrlExpiry());
    }

    @Bean
    @ConditionalOnProperty(prefix = "app.s3", name = "default-bucket")
    public ApplicationRunner s3BucketInitializer(S3Service s3Service, S3Properties props) {
        return args -> s3Service.ensureBucketExists(props.getDefaultBucket());
    }
}
