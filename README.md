# ServerGuard administration bot

This repository was empty when implementation began, so no existing website renderer, release manifest, hosting configuration, or `news/news.json` was available to preserve. The backend is standalone and the browser client in `js/news.js` is deliberately framework-free.

## Run

1. Install Python 3.11+, create a virtual environment, and run `pip install -e '.[test]'`.
2. Copy `.env.example` to `.env`. Set `TELEGRAM_BOT_TOKEN`, numeric comma-separated `TELEGRAM_ADMIN_IDS`, and `PUBLIC_API_URL`.
3. Start the API: `uvicorn api.main:app --host "$API_HOST" --port "$API_PORT"`.
4. Start the bot in a second process: `python -m bot.main`.
5. Put `js/news.js` on the website after its news container (`#news` or `.news-grid`). Set `window.SERVERGUARD_NEWS_API` if the API host differs.

The API process owns `DATABASE_PATH`; back up that SQLite file and `MEDIA_PATH` together. Run both processes under systemd, Docker, or another supervisor and put HTTPS/TLS reverse proxying in front of the API. The API exposes only read-only news and media routes; Telegram is the only write interface. CORS defaults to the production site plus local preview origins.

## Data compatibility

The database query enforces publication time, expiry, and soft deletion on every request. Since this checkout had no historical JSON file, no migration was run. If a legacy `news/news.json` is supplied, import it once with a reviewed migration script rather than silently duplicating records; preserve its original IDs by extending the importer/schema before production use.

## Tests

Run `pytest`. The API uses UTC ISO-8601 timestamps, the public endpoint is bounded/paginated, and user content is HTML-escaped in the supplied renderer. Telegram admin authorization is based only on numeric user IDs.
