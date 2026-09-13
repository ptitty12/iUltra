# Messages

A drink tracker that looks like iMessages.

## What it does

You log drinks by "texting" them. Each conversation is a drinking session, each "sent message" is a drink you had. The app parses what you typed ("heineken", "ipa 6%", "whiskey", "2 beers", "3 shots", "double whiskey"), figures out the ABV, runs the Widmark formula to estimate your BAC in real time, and replies with something that looks like a normal text — some innocuous opener, the BAC tucked in the middle, and a conversational closer. So if someone glances at your screen, it just looks like you're texting a friend.

The contact avatar at the top of a conversation shows your running standard drink count with your current estimated BAC underneath it, and turns green → amber → red as the count climbs. That BAC is "as of right now" — it keeps ticking down as you sober off, without needing a new drink logged. Long-press any drink to delete it or change its time (with a confirmation) — the BAC and counter update accordingly.

## Tech

Flask serves both the HTML and a small JSON API. SQLite for persistence. Single container, deployed via docker-compose on a VPS running Dokploy, which handles TLS/routing through Traefik. The frontend is plain vanilla JS, no framework — one HTML file.

### The keyboard

The keyboard is drawn in the page — an iOS-style dark keyboard with a QuickType-style suggestion strip, key pop-ups, shift/caps, number and symbol layers, and hold-to-repeat backspace. Nothing in the app is ever focused, so the system keyboard never opens.

That's deliberate, and it's the whole reason the custom keyboard exists. iOS attaches an accessory bar to the system keyboard, and it gives the app away:

- If there are real form fields on the page, you get the **prev / next / done** navigation bar.
- On any focused editable element at all — `<input>`, `<textarea>`, `contenteditable`, doesn't matter — you get the **AutoFill bar** with the passwords key, credit card, and address pin.

The second one can't be turned off from a web page. There is no API for it in mobile Safari or in a home-screen web app; only a native wrapper can clear `inputAccessoryView`. `autocomplete="off"`, `inputmode`, ARIA roles — none of them touch it. The only way to have a keyboard with no bar over it is to not use the system keyboard, so the app draws its own.

Two things fall out of that for free: nothing ever resizes the visual viewport (the system keyboard sliding up used to shove the transcript around), and the suggestion strip can offer real drink names instead of English words. Those come from `/api/vocab`, which pulls the plain-word alternatives back out of `DRINK_PATTERNS`, so anything the strip offers is guaranteed to parse to a real ABV.

The modals are the last place with real fields, and they stay `disabled` while their overlay is hidden so nothing on the page is focusable during normal use. Renaming a session types on the drawn keyboard too; the date pickers are left native, since those open a wheel picker rather than a keyboard.

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

All BAC and drink math lives on the backend so the frontend can't be tampered with. The phone weight/sex constants for the Widmark formula are hardcoded at the top of `app.py` — change them there if you need to recalibrate. **They're the single biggest lever on every number the app shows**: `WEIGHT_KG` is set to 86 (190 lb) and `WIDMARK_R` to 0.68, and if your real weight is lower than that, every BAC reads proportionally low.

`calc_bac` walks the drinks in order and burns alcohol off *between* them, clamping at zero at each step. The obvious shortcut — sum every drink's peak, subtract `METABOLISM × (time since the first drink)` — is wrong, and wrong in the dangerous direction: it keeps eliminating through stretches where there was nothing left to eliminate, so one beer at dinner banks negative alcohol against everything you drink later that night. A beer at 6pm followed by three at 1am used to read 0.000.

Quantities are parsed too — `2 beers`, `two beers`, `beer x2`, `a couple beers`, `3 shots`, `double whiskey`. The count scales the volume, so the standard-drink count and BAC both follow. It's skipped when the whole message is itself a drink name, so brands that read like counts (`two robbers`, `four loko`, `1800`, `151`, `3 floyds`, `triple sec`) still come out as one drink. Plurals match the dictionary as well — before, `beers` and `shots` missed every pattern and silently fell back to the generic 12 oz / 5% default.

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