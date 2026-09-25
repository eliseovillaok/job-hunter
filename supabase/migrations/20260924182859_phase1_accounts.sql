-- Phase 1: accounts and persistence (spec §6.2, trimmed to what phase 1 uses).
-- Idempotent: it can run again on a database that already has it.
--
-- Access model:
--   * Supabase Auth owns identities (auth.users); profiles.id is the same uuid.
--   * The app reads and writes the user's own rows with the user's JWT, so RLS applies.
--   * Rows the user must not be able to forge or erase (usage, search runs, deletions) are
--     written only by the server with the service role.

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create or replace function private.touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- ─── profiles ───────────────────────────────────────────────────────────────
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email_display text,
  full_name text,
  country_code text,
  locale text not null default 'en' check (locale in ('es', 'en')),
  timezone text not null default 'UTC',
  onboarding_completed boolean not null default false,
  deletion_requested_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  -- user_metadata is user-editable: it is only used for the display locale, never for authorization.
  insert into public.profiles (id, locale)
  values (new.id, case when new.raw_user_meta_data ->> 'locale' = 'es' then 'es' else 'en' end)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function private.handle_new_user();

-- ─── plans (catalog: limits live here, never in code) ───────────────────────
create table if not exists public.plans (
  id text primary key,
  name text not null,
  active boolean not null default true,
  monthly_search_limit integer check (monthly_search_limit >= 0),
  sources_per_search_limit integer check (sources_per_search_limit > 0),
  results_per_search_limit integer check (results_per_search_limit > 0),
  automation_enabled boolean not null default false,
  daily_email_enabled boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Provisional free-plan limits (spec §32 #5 is still open). Change them here, not in Python.
insert into public.plans (id, name, monthly_search_limit, sources_per_search_limit, results_per_search_limit)
values ('free', 'Free', 10, 8, 30)
on conflict (id) do nothing;

-- ─── cv_documents ───────────────────────────────────────────────────────────
create table if not exists public.cv_documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  storage_path text,
  original_filename text not null,
  mime_type text not null,
  file_size_bytes integer not null check (file_size_bytes > 0),
  content_sha256 text not null,
  raw_text text,
  parsed_profile jsonb,
  parser_version text,
  status text not null default 'uploaded' check (status in ('uploaded', 'parsed', 'failed')),
  is_current boolean not null default true,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists cv_documents_user_idx on public.cv_documents (user_id, created_at desc);
create unique index if not exists cv_documents_one_current
  on public.cv_documents (user_id) where is_current and deleted_at is null;

-- ─── candidate_profiles ─────────────────────────────────────────────────────
-- `profile` is the full profile the user reviewed; the columns next to it are a queryable copy.
-- What the AI extracted, before the user touched it, stays in cv_documents.parsed_profile.
create table if not exists public.candidate_profiles (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  cv_document_id uuid references public.cv_documents (id) on delete set null,
  source text not null default 'cv' check (source in ('cv', 'manual')),
  confirmed boolean not null default false,
  headline text,
  summary text,
  years_experience numeric check (years_experience >= 0),
  seniority text,
  skills jsonb not null default '[]',
  languages jsonb not null default '[]',
  industries jsonb not null default '[]',
  target_titles jsonb not null default '[]',
  locations jsonb not null default '[]',
  remote_preference text,
  availability text,
  profile jsonb not null default '{}',
  updated_at timestamptz not null default now()
);

-- ─── search_preferences ─────────────────────────────────────────────────────
create table if not exists public.search_preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references public.profiles (id) on delete cascade,
  job_titles jsonb not null default '[]',
  keywords jsonb not null default '[]',
  locations jsonb not null default '[]',
  work_modes jsonb not null default '[]',
  job_languages jsonb not null default '[]',
  remote_only boolean not null default false,
  employment_types jsonb not null default '[]',
  salary_min numeric,
  salary_max numeric,
  salary_currency text,
  excluded_companies jsonb not null default '[]',
  excluded_terms jsonb not null default '[]',
  source_ids jsonb not null default '[]',
  min_score integer not null default 65 check (min_score between 0 and 100),
  results_limit integer not null default 40 check (results_limit > 0),
  alert_threshold numeric not null default 80,
  frequency text not null default 'daily',
  schedule_hour_local integer not null default 8 check (schedule_hour_local between 0 and 23),
  next_run_at timestamptz,
  -- Automation does not exist yet (phase 5): nobody is scheduled until they turn it on.
  active boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ─── search_runs ────────────────────────────────────────────────────────────
create table if not exists public.search_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  run_type text not null default 'manual' check (run_type in ('manual', 'automated')),
  status text not null default 'queued'
    check (status in ('queued', 'running', 'succeeded', 'partial', 'failed', 'canceled')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  sources_requested integer not null default 0,
  sources_succeeded integer not null default 0,
  jobs_seen integer not null default 0,
  jobs_new integer,             -- null until the job inventory exists (phase 3)
  matches_created integer not null default 0,
  error_summary text,
  trace_id text,
  query jsonb not null default '{}',
  funnel jsonb,
  results jsonb,                -- snapshot of the evaluated listings, without descriptions
  model_name text,
  lang text
);
create index if not exists search_runs_user_idx on public.search_runs (user_id, started_at desc);

-- ─── saved_jobs ─────────────────────────────────────────────────────────────
-- Until job_offers exists (phase 3) a listing is identified by a fingerprint and kept as a snapshot.
create table if not exists public.saved_jobs (
  user_id uuid not null references public.profiles (id) on delete cascade,
  job_key text not null,
  state text not null check (state in ('saved', 'dismissed', 'applied', 'archived')),
  job jsonb not null,
  search_run_id uuid references public.search_runs (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, job_key)
);
create index if not exists saved_jobs_state_idx on public.saved_jobs (user_id, state, updated_at desc);

-- ─── usage_events ───────────────────────────────────────────────────────────
create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  event_type text not null,
  quantity integer not null default 1 check (quantity > 0),
  dimension jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create index if not exists usage_events_user_idx on public.usage_events (user_id, event_type, created_at desc);

-- ─── account_deletions ──────────────────────────────────────────────────────
-- Minimal record that a deletion happened. user_id is cleared when it completes, so a finished
-- deletion keeps no personal data; an unfinished one keeps it so it can be completed.
create table if not exists public.account_deletions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  requested_at timestamptz not null default now(),
  completed_at timestamptz,
  last_error text
);

-- ─── updated_at ─────────────────────────────────────────────────────────────
do $$
declare
  t text;
begin
  foreach t in array array['profiles', 'plans', 'cv_documents', 'candidate_profiles',
                           'search_preferences', 'saved_jobs']
  loop
    execute format('drop trigger if exists touch_updated_at on public.%I', t);
    execute format('create trigger touch_updated_at before update on public.%I
                    for each row execute function private.touch_updated_at()', t);
  end loop;
end;
$$;

-- ─── Search quota: check and record in one step ─────────────────────────────
-- Two tabs launching at once cannot both slip past the monthly limit: the per-user advisory lock
-- serializes them. Only the server (service role) can call it.
create or replace function public.start_search_run(p_user uuid, p_monthly_limit integer, p_run jsonb)
returns uuid
language plpgsql
set search_path = ''
as $$
declare
  used integer;
  run_id uuid;
begin
  perform pg_advisory_xact_lock(hashtextextended(p_user::text, 0));
  if p_monthly_limit is not null then
    select coalesce(sum(quantity), 0) into used
    from public.usage_events
    where user_id = p_user
      and event_type = 'search_run'
      and created_at >= date_trunc('month', now() at time zone 'utc') at time zone 'utc';
    if used >= p_monthly_limit then
      return null;
    end if;
  end if;
  insert into public.search_runs (user_id, status, sources_requested, query, trace_id, model_name, lang)
  values (p_user, 'running', coalesce((p_run ->> 'sources_requested')::integer, 0),
          coalesce(p_run -> 'query', '{}'), p_run ->> 'trace_id', p_run ->> 'model_name', p_run ->> 'lang')
  returning id into run_id;
  insert into public.usage_events (user_id, event_type, dimension)
  values (p_user, 'search_run', jsonb_build_object('search_run_id', run_id));
  return run_id;
end;
$$;
revoke execute on function public.start_search_run(uuid, integer, jsonb) from public, anon, authenticated;
grant execute on function public.start_search_run(uuid, integer, jsonb) to service_role;

-- ─── Row level security ─────────────────────────────────────────────────────
alter table public.profiles enable row level security;
alter table public.plans enable row level security;
alter table public.cv_documents enable row level security;
alter table public.candidate_profiles enable row level security;
alter table public.search_preferences enable row level security;
alter table public.search_runs enable row level security;
alter table public.saved_jobs enable row level security;
alter table public.usage_events enable row level security;
alter table public.account_deletions enable row level security;

-- Nothing here is for anonymous visitors except the plan catalog.
revoke all on public.profiles, public.cv_documents, public.candidate_profiles, public.search_preferences,
  public.search_runs, public.saved_jobs, public.usage_events, public.account_deletions from anon;
-- The user reads these; only the server writes them.
revoke insert, update, delete on public.search_runs, public.usage_events, public.account_deletions,
  public.plans from authenticated;
revoke all on public.account_deletions from authenticated;
revoke insert, delete on public.profiles from authenticated;

drop policy if exists "profiles: own row" on public.profiles;
create policy "profiles: own row" on public.profiles
  for select to authenticated using ((select auth.uid()) = id);
drop policy if exists "profiles: update own row" on public.profiles;
create policy "profiles: update own row" on public.profiles
  for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

drop policy if exists "plans: active catalog" on public.plans;
create policy "plans: active catalog" on public.plans
  for select to anon, authenticated using (active);

do $$
declare
  t text;
begin
  foreach t in array array['cv_documents', 'candidate_profiles', 'search_preferences', 'saved_jobs']
  loop
    execute format('drop policy if exists "%s: own rows" on public.%I', t, t);
    execute format('create policy "%s: own rows" on public.%I for all to authenticated
                    using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id)', t, t);
  end loop;
  foreach t in array array['search_runs', 'usage_events']
  loop
    execute format('drop policy if exists "%s: read own rows" on public.%I', t, t);
    execute format('create policy "%s: read own rows" on public.%I for select to authenticated
                    using ((select auth.uid()) = user_id)', t, t);
  end loop;
end;
$$;

-- ─── Storage: original CV files, private, one folder per user ───────────────
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('cv-documents', 'cv-documents', false, 10485760,
        array['application/pdf',
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
              'text/plain'])
on conflict (id) do nothing;

drop policy if exists "cv-documents: read own" on storage.objects;
create policy "cv-documents: read own" on storage.objects
  for select to authenticated
  using (bucket_id = 'cv-documents' and (storage.foldername(name))[1] = (select auth.uid())::text);
drop policy if exists "cv-documents: upload own" on storage.objects;
create policy "cv-documents: upload own" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'cv-documents' and (storage.foldername(name))[1] = (select auth.uid())::text);
drop policy if exists "cv-documents: replace own" on storage.objects;
create policy "cv-documents: replace own" on storage.objects
  for update to authenticated
  using (bucket_id = 'cv-documents' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'cv-documents' and (storage.foldername(name))[1] = (select auth.uid())::text);
drop policy if exists "cv-documents: delete own" on storage.objects;
create policy "cv-documents: delete own" on storage.objects
  for delete to authenticated
  using (bucket_id = 'cv-documents' and (storage.foldername(name))[1] = (select auth.uid())::text);
