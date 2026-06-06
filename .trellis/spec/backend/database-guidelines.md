# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

The backend uses Spring Data JPA entities and repositories in the monolith module.
Application Flyway migrations live under `backend/monolith/src/main/resources/db/migration/`
and use the `V{number}__description.sql` naming style.

---

## Query Patterns

<!-- How should queries be written? Batch operations? -->

(To be filled by the team)

---

## Migrations

Add monolith schema changes to `backend/monolith/src/main/resources/db/migration/`
with the next numeric `V{number}__description.sql` filename. When a task also
needs infrastructure bootstrap SQL, keep that in `infrastructure/database/`, but
do not treat it as a substitute for the monolith migration path.

For entities extending `AbstractStoredFileEntity`, keep SQL column definitions in
sync with the shared annotations: `bucket VARCHAR(255)`, `s3_key VARCHAR(1024)`,
`original_filename VARCHAR(512)`, `content_type VARCHAR(255)`, `size_bytes BIGINT`,
and nullable `owner_id UUID`.

---

## Naming Conventions

<!-- Table names, column names, index names -->

(To be filled by the team)

---

## Common Mistakes

<!-- Database-related mistakes your team has made -->

(To be filled by the team)
