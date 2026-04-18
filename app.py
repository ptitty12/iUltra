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
    (re.compile(r"\b(light\s*beer|bud\s*light|miller\s*lite|coors\s*light)\b", re.I), "light beer", 4.2, 12),
    (re.compile(r"\b(beer|lager|pilsner|heineken|corona|modelo|bud|budweiser|stella)\b", re.I), "beer", 5.0, 12),
    (re.compile(r"\b(ipa|pale\s*ale|stout|porter|ale|hazy|sour|craft)\b", re.I), "craft beer", 6.5, 12),
    (re.compile(r"\b(wine|chardonnay|cab|merlot|pinot|ros[eé]|sauvignon|riesling)\b", re.I), "wine", 13.0, 5),
    (re.compile(r"\b(shot|tequila|vodka|rum|gin|whiskey|whisky|bourbon|scotch|mezcal|brandy|cognac)\b", re.I), "spirit shot", 40.0, 1.5),
    (re.compile(r"\b(cocktail|margarita|mojito|old\s*fashion|negroni|manhattan|martini|daiquiri|sour)\b", re.I), "cocktail", 20.0, 4),
    (re.compile(r"\b(seltzer|white\s*claw|truly|hard\s*selt)\b", re.I), "hard seltzer", 5.0, 12),
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
    std_str = f"{total_std:.1f}"

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