# Хорар · by DowidAI

Russian-language experimental horary web application. Free public beta, AGPL-3.0-or-later. Separate from the DowidAI consulting website. No personal biography or employer information.

## Run

Python 3.12. Install `pip install -r requirements.txt`. Copy `.env.example` to `.env.local` and configure a dedicated OpenAI key, Postgres `DATABASE_URL`, and a random `SESSION_SECRET`. Never commit env files.

Initialise the database with `python -c "import app, storage; storage.migrate()"`. Run `uvicorn app:app --reload`. Tests: `pip install pytest`, then `python -m pytest tests`. Database integration tests require `HORARY_DB_TESTS=1`; use `--tb=no` to avoid driver tracebacks exposing connection strings. `HORARY_DATABASE_URL` takes priority over integration-managed connection strings, allowing independent credential rotation. `AI_PAUSED=1` disables new paid calls while leaving the example and archive available.

Deploy as a FastAPI project on Vercel. Production needs persistent Postgres; no in-memory or local-file budget counters. Static assets are served by FastAPI. The city dataset is bundled; there is no external geocoder request per keystroke.

## Implemented

- Russian responsive UI, topic selection, city search, server UTC timestamp.
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
