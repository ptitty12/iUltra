# Messages

A drink tracker that looks like iMessages.

## What it does

You log drinks by "texting" them. Each conversation is a drinking session, each "sent message" is a drink you had. The app parses what you typed ("heineken", "ipa 6%", "whiskey", etc.), figures out the ABV, runs the Widmark formula to estimate your BAC in real time, and replies with something that looks like a normal text — some innocuous opener, the BAC tucked in the middle, and a conversational closer. So if someone glances at your screen, it just looks like you're texting a friend.

The contact avatar at the top of a conversation shows your running standard drink count with your current estimated BAC underneath it, and turns green → amber → red as the count climbs. That BAC is "as of right now" — it keeps ticking down as you sober off, without needing a new drink logged. Long-press any drink to delete it or change its time (with a confirmation) — the BAC and counter update accordingly.

## Tech

Flask serves both the HTML and a small JSON API. SQLite for persistence. Single container, deployed via docker-compose on a VPS running Dokploy, which handles TLS/routing through Traefik. The frontend is plain vanilla JS, no framework — one HTML file.

The message box is a `contenteditable` div rather than an `<input>`, and the fields inside the modals stay `disabled` while their modal is closed. Both are on purpose: a real form field on the page makes mobile browsers stick a prev/next/done navigation bar above the keyboard, which is an obvious tell that you're in a form and not in Messages.

The structure is dead simple:

```
.
├── app.py              # Flask + all the math (Widmark, drink parsing, reply generation)
├── static/
│   ├── index.html      # The whole frontend
│   ├── manifest.json   # For add-to-home-screen on iOS
│   └── favicon.png
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

All BAC and drink math lives on the backend so the frontend can't be tampered with. The phone weight/sex constants for the Widmark formula are hardcoded at the top of `app.py` — change them there if you need to recalibrate.

## Running it

Local:

```bash
pip install -r requirements.txt
DB_PATH=./drinks.db python app.py
```

Production: push to the repo, Dokploy redeploys automatically. SQLite file lives in a Docker volume so data survives redeploys.

## iOS tip

On iPhone, open the site in Safari, hit share → "Add to Home Screen". Launching from that icon opens the app fullscreen with no Safari chrome, so it really does look like the Messages app.

i love this thing