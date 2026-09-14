create table if not exists public.store_memberships (
  user_id uuid primary key references auth.users(id) on delete cascade,
  store_id text not null references public.stores(id) on delete cascade,
  role text not null default 'OWNER' check (role in ('OWNER', 'MANAGER')),
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'SUSPENDED')),
  created_at timestamptz not null default now()
);

create index if not exists store_memberships_store_idx
  on public.store_memberships (store_id);

alter table public.store_memberships enable row level security;

create policy "members can read their membership"
  on public.store_memberships for select
  using (auth.uid() = user_id);
