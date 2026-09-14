create table if not exists public.pantries (
  id text primary key,
  name text not null,
  capacity_units integer not null check (capacity_units >= 0),
  accepts_refrigerated boolean not null default false,
  distance_km numeric(8,2) not null check (distance_km >= 0),
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.pantry_allocations (
  id uuid primary key default gen_random_uuid(),
  store_id text references public.stores(id),
  pantry_id text not null references public.pantries(id),
  allocated_units integer not null check (allocated_units > 0),
  inventory jsonb not null,
  status text not null default 'ALLOCATED'
    check (status in ('ALLOCATED', 'PICKUP_PENDING', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED')),
  created_at timestamptz not null default now()
);

create table if not exists public.volunteers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  vehicle text not null,
  active boolean not null default true,
  available boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.dispatches (
  id uuid primary key default gen_random_uuid(),
  allocation_id uuid not null references public.pantry_allocations(id),
  volunteer_id uuid not null references public.volunteers(id),
  status text not null default 'OFFERED'
    check (status in ('OFFERED', 'ACCEPTED', 'EN_ROUTE', 'PICKED_UP', 'DELIVERED', 'FAILED', 'CANCELLED')),
  pickup_location jsonb,
  dropoff_location text not null,
  estimated_eta_minutes integer not null check (estimated_eta_minutes >= 0),
  confirmation_token text not null default ('EDIFLOW-' || upper(substr(encode(gen_random_bytes(8), 'hex'), 1, 16))),
  created_at timestamptz not null default now()
);

create index if not exists pantry_allocations_store_status_idx
  on public.pantry_allocations (store_id, status);
create index if not exists pantry_allocations_pantry_status_idx
  on public.pantry_allocations (pantry_id, status);
create index if not exists dispatches_allocation_idx
  on public.dispatches (allocation_id);

alter table public.pantries enable row level security;
alter table public.pantry_allocations enable row level security;
alter table public.volunteers enable row level security;
alter table public.dispatches enable row level security;

insert into public.pantries (id, name, capacity_units, accepts_refrigerated, distance_km)
values
  ('PANTRY-NORTH-01', 'Hope Community Shelter & Pantry', 50, true, 2.40),
  ('PANTRY-WEST-02', 'Grace Table Food Bank', 10, true, 5.10)
on conflict (id) do nothing;

insert into public.volunteers (name, vehicle)
values
  ('Volunteer Ama', 'Hatchback - Tag #7312'),
  ('Volunteer Mark', 'Van - Tag #2841')
on conflict do nothing;
