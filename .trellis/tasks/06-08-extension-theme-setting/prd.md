# Add Theme Selection To Extension Settings

## Goal

Add a theme selector to the browser extension settings so users can choose how the popup and sidepanel are displayed.

## Requirements

* Add theme choices in the existing settings screen: system, light, and dark.
* Persist the selected theme in `chrome.storage.local` so it survives reopening the extension.
* Apply the selected theme to extension UIs that use `extension/assets/globals.css`.
* For the system choice, follow `prefers-color-scheme` and react to system changes while the UI is open.
* Keep the change frontend-only; do not involve backend APIs.

## Acceptance Criteria

* [ ] Settings screen shows a clear theme section with three choices.
* [ ] Selecting dark immediately applies the existing `.dark` CSS variables.
* [ ] Selecting light immediately removes the `.dark` class.
* [ ] Selecting system follows the browser/OS color scheme.
* [ ] The saved theme is restored when popup or sidepanel opens again.
* [ ] Extension type-check/build passes.

## Definition of Done

* Lint/type-check/build for the extension is run where available.
* Existing user or repository changes are preserved.
* No backend, bot, or unrelated extension behavior is changed.

## Technical Approach

Use the existing Tailwind `darkMode: ['class']` setup and the existing `.dark` CSS variable block in `extension/assets/globals.css`. Add a small theme settings service/hook around `chrome.storage.local`, then mount it in popup and sidepanel apps so both entrypoints stay in sync.

## Decision (ADR-lite)

**Context**: The repo already has class-based dark mode but no user-facing control.

**Decision**: Use a three-state preference (`system`, `light`, `dark`) and apply the resolved mode by toggling `.dark` on `document.documentElement`.

**Consequences**: This keeps the implementation small and compatible with existing styles. Future theme variants would need a broader token model, but that is outside this MVP.

## Out of Scope

* Custom color palettes beyond light/dark.
* Backend/user-profile synchronization.
* Theme controls outside the extension settings screen.

## Technical Notes

* Existing settings component: `extension/components/popup/SettingsScreen.tsx`.
* Existing extension entrypoints: `extension/entrypoints/popup/App.tsx`, `extension/entrypoints/sidepanel/App.tsx`.
* Current theme infrastructure: `extension/tailwind.config.ts` uses `darkMode: ['class']`; `extension/assets/globals.css` defines `.dark`.
* Existing settings storage pattern: `extension/services/micSettings.ts`.
