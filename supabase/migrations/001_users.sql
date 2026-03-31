-- Phase 1: Users table for auth
create extension if not exists "uuid-ossp";

create table if not exists users (
  id uuid primary key default uuid_generate_v4(),
  google_id text unique not null,
  email text unique not null,
  name text,
  picture_url text,
  access_token_encrypted text not null,
  refresh_token_encrypted text not null,
  token_expiry timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_users_google_id on users(google_id);
create index if not exists idx_users_email on users(email);
