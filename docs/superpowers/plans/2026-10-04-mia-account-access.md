# Mia Account Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Friends register with a username/password, automatically log in, and use the existing voice gateway without copying tokens.

**Architecture:** Add a SQLite account store and loopback aiohttp auth service in the existing gateway process. Opaque account sessions reuse the existing Bearer WebSocket authentication and are checked before each cloud round. iOS stores origin-bound sessions in Keychain and retains explicitly selected legacy maintenance access.

**Tech Stack:** Python 3.12, sqlite3, hashlib.scrypt, aiohttp==3.14.3, websockets==16.0; iOS 17+, SwiftUI, URLSession, Keychain.

**Spec:** `docs/mia-account-access-plan.md` (approved 2026-10-04).

## Global Constraints

- Work in the existing clean `feature/mia-ios-bootstrap` checkout, as requested by the user; preserve unrelated firmware and selected half-body UI.
- Python/pip/tests use `/root/projects/Mia/.venv/bin/python`; VPS uses `/opt/mia/.venv/bin/python`.
- No new cloud calls for automated tests; no API Keys, passwords or issued sessions in Git or logs.
- Do not change Opus, Xiaozhi messages, Providers, caption timing or microphone interaction.
- Username: NFKC/casefold, 3–32 letters/numbers/underscore including Chinese; password: 15–128 characters, preserve spaces.
- scrypt N=2^15, r=8, p=3, random 16-byte salt, 32-byte digest, 64 MiB maxmem; at most 2 actual hash jobs.
- Session: random 32-byte token, only SHA-256 persisted, 30 days, at most 5 sessions per account.
- Defaults: 100 accounts, 30 nonempty rounds per user/UTC day, 2 concurrent rounds including legacy maintenance.
- Auth API: loopback 8766, maximum body 4 KiB; gateway: loopback 8765. Database: `/var/lib/mia/accounts.sqlite3`, protected systemd StateDirectory.
- Current user authorization covers implementation and deployment. Execute directly in this session and retain one independent final code review; do not repeat an implementation permission request.

## Review Focus

1. Cancelling login while a password hash runs must retain its concurrency slot until the actual thread finishes (Task 1).
2. Two racing requests must not bypass account/session/daily limits or consume a round when the global gateway is busy (Tasks 1/2).
3. A revoked session on an already connected socket must be denied before another Provider call (Task 2).
4. TLS errors, malformed responses, cancelled login and failed Keychain updates must not destroy a valid old session or send it to another origin (Task 3).
5. Offline logout and origin/mode changes must disconnect voice, avoid automatic legacy fallback and report revocation failure accurately (Task 3).

---

### Task 1: Account persistence and HTTP service

**Files:**
- Create `server/account_store.py`, `server/account_http.py`, `server/account_admin.py`.
- Modify `server/requirements.txt` (only aiohttp direct dependency).
- Create `server/tests/test_accounts.py`, `server/tests/test_account_http.py`.

**Interfaces:**
- `AccountError(status: int, code: str, message: str)`; never includes input secrets.
- `AccountStore(path, max_users=100, daily_rounds=30, clock=time.time)`.
- Async `register(username,password)`, `login(username,password)` -> dict with `username`, `token`, `expires_at` (Unix seconds).
- Sync `authenticate(token) -> int | None`, `revoke(token)`, `consume_round(user_id)`; async `reset_password(username,password)`, `close()`.
- `create_app(store) -> aiohttp.web.Application` owns routes and bounded attempt limits.
- `POST /api/auth/register` returns 201; login 200; idempotent logout 204. All responses no-store. Errors use JSON `error`/`message`, 429 includes Retry-After.
- Normalize username before uniqueness and rate limiting; limits 20 attempts/IP/minute and 10/username/minute before scrypt, bounded to 4096 active buckets. Trust `X-Mia-Client-IP` only from loopback; Caddy overwrites it.

- [x] Write real temporary SQLite tests: registration/login, NFKC duplicate, distinct salts, invalid inputs, no plaintext credentials, persistence, expiry/revoke, maximum users and five sessions, concurrent registrations and UTC daily debit, administrator reset invalidates sessions. Expected credential lifetime is 2,592,000 seconds; wrong/unknown login returns the same 401 code.
- [x] Run `/root/projects/Mia/.venv/bin/python -m unittest server.tests.test_accounts -v`; expected missing implementation failure before adding code.
- [x] Implement store with SQL transactions/constraints and bounded asynchronous scrypt. Exercise cancellation using a controlled slow hash and assert the third job remains rejected until the first two finish.
- [x] Add aiohttp dependency to the project venv and create HTTP tests using real TestServer/TestClient: register→login→logout; invalid JSON/type/oversize; duplicate/unauthorized/uniform errors; rate limit before hashing; spoofed IP header cannot be trusted from a remote peer; no-store and generic errors.
- [x] Run HTTP tests before creating routes, confirm failure; implement routes, safe errors and limiter. Add hidden-password admin CLI without printing credentials.
- [x] Run both account suites and all service tests; expected all pass. Inspect diff, update progress docs, commit/push focused server stage.

### Task 2: Account sessions on the unchanged voice gateway

**Files:**
- Modify `server/xiaozhi_gateway.py`.
- Extend `server/tests/test_xiaozhi_gateway.py`.

**Interfaces:**
- Consume Task 1 `AccountStore.authenticate`, `consume_round`, `create_app`.
- `MiaGateway(token, provider_factory=VolcengineProvider, accounts=None, max_concurrent_rounds=2)` preserves old constructor callers.
- `MIA_ACCOUNTS_ENABLED=1` enables store/HTTP; `0` disables account access and preserves maintenance rollback. `MIA_ACCOUNT_DB`, `MIA_MAX_ACCOUNTS`, `MIA_DAILY_ROUNDS`, `MIA_MAX_CONCURRENT_ROUNDS` configure approved defaults.
- Account token and old shared token both use original Authorization header; account session revalidated before cloud calls. Unauthorized closes 1008 with `未授权`.
- Empty recording returns original error before debit. Busy rejection never debits. Started failures/interruptions remain charged; global slot always released.

- [ ] Add real WebSocket tests for account recording→ASR→LLM→TTS/Mia-only subtitle, revoked/expired tokens at handshake and on open sockets, wrong tokens, quota persistence, busy rejection, abort and Provider exceptions releasing slots; preserve original tests unchanged.
- [ ] Run gateway suite, confirm new behavior fails against existing code.
- [ ] Implement narrow auth/round checks and loopback HTTP lifecycle; provider code unchanged. Bind HTTP only to 127.0.0.1; cleanup runner, hash executor and DB at shutdown.
- [ ] Run all service tests, expected green, inspect diff and commit/push gateway stage with progress evidence.

### Task 3: iOS registration/login and stored account sessions

**Files:**
- Create `ios/MiaApp/MiaAccountAccess.swift`, `ios/MiaApp/MiaAccountView.swift`.
- Modify `ios/MiaApp/ContentView.swift`, `MiaTokenStore.swift`, `MiaWebSocketTransport.swift`, `MiaVoiceSession.swift`.
- Create `ios/MiaTests/MiaAccountAccessTests.swift`; extend transport tests as necessary.

**Interfaces:**
- `MiaAccountCredential: Codable, Equatable` holds username/token/expiresAt/origin; `usable(endpoint:now:)` validates origin/lifetime.
- `MiaAccountAPI(session: URLSession = .shared)` builds same-host HTTPS requests from WSS, rejects userinfo/fragments, uses timeout and reload/no-store policy, disables redirects; accepts only complete valid credential responses with a future expiry and opaque non-whitespace token.
- `MiaAccountAccess: ObservableObject` owns registration/login, origin-bound credentials, local invalidation and logout; storage operations injected as narrow closures for failure tests, defaulting to real Keychain.
- Keychain update uses SecItemUpdate then add if absent, never delete-before-save. Password is never persisted. Credential stored separately from legacy token.
- `MiaAccountView` login/registration sheet clears password on dismiss/success, allows cancellation, shows Chinese validation/errors.
- Account login disables explicit persisted maintenance mode. New installs use account mode; one-time migration permits existing old-token installations to continue maintenance. Logout never automatically enables maintenance.
- `MiaConnectionError.unauthorized` only for a definitive WebSocket policy close reason `未授权`; VoiceSession publishes auth rejection while preserving other error behavior.

- [ ] Add tests with URLProtocol transport fixtures for exact endpoint/JSON/headers, response validation, no cross-origin redirect, unknown expiry, malformed payload, HTTP 401/429 and TLS distinction.
- [ ] Add state tests: cancellation and failed save retain old credentials, wrong origin never usable, definite rejection clears, network failure retains, logout captures token before clearing/disconnect and offline failure never restores login/legacy mode. Use fake storage only for controlled failures; verify real Keychain round trip and update.
- [ ] Push tests first to existing macOS CI and confirm missing-feature failure; local Swift/Xcode unavailable.
- [ ] Implement account API/storage/state and integrate sheet/settings/home routing. Keep home portrait/orb layout and voice/Opus/caption logic. Normal settings show account/logout; old token/endpoint inside explicit Advanced Maintenance.
- [ ] Run macOS CI; expected all XCTest, simulator/device builds green. Inspect both native screenshot sizes and login/settings flows; fix actual regressions and document hardware limits.
- [ ] Inspect diff, update README/handoff/roadmap, commit/push iOS stage.

### Task 4: Protected deployment and real account verification

**Files:**
- Modify `server/deploy/install-ubuntu.sh`, `mia-gateway.service.example`, `Caddyfile.example`.
- Create `server/deploy/check_accounts.py`; update `server/README.md`, `ios/README.md`, `docs/mia-ios-handoff.md`, `docs/mia-ios-roadmap.md`, account spec status.

**Interfaces:**
- systemd StateDirectory=mia, StateDirectoryMode=0700, UMask=0077; installer retains keys, old token and DB, adds approved account env defaults only if absent.
- Caddy `/api/auth/*` -> 127.0.0.1:8766 with overwritten X-Mia-Client-IP; original voice route remains.
- Account check uses a disposable account with randomized test credentials held only in memory; verifies HTTP register/login, WebSocket hello, logout, refusal of new rounds after revoke. No cloud calls, no credential output. Clean only the disposable test user via privileged local DB cleanup after connections close.
- VPS backup code, service/Caddy configs, env and SQLite using protected paths and sqlite backup before updating; no secrets read back. Rollback preserves account data and existing cloud configuration.

- [ ] Test installer with temporary command doubles and existing protected env/DB: preservation, one-time defaults and no secrets in output; shell syntax check.
- [ ] Run full server suite, iOS CI, Python compile checks, diff/secret inspection and independent whole-change code review; resolve material findings with regression tests.
- [ ] Commit/push deploy materials, wait corresponding CI green.
- [ ] SSH using existing dedicated key and pinned host key. Apply protected backups then install code/config, validate Caddy before reload and restart gateway; verify service and endpoint bindings.
- [ ] Run VPS service tests and account loopback/HTTPS check; recheck external TLS without weakening trust. If备案 still blocks outside access, document that iPhone account/voice acceptance remains pending.
- [ ] Update deployed commit, verified results/rollback paths in docs and push; final working tree clean. Do not claim real iPhone validation from VPS self-test.
