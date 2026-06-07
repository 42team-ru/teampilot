# Research: WebM Duration Metadata Fixup in Chrome Extension Offscreen Document

- **Query**: How to fix WebM Duration metadata after MediaRecorder recording in a Chrome extension offscreen document (TypeScript/ESM, WXT framework)
- **Scope**: mixed (internal codebase + external library research)
- **Date**: 2026-06-07

---

## Context

The offscreen document at `extention/entrypoints/offscreen/main.ts` records audio with `MediaRecorder` in ~30s chunks (`audio/webm;codecs=opus`). Each chunk is sent as a raw byte array via `chrome.runtime.sendMessage` (`AUDIO_CHUNK` message) to the background, then forwarded to the Spring backend over WebSocket, and stored in MinIO.

**Problem**: `MediaRecorder` produces a "streamable" WebM — no `Duration` EBML element, no Cues/seek index. For Whisper transcription on the backend, this is mostly harmless (Whisper reads raw Opus frames regardless), but many players and some audio processing pipelines break on missing Duration.

**Constraint**: the fix must run client-side in the offscreen document. The offscreen document is a Chrome hidden page: TypeScript ESM, no Node.js APIs, no `Buffer` global, built by WXT (Vite under the hood).

---

## Findings

### Files Found

| File Path | Description |
|---|---|
| `extention/entrypoints/offscreen/main.ts` | Offscreen recording entrypoint — uses MediaRecorder, no duration fix |
| `extention/package.json` | Extension dependencies — no EBML libraries currently |
| `extention/wxt.config.ts` | WXT build config — standard Vite-based build, no special polyfills |
| `extention/tsconfig.json` | Extends WXT-generated tsconfig, `"jsx": "react-jsx"` |

### Current Recording Flow

```typescript
// extention/entrypoints/offscreen/main.ts — lines 241-272
function recordSingleChunk(durationMs: number): Promise<Blob> {
  return new Promise<Blob>((resolve, reject) => {
    const chunks: Blob[] = []
    const recorder = new MediaRecorder(mixedStream!, {
      mimeType: currentMimeType,   // "audio/webm;codecs=opus" or "audio/webm"
      audioBitsPerSecond: 128_000,
    })
    // ...
    recorder.start(5_000)  // timeslice = 5s
    recorder.onstop = () => {
      resolve(new Blob(chunks, { type: currentMimeType }))
    }
  })
}

async function sendAudioChunk(blob: Blob, finalChunk: boolean) {
  const buffer = await blob.arrayBuffer()
  const chunk = Array.from(new Uint8Array(buffer))   // sent as byte array
  await chrome.runtime.sendMessage({ type: 'AUDIO_CHUNK', chunk, ... })
}
```

The `startTime` of each chunk is not tracked — the duration must be measured externally (via `Date.now()` delta) before calling any fix library.

---

## Library Comparison

### 1. `fix-webm-duration` (RECOMMENDED)

| Property | Value |
|---|---|
| npm | `fix-webm-duration@1.0.6` |
| Published | 2024-07-04 |
| Weekly downloads | ~303,000 |
| License | MIT |
| Bundle size | 23 KB (single file, no dependencies) |
| TypeScript | Yes — ships `fix-webm-duration.d.ts` |
| ESM support | Works — UMD wrapper, Vite handles it |
| Node.js deps | **None** — pure browser JS |
| GitHub | https://github.com/yusitnikov/fix-webm-duration |

**How it works**: Parses the WebM blob in-memory using a self-contained EBML section map. Finds the `Info` section within `Segment`, locates or creates the `Duration` EBML float element, writes in the caller-supplied duration (ms), rebuilds the byte array, returns a new `Blob`. Does NOT reconstruct Cues/SeekHead — just injects Duration.

**API**:
```typescript
import fixWebmDuration from "fix-webm-duration"

// Promise style (preferred in async functions):
const fixedBlob = await fixWebmDuration(buggyBlob, durationMs, { logger: false })

// Callback style:
fixWebmDuration(buggyBlob, durationMs, (fixedBlob) => { ... })
```

**TypeScript import caveat**: issue #15 reports `Type 'typeof import(...)' has no call signatures` with `import fixWebmDuration from "fix-webm-duration"`. The workaround is:
```typescript
// Option A — default import with explicit type assertion
import fixWebmDuration from "fix-webm-duration"
// If TS complains:
import type { FixWebmDurationFunction } from "fix-webm-duration"
const fix = fixWebmDuration as unknown as FixWebmDurationFunction

// Option B — require-style
const fixWebmDuration = require("fix-webm-duration") as typeof import("fix-webm-duration").default
```

Or, add to `tsconfig.json`:
```json
{ "compilerOptions": { "esModuleInterop": true, "allowSyntheticDefaultImports": true } }
```

**Pros**:
- Zero dependencies — no Node.js `Buffer`, `events`, or `stream` polyfills needed
- ~303K weekly downloads; actively used
- Single 23 KB file — minimal bundle impact
- Works with audio-only blobs (issue #13 was a user error — passed seconds instead of ms)
- Returns a `Promise<Blob>`, drop-in for async offscreen code

**Cons**:
- Does NOT add Cues/SeekHead (no seek index) — only injects Duration
- Requires the caller to track `durationMs` externally (`Date.now()` delta before/after recording)
- Issue #26: playback pauses for 2–3 seconds in some Chrome scenarios (unrelated to Duration fixup itself)
- Chrome 138+ note (issue #27): Chromium bug 40482588 was fixed in Chrome 138, meaning the browser now writes Duration natively for some recording modes — the library gracefully skips blobs that already have Duration

---

### 2. `ts-ebml` (NOT RECOMMENDED for this use-case)

| Property | Value |
|---|---|
| npm | `ts-ebml@3.0.2` |
| Published | 2025-09-28 (v3.0.2 security/cleanup release) |
| Weekly downloads | ~30,000 |
| License | MIT |
| Bundle size | Large — pulls in `ebml`, `ebml-block`, `events`, `int64-buffer`, `matroska-schema` |
| TypeScript | Yes — full types |
| ESM support | CJS only (`main: ./lib/index.js`), has `src/esm.mts` but not published as ESM package |
| Node.js deps | **Critical issue** — heavily relies on `Buffer` (Node.js global) |
| GitHub | https://github.com/legokichi/ts-ebml |

**How it works**: Full EBML decoder/encoder/reader pipeline. `tools.makeMetadataSeekable()` extracts metadata, injects Duration + SeekHead + Cues, and produces a completely rebuilt seekable WebM. More powerful than `fix-webm-duration` but proportionally more complex.

**Key API** (for seekable conversion):
```typescript
import * as ebml from "ts-ebml"

// Step 1 — decode entire WebM
const decoder = new ebml.Decoder()
const reader = new ebml.Reader()
reader.logging = false
reader.drop_default_duration = true

const buf = await blob.arrayBuffer()
const elements = decoder.decode(buf)
elements.forEach(elm => reader.read(elm))
reader.stop()

// Step 2 — inject Duration + SeekHead + Cues
const seekableMetadata = ebml.tools.makeMetadataSeekable(
  reader.metadatas,
  reader.duration,
  reader.cues
)

// Step 3 — reconstruct blob
const body = buf.slice(reader.metadataSize)
const fixedBlob = new Blob([seekableMetadata, body], { type: blob.type })
```

**Browser/extension compatibility issues**:
- **`Buffer` is not defined** (GitHub issues #25, #37 — both OPEN since 2019–2021, never fixed): `lib/tools.js` calls `Buffer.from(...)` and `Buffer.alloc(...)` throughout. In a browser/extension without a `Buffer` polyfill, this crashes at runtime.
- **Vite/WXT workaround**: Add to `vite.config.ts` (or WXT's `vite` option):
  ```typescript
  resolve: { alias: { buffer: 'buffer/' } }
  plugins: [inject({ Buffer: ['buffer', 'Buffer'] })]
  ```
  Requires `npm install buffer` (the npm `buffer` package — browser polyfill). This adds ~7 KB to the bundle but fixes the issue.
- **No ESM export in published package**: Only ships CJS (`./lib/index.js`). Vite can handle CJS but tree-shaking is lost.
- **Chrome 131 regression** (issue #56): After Chrome 131, `makeMetadataSeekable` produces non-seekable output in some cases. The `hiroMTB/ts-ebml` fork has a fix (`Timecode → TimeStamp` rename for Chrome's changed output), but the upstream `legokichi/ts-ebml` does not.
- **Issue #55**: `makeMetadataSeekable` returns broken WebM on server-side (Node.js) in some cases.

**Pros**:
- Full seekable WebM output (Duration + SeekHead + Cues)
- Maintained (v3.0.2 released Sep 2025 — CVE fixes, dependency cleanup)
- Comprehensive EBML parsing — can decode any element

**Cons**:
- `Buffer` not defined in browser/extension without a polyfill — requires Vite config changes
- Heavy dependency tree (6 runtime deps, some with sub-deps)
- Chrome 131+ regression in upstream repo
- No native ESM module export in published package
- 10x fewer weekly downloads than `fix-webm-duration`

---

### 3. `webm-duration-fix`

| Property | Value |
|---|---|
| npm | `webm-duration-fix@1.0.4` |
| Published | 2022-04-04 |
| Weekly downloads | ~48,000 |
| License | ISC |
| TypeScript | No (no `.d.ts`) |
| Node.js deps | `buffer`, `ebml-block`, `events`, `int64-buffer` — all require polyfills |
| GitHub | https://github.com/buynao/webm-duration-fix |

**Notes**: A fork/rewrite of ts-ebml focused on large files (>2 GB). Still depends on Node.js globals. Not recommended — same polyfill issues as ts-ebml with fewer users and no TypeScript types.

---

### 4. `ebml-wasm` (not found on npm)

No package named `ebml-wasm` exists on npm as of 2026-06-07. This approach would require a custom Rust/C WASM build, which is out of scope for this project.

---

### 5. Custom EBML Parser (Zero-dependency)

Writing a minimal EBML parser inline in TypeScript is feasible for Duration injection only. The EBML structure needed:

```
Segment (0x18538067)
  └─ Info (0x1549A966)
       └─ Duration (0x4489) — float64 in TimecodeScale units (default 1ms)
```

Key steps:
1. Find `Info` container bytes via ID scan (`0x1549A966`)
2. Scan for `Duration` (`0x4489`) inside — if found, patch the 8-byte IEEE 754 value; if not found, insert new element bytes
3. Adjust VINT-encoded sizes of `Info` and `Segment` containers

**Pros**: Zero dependencies, zero polyfills, full control, ~100 LOC
**Cons**: VINT encoding/decoding for EBML sizes is non-trivial; if `Info` size uses unknown-size encoding (Chrome sometimes does this), patching is harder

---

### 6. Backend-side ffmpeg

Process the uploaded chunks server-side (Spring backend) after MinIO storage:

```java
// After storing chunks to MinIO, concatenate and remux:
// ffmpeg -i input.webm -c copy output.webm
```

**Pros**: No client changes; handles all formats; robust
**Cons**:
- Chunks are sent as 30s increments — ffmpeg would need to run per-chunk or after all chunks are assembled
- Adds latency to Whisper transcription pipeline
- Requires ffmpeg binary in the Spring container
- Doesn't help if Duration is needed for in-browser playback before upload

---

## Recommendation

**Use `fix-webm-duration`** for client-side Duration injection in the offscreen document.

Rationale:
1. **No polyfills** — works in the extension's browser context without Vite config changes
2. **Tiny** — 23 KB, zero deps, pure browser JS
3. **Well-used** — 303K downloads/week vs ts-ebml's 30K
4. **Simple API** — single async call wrapping each `recordSingleChunk` result
5. **Audio-only confirmed working** — issue #13 was a usage error (seconds vs ms)

The only prerequisite is tracking `durationMs` per chunk:

```typescript
// In recordSingleChunk or its caller:
const startTime = Date.now()
const blob = await recordSingleChunk(CHUNK_DURATION_MS)
const durationMs = Date.now() - startTime

import fixWebmDuration from "fix-webm-duration"
const fixedBlob = await fixWebmDuration(blob, durationMs, { logger: false })
// Send fixedBlob instead of blob
```

**If full seekable WebM (with Cues) is ever needed** (e.g., for in-browser <audio> scrubbing), use `ts-ebml` with the following Vite polyfill config added to `wxt.config.ts`:

```typescript
// wxt.config.ts
import { defineConfig } from "wxt"
import inject from "@rollup/plugin-inject"

export default defineConfig({
  vite: () => ({
    resolve: { alias: { buffer: "buffer/" } },
    plugins: [inject({ Buffer: ["buffer", "Buffer"] })],
    optimizeDeps: { include: ["buffer"] },
  }),
  // ...
})
```

And `npm install buffer @rollup/plugin-inject`.
Note: use `hiroMTB/ts-ebml` fork or apply the `Timecode → Timestamp` patch for Chrome 131+ compatibility.

---

## Chrome 138+ Note

Chromium bug 40482588 (MediaRecorder not writing Duration) was reportedly fixed in Chrome 138. Since this is a Chrome extension context, if the minimum Chrome target is 138+, the Duration fix may not be needed at all. However, Chrome stable as of June 2026 may not universally be 138+ for all users, and the fix is cheap enough to apply unconditionally (the library skips blobs that already have valid Duration).

---

## Caveats / Not Found

- `ebml-wasm` does not exist on npm
- `fixwebmduration` does not exist on npm (the correct package name is `fix-webm-duration`)
- ts-ebml issue #56 (Chrome 131+ regression in `makeMetadataSeekable`) has no upstream fix as of Sep 2025; workaround is the `hiroMTB/ts-ebml` fork
- The custom EBML parser approach was not prototyped — complexity estimate is based on EBML spec analysis
- Whisper (backend) may not require Duration at all — missing Duration is a player-only problem; if Whisper transcription is the only consumer, the Duration fix may be optional
