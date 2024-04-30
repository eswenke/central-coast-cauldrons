create table
  public.carts (
    id integer generated by default as identity,
    customer text not null default ''::text,
    class text not null default ''::text,
    level integer not null default 0,
    constraint carts_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.constants (
    id integer generated by default as identity,
    ml_capacity integer not null default 10000,
    potion_capacity integer not null default 50,
    constraint global_inventory_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.timestamps (
    id integer generated by default as identity,
    day text not null default ''::text,
    hour integer not null default 0,
    visits text[] null,
    constraint timestamps_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.processed (
    id integer not null,
    type text null default ''::text,
    constraint processed_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.potions (
    sku text not null default ''::text,
    price integer not null default 0,
    type integer[] null,
    constraint potions_pkey primary key (sku)
  ) tablespace pg_default;

create table
  public.cart_items (
    id integer generated by default as identity,
    cart integer not null default 0,
    potion text not null default ''::text,
    quantity integer not null default 0,
    constraint cart_items_pkey primary key (id),
    constraint public_cart_items_cart_fkey foreign key (cart) references carts (id) on delete cascade,
    constraint public_cart_items_potion_fkey foreign key (potion) references potions (sku)
  ) tablespace pg_default;

create table
  public.gold_ledger (
    id integer generated by default as identity,
    gold integer not null default 0,
    constraint gold_ledger_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.ml_ledger (
    id integer generated by default as identity,
    red_ml integer not null default 0,
    green_ml integer not null default 0,
    blue_ml integer not null default 0,
    dark_ml integer not null default 0,
    constraint ml_ledger_pkey primary key (id)
  ) tablespace pg_default;

create table
  public.potions_ledger (
    id integer generated by default as identity,
    quantity integer not null default 0,
    sku text not null default '0'::text,
    timestamp timestamp without time zone not null default now(),
    constraint potions_ledger_pkey primary key (id),
    constraint public_potions_ledger_sku_fkey foreign key (sku) references potions (sku)
  ) tablespace pg_default;

create table
  public.preferences (
    id integer generated by default as identity,
    day text not null default ''::text,
    pot_pref text[] null,
    constraint preferences_pkey primary key (id)
  ) tablespace pg_default;