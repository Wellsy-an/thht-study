-- Synthetic UUID-only user and allowlist entry exist only within this rolled-back transaction.
-- No contact details, passwords, invitations, or real accounts are used.
begin;
select set_config('test.expected_count',(select count(*)::text from public.responses),true);
insert into auth.users(id) values ('ffffffff-1111-4111-8111-fffffffffff1');
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"ffffffff-1111-4111-8111-fffffffffff1","role":"authenticated"}',true);
do $$begin
  if public.researcher_access() is distinct from false then raise exception 'Unlisted account accepted'; end if;
  if (select count(*) from public.responses) <> 0 then raise exception 'Unlisted account leaked rows'; end if;
  if has_table_privilege('authenticated','private.researchers','INSERT') then raise exception 'Self-grant researcher possible'; end if;
  if has_table_privilege('authenticated','public.responses','INSERT') then raise exception 'Direct response write possible'; end if;
end$$;
reset role;
insert into private.researchers(user_id) values ('ffffffff-1111-4111-8111-fffffffffff1');
set local role authenticated;
do $$begin
  if public.researcher_access() is distinct from true then raise exception 'Allowlisted account denied'; end if;
  if (select count(*) from public.responses) <> current_setting('test.expected_count')::integer then raise exception 'Authorized read count mismatch'; end if;
end$$;
reset role;
do $$begin
  if has_table_privilege('anon','public.responses','SELECT') then raise exception 'Anonymous direct read possible'; end if;
  if has_table_privilege('anon','public.responses','INSERT') then raise exception 'Anonymous direct insert possible'; end if;
  if has_table_privilege('anon','private.submission_keys','SELECT') then raise exception 'Retry token hash readable'; end if;
  if not has_function_privilege('anon','public.submit_thht(jsonb,text)','EXECUTE') then raise exception 'Submission entrypoint missing'; end if;
end$$;
rollback;
select 'PASS: unlisted auth reads zero; listed auth reads all; no self-grant/direct writes/anon reads; all test identity changes rolled back' as result;
