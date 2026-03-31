-- Phase 3: Full schema — emails, personas, rules, modifications, embeddings
create extension if not exists vector;

-- ============================================================
-- EMAILS TABLE
-- ============================================================
create table if not exists emails (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade,
  gmail_message_id text not null,
  gmail_thread_id text not null,
  direction text not null check (direction in ('inbound', 'outbound')),
  from_address text,
  to_address text,
  subject text,
  body_text text,
  body_html text,
  labels text[],
  received_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, gmail_message_id)
);

create index if not exists idx_emails_user_id on emails(user_id);
create index if not exists idx_emails_gmail_thread on emails(user_id, gmail_thread_id);

-- ============================================================
-- PERSONAS TABLE
-- ============================================================
create table if not exists personas (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade unique,
  display_name text,
  tone text default 'professional',
  style_notes text,
  signature text,
  language text default 'en',
  custom_instructions text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- RULES TABLE
-- ============================================================
create table if not exists rules (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade,
  rule_text text not null,
  category text default 'general',
  is_active boolean default true,
  priority int default 0,
  created_at timestamptz default now()
);

create index if not exists idx_rules_user_id on rules(user_id);

-- ============================================================
-- MODIFICATIONS TABLE
-- ============================================================
create table if not exists modifications (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade,
  email_id uuid references emails(id) on delete set null,
  original_email_subject text,
  original_email_snippet text,
  draft_before text not null,
  draft_after text not null,
  diff_summary text,
  created_at timestamptz default now()
);

create index if not exists idx_modifications_user_id on modifications(user_id);

-- ============================================================
-- EMBEDDINGS TABLE
-- ============================================================
create table if not exists embeddings (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id) on delete cascade,
  source_type text not null check (source_type in ('email', 'rule', 'modification', 'persona')),
  source_id uuid not null,
  content_text text not null,
  embedding vector(768) not null,
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

create index if not exists idx_embeddings_user_id on embeddings(user_id);

-- HNSW index for cosine similarity
create index if not exists idx_embeddings_vector on embeddings
  using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

-- ============================================================
-- match_embeddings RPC
-- ============================================================
create or replace function match_embeddings(
  query_embedding vector(768),
  query_user_id uuid,
  filter_source_types text[] default array['email', 'rule', 'modification', 'persona'],
  match_threshold float default 0.5,
  match_count int default 10
)
returns table (
  id uuid,
  source_type text,
  source_id uuid,
  content_text text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    embeddings.id,
    embeddings.source_type,
    embeddings.source_id,
    embeddings.content_text,
    embeddings.metadata,
    1 - (embeddings.embedding <=> query_embedding) as similarity
  from embeddings
  where embeddings.user_id = query_user_id
    and embeddings.source_type = any(filter_source_types)
    and 1 - (embeddings.embedding <=> query_embedding) > match_threshold
  order by embeddings.embedding <=> query_embedding
  limit match_count;
$$;
