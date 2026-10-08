from flask import Flask, request, jsonify, send_from_directory
import sqlite3, os, re, random, json, bisect
from datetime import datetime, timedelta, timezone

from replies import generate_reply, suggest_name

app = Flask(__name__, static_folder='static')

DB_PATH = os.environ.get("DB_PATH", "/data/drinks.db" if os.path.isdir("/data") else "./drinks.db")

# --- body params (widmark formula inputs) ---
WEIGHT_KG = 86.0
WIDMARK_R = 0.68
METABOLISM = 0.015  # %/hr
HOUR_MS = 3600000
DAY_MS = 86400000

# --- drink parsing ---
DRINK_PATTERNS = [
    (re.compile(r"\b(light\s*beer|bud\s*light|miller\s*lite|coors\s*light|michelob\s*ultra|ultra|mich\s*ultra|natural\s*light|natty\s*light|natty|keystone\s*light|keystone|busch\s*light|busch|pabst|pbr|rolling\s*rock|hamms|hamm|stroh|old\s*milwaukee|schlitz|genessee|genny|labatt\s*blue|labatt|molson\s*light|blue\s*moon\s*light|amstel\s*light|heineken\s*light|corona\s*light|modelo\s*light|dos\s*equis\s*light|tecate\s*light|fosters\s*light|carlsberg\s*light|peroni\s*leggera|sapporo\s*light|kirin\s*light|asahi\s*light|yuengling\s*light|lionshead|ice\s*house|icehouse|milwaukee\s*best|beast|the\s*beast|mic|mic\s*ultra|michelob)\b", re.I), "light beer", 4.2, 12),

    (re.compile(r"\b(beer|lager|pilsner|heineken|corona|modelo|bud|budweiser|stella|pacifico|dos\s*equis|tecate|negra\s*modelo|victoria|sol|carta\s*blanca|bohemia|presidente|presidente|tiger|kingfisher|tusker|castle|windhoek|lion|singha|chang|leo|bintang|red\s*stripe|banks|carib|presidente|belikin|brahma|skol|antartica|nova\s*schin|kaiser|bavaria|aguila|club\s*colombia|cristal|cusquena|toña|gallo|salva\s*vida|imperial|pilsen|club|poker|peroni|moretti|birra|nastro|carlsberg|tuborg|efes|bomonti|marmara|mythos|alpha|fix|zywiec|okocim|tyskie|lech|kozel|staropramen|budvar|gambrinus|krusovice|zlatopramen|sapporo|kirin|asahi|orion|hitachino|yebisu|tsingtao|snow|harbin|yanjing|kingway|reeb|blue\s*ribbon|pabst\s*blue|old\s*style|grain\s*belt|leinenkugel|leine|yuengling|yeungling|shiner|shiner\s*bock|lone\s*star|pearl|big\s*bend|saint\s*arnold|abita|sweetwater|terrapin|dogfish|sam\s*adams|samuel\s*adams|boston\s*lager|fosters|tooheys|vb|victoria\s*bitter|xxxx|castlemaine|coopers|great\s*northern|steinlager|tui|speights|mac|wainuiomata|windmill|windhoek|hansa|castle\s*lite)\b", re.I), "beer", 5.0, 12),

    (re.compile(r"\b(ipa|pale\s*ale|stout|porter|ale|hazy|sour|craft|double\s*ipa|dipa|triple\s*ipa|west\s*coast\s*ipa|new\s*england\s*ipa|neipa|session\s*ipa|black\s*ipa|red\s*ale|amber\s*ale|brown\s*ale|blonde\s*ale|golden\s*ale|kolsch|kölsch|hefeweizen|weizen|wheat\s*beer|witbier|wit|saison|farmhouse|belgian|dubbel|tripel|quad|quadrupel|barleywine|barley\s*wine|imperial\s*stout|milk\s*stout|oatmeal\s*stout|dry\s*stout|cream\s*ale|steam\s*beer|california\s*common|bock|doppelbock|maibock|dunkel|schwarzbier|rauchbier|smoked|gose|berliner|lambic|gueuze|kriek|flanders|oud\s*bruin|brett|brettanomyces|wild\s*ale|mixed\s*ferm|spontaneous|cask|nitro|cellar|barrel\s*aged|ba\s*stout|pastry\s*stout|fruited|kettle\s*sour|brut\s*ipa|milkshake\s*ipa|smoothie|slushie|frozen\s*sour|lager\s*ipa|cold\s*ipa|cold\s*crash|lager\s*yeast|stone|lagunitas|sierra\s*nevada|new\s*belgium|bells|founders|oskar\s*blues|dogfish\s*head|russian\s*river|pliny|3\s*floyds|goose\s*island|boulevard|odell|great\s*lakes|deschutes|rogue|ninkasi|elysian|ballast\s*point|green\s*flash|firestone|alesmith|modern\s*times|pizza\s*port|epic|uinta|wasatch|squatters|cigar\s*city|funky\s*buddha|due\s*south|swamp\s*head|sweetwater|terrapin|creature\s*comforts|monday\s*night|second\s*self|tropicalia|weldwerks|cerebral|crooked\s*stave|black\s*project|casey|jester\s*king|live\s*oak|real\s*ale|saint\s*arnolds|karbach|8th\s*wonder|no\s*label|southern\s*star|buffalo\s*bayou|ingenious)\b", re.I), "craft beer", 6.5, 12),

    (re.compile(r"\b(wine|chardonnay|cab|merlot|pinot|ros[eé]|sauvignon|riesling|cabernet|zinfandel|zin|syrah|shiraz|grenache|mourvedre|tempranillo|rioja|malbec|carmenere|petite\s*sirah|petite\s*verdot|cab\s*franc|cabernet\s*franc|sangiovese|chianti|barolo|barbaresco|brunello|amarone|valpolicella|montepulciano|primitivo|negroamaro|nero\s*d\s*avola|aglianico|vermentino|verdicchio|soave|pinot\s*grigio|pinot\s*gris|gewurztraminer|gruner|grüner|albariño|albarino|txakoli|verdejo|rueda|cava|chablis|burgundy|beaujolais|gamay|viognier|roussanne|marsanne|chenin|vouvray|muscadet|sancerre|pouilly|bordeaux|champagne|prosecco|sparkling|moscato|muscat|port|porto|sherry|madeira|marsala|vermouth|ice\s*wine|icewine|eiswein|late\s*harvest|botrytis|sauternes|barsac|tokay|tokaji|vin\s*santo|passito|amarone|recioto|lambrusco|brachetto|vinho\s*verde|alentejo|douro|dao|ribera|priorat|penedes|somontano|navarra|rueda|white\s*wine|red\s*wine|rose\s*wine|box\s*wine|table\s*wine|house\s*wine|by\s*the\s*glass|btg|natural\s*wine|orange\s*wine|biodynamic|organic\s*wine|piquette)\b", re.I), "wine", 13.0, 5),

    (re.compile(r"\b(shot|tequila|vodka|rum|gin|whiskey|whisky|bourbon|scotch|mezcal|brandy|cognac|blanco|reposado|anejo|añejo|extra\s*anejo|cristalino|silver\s*tequila|gold\s*tequila|patron|casamigos|don\s*julio|herradura|espolon|olmeca|sauza|jose\s*cuervo|cuervo|1800|hornitos|cazadores|milagro|el\s*jimador|lunazul|codigo|tequila\s*ocho|fortaleza|tapatio|siete\s*leguas|el\s*tesoro|arette|olmeca\s*altos|altos|avion|deleon|clase\s*azul|volcan|g4|mijenta|teremana|lobos|cincoro|cincoro|818|kendall\s*jenner|tequila|grey\s*goose|belvedere|ketel\s*one|absolut|smirnoff|tito|titos|ciroc|stolichnaya|stoli|russian\s*standard|chopin|beluga|crystal\s*head|wheatley|deep\s*eddy|new\s*amsterdam|skyy|three\s*olives|burnetts|svedka|pinnacle|vladamir|vlad|hawkeye|everclear|grain\s*alcohol|190|151|bacardi|captain\s*morgan|captain|spiced\s*rum|malibu|kraken|mount\s*gay|appleton|myers|plantation|diplomatico|diplomático|zacapa|flor\s*de\s*cana|don\s*q|ron\s*del\s*barrilito|angostura|el\s*dorado|pusser|goslings|gosling|dark\s*and\s*stormy|sailor\s*jerry|blackheart|tanqueray|bombay|hendricks|hendrick|beefeater|gordons|gordon|sipsmith|the\s*botanist|malfy|aviation|bulldog|monkey\s*47|roku|nikka\s*coffey|jin\s*jiji|jackd|jack\s*daniels|jack|jim\s*beam|jim|makers|maker|woodford|knob\s*creek|knob|buffalo\s*trace|eagle\s*rare|blantons|blanton|weller|pappy|four\s*roses|wild\s*turkey|russell|elijah\s*craig|heaven\s*hill|larceny|old\s*forester|old\s*fitzgerald|redemption|high\s*west|angels\s*envy|angel|michter|mitchers|rabbit\s*hole|bardstown|legent|basil\s*hayden|basil|old\s*grand\s*dad|ezra\s*brooks|ezra|1792|colonel\s*e|e\.h\s*taylor|bookers|booker|bakers|baker|knob|johnny\s*walker|johnnie\s*walker|johnnie|red\s*label|black\s*label|blue\s*label|green\s*label|gold\s*label|double\s*black|glenfiddich|glenlivet|macallan|balvenie|dalmore|highland\s*park|oban|lagavulin|laphroaig|ardbeg|bowmore|bunnahabhain|caol\s*ila|kilchoman|bruichladdich|springbank|glendronach|aberlour|glenfarclas|benriach|glen\s*moray|tomatin|dalwhinnie|glenmorangie|talisker|clynelish|aberfeldy|craigellachie|mortlach|deanston|tobermory|ledaig|jura|isle\s*of\s*jura|hibiki|yamazaki|hakushu|nikka|yoichi|miyagikyo|kavalan|amrut|paul\s*john|rampur|indri|hennessy|henny|remy|remy\s*martin|martell|courvoisier|camus|delamain|bertrand|chateau|torres|cardenal\s*mendoza|gran\s*duque|vecchio\s*amaro|armagnac|calvados|pisco|grappa|slivovitz|aguardiente|cachaça|cachaca|batida|singani|eau\s*de\s*vie|schnapps|aquavit|akvavit|absinthe|pastis|sambuca|limoncello|amaro|fernet|fernet\s*branca|branca|averna|montenegro|meletti|cynar|aperol|campari|suze|lillet|chartreuse|benedictine|drambuie|baileys|kahlua|khalua|frangelico|disaronno|amaretto|midori|blue\s*curacao|curacao|triple\s*sec|cointreau|grand\s*marnier|st\s*germain|elderflower|hypnotiq|hpnotiq|alize|sourpuss|peach\s*schnapps|butterscotch\s*schnapps|fireball|fireball\s*whiskey|jack\s*fire|jim\s*beam\s*fire|cinnamon\s*whiskey|rumchata|horchata\s*rum|cream\s*liqueur|irish\s*cream|irish\s*whiskey|jameson|jamo|bushmills|tullamore|redbreast|green\s*spot|yellow\s*spot|writers\s*tears|powers|teeling|slane|roe|connacht|dingle|waterford|westmeath)\b", re.I), "spirit shot", 40.0, 1.5),

    (re.compile(r"\b(cocktail|margarita|mojito|old\s*fashion|old\s*fashioned|negroni|manhattan|martini|daiquiri|sour|cosmopolitan|cosmo|aperol\s*spritz|spritz|paloma|ranch\s*water|moscow\s*mule|mule|dark\s*and\s*stormy|penicillin|paper\s*plane|last\s*word|corpse\s*reviver|bee\s*sting|bee\s*keeper|naked\s*and\s*famous|jungle\s*bird|mai\s*tai|tiki|zombie|painkiller|pina\s*colada|pina|colada|bahama\s*mama|sex\s*on\s*the\s*beach|woo\s*woo|bay\s*breeze|madras|cape\s*cod|sea\s*breeze|harvey\s*wallbanger|fuzzy\s*navel|screwdriver|mimosa|bellini|kir|kir\s*royale|french\s*75|sidecar|between\s*the\s*sheets|stinger|grasshopper|pink\s*squirrel|brandy\s*alexander|alexander|white\s*russian|black\s*russian|espresso\s*martini|porn\s*star\s*martini|dirty\s*martini|gibson|vesper|gimlet|bee\s*knees|southside|clover\s*club|aviation|french\s*connection|rusty\s*nail|godfather|godmother|rob\s*roy|bobby\s*burns|blood\s*and\s*sand|remember\s*the\s*maine|vieux\s*carre|sazerac|toronto|monte\s*carlo|black\s*manhattan|red\s*hook|greenpoint|bensonhurst|bushwick|slope|carroll|cobble|prospect|fort\s*hamilton|dead\s*rabbit|new\s*york\s*sour|whiskey\s*sour|amaretto\s*sour|pisco\s*sour|mezcal\s*sour|tequila\s*sour|gin\s*sour|rum\s*sour|bourbon\s*sour|vodka\s*sour|tom\s*collins|john\s*collins|vodka\s*collins|rum\s*collins|tequila\s*collins|gin\s*fizz|sloe\s*gin\s*fizz|ramos\s*gin\s*fizz|silver\s*fizz|golden\s*fizz|royal\s*fizz|long\s*island|long\s*island\s*iced\s*tea|electric\s*lemonade|adios|adios\s*motherfucker|amf|blue\s*motorcycle|island|hurricane|lemonade\s*cocktail|arnold\s*palmer|hard\s*arnold|jack\s*and\s*coke|jack\s*coke|rum\s*and\s*coke|rum\s*coke|cuba\s*libre|gin\s*and\s*tonic|gin\s*tonic|g\s*and\s*t|vodka\s*soda|vodka\s*water|vodka\s*tonic|tequila\s*soda|bourbon\s*ginger|whiskey\s*ginger|ginger\s*highball|highball|lowball|build|stirred|shaken|strained|neat|on\s*the\s*rocks|up|frozen|blended|smash|julep|mint\s*julep|whiskey\s*smash|gin\s*smash|vodka\s*smash|swizzle|buck|mule\s*variation|punch|bowl|sangria|batch|clarified|milk\s*punch|clarified\s*milk|fat\s*washed|infused|shrub|oleo\s*saccharum|sous\s*vide|rotovap|centrifuge)\b", re.I), "cocktail", 20.0, 4),

    (re.compile(r"\b(seltzer|white\s*claw|truly|hard\s*selt|hard\s*seltzer|bon\s*viv|bon\s*vivant|vizzy|bud\s*light\s*seltzer|bud\s*seltzer|corona\s*seltzer|corona\s*hard|michelob\s*ultra\s*seltzer|ultra\s*seltzer|naturdays|natural\s*light\s*seltzer|natty\s*seltzer|topo\s*chico\s*hard|topo\s*chico|lone\s*river|ranch\s*water\s*can|high\s*noon|aha\s*topo|cacti|brizzy|press|press\s*hard\s*seltzer|straightaway|austere|social|crook|crook\s*and\s*marker|noca|wild\s*basin|oskar\s*blues\s*seltzer|Two\s*Robbers|two\s*robbers|pabst\s*hard|pabst\s*seltzer|rolling\s*seltzer|corona\s*refresca|seagrams\s*escape|mikes\s*harder|mike\s*harder|mikes\s*hard|mikes|four\s*loko\s*hard|four\s*loko|loco|loco\s*hard|beast\s*ice|beast\s*seltzer|beast\s*light\s*seltzer|easy\s*ice|arctic\s*ice)\b", re.I), "hard seltzer", 5.0, 12),
]

def parse_drink(text):
    dtype, abv, oz = "drink", 5.0, 12.0
    for pat, t, a, o in DRINK_PATTERNS:
        if pat.search(text):
            dtype, abv, oz = t, a, o
            break
    am = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if am: abv = float(am.group(1))
    om = re.search(r"(\d+(?:\.\d+)?)\s*oz", text, re.I)
    if om: oz = float(om.group(1))
    return dtype, abv, oz

# rough kcal per fluid ounce by drink type, for the dashboard's fun numbers
KCAL_PER_OZ = {
    "light beer": 100 / 12, "beer": 150 / 12, "craft beer": 200 / 12, "wine": 125 / 5,
    "spirit shot": 97 / 1.5, "cocktail": 180 / 4, "hard seltzer": 100 / 12, "drink": 150 / 12,
}

def std_drinks(oz, abv):
    return (oz * 29.5735 * (abv / 100) * 0.789) / 14

def drink_rise(d):
    """how much one drink lifts BAC (widmark, in %)"""
    grams = (d["oz"] * 29.5735) * (d["abv"] / 100) * 0.789
    return (grams / (WEIGHT_KG * 1000 * WIDMARK_R)) * 100

def timeline(drinks):
    """Piecewise widmark curve for drinks sorted by ts.

    Returns a list of (ts, bac_after) per drink. Between drinks BAC burns off at
    METABOLISM per hour and never goes below zero, so a long gap mid-session
    resets you properly instead of being credited against later drinks.
    """
    out = []
    bac = 0.0
    prev = None
    for d in drinks:
        if prev is not None:
            bac = max(0.0, bac - METABOLISM * (d["ts"] - prev) / HOUR_MS)
        bac += drink_rise(d)
        out.append((d["ts"], bac))
        prev = d["ts"]
    return out

def bac_at(tl, t_ms):
    """BAC at t_ms from a timeline() result."""
    if not tl:
        return 0.0
    ts_list = [p[0] for p in tl]
    i = bisect.bisect_right(ts_list, t_ms) - 1
    if i < 0:
        return 0.0
    ts, after = tl[i]
    return max(0.0, after - METABOLISM * (t_ms - ts) / HOUR_MS)

def calc_bac(drinks, now_ms=None):
    """widmark bac at now_ms given list of {ts, oz, abv} (any order)"""
    if now_ms is None:
        now_ms = int(datetime.now().timestamp() * 1000)
    ds = sorted((d for d in drinks if d["ts"] <= now_ms), key=lambda d: d["ts"])
    return bac_at(timeline(ds), now_ms)

def sober_at(tl):
    if not tl:
        return None
    ts, after = tl[-1]
    return int(ts + after / METABOLISM * HOUR_MS)

def curve_stats(tl, now_ms):
    """peak / time-weighted average / hours above zero and above .08 for one session"""
    if not tl:
        return {"peak": 0.0, "peak_ts": None, "avg": 0.0, "hours_buzzed": 0.0, "hours_over_08": 0.0}
    peak_ts, peak = max(tl, key=lambda p: p[1])
    area = 0.0
    buzzed = 0.0
    over = 0.0
    for i, (ts, after) in enumerate(tl):
        nxt = tl[i + 1][0] if i + 1 < len(tl) else None
        t_sober = ts + after / METABOLISM * HOUR_MS
        seg_end = min(x for x in (nxt, t_sober, now_ms) if x is not None)
        if seg_end <= ts:
            continue
        dt_h = (seg_end - ts) / HOUR_MS
        end_bac = max(0.0, after - METABOLISM * dt_h)
        area += (after + end_bac) / 2 * dt_h
        buzzed += dt_h
        if after > 0.08:
            over += min(dt_h, (after - 0.08) / METABOLISM)
    return {
        "peak": peak, "peak_ts": peak_ts,
        "avg": (area / buzzed) if buzzed else 0.0,
        "hours_buzzed": buzzed, "hours_over_08": over,
    }

def recompute_session_bacs(conn, session_id):
    """Recompute each drink's stored bac/std_total snapshot (and the legacy reply
    columns) from all drinks in the session sorted by ts. Called after any mutation."""
    drinks = [dict(d) for d in conn.execute(
        "SELECT * FROM drinks WHERE session_id = ? ORDER BY ts ASC", (session_id,)
    ).fetchall()]
    tl = timeline(drinks)
    running_total = 0.0
    for d, (_, bac) in zip(drinks, tl):
        running_total += std_drinks(d["oz"], d["abv"])
        conn.execute(
            """UPDATE drinks SET bac = ?, std_total = ?, reply_bac_str = ?, reply_std = ?
               WHERE id = ?""",
            (bac, running_total, f"{bac:.3f}", f"{round(running_total)}", d["id"])
        )
    conn.commit()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS drinks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            raw TEXT NOT NULL,
            ts INTEGER NOT NULL,
            type TEXT NOT NULL,
            abv REAL NOT NULL,
            oz REAL NOT NULL,
            bac REAL NOT NULL,
            std_total REAL NOT NULL,
            reply_opener TEXT NOT NULL,
            reply_bac_str TEXT NOT NULL,
            reply_std TEXT NOT NULL,
            reply_closer TEXT NOT NULL
        );
    """)
    # reply_text: JSON list of bubbles; added after the first release, so migrate in place
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(drinks)").fetchall()}
    if "reply_text" not in cols:
        conn.execute("ALTER TABLE drinks ADD COLUMN reply_text TEXT")
    conn.commit()
    conn.close()

init_db()

def reply_list(row):
    """bubbles for a drink row; legacy rows fall back to their opener/closer"""
    txt = row.get("reply_text")
    if txt:
        try:
            v = json.loads(txt)
            if isinstance(v, list) and v:
                return [str(x) for x in v]
        except ValueError:
            pass
    return [row.get("reply_opener") or "lol", row.get("reply_closer") or "hbu"]

def ensure_replies(conn, drinks, tz):
    """generate + persist reply_text for legacy rows that don't have one yet"""
    recent = []
    for i, d in enumerate(drinks):
        if not d.get("reply_text"):
            bubbles = generate_reply(d["ts"], tz, i + 1, recent)
            d["reply_text"] = json.dumps(bubbles)
            conn.execute("UPDATE drinks SET reply_text = ? WHERE id = ?", (d["reply_text"], d["id"]))
        recent.extend(reply_list(d))
        recent = recent[-40:]

def session_payload(conn, s, now_ms, tz):
    drinks = [dict(d) for d in conn.execute(
        "SELECT * FROM drinks WHERE session_id = ? ORDER BY ts ASC", (s["id"],)
    ).fetchall()]
    ensure_replies(conn, drinks, tz)
    for d in drinks:
        d["reply"] = reply_list(d)
        d["std"] = std_drinks(d["oz"], d["abv"])
    tl = timeline([d for d in drinks if d["ts"] <= now_ms])
    return {
        "id": s["id"],
        "name": s["name"],
        "start": s["start"],
        "drinks": drinks,
        "bac": bac_at(tl, now_ms),
        "total_std": sum(d["std"] for d in drinks),
        "sober_at": sober_at(tl),
        "metabolism": METABOLISM,
        "server_now": now_ms,
    }

def tz_arg():
    try:
        return int(request.args.get("tz", "0"))
    except ValueError:
        return 0

# --- routes ---

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    conn = get_db()
    now_ms = int(datetime.now().timestamp() * 1000)
    tz = tz_arg()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY start DESC").fetchall()
    result = [session_payload(conn, s, now_ms, tz) for s in sessions]
    conn.commit()
    conn.close()
    return jsonify(result)

@app.route("/api/sessions", methods=["POST"])
def create_session():
    body = request.get_json() or {}
    conn = get_db()
    name = (body.get("name") or "").strip()
    if not name:
        taken = [r["name"] for r in conn.execute("SELECT name FROM sessions").fetchall()]
        name = suggest_name(taken)
    start = int(body.get("start") or datetime.now().timestamp() * 1000)
    cur = conn.execute(
        "INSERT INTO sessions (name, start, created_at) VALUES (?, ?, ?)",
        (name, start, int(datetime.now().timestamp() * 1000))
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return jsonify({
        "id": sid, "name": name, "start": start, "drinks": [],
        "bac": 0.0, "total_std": 0.0, "sober_at": None,
        "metabolism": METABOLISM, "server_now": int(datetime.now().timestamp() * 1000),
    })

@app.route("/api/sessions/<int:session_id>", methods=["PATCH"])
def rename_session(session_id):
    body = request.get_json() or {}
    conn = get_db()
    if "name" in body and body["name"].strip():
        conn.execute("UPDATE sessions SET name = ? WHERE id = ?", (body["name"].strip(), session_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    conn = get_db()
    conn.execute("DELETE FROM drinks WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/sessions/<int:session_id>/drinks", methods=["POST"])
def add_drink(session_id):
    body = request.get_json() or {}
    raw = (body.get("raw") or "").strip()
    if not raw:
        return jsonify({"error": "empty"}), 400
    ts = int(body.get("ts") or datetime.now().timestamp() * 1000)  # frontend can send past timestamps
    tz = int(body.get("tz") or 0)

    conn = get_db()
    s = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not s:
        conn.close()
        return jsonify({"error": "session not found"}), 404

    dtype, abv, oz = parse_drink(raw)

    prior = [dict(d) for d in conn.execute(
        "SELECT * FROM drinks WHERE session_id = ? ORDER BY ts ASC", (session_id,)
    ).fetchall()]
    recent = []
    for d in prior[-12:]:
        recent.extend(reply_list(d))
    bubbles = generate_reply(ts, tz, len(prior) + 1, recent)

    # insert with placeholder bac/std_total, then recompute the whole session
    cur = conn.execute(
        """INSERT INTO drinks
           (session_id, raw, ts, type, abv, oz, bac, std_total,
            reply_opener, reply_bac_str, reply_std, reply_closer, reply_text)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (session_id, raw, ts, dtype, abv, oz, 0.0, 0.0,
         bubbles[0], "0.000", "0", bubbles[-1], json.dumps(bubbles))
    )
    conn.commit()
    drink_id = cur.lastrowid
    recompute_session_bacs(conn, session_id)

    drink = dict(conn.execute("SELECT * FROM drinks WHERE id = ?", (drink_id,)).fetchone())
    conn.close()
    drink["reply"] = bubbles
    drink["std"] = std_drinks(drink["oz"], drink["abv"])
    return jsonify(drink)

@app.route("/api/drinks/<int:drink_id>", methods=["PATCH"])
def edit_drink(drink_id):
    body = request.get_json() or {}
    conn = get_db()
    drink = conn.execute("SELECT session_id FROM drinks WHERE id = ?", (drink_id,)).fetchone()
    if not drink:
        conn.close()
        return jsonify({"error": "drink not found"}), 404
    if "ts" in body:
        conn.execute("UPDATE drinks SET ts = ? WHERE id = ?", (int(body["ts"]), drink_id))
    if "raw" in body and str(body["raw"]).strip():
        raw = str(body["raw"]).strip()
        dtype, abv, oz = parse_drink(raw)
        conn.execute("UPDATE drinks SET raw = ?, type = ?, abv = ?, oz = ? WHERE id = ?",
                     (raw, dtype, abv, oz, drink_id))
    conn.commit()
    recompute_session_bacs(conn, drink["session_id"])
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/drinks/<int:drink_id>", methods=["DELETE"])
def delete_drink(drink_id):
    conn = get_db()
    drink = conn.execute("SELECT session_id FROM drinks WHERE id = ?", (drink_id,)).fetchone()
    if not drink:
        conn.close()
        return jsonify({"error": "drink not found"}), 404
    session_id = drink["session_id"]
    conn.execute("DELETE FROM drinks WHERE id = ?", (drink_id,))
    conn.commit()
    recompute_session_bacs(conn, session_id)
    conn.close()
    return jsonify({"ok": True})

# --- keyboard vocabulary: every name the parser knows, so QuickType can suggest them ---
_VOCAB = None

def vocab():
    global _VOCAB
    if _VOCAB is None:
        words = []
        seen = set()
        for pat, dtype, _, _ in DRINK_PATTERNS:
            body = pat.pattern
            body = body[body.index("(") + 1:body.rindex(")")]
            for alt in body.split("|"):
                w = alt.replace("\\s*", " ").replace("\\.", ".").strip().lower()
                if not w or re.search(r"[\\\[\]\(\)\?\+\*\{\}\^\$]", w):
                    continue
                if w in seen:
                    continue
                seen.add(w)
                words.append({"w": w, "t": dtype})
        _VOCAB = words
    return _VOCAB

@app.route("/api/vocab")
def get_vocab():
    return jsonify(vocab())

# --- dashboard ---

def local_day_index(ts_ms, tz):
    return (ts_ms - tz * 60000) // DAY_MS

def day_label(day_index, tz):
    d = datetime.fromtimestamp(day_index * 86400, tz=timezone.utc)
    return d.strftime("%a"), d.strftime("%Y-%m-%d")

@app.route("/api/stats")
def stats():
    """Everything the hidden dashboard shows. tz = JS getTimezoneOffset() so the
    day buckets follow the phone's local midnight, days = window length."""
    tz = tz_arg()
    try:
        days = max(1, min(90, int(request.args.get("days", "7"))))
    except ValueError:
        days = 7
    now_ms = int(datetime.now().timestamp() * 1000)
    today = local_day_index(now_ms, tz)
    first_day = today - (days - 1)
    window_start = (first_day * DAY_MS) + tz * 60000
    prev_start = window_start - days * DAY_MS

    conn = get_db()
    sessions = [dict(s) for s in conn.execute("SELECT * FROM sessions").fetchall()]
    all_drinks = [dict(d) for d in conn.execute(
        "SELECT * FROM drinks WHERE ts >= ? AND ts <= ? ORDER BY ts ASC", (prev_start, now_ms)
    ).fetchall()]
    conn.close()
    by_session = {}
    for d in all_drinks:
        d["std"] = std_drinks(d["oz"], d["abv"])
        by_session.setdefault(d["session_id"], []).append(d)
    names = {s["id"]: s for s in sessions}

    cur_drinks = [d for d in all_drinks if d["ts"] >= window_start]
    prev_drinks = [d for d in all_drinks if d["ts"] < window_start]

    # per day buckets
    by_day = []
    day_map = {}
    for i in range(days):
        idx = first_day + i
        label, date = day_label(idx, tz)
        row = {"label": label, "date": date, "std": 0.0, "count": 0, "peak": 0.0, "today": idx == today}
        by_day.append(row)
        day_map[idx] = row

    # per session curves (whole session, so bac snapshots include drinks before the window)
    session_rows = []
    curves = []
    total_peak = (0.0, None, None)
    total_area = 0.0
    total_buzzed = 0.0
    total_over = 0.0
    current_bac = 0.0
    latest_sober = None
    for sid, drinks in by_session.items():
        drinks.sort(key=lambda d: d["ts"])
        tl = timeline(drinks)
        in_window = [d for d in drinks if d["ts"] >= window_start]
        if not in_window:
            continue
        cs = curve_stats(tl, now_ms)
        curves.append(tl)
        sa = sober_at(tl)
        current_bac += bac_at(tl, now_ms)
        if sa and sa > now_ms:
            latest_sober = max(latest_sober or 0, sa)
        if cs["peak"] > total_peak[0]:
            total_peak = (cs["peak"], cs["peak_ts"], names.get(sid, {}).get("name"))
        total_area += cs["avg"] * cs["hours_buzzed"]
        total_buzzed += cs["hours_buzzed"]
        total_over += cs["hours_over_08"]
        for d, (_, after) in zip(drinks, tl):
            idx = local_day_index(d["ts"], tz)
            row = day_map.get(idx)
            if row is not None:
                row["std"] += d["std"]
                row["count"] += 1
                row["peak"] = max(row["peak"], after)
        s = names.get(sid, {"name": "?", "start": drinks[0]["ts"]})
        session_rows.append({
            "id": sid, "name": s["name"], "start": s["start"],
            "first_ts": drinks[0]["ts"], "last_ts": drinks[-1]["ts"],
            "std": sum(d["std"] for d in drinks), "count": len(drinks),
            "peak": cs["peak"], "peak_ts": cs["peak_ts"], "avg": cs["avg"],
            "hours_buzzed": cs["hours_buzzed"], "hours_over_08": cs["hours_over_08"],
            "duration_h": (drinks[-1]["ts"] - drinks[0]["ts"]) / HOUR_MS,
            "sober_at": sa,
            "types": sorted({d["type"] for d in drinks}),
        })
    session_rows.sort(key=lambda r: r["first_ts"], reverse=True)

    # weekly bac curve, sampled
    step = 10 * 60000 if days <= 14 else 30 * 60000
    n = int((now_ms - window_start) // step) + 1
    values = []
    for i in range(n):
        t = window_start + i * step
        values.append(round(sum(bac_at(tl, t) for tl in curves), 4))

    # type + favorite breakdowns
    type_map = {}
    fav_map = {}
    hours = [0] * 24
    for d in cur_drinks:
        t = type_map.setdefault(d["type"], {"type": d["type"], "std": 0.0, "count": 0})
        t["std"] += d["std"]
        t["count"] += 1
        key = re.sub(r"\s+", " ", d["raw"].strip().lower())
        fav_map[key] = fav_map.get(key, 0) + 1
        local_h = datetime.fromtimestamp(d["ts"] / 1000, tz=timezone.utc) - timedelta(minutes=tz)
        hours[local_h.hour] += 1
    by_type = sorted(type_map.values(), key=lambda t: -t["std"])
    favorites = sorted(({"raw": k, "count": v} for k, v in fav_map.items()), key=lambda f: -f["count"])[:5]

    drinking_days = sum(1 for r in by_day if r["count"])
    total_std = sum(d["std"] for d in cur_drinks)
    calories = sum(d["oz"] * KCAL_PER_OZ.get(d["type"], KCAL_PER_OZ["drink"]) for d in cur_drinks)
    biggest = max(by_day, key=lambda r: r["std"]) if cur_drinks else None
    prev_sessions = {d["session_id"] for d in prev_drinks}

    return jsonify({
        "days": days, "window_start": window_start, "now": now_ms, "tz": tz,
        "totals": {
            "std": total_std, "count": len(cur_drinks), "sessions": len(session_rows),
            "peak_bac": total_peak[0], "peak_ts": total_peak[1], "peak_session": total_peak[2],
            "avg_bac": (total_area / total_buzzed) if total_buzzed else 0.0,
            "hours_buzzed": total_buzzed, "hours_over_08": total_over,
            "calories": calories, "drinking_days": drinking_days, "dry_days": days - drinking_days,
            "avg_per_session": (total_std / len(session_rows)) if session_rows else 0.0,
            "avg_per_drinking_day": (total_std / drinking_days) if drinking_days else 0.0,
            "biggest_day": biggest["label"] if biggest else None,
            "biggest_day_std": biggest["std"] if biggest else 0.0,
        },
        "prev": {
            "std": sum(d["std"] for d in prev_drinks), "count": len(prev_drinks),
            "sessions": len(prev_sessions),
        },
        "by_day": by_day,
        "by_type": by_type,
        "favorites": favorites,
        "hours": hours,
        "sessions": session_rows,
        "curve": {"start": window_start, "step_ms": step, "values": values},
        "current": {"bac": current_bac, "sober_at": latest_sober},
        "model": {"weight_kg": WEIGHT_KG, "r": WIDMARK_R, "metabolism": METABOLISM},
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
