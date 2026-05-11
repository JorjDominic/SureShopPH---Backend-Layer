-- Run this in the Supabase SQL editor.
-- The `profiles` table already exists — do not recreate.

-- ---------- access_tokens ----------
create table if not exists public.access_tokens (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users (id) on delete cascade,
    token_hash text not null,
    revoked boolean default false,
    created_at timestamptz default now()
);
alter table public.access_tokens enable row level security;
create policy "access_tokens_owner_select"
    on public.access_tokens for select
    using (auth.uid() = user_id);
create policy "access_tokens_owner_insert"
    on public.access_tokens for insert
    with check (auth.uid() = user_id);
create policy "access_tokens_owner_update"
    on public.access_tokens for update
    using (auth.uid() = user_id);

-- ---------- scan_history ----------
create table if not exists public.scan_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users (id) on delete cascade,
    platform text,
    url text,
    risk_score integer,
    risk_level text,
    flags jsonb,
    confidence_level text,
    confidence_pct integer,
    scan_mode text,
    created_at timestamptz default now()
);
alter table public.scan_history enable row level security;
create policy "scan_history_owner_select"
    on public.scan_history for select
    using (auth.uid() = user_id);
create policy "scan_history_owner_insert"
    on public.scan_history for insert
    with check (auth.uid() = user_id);

-- ---------- high_risk_listings ----------
create table if not exists public.high_risk_listings (
    id uuid primary key default gen_random_uuid(),
    url text,
    platform text,
    risk_score integer,
    risk_level text,
    flags jsonb,
    verified boolean default false,
    verified_by uuid references auth.users (id),
    created_at timestamptz default now()
);
alter table public.high_risk_listings enable row level security;
-- All authenticated users can read public high-risk listings
create policy "high_risk_listings_authenticated_read"
    on public.high_risk_listings for select
    using (auth.role() = 'authenticated');

-- ---------- user_reports ----------
create table if not exists public.user_reports (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users (id) on delete cascade,
    listing_url text,
    report_type text,
    description text,
    created_at timestamptz default now()
);
alter table public.user_reports enable row level security;
create policy "user_reports_owner_select"
    on public.user_reports for select
    using (auth.uid() = user_id);
create policy "user_reports_owner_insert"
    on public.user_reports for insert
    with check (auth.uid() = user_id);

-- ---------- admin_logs ----------
create table if not exists public.admin_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users (id) on delete cascade,
    action text,
    details jsonb,
    created_at timestamptz default now()
);
alter table public.admin_logs enable row level security;
-- Admin-only read; service role bypasses RLS
create policy "admin_logs_admin_read"
    on public.admin_logs for select
    using (
        exists (
            select 1 from public.profiles p
            where p.id = auth.uid() and p.role = 'admin'
        )
    );

-- ---------- training_data ----------
-- Labeled review samples submitted by admins for retraining the fake-review classifier.
create table if not exists public.training_data (
    id uuid primary key default gen_random_uuid(),
    text text not null,
    is_fake boolean not null,
    notes text,
    submitted_by uuid references auth.users (id) on delete set null,
    created_at timestamptz default now()
);
alter table public.training_data enable row level security;
-- Admin-only access; service role bypasses RLS for backend writes
create policy "training_data_admin_read"
    on public.training_data for select
    using (
        exists (
            select 1 from public.profiles p
            where p.id = auth.uid() and p.role = 'admin'
        )
    );
create policy "training_data_admin_insert"
    on public.training_data for insert
    with check (
        exists (
            select 1 from public.profiles p
            where p.id = auth.uid() and p.role = 'admin'
        )
    );
create policy "training_data_admin_delete"
    on public.training_data for delete
    using (
        exists (
            select 1 from public.profiles p
            where p.id = auth.uid() and p.role = 'admin'
        )
    );

-- ---------- model_versions ----------
-- Bookkeeping for trained model snapshots (accuracy, sample count, trained_at).
create table if not exists public.model_versions (
    id uuid primary key default gen_random_uuid(),
    sample_count integer not null,
    accuracy numeric,
    notes text,
    trained_by uuid references auth.users (id) on delete set null,
    created_at timestamptz default now()
);
alter table public.model_versions enable row level security;
create policy "model_versions_admin_read"
    on public.model_versions for select
    using (
        exists (
            select 1 from public.profiles p
            where p.id = auth.uid() and p.role = 'admin'
        )
    );


-- ===================================================================
-- v1.1.0 additions: soft-delete, model versioning, metrics columns
-- (Idempotent: safe to re-run.)
-- ===================================================================

-- training_data: soft-delete columns
alter table public.training_data add column if not exists deleted_at timestamptz;
alter table public.training_data add column if not exists deleted_by uuid references auth.users (id) on delete set null;
create index if not exists training_data_active_idx
    on public.training_data (created_at desc) where deleted_at is null;

-- model_versions: activation flag + on-disk path + per-class metrics
alter table public.model_versions add column if not exists is_active boolean default false;
alter table public.model_versions add column if not exists file_path text;
alter table public.model_versions add column if not exists fake_count integer;
alter table public.model_versions add column if not exists real_count integer;
alter table public.model_versions add column if not exists precision numeric;
alter table public.model_versions add column if not exists recall numeric;
alter table public.model_versions add column if not exists f1 numeric;
-- Only one row may be active at a time
create unique index if not exists model_versions_one_active_idx
    on public.model_versions (is_active) where is_active = true;
