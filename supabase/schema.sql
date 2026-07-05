-- KLH Poetry — comments + feedback with back-end moderation
-- Run once in Supabase → SQL Editor. Safe to re-run.

-- ---------- COMMENTS (public after approval) ----------
create table if not exists public.comments (
  id          bigint generated always as identity primary key,
  scope       text not null check (scope in ('page','guestbook')),
  page_id     text,                       -- slug for 'page' scope; null for guestbook
  body        text not null check (char_length(trim(body)) between 1 and 4000),
  status      text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at  timestamptz not null default now(),
  approved_at timestamptz
);
create index if not exists comments_public_idx
  on public.comments (scope, page_id, created_at desc) where status = 'approved';
create index if not exists comments_pending_idx
  on public.comments (created_at) where status = 'pending';

-- ---------- FEEDBACK (operator-only, never public) ----------
create table if not exists public.feedback (
  id          bigint generated always as identity primary key,
  body        text not null check (char_length(trim(body)) between 1 and 4000),
  page_id     text,                       -- where the reader was (context)
  status      text not null default 'pending' check (status in ('pending','reviewed')),
  created_at  timestamptz not null default now()
);

-- ---------- Row Level Security ----------
alter table public.comments enable row level security;
alter table public.feedback enable row level security;

-- Public (anon) may SUBMIT only as pending
drop policy if exists comments_insert on public.comments;
create policy comments_insert on public.comments
  for insert to anon with check (status = 'pending');

-- Public (anon) may READ only approved comments
drop policy if exists comments_select_approved on public.comments;
create policy comments_select_approved on public.comments
  for select to anon using (status = 'approved');

-- Feedback: anyone may SUBMIT as pending; NO anon SELECT (operator-only via dashboard/service role)
drop policy if exists feedback_insert on public.feedback;
create policy feedback_insert on public.feedback
  for insert to anon with check (status = 'pending');
