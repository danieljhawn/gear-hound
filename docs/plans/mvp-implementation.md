# Gear Hound MVP Implementation Plan

> **For Hermes:** Use test-driven development and execute this plan task-by-task. Verify source behavior against live pages before relying on saved fixtures.

**Goal:** Build a password-protected, responsive single-user web app at `gear.overstimulationstation.com` that checks Austin/Cedar Park Craigslist and local Guitar Center used inventory daily, stores matching listings at or below $500, discovers FSOT/WTT opportunities across all local Craigslist categories, and supports browsing, barter matching, searching, filtering, marking Interested, hiding, and archiving listings.

**Architecture:** Run a Dockerized Python/FastAPI application on the existing VPS, with server-rendered Jinja templates and HTMX for interactions. Store durable state in a host-mounted SQLite database. Implement each marketplace as an isolated source adapter: Craigslist performs normal music-gear discovery plus an all-category local trade search, using lightweight HTTP parsing when viable with Playwright fallback; Guitar Center uses its website's Algolia search index, because direct website access currently returns HTTP 403. A daily one-shot collector container upserts listings, records observations, computes explainable barter matches against the user's interests and editable My Gear inventory, and archives items only after repeated absence from successful complete runs.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Jinja2, HTMX, SQLAlchemy 2, Alembic, SQLite, HTTPX, BeautifulSoup/lxml, Playwright/Chromium, pytest, pytest-asyncio, Docker Compose, Caddy or the VPS's existing port-80/443 proxy.

---

## 1. Confirm deployment ownership and create the project skeleton

**Objective:** Establish a safe project location and determine how the existing listeners on ports 80/443 are managed before changing anything.

**Target path:** `/home/hermes/projects/gear-hound`

**Files to create:**
- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `README.md`
- `app/__init__.py`
- `tests/__init__.py`

**Steps:**
1. Determine which container or service owns ports 80/443 using elevated read-only inspection. Docker is installed and active, but the `hermes` user currently lacks access to `/var/run/docker.sock`.
2. Do not add `hermes` to the Docker group automatically: Docker group membership is effectively root-equivalent. Prefer running deployment commands with explicit `sudo docker compose ...` unless the user approves persistent group access.
3. Check whether the existing 80/443 service can accept another virtual host. Do not replace or restart it until its purpose and configuration are known.
4. Initialize a Git repository in `/home/hermes/projects/gear-hound`.
5. Configure Python dependencies and developer commands in `pyproject.toml`.
6. Add a startup smoke test that imports `app.main` and requests `/healthz`.

**Verification:**
- `pytest tests/test_health.py -v` passes.
- `docker compose config` validates after the Compose file is added later.
- Existing services on ports 80/443 remain reachable throughout discovery.

## 2. Define configuration and the database model

**Objective:** Create explicit, testable storage for listings, source runs, user state, editable settings, searches, and future price history.

**Files:**
- Create: `app/config.py`
- Create: `app/db.py`
- Create: `app/models.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_initial.py`
- Test: `tests/test_models.py`
- Test: `tests/test_settings.py`

**Core tables:**
- `listings`: source, source ID, canonical URL, title, price in cents, location/store, source category, normalized category, image URL, source-posted time, first seen, last seen, active flag, consecutive-miss count, and raw metadata JSON.
- `listing_observations`: listing ID, observed time, price, availability, title, and location. This preserves data needed for later valuation without building deal scoring now.
- `collection_runs`: source, start/end times, status, number discovered/inserted/updated/archived, error summary, and optional diagnostic artifact path.
- `listing_states`: listing ID and state (`normal`, `interested`, or `hidden`). Keep this separate from marketplace availability.
- `saved_searches`: name, terms, active flag, optional category and price overrides.
- `owned_gear`: editable My Gear inventory with item name, aliases, category, available-for-trade flag, optional notes, and active flag. Do not require the user to enter estimated value in the MVP.
- `trade_details`: listing ID, trade-language phrases, extracted offered text, extracted wanted text, trade-only/FSOT flag, match type, matched terms, and confidence/explanation. Preserve original text snippets so matches are auditable.
- `settings`: typed JSON values for maximum price, category rules, exclusion rules, source settings, local store names, and archive threshold.

**Initial settings:**
- Maximum price: `$500`.
- Region: Austin/Cedar Park.
- Categories: Bass, Synths/Keys, Guitar, Effects, Amps, Recording, and Other/Oddball.
- Conventional drum exclusions: kits, snares, toms, bass drums, cymbals, hi-hats, routine stands/hardware, and conventional electronic drum pads/kits.
- Explicitly allowed despite percussion terms: drum machines, grooveboxes, samplers, gongs, tablas, unusual percussion, and oddball instruments.
- Archive after two consecutive successful complete runs in which an item is absent; failed or partial runs never increment miss counts.

**Tests:**
1. Write failing tests for unique `(source, source_listing_id)` behavior.
2. Test observation history when price changes.
3. Test that user state survives listing updates and archival.
4. Test default settings and updates through a repository layer.
5. Test owned-gear aliases, available-for-trade state, and trade-detail relationships.
6. Run migrations against a temporary SQLite database and verify downgrade/upgrade.

## 3. Create a source-adapter contract and fixture framework

**Objective:** Ensure each marketplace returns the same normalized listing shape and can fail independently.

**Files:**
- Create: `app/collectors/base.py`
- Create: `app/collectors/types.py`
- Create: `app/services/ingestion.py`
- Create: `tests/collectors/test_contract.py`
- Create: `tests/fixtures/README.md`

**Contract:**
- `collect(settings) -> CollectionResult`
- Each normalized item contains source, immutable source ID, title, integer price cents, URL, location/store, image URL when available, source-posted timestamp when available, source category, and raw metadata.
- Results explicitly declare `complete=True/False`; only complete successful runs can drive archival.
- Source failures create a failed `collection_runs` record but do not prevent another source from completing.

**Ingestion behavior:**
1. Upsert by source and source ID.
2. Refresh title, price, URL, location, image, and last-seen time.
3. Record a new observation on first sighting and whenever tracked fields change.
4. Preserve Interested/Hidden state.
5. Increment miss counts only after a successful complete scan.
6. Mark inactive after the configured miss threshold.
7. Reactivate a previously archived item if it returns.

**Verification:** Contract tests run against deterministic fixtures; database integration tests cover new, changed, absent, failed-run, and reappearing listings.

## 4. Implement semantic classification and filtering

**Objective:** Keep desirable oddball items while suppressing routine drum listings and over-budget items.

**Files:**
- Create: `app/services/classifier.py`
- Create: `app/services/filtering.py`
- Test: `tests/test_classifier.py`
- Test: `tests/test_filtering.py`

**Rule order:**
1. Reject invalid/missing prices and prices above the configurable ceiling.
2. Apply explicit allow phrases before broad conventional-drum exclusions.
3. Apply source category mappings and title keyword rules.
4. Assign one normalized category, falling back to `Other/Oddball` rather than discarding an unfamiliar music item.
5. Evaluate saved-search matches separately so the UI can badge them without hiding broad-category discoveries.

**Trade-mode exception:**
- Listings found through explicit FSOT/WTT/barter discovery are evaluated across every Austin-area Craigslist category, especially Electronics and Barter.
- A trade listing may be retained without a usable cash price, and the normal $500 ceiling does not reject a trade-only listing. If a cash price is present, display it and preserve the configured price filter as a UI option.
- Retain a trade listing when the offered item matches Gear Hound interests, the wanted item matches My Gear, or the parser cannot confidently separate the offer and want but the listing is clearly music/electronics related.
- Conventional drum exclusions still apply to the offered side, but an unusual item or a match against My Gear can keep the listing visible with an explanation.

**Required examples:**
- Exclude: `14-inch hi-hat cymbal pair`, `snare stand`, `bass drum spur legs`, `electronic drum pad`.
- Include: `drum machine`, `sampler`, `groovebox`, `gong`, `tabla`, `bass guitar`, `synthesizer`, `Portastudio`, and unfamiliar musical devices under $500.
- Ensure `bass drum` is excluded while `bass guitar` and `bass amp` are included.
- Detect `FSOT`, `WTT`, `WTTF`, `for sale or trade`, `trade for`, `looking for`, `consider trades`, and common punctuation/casing variations.
- Distinguish “have/offering” from “want/seeking” where the description provides enough structure; otherwise store an uncertain but visible trade match.

**Verification:** Table-driven unit tests cover mixed casing, punctuation, ambiguous “bass,” missing prices, and allow-list precedence.

## 5. Implement Austin Craigslist sale and barter collectors

**Objective:** Collect current Austin musical-instrument listings under the configured price ceiling and discover explicit trade opportunities across all local Craigslist categories, including Electronics and Barter.

**Files:**
- Create: `app/collectors/craigslist.py`
- Create: `app/services/trade_parser.py`
- Create: `app/services/trade_matcher.py`
- Create: `tests/fixtures/craigslist/search.html`
- Create: `tests/fixtures/craigslist/trade_search.html`
- Create: `tests/fixtures/craigslist/trade_detail.html`
- Create: `tests/collectors/test_craigslist.py`
- Create: `tests/test_trade_parser.py`
- Create: `tests/test_trade_matcher.py`

**Observed live behavior:**
- The search resolves to `https://www.craigslist.org/search/area/austin?cat=msa&max_price=500&sort=date`.
- Listing cards currently expose `data-pid`, title, price, Austin-area location, listing URL, and image elements.

**Approach:**
1. Run the normal Musical Instruments search with the configured maximum price.
2. Run dedicated all-category Austin-area searches for trade phrases such as FSOT, WTT, WTTF, “for sale or trade,” “trade for,” “looking for,” and “consider trades.” Include Craigslist's Barter category explicitly and ensure Electronics results are covered.
3. Deduplicate overlapping phrase/category results by Craigslist post ID before fetching details.
4. Attempt HTTPX fetches with conservative headers, timeout, caching, and a low request rate.
5. Parse complete search results from returned HTML when possible.
6. If no valid cards are present or the page requires JavaScript, invoke Playwright Chromium for that run.
7. Fetch detail pages only for deduplicated trade candidates, because the body text is required to determine what is offered and wanted. Do not fetch every ordinary sale listing detail page.
8. Parse and retain title/body snippets indicating offered items, wanted items, openness to trades, and ambiguity.
9. Compare the offered side to saved interests and the wanted side to active My Gear aliases. Emit explicit reasons such as `Offers: Korg synth` and `Wants: Jazz Bass (matches My Gear: Fender bass)`.
10. Capture a screenshot and trimmed HTML diagnostic when Playwright cannot find the expected structure.
11. Traverse pagination with a hard cap and mark the run partial if a later page fails.

**Tests:**
- Parse source ID, title, cents price, URL, location, and first image from fixture cards.
- Skip malformed cards without failing the entire run.
- Verify pagination and partial-result signaling.
- Test HTTP-to-Playwright fallback with mocks.
- Verify all-category trade-term searches are generated and overlapping results are deduplicated before detail fetches.
- Test offer/want extraction, My Gear alias matching, interest matching, uncertain matches, no-price trade listings, and descriptions containing several possible trades.
- Verify an Electronics-category FSOT synth is included and a conventional drum-kit trade remains excluded unless its wanted side matches My Gear or it includes another relevant offered item.

**Live verification:** Run one non-persisting collector probe, compare several records to the live page manually, and report counts without changing production data.

## 6. Implement the local Guitar Center collector through Algolia

**Objective:** Collect used Guitar Center items at or below $500 associated with Austin-area stores without scraping the blocked storefront HTML.

**Files:**
- Create: `app/collectors/guitar_center.py`
- Create: `tests/fixtures/guitar_center/algolia_page.json`
- Create: `tests/collectors/test_guitar_center.py`

**Observed live behavior:**
- `https://www.guitarcenter.com/Used/` returns HTTP 403 from the VPS and an Access Denied browser page.
- Guitar Center's frontend uses a public Algolia index that exposes SKU ID, display name, prices, creation date, SEO URL, store name/stores, brand, condition, categories, and other listing metadata.

**Approach:**
1. Query the Algolia index with price, used-condition, relevant-category, and pagination filters.
2. Retrieve image attributes and category fields in addition to the minimal fields found during discovery.
3. Filter to configured Austin-area store names based on live returned store values. Seed the exact store names only after a probe shows their canonical spelling.
4. Reimplement only the needed request logic; do not vendor or blindly copy third-party scraper code.
5. Treat the public frontend key/index as replaceable configuration and emit a clear health error if Guitar Center changes it.
6. Do not use Playwright as the primary GC path while the storefront blocks the VPS. Keep a browser probe only for diagnostics or future endpoint discovery.

**Tests:**
- Normalize SKU, title, cents price, store, condition, category, URL, created time, and image.
- Filter out non-local stores, over-$500 inventory, and conventional drums.
- Test pagination, rate limiting, changed credentials, malformed hits, and partial results.

**Live verification:** Query a single page, identify the canonical Austin-area store values, confirm several URLs, and verify the app does not classify a nationwide item as local merely because shipping is available.

## 7. Build the responsive dashboard

**Objective:** Provide a fast page usable on both phone and desktop.

**Files:**
- Create: `app/main.py`
- Create: `app/routes/listings.py`
- Create: `app/routes/actions.py`
- Create: `app/templates/base.html`
- Create: `app/templates/listings/index.html`
- Create: `app/templates/listings/_grid.html`
- Create: `app/templates/listings/_card.html`
- Create: `app/static/css/app.css`
- Create: `app/static/js/app.js` only if HTMX cannot cover a small behavior
- Test: `tests/web/test_listings.py`
- Test: `tests/web/test_actions.py`

**UI requirements:**
- Default: active, non-hidden listings sorted newest first.
- Mobile: touch-friendly cards with image, title, prominent price, category, source, location, first/last-seen information, and source link.
- Desktop: denser responsive grid; avoid a separate complex SPA.
- Category tabs/filters: All, Bass, Synths/Keys, Guitar, Effects, Amps, Recording, Other/Oddball.
- Filters: price range, source, location, listing status, and free-text title search.
- Views: Interested, Hidden, and Archived.
- A dedicated Barter view with badges for `They have something you may like`, `They want something you may have`, `Two-way match`, and `Uncertain trade`.
- Barter cards show offered/wanted snippets and the exact saved-interest or My Gear terms that caused the match. They must link to the original listing and never imply that an inferred match is certain.
- Actions: mark/unmark Interested and Hide/unhide without a full-page reload.
- Display collection health and last successful update unobtrusively.
- Visual style: borrow the color and personality of overstimulationstation.com while prioritizing scanning and readability.

**Tests:**
- Query-string filters compose correctly.
- Hidden and archived listings do not appear in the default feed.
- Interested state toggles and persists.
- Source links use safe external-link attributes.
- Empty, failed-source, and stale-data states are understandable.

## 8. Build the Settings and collection-status pages

**Objective:** Let the user manage preferences without editing VPS files.

**Files:**
- Create: `app/routes/settings.py`
- Create: `app/templates/settings/index.html`
- Create: `app/templates/status/index.html`
- Test: `tests/web/test_settings.py`

**Editable fields:**
- Maximum price.
- Enabled sources.
- Normalized category keywords.
- Conventional-drum exclusion phrases.
- Explicit oddball/allow phrases.
- Saved searches and model names.
- My Gear inventory: names, aliases, category, notes, and an Available for Trade toggle.
- Trade-discovery phrases and enabled Craigslist category scopes, defaulting to all local categories with explicit emphasis on Electronics and Barter.
- Local Guitar Center store names.
- Archive miss threshold.

**Safety:**
- Validate numeric ranges and term lengths.
- Use CSRF protection for all state-changing forms.
- Keep secrets and Algolia configuration out of editable browser settings.
- Show settings changes immediately without triggering an unbounded collection run.

**Verification:** Web tests cover valid updates, invalid values, CSRF failure, adding/removing saved searches, My Gear CRUD and aliases, Available for Trade toggles, trade-match explanations, and reset-to-default behavior.

## 9. Add daily collection commands, observability, and backups

**Objective:** Make daily operation reliable and diagnosable without notifications.

**Files:**
- Create: `app/cli.py`
- Create: `scripts/backup.sh`
- Create: `scripts/healthcheck.sh`
- Create: `tests/test_cli.py`

**Commands:**
- `python -m app.cli collect --source all`
- `python -m app.cli collect --source craigslist --dry-run`
- `python -m app.cli collect --source guitar-center --dry-run`
- `python -m app.cli doctor`

**Behavior:**
- Use a process lock so two daily runs cannot overlap.
- Run sources independently and summarize each result.
- Return nonzero only when appropriate while retaining successful source data.
- Rotate diagnostics and logs.
- Use SQLite's online backup API or `VACUUM INTO`, not a raw copy of an actively written database.
- Retain a small rolling set of local backups, with the backup directory mounted from the host.
- No user notifications in the MVP.

**Verification:** Simulate one source failing while the other succeeds; verify collection records, no false archival, lock behavior, and restorable backup integrity.

## 10. Containerize the application and browser dependencies

**Objective:** Package exact Python and Chromium dependencies while keeping durable data on the host.

**Files:**
- Create: `Dockerfile`
- Create: `compose.yaml`
- Create: `.dockerignore`
- Create: `docker/entrypoint.sh`

**Design:**
- Build from a pinned Playwright Python base image or a pinned Python image with a pinned Playwright Chromium install.
- Run as a non-root application user inside the container.
- Mount `/home/hermes/projects/gear-hound-data/` for SQLite, backups, and diagnostics.
- Bind the app only to `127.0.0.1` on a chosen unused host port; never expose Uvicorn directly to the internet.
- Use the same image for the web service and one-shot collector command.
- Add health checks and resource limits appropriate for a 2-core/8-GB VPS.

**Scheduling:**
- Prefer a host systemd timer that executes `docker compose run --rm collector` once daily. This makes run history visible to the host and avoids an always-running scheduler inside the web process.
- Choose a low-traffic local time after confirming Guitar Center's inventory update cadence.

**Verification:**
- `docker compose build` succeeds.
- Unit and integration tests run inside the image.
- A one-shot collector exits cleanly.
- Restarting/rebuilding containers does not lose SQLite data or user states.

## 11. Configure the protected subdomain and HTTPS

**Objective:** Publish Gear Hound securely without disrupting the existing site or gateway.

**Files depend on existing proxy discovery:**
- Likely create a virtual-host fragment for the service currently owning ports 80/443.
- Create a password hash in a root-readable secret/config location, never in Git.

**Steps:**
1. Identify the current reverse-proxy/container configuration and back it up.
2. Add an `A` record for `gear.overstimulationstation.com` pointing to the VPS public IP. This is the only required change to the Porkbun-hosted site; the main site remains where it is.
3. Add a virtual host that terminates HTTPS and proxies only to the loopback Gear Hound port.
4. Protect the entire subdomain with one strong username/password at the proxy layer.
5. Add standard security headers and request-size limits.
6. Validate the proxy configuration before reload; use a graceful reload, not a blind restart.

**Verification:**
- Unauthenticated requests receive an authentication challenge.
- Authenticated requests load the dashboard over a valid HTTPS certificate.
- Uvicorn's host port is unreachable externally.
- `overstimulationstation.com` and all pre-existing VPS services still work.

## 12. End-to-end acceptance and launch

**Objective:** Prove the MVP works with real data and survives routine operations.

**Acceptance checklist:**
- Daily collection obtains current Austin-area Craigslist and local GC listings at or below $500.
- Daily Craigslist collection also searches explicit FSOT/WTT/barter language across all Austin-area categories, especially Electronics and Barter.
- Conventional drum listings are filtered, while drum machines, samplers, gongs, tablas, and other oddball items remain eligible.
- Trade-only listings without a cash price can appear in Barter and are not incorrectly rejected by the $500 sale ceiling.
- My Gear can be edited in the app, and Barter explains whether a listing matches something the user likes, something the user has available, both, or is uncertain.
- Cards show image, title, price, source, location/store, timestamps, and direct link.
- Search, categories, source, location, price, and state filters work on phone and desktop.
- Interested and Hidden actions persist after restart and subsequent collection.
- Missing listings move to Archived only after two successful complete misses.
- Failed source runs are visible and never cause mass archival.
- Settings can be updated safely through the app.
- The app is HTTPS-only and password-protected.
- Database backup can be restored into a clean container and passes integrity checks.

**Final commands:**
- Run the full test suite in Docker.
- Run both collectors in dry-run mode.
- Run one real ingestion.
- Compare a sample from each source to its live listing.
- Test responsive layout at representative mobile and desktop widths.
- Restart the stack and verify state persistence.

---

## Explicitly deferred from the MVP

- Notifications or daily digests.
- Reverb collection and nationwide resale-value analysis.
- “Good deal” scoring, estimated market value, and machine-learning ranking.
- Facebook Marketplace or eBay.
- Multiple users, registration, or separate preferences.
- Automated purchasing or seller contact.

## Future valuation phase

When the listing pipeline has accumulated reliable history:
1. Add a nationwide Reverb source adapter for active comparable listings.
2. Prefer actual sold/completed prices where legally and technically available; do not present asking prices as realized resale value.
3. Normalize brand, model, variant, condition, shipping cost, and bundled accessories.
4. Use robust comparable statistics with sample counts and confidence indicators.
5. Add deal scoring only after manually validating matches and avoiding misleading comparisons.
6. Add notifications only after false-positive rates are acceptable.

## Principal risks and mitigations

- **Marketplace changes or blocking:** source adapters, fixtures, health records, conservative request rates, and Playwright diagnostics isolate failures.
- **Guitar Center public search changes:** keep index credentials configurable and expose a clear source-health failure rather than silently returning zero listings.
- **False archival:** require complete successful scans and multiple misses.
- **Over-filtering oddball gear:** allow-list precedence and an Other/Oddball fallback.
- **Docker privilege:** use explicit elevated deployment commands rather than casually granting permanent Docker socket access.
- **Existing proxy conflict:** discover and back up the current owner of ports 80/443 before any deployment change.
- **SQLite durability:** host-mounted storage, migrations, online backups, and restore tests.
