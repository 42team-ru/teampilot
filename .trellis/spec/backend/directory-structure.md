# Directory Structure

> How backend code is organized in this project.

---

## Overview

<!--
Document your project's backend directory structure here.

Questions to answer:
- How are modules/packages organized?
- Where does business logic live?
- Where are API endpoints defined?
- How are utilities and helpers organized?
-->

(To be filled by the team)

---

## Directory Layout

```
<!-- Replace with your actual structure -->
src/
├── ...
└── ...
```

---

## Module Organization

<!-- How should new features/modules be organized? -->

(To be filled by the team)

---

## Naming Conventions

<!-- File and folder naming rules -->

(To be filled by the team)

---

## API Routing

- Spring MVC controllers and generated Swagger expose routes without an `/api` prefix, for example `/tasks` and `/teams`.
- Public traffic uses Caddy's `/api/*` route; Caddy strips `/api` before proxying the request to the backend.
- Internal clients that connect directly to Spring, including the bot's local `BACKEND_URL`, must use the unprefixed Swagger route.

---

## Examples

<!-- Link to well-organized modules as examples -->

(To be filled by the team)
