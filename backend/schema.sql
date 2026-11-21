-- THHT production schema. No participant reads; researcher reads require a server-managed UUID allowlist.
create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to anon, authenticated;
create table private.researchers (
  user_id uuid primary key references auth.users(id) on delete cascade,
  added_at timestamptz not null default now()
);
alter table private.researchers enable row level security;
revoke all on private.researchers from public, anon, authenticated;
create table public.responses (
  participant_id uuid primary key,
  received_at timestamptz not null default now(),
  receipt_id uuid not null unique default gen_random_uuid(),
  payload jsonb not null check (jsonb_typeof(payload) = 'object')
);
alter table public.responses enable row level security;
revoke all on public.responses from public, anon, authenticated;
grant select on public.responses to authenticated;
create index responses_received_at_idx on public.responses(received_at);
create table private.submission_keys (
  participant_id uuid primary key references public.responses(participant_id),
  token_hash bytea not null,
  payload_hash bytea not null
);
alter table private.submission_keys enable row level security;
revoke all on private.submission_keys from public, anon, authenticated;
create function private.is_researcher() returns boolean language sql stable security definer
set search_path = '' as $$
  select exists(select 1 from private.researchers where user_id = (select auth.uid()));
$$;
revoke all on function private.is_researcher() from public, anon;
grant execute on function private.is_researcher() to authenticated;
create policy researcher_read on public.responses for select to authenticated
using ((select private.is_researcher()));
create function public.researcher_access() returns boolean language sql stable security invoker
set search_path = '' as $$ select private.is_researcher(); $$;
revoke all on function public.researcher_access() from public, anon;
grant execute on function public.researcher_access() to authenticated;

-- Only a receipt is returned; the secret retry token is never returned, logged, or published.
create function private.submit_thht(record jsonb, submission_token text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  pid uuid; saved public.responses%rowtype; key_row private.submission_keys%rowtype;
  clean jsonb; digest bytea; token_digest bytea; n integer; easy integer; hard integer;
  i integer; x integer; shs_total integer := 0; ids jsonb; status text;
begin
  if jsonb_typeof(record) is distinct from 'object' or octet_length(record::text) > 100000
     or submission_token is null or submission_token !~ '^[a-zA-Z0-9_-]{40,128}$' then
    raise exception 'Invalid submission' using errcode='22023';
  end if;
  if record->>'study_id' is distinct from 'thht_ai_video'
     or coalesce(record->>'protocol_version','') not in ('thht-online-v7-tomato-20261121','thht-online-v7-peach-20261121')
     or coalesce(record->>'attention_version','') not in ('wedding-fruit-tomato-v1','wedding-fruit-peach-v1')
     or record->>'preview_mode' is distinct from 'false'
     or record->>'consent' is distinct from 'true' or record->>'age_eligible' is distinct from 'true'
     or coalesce(record->>'condition','') not in ('fruit_violent','fruit_nonviolent') then
    raise exception 'Invalid study record' using errcode='22023';
  end if;
  pid := (record->>'participant_id')::uuid;
  if pid is null then raise exception 'Participant ID required' using errcode='22023'; end if;
  status := record->>'completion_status';
  if coalesce(status,'') not in ('complete','withdrawn_during_study') then
    raise exception 'Invalid completion status' using errcode='22023';
  end if;
  clean := record - 'submission_status';
  if status = 'complete' then
    ids := record->'selected_puzzle_ids';
    if jsonb_typeof(ids) is distinct from 'array' then raise exception 'Invalid puzzles' using errcode='22023'; end if;
    select count(distinct value), count(*) filter(where value ~ '^P0[1-9]$' or value='P10'),
           count(*) filter(where value ~ '^P2[1-9]$' or value='P30')
      into n,easy,hard from jsonb_array_elements_text(ids);
    if n<>11 or jsonb_array_length(ids)<>11 or exists(
      select 1 from jsonb_array_elements_text(ids) where value !~ '^P(0[1-9]|[12][0-9]|30)$')
      or record->>'watch_ok' is distinct from 'true' or record->>'withdrawn' is distinct from 'false'
      or coalesce(record->>'attention_response','') not in ('banana','tomato','peach','blueberry')
      or coalesce(record->>'attention_final_response','') not in ('banana','tomato','peach','blueberry')
      or coalesce(record->>'perceived_violence','') !~ '^[1-5]$'
      or coalesce(record->>'ai_content_freq','') !~ '^[1-5]$'
      or coalesce(record->>'believed_other_participant','') not in ('yes','no','not_sure')
      or coalesce(record->>'daily_short_video_time','') not in ('lt30','30_60','1_2h','2_3h','gt3h')
      or coalesce(record->>'gender','') not in ('woman','man','non_binary','self_describe','prefer_not')
      or coalesce(record->>'age','') !~ '^\d{2,3}$' then
      raise exception 'Incomplete or invalid response' using errcode='22023';
    end if;
    if (record->>'age')::integer not between 18 and 120 then raise exception 'Invalid age' using errcode='22023'; end if;
    for i in 1..8 loop
      if coalesce(record->>('shs0'||i),'') !~ '^[1-5]$' then raise exception 'Invalid SHS item' using errcode='22023'; end if;
      x := (record->>('shs0'||i))::integer;
      shs_total := shs_total + case when i%2=0 then 6-x else x end;
    end loop;
    if record->>'finish_time' is null or record->>'start_time' is null then raise exception 'Missing time' using errcode='22023'; end if;
    perform (record->>'finish_time')::timestamptz, (record->>'start_time')::timestamptz;
    clean := clean || jsonb_build_object('attention_pass',record->>'attention_response'='tomato',
      'thht_easy_count',easy,'thht_medium_count',11-easy-hard,'thht_hard_count',hard,
      'thht_help',greatest(0,easy-1),'thht_hurt',greatest(0,hard-1),
      'thht_difference',greatest(0,easy-1)-greatest(0,hard-1),
      'thht_counts_sum_ok',true,'shs_mean',round(shs_total::numeric/8,3));
  else
    -- Mid-study exits keep only session metadata, never answers.
    if record->>'withdrawn' is distinct from 'true' then raise exception 'Invalid withdrawal' using errcode='22023'; end if;
    select jsonb_object_agg(key,value) into clean from jsonb_each(clean) where key = any(array[
      'participant_id','study_id','protocol_version','attention_version','shs_version','preview_mode','condition',
      'character_type','violence_condition','video_id','consent','age_eligible','consent_time','start_time',
      'finish_time','reload_count','withdrawn','withdrawn_at','withdrawn_at_step','completion_status']);
  end if;
  clean := clean || jsonb_build_object('submission_status','uploaded');
  digest := sha256(convert_to(clean::text,'UTF8'));
  token_digest := sha256(convert_to(submission_token,'UTF8'));
  insert into public.responses(participant_id,payload) values(pid,clean) on conflict do nothing returning * into saved;
  if found then
    insert into private.submission_keys values(pid,token_digest,digest);
  else
    select * into saved from public.responses where participant_id=pid;
    select * into key_row from private.submission_keys where participant_id=pid;
    if key_row.token_hash is distinct from token_digest or key_row.payload_hash is distinct from digest then
      raise exception 'Submission conflict' using errcode='22023';
    end if;
  end if;
  return jsonb_build_object('ok',true,'participant_id',saved.participant_id,'receipt_id',saved.receipt_id,'received_at',saved.received_at);
end; $$;
revoke all on function private.submit_thht(jsonb,text) from public;
grant execute on function private.submit_thht(jsonb,text) to anon,authenticated;
create function public.submit_thht(record jsonb, submission_token text) returns jsonb
language sql security invoker set search_path = '' as $$ select private.submit_thht(record,submission_token); $$;
revoke all on function public.submit_thht(jsonb,text) from public;
grant execute on function public.submit_thht(jsonb,text) to anon,authenticated;
alter publication supabase_realtime add table public.responses;
