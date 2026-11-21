# THHT Study

- Participant study: https://wellsy-an.github.io/thht-study/experiment.html
- Private researcher panel: https://wellsy-an.github.io/thht-study/ (also `dashboard.html`)

The root opens the researcher panel directly, not a prototype/version menu. No account or password is required. A private management entry is required to read data.
The bilingual participant flow, stimuli, puzzles, and questionnaires are unchanged;
only the approved attention question and necessary collection/receipt handling changed.
The confirmed attention key is **Tomato / 番茄** (first response scored; final response also retained).

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

## Private management entry — no account required

The owner uses a **private local HTML entry file**, delivered separately, to open the panel. It contains
a cryptographically random read-only management capability. The capability travels in a URL fragment
(not query parameters), is consumed into that browser's localStorage, and is immediately removed from
the address bar. Later, the same browser can open the plain site root directly. Clearing browser data,
using a private window, or changing devices requires reopening the private entry file. The entry file
uses a plain link and no third-party scripts, and can be opened through file:// on desktop/mobile.

The entry file and raw capability are **not in this repository or the public zip**. Never send them to
participants, paste the private link in a public chat, or upload the file to a public site. Anyone holding
the entry can view and export study data. “Forget this browser” removes the remembered capability and
rendered records from that browser; it does not revoke a copy of the private file held elsewhere.

`backend/management_access.sql` installs a read-only paginated RPC. A private database table stores
only a SHA-256 hash of the random capability; fixed-size hashes are compared byte-by-byte without
an early-exit match test. A token only authorizes this read endpoint, not direct table access or writes.
The API sets `Cache-Control: no-store, private`; raw participant records stay in page memory, not
localStorage. Empty/invalid/revoked capabilities cannot fetch records. The anonymous direct-table
read/write restrictions remain in place. No public read policy, email, password, invitation, or account
registration is involved. The old Auth allowlist remains unused, empty, and does not affect this path.

The panel refreshes automatically every **5 seconds** and labels its last confirmed refresh time.
This is protected polling, not a websocket stream; charts/table update after each completed record
is received, normally on the next refresh. Network failures display a stale-data warning and retry.
Per-person details and filtered CSV/JSON exports use the actual flat-v7 records and correct THHT
and SHS scoring. The eight charts are unchanged. Attention failures are flagged, not silently dropped.
Empty means are null, not zero. Times/days are Asia/Shanghai (UTC+8).

To revoke the current entry, a privileged project administrator can set
`private.management_access.enabled=false` for id 1. To rotate it, generate a new high-entropy entry
outside the repo, replace only the server-side SHA-256 hash, and deliver the new private file to the
owner. Do not put a raw token, launcher, service-role key, or secret key in source, logs, or the zip.
Existing saved copies cease to read after hash rotation. No paid resources or Auth accounts are needed.

The project's free tier can pause after inactivity and has resource quotas. No paid resources were
created. Test access from the actual participant networks before recruitment; GitHub/Supabase access
from mainland China may differ from the development network. Arrange an independent data backup
and retention/access policy before real recruitment.

## Local verification

Serve this folder at `http://127.0.0.1:8765` (e.g. `python3 -m http.server 8765`).
Use a Python environment with Playwright and Chromium:

- `python tests/test_flow_production.py` — full desktop/mobile preview regression (real video playback).
- `python tests/test_dashboard.py` — synthetic, offline dashboard UI/chart/access-state tests.
- `python tests/test_dashboard_startup.py` — offline desktop/mobile nonblank-startup, legacy-browser, storage-denial, blocked/slow/broken-chart, network failure/retry, timeout and empty-state regressions.
- `python tests/test_attention_bilingual.py` — desktop/mobile English/Chinese attention text and scoped translation protection.
- `python tests/test_capability.py` — actual private API + local file entry + browser automatic-update test; requires the separately stored private entry and writes a clearly tagged synthetic row. Clean up only its exact manifest UUID afterward.
- `python tests/test_production_integration.py` — writes tagged synthetic records to the real project;
  run only before recruitment or with explicit test authorization. It writes an exact ID manifest under
  `/workspace/thht/production-test-records.json`; remove only those test IDs via a privileged connection
  after checking the manifest. Do not remove real data or run indiscriminate truncate/delete statements.

The two dashboard HTML entry pages embed their critical CSS and application JavaScript, protected
by an exact CSP script hash. After editing `dashboard.js`, `dashboard.css` or
`scripts/dashboard.template.html`, run `python scripts/build_dashboard.py` to regenerate both pages.
Chart.js loads asynchronously and is optional: a slow, blocked or broken chart renderer cannot
prevent data access, the individual-record table, or exports. Startup, empty-data and connection
failure states provide explicit instructions instead of hiding the whole panel. Requests use a
compatible abort/timer fallback rather than requiring `AbortSignal.timeout`.

Chart.js 4.4.1 is loaded locally; no third-party script CDN is needed at runtime. The previously
vendored supabase-js bundle remains unused. See `vendor/NOTICE.md` and bundled MIT license notices.
`experiment-en.html` remains an unchanged legacy standalone artifact, not linked from the study root;
do not use it for recruitment. The downloadable zip is updated to match the production source.
