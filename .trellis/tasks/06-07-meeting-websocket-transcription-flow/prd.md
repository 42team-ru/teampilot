# Meeting WebSocket transcription flow

## Goal

Add live meeting support: managers create a meeting for a team, one primary recorder streams audio chunks over Spring WebSocket/STOMP, Spring stores chunks in MinIO and publishes Kafka events, the LLM worker transcribes with Whisper using an accumulated sliding context, extracts tasks/statuses/summary context, and Spring broadcasts live results back to subscribed meeting clients.

## What I already know

* User requested Spring WebSocket/WebSTOMP and explicitly asked to use Context7.
* User requested no tests for this task.
* A `Meeting` entity must be attached to `Team` and contain `meetingUrl` for Yandex Telemost.
* Only a manager should be able to create a meeting using `url + teamId`.
* Audio should arrive as chunks, be stored in MinIO, and publish Kafka events.
* Existing backend has `Team`, `TeamUser`, manager checks, MinIO `S3Service`, Kafka publishers/consumers, and LLM event consumers.
* Existing LLM worker already handles `audio.new`: MinIO download, Whisper transcription, transcript chunking, task/status extraction, file summary, and publishing `llm.tasks.create`, `llm.status.change`, `files.transcript_ready`.

## Assumptions

* The meeting creator is the `primaryRecorder`; only this user may send audio chunks that Spring persists and publishes. Other team members may connect and subscribe to live results.
* WebSocket auth uses the existing authenticated user model where possible; STOMP clients pass the same auth material used by REST (`Authorization` JWT or `X-Telegram-Id`) during connect/send.
* A chunk is sent as a STOMP JSON message with base64-encoded audio bytes. This keeps the first implementation simple and avoids binary STOMP converter work.
* Spring broadcasts results to `/topic/meetings/{meetingId}/results`; clients send chunks to `/app/meetings/{meetingId}/chunks`.
* LLM worker publishes a new Kafka result event for live meeting output; existing `llm.tasks.create` and `llm.status.change` remain the source of DB task mutations.

## Requirements

* Add backend `Meeting` persistence attached to `Team`.
* Add manager-only REST endpoint to create a meeting from `teamId` and `meetingUrl`.
* Add GET endpoint to resolve an active meeting by `meetingUrl`.
* If a lookup by `meetingUrl` finds nothing, return an error telling the user that the manager has not attached this meeting to a team yet and should be asked to create it.
* Add Spring WebSocket/STOMP configuration and endpoint.
* Add STOMP message handler for meeting audio chunks.
* Store each accepted chunk in MinIO using a deterministic meeting/chunk object key.
* Publish a Kafka event for each stored meeting chunk with meeting/team metadata, S3 location, chunk index, and team context needed by the LLM worker.
* Reject chunks from non-members and from users other than `primaryRecorder`.
* Add LLM worker consumer for meeting chunk events.
* LLM worker downloads chunk audio, converts/transcribes with Whisper, accumulates transcript context per meeting, and periodically runs extraction on the accumulated window.
* LLM worker publishes live meeting results back to Spring with transcript text, summary/context, extracted task candidates, and status changes.
* Spring consumes meeting result events and broadcasts them over STOMP to all subscribers of that meeting.
* Do not add tests.
* Add a usage document explaining REST auth, meeting lookup/creation, STOMP destinations, chunk payloads, live result payloads, and internal Kafka flow.

## Acceptance Criteria

* A manager can `POST` a meeting with `teamId` and `meetingUrl`; non-managers are rejected by existing team-role rules.
* A client can `GET` an active meeting by `meetingUrl`.
* Unknown `meetingUrl` returns a user-facing not-found error that asks the user to contact the manager.
* Created meeting stores `team`, `meetingUrl`, `primaryRecorder`, and active status.
* Spring exposes a STOMP endpoint and destination for meeting chunks.
* Accepted chunks are uploaded to MinIO and produce Kafka events.
* LLM worker consumes meeting chunk events, transcribes via existing Whisper integration, keeps a sliding text context, and emits live result events.
* Spring broadcasts live results to the meeting topic.
* Usage documentation exists for client/backend integration.
* Gradle/Python syntax checks pass where feasible, without adding or running tests unless unavoidable.

## Out of Scope

* Browser extension UI changes.
* Realtime speaker diarization.
* Perfect deduplication of repeated partial LLM output.
* Durable distributed meeting transcript state across LLM worker restarts.
* End-to-end integration tests.

## Research References

* [`research/spring-websocket-stomp.md`](research/spring-websocket-stomp.md) — Context7-backed Spring WebSocket/STOMP setup notes.

## Technical Notes

* Spring Boot version: 4.0.3.
* Boot docs identify `spring-boot-starter-websocket` as the starter for MVC WebSocket/STOMP support.
* Spring Framework docs use `@EnableWebSocketMessageBroker`, `WebSocketMessageBrokerConfigurer`, STOMP endpoint registration, `setApplicationDestinationPrefixes`, and `/topic`/`/queue` broker destinations.
* Project Kafka spec: Spring → Python JSON uses camelCase; Python Pydantic models need aliases. Python → Spring inbound consumers currently use snake_case-compatible mapper behavior.
* Monolith currently uses `spring.jpa.hibernate.ddl-auto=update`; backend spec still asks new monolith schema migrations under `backend/monolith/src/main/resources/db/migration/`.
