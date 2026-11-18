# Bangladesh News Hub — automated PWA

## What it does
- Reads publisher RSS feeds for original headlines, article URLs, timestamps and available RSS images.
- Updates every three hours using GitHub Actions; first scheduled run is 06:00 Bangladesh time.
- Groups similar headlines and provides direct publisher links.
- Displays available publisher-provided news images (subject to publisher permissions and image hosting restrictions).
- Stores up to 120 recent stories and a daily archive. Morning 30–40 stories is a target, not a guarantee.
- Requires no AI service, API key, or paid summarization.
- Installs as a PWA using Chrome on Android after hosting via GitHub Pages.

## Limits
- Publishers may remove or block RSS feeds or remote images; missing photos are hidden.
- Verify each source's RSS/image reuse terms before publishing publicly.
- GitHub scheduled runs can be delayed; no push notifications are configured.
- The morning edition is a collection of current stories, not a separately curated 30–40-story product.

## Deploy (one-time setup)
1. Create a GitHub account and a new **public** repository, e.g. `bangladesh-news-hub`. (A public repo is the easiest GitHub Pages setup.)
2. Upload all files in this folder to the repository root. Keep `.github/workflows/update-news.yml`.
3. In GitHub: **Settings → Pages → Build and deployment → Deploy from a branch → main → / (root)**, then Save.
4. Go to **Actions → Update Bangladesh News → Run workflow** once. This creates `news.json`.
5. Wait for GitHub Pages to publish. Your site URL will look like `https://YOUR-USERNAME.github.io/bangladesh-news-hub/`.
6. Open that HTTPS URL in Chrome on Android → ⋮ → **Install app** (or **Add to Home screen**).

## How the schedule works
GitHub Actions runs at minute 0 every 3 hours (UTC): 00:00, 03:00, ... 21:00. Bangladesh is UTC+6, so the first run is 06:00 local. GitHub scheduled workflows can be delayed during busy periods; they are not a hard real-time SLA.

## Local test
```bash
python -m pip install -r requirements.txt
python scripts/update_news.py
```

## Feed list
Edit `sources.json` to add/remove publishers. Feed URLs should be verified and used only according to each publisher's terms.
