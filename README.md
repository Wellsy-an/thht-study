# THHT Study

- Participant study: https://wellsy-an.github.io/thht-study/experiment.html
- Private researcher panel: https://wellsy-an.github.io/thht-study/ (also `dashboard.html`)

The root opens the researcher sign-in screen directly, not a prototype/version menu.
The bilingual participant flow, stimuli, puzzles, and questionnaires are unchanged;
only the approved attention question and necessary collection/receipt handling changed.
The confirmed attention key is **Peach / 桃子** (first response scored; final response also retained).

## Production data

Supabase project: `thht-study` (`dhoelfaebggvzubxinxr`), Singapore, Free plan.
`backend/schema.sql` records the initial production schema (already applied).
Only the publishable frontend key is in this repository. Never add secret/service-role keys.

Participants use `submit_thht`: validated completion records or response-free mid-study exit metadata.
No anonymous direct table access exists. Each session has a random participant UUID and a separate
browser-only retry token; immutable retries return the same receipt without duplicate rows.
Server-side THHT/SHS/attention scores are recomputed. “Uploaded” is shown only after a matching
committed database receipt. If a request fails or times out, a local backup remains and retry is offered.
Preview (`?preview=1`) stays browser-only; the database also rejects preview submissions.
The new protocol/storage namespace separates previous tests and the old attention item from production.
No in-progress answers are uploaded. A complete row appears when the participant reaches debrief.

## Researcher access — required before first use

The dashboard is static public HTML, but the data are not public. It requires both Supabase Auth login
and a server-managed UUID allowlist. Merely creating/signing into an Auth account does NOT grant reads.
No researcher identity is guessed or automatically granted. The allowlist starts empty.

1. The owner specifies the intended researcher login identity.
2. Create that account under Supabase **Authentication → Users → Add user**. Use an approved secure
   account setup flow. Do not put a password in SQL, this repository, logs, or chat. Creating an email
   invitation requires separately authorizing that outgoing email; no invitations were sent by this work.
3. Obtain the verified Auth **user UUID**, then add ONLY that UUID from a privileged SQL session:
   `insert into private.researchers(user_id) values ('<verified-auth-user-uuid>');`
4. Sign in at the panel using that account. Test one upload, data read, realtime update, and logout.
   Disable public signups in Auth settings if not needed. Login has no public registration UI.
5. To remove reads, delete only the intended UUID from `private.researchers` and revoke that account's
   sessions in Auth. Do not delete any participant response when changing researcher access.

The panel reads the actual flat v7 schema, displays individual records and full-field CSV/JSON exports,
and subscribes to RLS-protected Postgres INSERT changes. It also rechecks authorization and refreshes
every 15 seconds as a connection fallback. No raw participant records are cached in localStorage.
Charts: daily/cumulative completions (Asia/Shanghai UTC+8), THHT condition means, SHS/violence means,
difference histogram, difficulty share, attention outcomes, belief responses, daily viewing duration.
No demo records or simulated-live mode exist. Charts use completed records; attention failures are
flagged, not silently dropped. Null means missing, not zero. Exports follow visible filters.

The project's free tier can pause after inactivity and has resource quotas. No paid resources were
created. Test access from the actual participant networks before recruitment; GitHub/Supabase access
from mainland China may differ from the development network. Arrange an independent data backup
and retention/access policy before real recruitment.

## Local verification

Serve this folder at `http://127.0.0.1:8765` (e.g. `python3 -m http.server 8765`).
Use a Python environment with Playwright and Chromium:

- `python tests/test_flow_production.py` — full desktop/mobile preview regression (real video playback).
- `python tests/test_dashboard.py` — synthetic, offline dashboard UI/chart/auth-state tests.
- `python tests/test_production_integration.py` — writes tagged synthetic records to the real project;
  run only before recruitment or with explicit test authorization. It writes an exact ID manifest under
  `/workspace/thht/production-test-records.json`; remove only those test IDs via a privileged connection
  after checking the manifest. Do not remove real data or run indiscriminate truncate/delete statements.

Chart.js 4.4.1 and supabase-js 2.86.2 are vendored so the panel does not depend on a third-party script
CDN at runtime. Both are MIT-licensed; see `vendor/NOTICE.md` and bundled license notices.
`experiment-en.html` remains an unchanged legacy standalone artifact, not linked from the study root;
do not use it for recruitment. The downloadable zip is updated to match the production source.
