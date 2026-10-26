# Хорар · by DowidAI

Russian-language experimental horary web application. Free public beta, AGPL-3.0-or-later. Separate from the DowidAI consulting website. No personal biography or employer information.

## Run

Python 3.12. Install `pip install -r requirements.txt`. Copy `.env.example` to `.env.local` and configure a dedicated OpenAI key, Postgres `DATABASE_URL`, and a random `SESSION_SECRET`. Never commit env files.

Initialise the database with `python -c "import app, storage; storage.migrate()"`. Run `uvicorn app:app --reload`. Tests: `pip install pytest`, then `python -m pytest tests`. Database integration tests require `HORARY_DB_TESTS=1`; use `--tb=no` to avoid driver tracebacks exposing connection strings. `HORARY_DATABASE_URL` takes priority over integration-managed connection strings, allowing independent credential rotation. `AI_PAUSED=1` disables new paid calls while leaving the example and archive available.

Deploy as a FastAPI project on Vercel. Production needs persistent Postgres; no in-memory or local-file budget counters. Static assets are served by FastAPI. The city dataset is bundled; there is no external geocoder request per keystroke.

## Implemented

- Russian and English responsive UI, topic selection, city search, server UTC timestamp.
- Seven classical planets, Regiomontanus houses, longitudes/speeds/retrograde, five major aspects within a fixed display orb of 6°. SVG/PNG chart.
- OpenAI explanation with validated fact and rule references; unsupported topics rejected. One model call, no retries.
- Persistent private results, browser-owner cookie, explicit revocable sharing, deletion, JSON export, usefulness feedback.
- Database-atomic rate limits and conservative monthly budget reservation. Up to 10 report attempts per owner in a rolling 24h window (including failed AI calls; repeated questions allowed), one request per IP hash per minute, 380 attempts/calendar month UTC globally. Each attempt reserves $0.05 without refunds, including failed calls; ceiling $19 leaves $1 buffer. This is deliberately conservative, not actual billing. At configured model rates and maximum 30KB prompt for mini or 12KB for full GPT-4.1 / 1400 output tokens, individual call cost is below the reservation. Model/prices must be rechecked before changes. The OpenAI project/provider budget is separate and not configured by this code. Do not use the app's key outside this app.

## Important limits

This is not an expert-validated horary engine and does not claim predictive accuracy. v0.1 does NOT calculate essential dignities, reception, void-of-course Moon, translation/collection of light, perfection of future aspects, or precise timing. No yes/no verdict is generated. The interface discloses these limits. Applying means the aspect error is smaller one hour later, not that the aspect will perfect before sign changes/stations.

Ephemeris uses the built-in Moshier calculations in Swiss Ephemeris through the pysweph wrapper. Current dates only. Polar latitudes outside ±66° are rejected explicitly. No external ephemeris files are required.

Private archive currently depends on a cookie (one year renewable by future UX); no login/recovery yet. Users should export important results before clearing cookies. Stored results have no scheduled expiration while the service operates. Backups follow the database provider's retention. IP HMAC throttle records expire after two days and are purged on the next new reading. Model requests are not written to application logs; final answers and token usage are saved with the reading. The share URL uses a fragment so the bearer token is not in the page-request URL.

## License and sources

AGPL-3.0-or-later; see LICENSE. Source link is in the site footer. Dependency copyrights remain with their respective authors. Swiss Ephemeris © Astrodienst AG, Dieter Koch and Alois Treindl. Python wrapper: pysweph / pyswisseph contributors (AGPL). See https://github.com/sailorfe/pysweph and https://github.com/aloistr/swisseph .

Cities from GeoNames via geonamescache (https://www.geonames.org/, CC BY 4.0 for GeoNames data). Knowledge notes and links in `knowledge/rules.md`; prose summaries are original, not copied articles. Astronomical calculation precision is not evidence of astrological predictive validity.

## Owner-only model setting

In the dowidai-horary Vercel project, Settings → Environment Variables → HORARY_AI_MODEL:
- `gpt-4.1-mini-2025-04-14` (default)
- `gpt-4.1-2025-04-14`

Set Production and redeploy to apply. Visitors cannot select a model. Unknown values disable new readings. The about page reflects the selected model; saved reports keep their original model. Both options use the existing OpenAI key and the same $0.05 reservation with model-specific input caps. Current prices checked 2026-10-23: mini $0.40/$1.60 and full $2/$8 per million input/output tokens. Recheck pricing before modifying caps or allowed models. Both models are marked deprecated by OpenAI; review replacements before the announced January 14, 2027 shutdown.

## Languages

`/ru` and `/en` share the same private archive and calculations. `/` remains the Russian entry point. The header switch preserves the current page and shared-link fragment. Interface language is passed as `X-Horary-Language`; a reading also includes a validated `language` field. Saved AI answers retain their original language, while chart labels follow the interface. Legacy records without a language are Russian. Switching language does not translate or regenerate an existing AI answer.

To add a language:
1. Register its code, display name, formatting locale and prompt language in `i18n.LANGUAGES`.
2. Add `static/locales/<code>.json` for interface strings and `locales/<code>.json` for API errors and calculated labels. Russian source strings are the keys; `{name}` placeholders are replaced by the client.
3. Add authored content in `static/<code>/about.html`, `technical.html` and `articles/`. English content is maintained in `scripts/build_english_pages.py`; regenerate it with `python scripts/build_english_pages.py`.
4. Verify transcription support for the language, check its terminology with a native speaker, and extend localization tests. New locales inherit routes, navigation, alternate links and statistics grouping without changes to the calculation engine.

## Owner statistics

`/admin` is a separate password-protected dashboard. It shows saved reports, distinct browser archives, last 24h/7d counts, a 30-day UTC chart, languages, topics, models, helpful/not-helpful votes, recorded input/output tokens and the monthly reservation counter. The stats endpoint never returns question text or cities; separate authenticated admin endpoints allow private question/answer review. Owner identifiers and IPs are never returned. Counts reflect the current database: deleted records are excluded, demos and failed calls are not saved reports, and browser archives are not unique people. Tokens cover saved answers only; budget reservations cover reading and voice calls, including failures. Neither is the actual OpenAI account balance.

Run `python scripts/setup_admin.py` once to create a random high-entropy password in ignored `.key-setup/horary-admin.txt` and its SHA-256 hash in `.env.local` as `HORARY_ADMIN_PASSWORD_HASH`. Configure only the hash as a sensitive Production variable in the linked Vercel project, then redeploy. Never put the plaintext password in source, URLs or public variables. SHA-256 here relies on the generated 256-bit random password; do not substitute a short human password. The setup script refuses to overwrite an existing credential.

Admin sessions use a separate signed HttpOnly cookie with an eight-hour expiry, Secure in production, SameSite=Strict and cross-origin POST protection. Five login attempts per IP per 15 minutes are enforced in PostgreSQL. A changed hash or SESSION_SECRET invalidates existing admin sessions. Missing configuration fails closed. Existing tables suffice; this release needs no database migration.

Validation: `python -m pytest tests`, `node --test tests/voice.test.cjs`. For isolated database integration tests load the local configuration first: `HORARY_DB_TESTS=1 python -c "import app, pytest; raise SystemExit(pytest.main(['tests/test_storage.py','-q','--tb=no']))"`. The database suite creates and drops its own temporary schemas.

Admin questions: the authenticated dashboard lists saved questions (20 per page) with city, date, language and model, and expands saved AI answers. The private API never creates share links or returns owner identifiers. Deleted reports are absent.

AI costs in admin are estimated for currently saved reports only, from input/output/cached token counts and model-specific standard rates checked 2026-10-23. Shows total, UTC current month, average and models. Unknown models/missing usage are counted as excluded, not free. Voice, deleted/failed/unsaved calls are not covered. The OpenAI Usage link provides billing reconciliation; no balance is inferred from the $20 top-up.

Primary public domain: https://www.askhorary.app (apex redirects in Vercel). SEO canonical/hreflang URLs use this domain; sitemap.xml lists 16 public RU/EN pages only. Search Console domain property askhorary.app is verified with a DNS TXT record; keep that record. Ask Horary logo is an original SVG; og-card.png is the share preview.
