# Flip Extension Live Transcript Log Order

## Goal

Show live transcript events in the extension sidepanel in chronological order: older entries at the top, newer transcript entries at the bottom.

## Requirements

* Live transcript/event log displays old entries above new entries.
* Keep limiting the visible live log to the latest 20 stored events.
* Keep automatic scrolling to the newest entry when new live events arrive.
* Do not change backend/WebSocket/storage event contracts.

## Acceptance Criteria

* [ ] Given stored live events `[old, middle, new]`, the sidepanel live tab renders `old`, then `middle`, then `new`.
* [ ] When a new transcript event arrives, it is appended visually at the bottom of the live log.
* [ ] The live tab still scrolls to the newest entry after updates.
* [ ] Extension build/type validation for the changed code passes or any pre-existing blockers are reported.

## Definition of Done

* Tests/build checks run where practical.
* Lint/type/build issues from this change are fixed.
* Existing user changes outside this task are not touched.
* No spec update unless this reveals a durable project convention.

## Technical Approach

`extension/services/storage.ts` already appends live events in chronological order using `push`. The current reversed visual order comes from `extension/components/sidepanel/LiveTab.tsx`, where the component uses `events.slice(-20).reverse()`. Change the displayed list to keep the sliced order while preserving the existing `endRef` scroll target.

## Decision (ADR-lite)

**Context**: The UI currently reverses the latest 20 live events, placing the newest item first.
**Decision**: Remove the UI reversal and render the latest 20 events in storage order.
**Consequences**: The newest transcript entry appears at the bottom, matching chat/log conventions and the existing scroll-to-bottom behavior.

## Out of Scope

* Changing event creation, backend WebSocket payloads, or storage schema.
* Adding new live-log filters or visual redesign.
* Re-encoding existing mojibake Russian strings in unrelated files.

## Technical Notes

* Relevant spec: `.trellis/spec/frontend/extension-integrations.md`.
* Relevant files inspected:
  * `extension/components/sidepanel/LiveTab.tsx`
  * `extension/services/storage.ts`
  * `extension/types/recording.ts`
