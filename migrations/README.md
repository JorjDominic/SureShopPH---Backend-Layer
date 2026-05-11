# SureShopPH Backend — Database Migrations

The full current schema lives in [`supabase_schema.sql`](../supabase_schema.sql).
This folder tracks **incremental** migrations so a Supabase project that was
provisioned from an earlier version of `supabase_schema.sql` can be upgraded
in place without dropping data.

## How to apply

1. Open the Supabase **SQL editor** for your project.
2. Run the migrations **in numerical order**, skipping any you have already
   applied. Every migration in this folder is written to be **idempotent**
   (`if not exists`, `add column if not exists`, etc.), so re-running a
   migration is safe.
3. Record applied migrations in your team’s ops log.

## Current files

| File | Purpose |
|---|---|
| `0001_initial.sql` | Snapshot of the v1.0 schema (mirrors `supabase_schema.sql` as of that release). |
| `0002_audit_softdelete_modelversions.sql` | v1.1.0 additions: `training_data` soft-delete columns, `model_versions.is_active` + `file_path` + per-class metrics, supporting indexes. |

## Adding a new migration

* Use the next sequential 4-digit prefix (e.g. `0003_…`).
* Keep each migration **forward-only** and **idempotent**.
* Update `supabase_schema.sql` to reflect the new "current" state so a fresh
  install via that single file is equivalent to running every migration.
