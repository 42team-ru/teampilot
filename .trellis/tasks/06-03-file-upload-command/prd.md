# PRD: File Upload Command (Bot -> MinIO -> Kafka)

## Goal
Add a dedicated Telegram bot `/upload` command that accepts a file, stores it in MinIO, publishes a `files.uploaded` Kafka event, and persists the uploaded-file metadata in the Spring backend.

## Data Flow
Telegram user sends `/upload` -> bot waits for a file -> bot downloads Telegram file bytes -> bot uploads to MinIO -> bot publishes `FileUploadedEvent` to Kafka topic `files.uploaded` -> Spring consumer reads event -> backend stores metadata in `uploaded_files`.

## Bot Requirements
- Add Kafka topic constant `FILES_UPLOADED = "files.uploaded"`.
- Add Pydantic event model `FileUploadedEvent` with:
  - `user_id: int`
  - `chat_id: int`
  - `username: str | None`
  - `first_name: str | None`
  - `original_filename: str`
  - `content_type: str`
  - `minio_bucket: str`
  - `minio_key: str`
  - `file_size: int`
  - `uploaded_at: datetime`
- Add async MinIO client service using aioboto3 and configuration values:
  - `MINIO_ENDPOINT`
  - `MINIO_ACCESS_KEY`
  - `MINIO_SECRET_KEY`
  - `MINIO_BUCKET`
- MinIO keys must use `uploads/{chat_id}/{uuid4}/{filename}`.
- Add `FileUploadStates.waiting_for_file`.
- Add `/upload` handler:
  - `/upload` replies with a prompt to send a file and sets waiting state.
  - While waiting, accept `document`, `audio`, `voice`, `video`, `photo`, and `video_note`.
  - Download file bytes through the bot API.
  - Upload to MinIO.
  - Publish `FileUploadedEvent` to `Topics.FILES_UPLOADED`.
  - Reply with confirmation and MinIO key.
  - Clear FSM state after success.
  - For non-file messages while waiting, reply that a file is expected and `/cancel` can cancel.
- Register upload router in `bot/main.py` before existing passive file/group routers.
- Add `aioboto3` to `bot/requirements.txt` if missing.

## Spring / Backend Requirements
- Add Kafka topic constant `FILES_UPLOADED = "files.uploaded"` in kafka-common.
- Add Java `FileUploadedEvent` modeled after the existing event classes:
  - `userId`
  - `chatId`
  - `username`
  - `firstName`
  - `originalFilename`
  - `contentType`
  - `bucket`
  - `s3Key`
  - `fileSize`
  - `uploadedAt`
- Add `UploadedFile` entity extending the existing stored-file base entity and adding Telegram metadata:
  - `telegramUserId`
  - `telegramChatId`
  - `telegramUsername`
  - `telegramFirstName`
- Add database migration `V002__CREATE_UPLOADED_FILES.sql` creating:
  - `id UUID PRIMARY KEY`
  - `bucket VARCHAR(255) NOT NULL`
  - `s3_key VARCHAR(1000) NOT NULL`
  - `original_filename VARCHAR(500)`
  - `content_type VARCHAR(255)`
  - `size_bytes BIGINT`
  - `owner_id UUID`
  - Telegram metadata columns
  - `created_at` / `updated_at` timestamptz defaults
- Add `UploadedFileRepository` extending the stored-file repository abstraction with:
  - `findByTelegramUserId(Long userId)`
  - `findByTelegramChatId(Long chatId)`
- Add `FileUploadService` that saves uploaded-file metadata from events.
- Add `FileUploadConsumer` modeled after the existing chat/message consumers:
  - `@KafkaListener(topics = KafkaTopics.FILES_UPLOADED)`
  - deserialize JSON into `FileUploadedEvent`
  - delegate persistence to `FileUploadService`.

## Acceptance Criteria
- `/upload` starts an FSM upload session and accepts the supported Telegram file message types.
- Successful uploads result in an object stored in MinIO under the required key shape.
- Successful uploads publish a `files.uploaded` event with matching Python and Java field contracts.
- Spring consumes the event and stores a row in `uploaded_files`.
- Existing passive file handling remains separate from the new command flow.
- Relevant lint/type-check/test commands are run where available, or any inability to run them is documented.
