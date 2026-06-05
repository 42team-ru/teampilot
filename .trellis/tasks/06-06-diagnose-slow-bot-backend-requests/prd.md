# Diagnose Slow Bot Backend Requests

## Problem

Backend endpoints respond quickly from Postman (~12 ms), but requests made by the Telegram bot feel slow. The user already tried moving work to threads, so the likely issue is in the bot event loop, connection setup, request fan-out, or delayed callback acknowledgement.

## Goals

- Add enough instrumentation to distinguish:
  - event-loop stalls before requests start
  - DNS/connect delays
  - backend response time
  - body-read time
- Reduce common local HTTP client latency causes, especially `localhost` IPv6 fallback on Windows.
- Move synchronous Kafka publish work off the event loop so it cannot delay bot update processing.
- Keep backend contracts unchanged.
- Keep the bot async-first; do not move aiohttp calls into threads.

## Non-Goals

- Do not rewrite all handlers.
- Do not change backend code unless local evidence points there.
- Do not remove existing logs.

## Acceptance Criteria

- HTTP client logs phase timings for slow requests.
- Bot logs event-loop stalls when callbacks or blocking code stop the loop.
- HTTP connector can force IPv4 by default to avoid `localhost` IPv6 delays.
- HTTP client uses separate connect/read timeout values.
- Kafka publish does not execute synchronous producer calls on the event loop.
- Changed Python files compile successfully.
