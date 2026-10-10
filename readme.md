# Messages

A drink tracker that looks like iMessage.

## What it does

You log drinks by "texting" them. Each conversation is a drinking session, each sent bubble is a drink you had. The app parses what you typed ("heineken", "ipa 6%", "whiskey", etc.), figures out the ABV, runs the Widmark formula to estimate your BAC in real time, and a fake friend texts back. The replies read like a normal thread with a 26-year-old guy: short reactions, longer rambles about work / the gym / fantasy / dating, sometimes split over two or three bubbles, sometimes ending in a question, and a little time-aware ("bro it's a tuesday", "lol it's not even noon", "pace yourself champ" once you're deep). Nothing in the text gives the game away. **Tap any bubble** and a small iMessage-style caption shows the time, your BAC right after that drink, and the running drink count. Tap again to hide it.

The contact avatar at the top of a conversation shows the session's standard drink count with your current estimated BAC underneath it, and turns green → amber → red as the count climbs. That BAC is "as of right now" and keeps ticking down as you sober off. New conversations get a friend's name by default (rename from the header). Long-press a sent bubble to edit its time or text, or delete it; long-press a conversation to rename or delete it. The **+** button stamps the next message with a different time (an iOS-style drum picker with "15m ago / 1h ago" shortcuts) for drinks you forgot to log.

### Hidden dashboard

Tap **Edit** in the top-left of the conversation list. It opens an Insights view for the last 7 (or 30) days: total standard drinks with the change vs the prior period, your BAC right now and when it hits zero, peak BAC (and when), time-weighted average BAC, hours over 0.08, hours with anything on board, drinks per session, calories, drinks-per-day bars, a BAC curve for the week with the 0.08 line, what you drank by type, your go-to orders, every session with its peak and span, and some fun numbers (your week in Michelob Ultras, your biggest day, dry days, the hour you drink most). **Done** takes you back.

## Keyboard

The composer is a real text field, so you type with your phone's own keyboard (autocorrect, dictation, your usual emoji). On iPhone that means iOS also shows its small form toolbar (up/down arrows and a checkmark) above the keyboard; WebKit draws that for every text field and no web page can turn it off. The app pins itself to the visible area while the keyboard is up so the composer sits right on top of it.

## Tech

Flask serves the HTML and a small JSON API. SQLite for persistence. Single container, deployed via docker-compose on a VPS running Dokploy, which handles TLS/routing through Traefik. The frontend is vanilla JS, no framework or build step.

```
.
├── app.py              # Flask + all the math (Widmark timeline, drink parsing, stats)
├── replies.py          # the fake friend: reply pools + generator, default contact names
├── static/
│   ├── index.html      # markup + SVG icon sprite
│   ├── style.css       # iOS 26 Messages look, glass chrome, dashboard
│   ├── app.js          # list / thread / composer / sheets / drum picker
│   ├── dashboard.js    # hidden Insights view, charts are inline SVG
│   ├── manifest.json   # for add-to-home-screen on iOS
│   └── favicon.png
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

All BAC and drink math lives on the backend. BAC follows a piecewise Widmark curve: each drink adds its dose, it burns off at 0.015 %/hr between drinks and never goes below zero, so a long gap mid-session resets you instead of being credited against later drinks. The body constants are hardcoded at the top of `app.py`; change them there to recalibrate.

API: `GET/POST /api/sessions`, `PATCH/DELETE /api/sessions/<id>`, `POST /api/sessions/<id>/drinks` (`raw`, `ts`, `tz`), `PATCH/DELETE /api/drinks/<id>` (`ts` and/or `raw`), `GET /api/stats?days=7&tz=<minutes>` for the dashboard. `tz` is JavaScript's `getTimezoneOffset()` so day buckets and time-of-day replies follow the phone's clock. Replies are stored per drink in a `reply_text` column that is added automatically to existing databases.

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
