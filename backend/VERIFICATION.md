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
- Database performance advisor: no findings. Security advisor: only intentional INFO-level
  notices for RLS with no client policy on the private researcher/key/capability tables. Those
  tables are deliberately inaccessible to clients; privileged functions alone touch them.
  Reference: https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy

## No-account management access (later update)

The account requirement was removed at the owner's request. The existing Auth allowlist remains
unused. A separately delivered private file opens a hash-verified, scoped, read-only management
RPC; no global public read policy was introduced. The raw capability is not in source or the zip.
The protected panel polls every 5 seconds, labels the last confirmed refresh, remembers only the
capability in the browser, and clears its URL fragment immediately. Raw response rows are not cached
in localStorage and protected HTTP responses are marked private/no-store.

## Attention key correction (2026-11-21, later the same evening, Asia/Shanghai UTC+8)

User superseded the earlier Peach key. The live scoring key is Tomato / 番茄 for both conditions.
Question wording, option order, and other participant content are unchanged. Server scoring
recomputes attention_pass from the first response. Previous protocol/attention version labels
are still accepted so in-flight retries keep a stable receipt. At the time of the correction,
there were 0 stored responses, so no existing records needed derived-score revision.

## Attention bilingual display protection

The published raw source and native headless-browser DOM were already English followed by Chinese,
including Banana/Tomato/Peach/Blueberry and the four Chinese translations. The reported duplicate-
Chinese display was not reproduced in the native test browser; its exact client-side cause is not
established. Scoped `translate="no"`, `notranslate`, and language spans were added only to the attention
question/options. No site-wide auto-translation or questionnaire rewriting was applied. Desktop/mobile
native rendered English/Chinese lines and the unchanged Tomato key are tested separately.

## Capability access verification

Actual HTTPS tests (not Auth mocks) verified valid private-capability reads, invalid/empty denial,
anonymous direct-table read/write denial, and refusal of write-shaped calls to the read-only RPC.
A file:// launcher opened the protected dashboard on desktop and mobile; the fragment was cleared,
plain-root refresh reused only the remembered capability, and forgetting access cleared it and the
rendered records. An actual synthetic completed participant submission updated the open dashboard
rows, KPIs, and line chart automatically on the next five-second poll (observed 3.0 seconds in the
local panel test). The participant browser was isolated from the researcher browser. No raw response
records were cached by the dashboard in localStorage. Full desktop/mobile study regression passed.
The same private-capability flow must also be checked against the published panel before handover.


## Dashboard nonblank startup (2026-11-22, Asia/Shanghai)

The original live private launcher opened the dashboard in clean desktop and mobile Chromium
without errors. Therefore the user's exact browser/network failure is not established. Controlled
reproductions did identify two real failure paths: a chart constructor error stopped initialization
before the panel opened, and an absent `AbortSignal.timeout` prevented every API request. A failed
API request also hid the main panel with only an easy-to-miss generic stale-data warning.

The dashboard now embeds critical CSS/application code with an exact CSP script hash; optional
Chart.js loads asynchronously and cannot prevent the records/table/export path. Chart construction
and update failures are contained. A mobile-compatible request timeout replaces the newer browser
API requirement; daily chart keys are assembled in a locale-independent UTC+8 format. Explicit
startup guidance, connection failure/retry and zero-response states remain visible. No experiment,
question, scoring, database, capability or launcher change is included. Failure-injection tests use
only offline mock records; live diagnosis is read-only and creates/deletes no production records.
