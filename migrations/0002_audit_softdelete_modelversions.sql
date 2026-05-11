-- 0002_audit_softdelete_modelversions.sql
-- v1.1.0 — Soft delete for training data + model version activation/metrics.
-- Safe to re-run.

-- ---------------- training_data: soft delete ----------------
alter table public.training_data
    add column if not exists deleted_at timestamptz;
alter table public.training_data
    add column if not exists deleted_by uuid references auth.users (id) on delete set null;

create index if not exists training_data_active_idx
    on public.training_data (created_at desc)
    where deleted_at is null;

-- ---------------- model_versions: activation + metrics ----------------
alter table public.model_versions
    add column if not exists is_active   boolean default false;
alter table public.model_versions
    add column if not exists file_path   text;
alter table public.model_versions
    add column if not exists fake_count  integer;
alter table public.model_versions
    add column if not exists real_count  integer;
alter table public.model_versions
    add column if not exists precision   numeric;
alter table public.model_versions
    add column if not exists recall      numeric;
alter table public.model_versions
    add column if not exists f1          numeric;

-- Only one row can be active at a time. Partial unique index ensures that
-- inserting a second is_active=true row is rejected at the database level.
create unique index if not exists model_versions_one_active_idx
    on public.model_versions (is_active)
    where is_active = true;
