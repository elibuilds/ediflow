create extension if not exists pgcrypto;

create table if not exists public.stores (
  id text primary key,
  name text not null,
  latitude double precision,
  longitude double precision,
  created_at timestamptz not null default now()
);

create table if not exists public.inventory_items (
  id uuid primary key default gen_random_uuid(),
  store_id text not null references public.stores(id),
  sku text not null,
  name text not null,
  quantity integer not null check (quantity >= 0),
  expires_in_days integer not null check (expires_in_days >= 0),
  refrigeration_required boolean not null default false,
  unit_price_usd numeric(10,2) not null check (unit_price_usd >= 0),
  source text not null default 'ims',
  synced_at timestamptz not null default now(),
  unique (store_id, sku)
);

create table if not exists public.flash_sale_listings (
  id uuid primary key default gen_random_uuid(),
  store_id text not null references public.stores(id),
  inventory_item_id uuid references public.inventory_items(id),
  sku text not null,
  name text not null,
  quantity_available integer not null check (quantity_available >= 0),
  original_unit_price_usd numeric(10,2) not null check (original_unit_price_usd >= 0),
  sale_unit_price_usd numeric(10,2) not null check (sale_unit_price_usd >= 0),
  discount_percent integer not null check (discount_percent between 50 and 70),
  expires_at timestamptz not null,
  status text not null default 'PUBLISHED'
    check (status in ('PUBLISHED', 'SOLD_OUT', 'EXPIRED', 'CANCELLED')),
  created_at timestamptz not null default now()
);

create table if not exists public.reservations (
  id uuid primary key default gen_random_uuid(),
  listing_id uuid not null references public.flash_sale_listings(id),
  quantity integer not null check (quantity > 0),
  resident_reference text not null,
  status text not null default 'CONFIRMED'
    check (status in ('PENDING', 'CONFIRMED', 'FULFILLED', 'EXPIRED', 'CANCELLED')),
  created_at timestamptz not null default now()
);

create table if not exists public.rescue_runs (
  id uuid primary key default gen_random_uuid(),
  store_id text not null references public.stores(id),
  idempotency_key text not null unique,
  status text not null default 'STARTED',
  agent_output text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists flash_sale_store_status_idx
  on public.flash_sale_listings (store_id, status);
create index if not exists reservations_listing_idx
  on public.reservations (listing_id);

alter table public.stores enable row level security;
alter table public.inventory_items enable row level security;
alter table public.flash_sale_listings enable row level security;
alter table public.reservations enable row level security;
alter table public.rescue_runs enable row level security;

create or replace function public.reserve_flash_sale(
  requested_listing_id uuid,
  requested_quantity integer,
  requested_resident_reference text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  listing public.flash_sale_listings;
  reservation public.reservations;
begin
  if requested_quantity <= 0 then
    raise exception using errcode = '22023', message = 'quantity must be positive';
  end if;

  select * into listing
  from public.flash_sale_listings
  where id = requested_listing_id
    and status = 'PUBLISHED'
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'Flash-sale listing not found';
  end if;
  if listing.quantity_available < requested_quantity then
    raise exception using errcode = 'P0001', message = 'Not enough inventory available';
  end if;

  update public.flash_sale_listings
  set quantity_available = quantity_available - requested_quantity,
      status = case when quantity_available - requested_quantity = 0
                    then 'SOLD_OUT' else status end
  where id = requested_listing_id;

  insert into public.reservations (listing_id, quantity, resident_reference)
  values (requested_listing_id, requested_quantity, requested_resident_reference)
  returning * into reservation;

  return jsonb_build_object(
    'reservation_id', reservation.id,
    'listing_id', reservation.listing_id,
    'quantity', reservation.quantity,
    'resident_reference', reservation.resident_reference,
    'status', reservation.status
  );
end;
$$;
