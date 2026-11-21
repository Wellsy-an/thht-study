# Prelaunch verification (2026-11-21, Asia/Shanghai UTC+8)

- Desktop and mobile full experiment regression: all checks passed (`ERRORS: 0`). The pre-existing
  missing favicon request is answered by the test harness only; the participant document is not
  otherwise modified to fix unrelated issues.
- Numbered participant HTML steps 1, 2, 4–10 and the mid-study exit section are byte-identical to
  the preceding production version. Puzzle construction and consent validation are unchanged.
- Actual browser → Supabase HTTPS/CORS calls: durable matching receipt; repeated and concurrent
  identical submissions return the same receipt; changed payload or wrong retry token is rejected;
  a lost receipt after commit recovers on refresh and retry; only one row remains per UUID.
- Actual preview: no requests from browser; preview=true payloads are rejected by the server.
- Actual server scoring checked: THHT help/hurt/difference, first-answer Tomato attention key, SHS
  mean; answers are stripped from mid-study exit rows.
- Actual anonymous API calls cannot read responses, write tables directly, call researcher access,
  or select the unexposed private schema.
- Actual database role tests in a rolled-back transaction: unlisted authenticated UUID reads zero
  rows; temporary allowlisted UUID can read rows; no client self-grant, direct write, or token-hash
  access. No contact details, passwords, or invitations were used or sent.
- Dashboard UI tests (synthetic mocked Auth/data transport, **not a real researcher login**): eight
  charts, accurate flat-v7 scores, UTC+8 date grouping, null group means, filters, CSV export,
  INSERT callback refresh, revocation/logout clearing, desktop and mobile.
- Database performance advisor: no findings. Security advisor: only the two intentional INFO-level
  notices for RLS with no client policy on private.researchers and private.submission_keys. Those
  tables are deliberately inaccessible to clients; privileged functions alone touch them.
  Reference: https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy

## Remaining before recruitment

The actual intended researcher account is not known and no UUID is allowlisted. The site safely
shows a researcher login/authorization boundary, not public data. Establish that account with the
owner, authorize its verified UUID, then verify password login, authenticated HTTPS SELECT, and
actual authenticated websocket INSERT delivery end-to-end. The code uses Postgres Changes with
RLS and a 15-second refresh fallback, but a real researcher websocket login cannot be truthfully
claimed tested until that account exists. Network tests use the box network, not the offline user's
computer or the actual participant networks.

## Attention key correction (2026-11-21, later the same evening, Asia/Shanghai UTC+8)

User superseded the earlier Peach key. The live scoring key is Tomato / 番茄 for both conditions.
Question wording, option order, and other participant content are unchanged. Server scoring
recomputes attention_pass from the first response. Previous protocol/attention version labels
are still accepted so in-flight retries keep a stable receipt. At the time of the correction,
there were 0 stored responses, so no existing records needed derived-score revision.
