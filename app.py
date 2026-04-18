from flask import Flask, request, jsonify, send_from_directory
import sqlite3, os, re, random
from datetime import datetime

app = Flask(__name__, static_folder='static')

DB_PATH = os.environ.get("DB_PATH", "/data/drinks.db")

# --- body params (widmark formula inputs) ---
WEIGHT_KG = 86.0
WIDMARK_R = 0.68
METABOLISM = 0.015  # %/hr

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

def std_drinks(oz, abv):
    return (oz * 29.5735 * (abv / 100) * 0.789) / 14

def calc_bac(drinks, now_ms=None):
    """widmark bac at now_ms given list of {ts, oz, abv}"""
    if now_ms is None:
        now_ms = int(datetime.now().timestamp() * 1000)
    bac = 0.0
    for d in drinks:
        h = (now_ms - d["ts"]) / 3600000
        grams = (d["oz"] * 29.5735) * (d["abv"] / 100) * 0.789
        peak = (grams / (WEIGHT_KG * 1000 * WIDMARK_R)) * 100
        bac += max(0, peak - METABOLISM * h)
    return max(0, bac)

# --- reply phrases ---
OPENERS = ["yeah we're on our way","just leaving now","omw, maybe 10 min","sounds good to me","lol yeah for sure","haha yeah that was wild","on my way now","just got here actually","yeah totally agree","that's so funny you say that","just parked","yeah pulling up now","dude same honestly","no yeah that makes sense","lmao right","yeah I saw that too"]
CLOSERS = ["how are you doing?","what are you up to later?","you coming out tonight?","miss you btw","let me know when you're free","we should catch up soon","how was your day?","you eat yet?","you good?","what's the plan?","you still down for later?","call me when you can","hope you're having a good one","let me know!","you around this weekend?","hbu?"]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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
    conn.commit()
    conn.close()

init_db()

# --- routes ---

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    conn = get_db()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY start DESC").fetchall()
    now_ms = int(datetime.now().timestamp() * 1000)
    result = []
    for s in sessions:
        drinks = conn.execute(
            "SELECT * FROM drinks WHERE session_id = ? ORDER BY ts ASC", (s["id"],)
        ).fetchall()
        drink_dicts = [dict(d) for d in drinks]
        bac = calc_bac(drink_dicts, now_ms)
        total_std = sum(std_drinks(d["oz"], d["abv"]) for d in drink_dicts)
        result.append({
            "id": s["id"],
            "name": s["name"],
            "start": s["start"],
            "drinks": drink_dicts,
            "bac": bac,
            "total_std": total_std,
        })
    conn.close()
    return jsonify(result)

@app.route("/api/sessions", methods=["POST"])
def create_session():
    body = request.get_json()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO sessions (name, start, created_at) VALUES (?, ?, ?)",
        (body["name"], body["start"], int(datetime.now().timestamp() * 1000))
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return jsonify({"id": sid, "name": body["name"], "start": body["start"], "drinks": []})

@app.route("/api/sessions/<int:session_id>", methods=["PATCH"])
def rename_session(session_id):
    body = request.get_json()
    conn = get_db()
    conn.execute("UPDATE sessions SET name = ? WHERE id = ?", (body["name"], session_id))
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
    body = request.get_json()
    raw = body["raw"]
    ts = body["ts"]

    conn = get_db()
    s = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not s:
        conn.close()
        return jsonify({"error": "session not found"}), 404

    dtype, abv, oz = parse_drink(raw)

    # fetch existing drinks to compute bac/total with new one added
    existing = conn.execute(
        "SELECT ts, oz, abv FROM drinks WHERE session_id = ? ORDER BY ts ASC", (session_id,)
    ).fetchall()
    all_drinks = [dict(d) for d in existing] + [{"ts": ts, "oz": oz, "abv": abv}]
    bac = calc_bac(all_drinks, ts)
    total_std = sum(std_drinks(d["oz"], d["abv"]) for d in all_drinks)

    opener = random.choice(OPENERS)
    closer = random.choice(CLOSERS)
    bac_str = f"{bac:.3f}"
    std_str = f"{round(total_std)}"

    cur = conn.execute(
        """INSERT INTO drinks
           (session_id, raw, ts, type, abv, oz, bac, std_total,
            reply_opener, reply_bac_str, reply_std, reply_closer)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (session_id, raw, ts, dtype, abv, oz,
         bac, total_std, opener, bac_str, std_str, closer)
    )
    conn.commit()
    drink_id = cur.lastrowid
    conn.close()
    return jsonify({
        "id": drink_id, "raw": raw, "ts": ts, "type": dtype, "abv": abv, "oz": oz,
        "bac": bac, "std_total": total_std,
        "reply_opener": opener, "reply_bac_str": bac_str,
        "reply_std": std_str, "reply_closer": closer,
    })

@app.route("/api/drinks/<int:drink_id>", methods=["DELETE"])
def delete_drink(drink_id):
    conn = get_db()
    conn.execute("DELETE FROM drinks WHERE id = ?", (drink_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)