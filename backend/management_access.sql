-- Passwordless, read-only bearer capability. No token or token hash is committed here.
create table private.management_access (
  id smallint primary key check(id=1),
  token_hash bytea not null check(octet_length(token_hash)=32),
  enabled boolean not null default true,
  created_at timestamptz not null default now()
);
alter table private.management_access enable row level security;
revoke all on private.management_access from public,anon,authenticated;

-- Fixed-work comparison of two fixed-size SHA-256 hashes. No early exit on differing bytes.
create function private.constant_time_equal32(a bytea,b bytea) returns boolean
language plpgsql immutable set search_path='' as $$
declare difference integer:=0; i integer;
begin
 if a is null or b is null or octet_length(a)<>32 or octet_length(b)<>32 then return false; end if;
 for i in 0..31 loop
   difference:=difference | (get_byte(a,i) # get_byte(b,i));
 end loop;
 return difference=0;
end; $$;
revoke all on function private.constant_time_equal32(bytea,bytea) from public,anon,authenticated;

create function private.read_dashboard(management_token text,page_offset integer default 0)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare stored_hash bytea; supplied_hash bytea; allowed boolean; output_rows jsonb; total bigint;
begin
 if management_token is null or management_token !~ '^[A-Za-z0-9_-]{64}$'
    or page_offset is null or page_offset<0 or page_offset>1000000 then
   raise exception 'Management access unavailable' using errcode='42501';
 end if;
 supplied_hash:=sha256(convert_to(management_token,'UTF8'));
 select token_hash,enabled into stored_hash,allowed from private.management_access where id=1;
 if not private.constant_time_equal32(supplied_hash,coalesce(stored_hash,decode(repeat('00',32),'hex')))
    or allowed is distinct from true then
   raise exception 'Management access unavailable' using errcode='42501';
 end if;
 perform set_config('response.headers','[{"Cache-Control":"no-store, private"},{"Pragma":"no-cache"}]',true);
 select count(*) into total from public.responses;
 select coalesce(jsonb_agg(to_jsonb(r)),'[]'::jsonb) into output_rows from (
   select participant_id,received_at,receipt_id,payload from public.responses
   order by received_at desc,participant_id asc limit 500 offset page_offset
 ) r;
 return jsonb_build_object('ok',true,'records',output_rows,'total_count',total,'refreshed_at',now());
end; $$;
revoke all on function private.read_dashboard(text,integer) from public;
grant execute on function private.read_dashboard(text,integer) to anon,authenticated;
create function public.read_dashboard(management_token text,page_offset integer default 0)
returns jsonb language sql stable security invoker set search_path='' as $$
 select private.read_dashboard(management_token,page_offset);
$$;
revoke all on function public.read_dashboard(text,integer) from public;
grant execute on function public.read_dashboard(text,integer) to anon,authenticated;
