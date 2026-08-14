from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import date
import sqlite3

app = Flask(__name__)
CORS(app)

DATABASE = "streak.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            total_games INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            last_played_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            puzzle_date TEXT NOT NULL,
            puzzle_id INTEGER NOT NULL,
            guess TEXT NOT NULL,
            correct INTEGER NOT NULL,
            answer TEXT NOT NULL,
            played_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, puzzle_date)
        )
    """)

    conn.commit()
    conn.close()


PUZZLES = [
    {"id": 1, "type": "logic",
     "question": "What comes next? 2 → 6 → 12 → 20 → 30 → ?",
     "answer": "42"},

    {"id": 2, "type": "logic",
     "question": "A farmer has 10 animals consisting only of chickens and cows. There are 28 legs in total. How many cows are there?",
     "answer": "4"},

    {"id": 3, "type": "logic",
     "question": "A clock shows 3:00. What is the angle between the hour and minute hands?",
     "answer": "90"},

    {"id": 4, "type": "number",
     "question": "What number is missing? 5, 10, 20, 40, ?",
     "answer": "80"},

    {"id": 5, "type": "logic",
     "question": "If 3 cats catch 3 mice in 3 minutes, how many cats are needed to catch 100 mice in 100 minutes?",
     "answer": "3"},

    {"id": 6, "type": "number",
     "question": "What comes next? 1, 4, 9, 16, 25, ?",
     "answer": "36"},

    {"id": 7, "type": "logic",
     "question": "You have 5 apples and take away 2. How many apples do you have?",
     "answer": "2"},

    {"id": 8, "type": "number",
     "question": "What comes next? 3, 6, 12, 24, ?",
     "answer": "48"},

    {"id": 9, "type": "logic",
     "question": "A dozen eggs costs ₹60. How much does one egg cost?",
     "answer": "5"},

    {"id": 10, "type": "number",
     "question": "What comes next? 100, 90, 81, 73, ?",
     "answer": "66"}
]


def puzzle_for_date(date_string):
    current_date = date.fromisoformat(date_string)
    index = current_date.toordinal() % len(PUZZLES)
    return PUZZLES[index]


def get_or_create_player(username):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM players WHERE username = ?",
        (username,)
    )
    player = cursor.fetchone()

    if player is None:
        cursor.execute("""
            INSERT INTO players
            (username, current_streak, best_streak,
             total_games, wins, losses, last_played_date)
            VALUES (?, 0, 0, 0, 0, 0, NULL)
        """, (username,))
        conn.commit()

        cursor.execute(
            "SELECT * FROM players WHERE username = ?",
            (username,)
        )
        player = cursor.fetchone()

    conn.close()
    return player


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "success",
        "message": "Streak API is running"
    })


@app.route("/api/player", methods=["POST"])
def create_player():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()

    if not username:
        return jsonify({"error": "Username is required."}), 400

    if len(username) > 50:
        return jsonify({
            "error": "Username must be 50 characters or less."
        }), 400

    player = get_or_create_player(username)
    today = date.today().isoformat()

    return jsonify({
        "id": player["id"],
        "username": player["username"],
        "current_streak": player["current_streak"],
        "best_streak": player["best_streak"],
        "played_today": player["last_played_date"] == today
    })


@app.route("/api/today")
def today():
    username = request.args.get("username", "").strip().lower()

    if not username:
        return jsonify({"error": "Username is required."}), 400

    player = get_or_create_player(username)

    today_date = date.today()
    today_string = today_date.isoformat()

    current_streak = player["current_streak"]

    if player["last_played_date"]:
        last_date = date.fromisoformat(player["last_played_date"])
        if (today_date - last_date).days > 1:
            current_streak = 0

            conn = get_db()
            conn.execute(
                "UPDATE players SET current_streak = 0 WHERE username = ?",
                (username,)
            )
            conn.commit()
            conn.close()

    puzzle = puzzle_for_date(today_string)

    conn = get_db()
    played = conn.execute("""
        SELECT id FROM game_history
        WHERE username = ? AND puzzle_date = ?
    """, (username, today_string)).fetchone()
    conn.close()

    return jsonify({
        "date": today_string,
        "played_today": played is not None,
        "current_streak": current_streak,
        "best_streak": player["best_streak"],
        "puzzle": {
            "id": puzzle["id"],
            "type": puzzle["type"],
            "question": puzzle["question"]
        }
    })


@app.route("/api/guess", methods=["POST"])
def submit_guess():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip().lower()
    guess = str(data.get("guess", "")).strip()

    if not username:
        return jsonify({"error": "Username is required."}), 400

    if not guess:
        return jsonify({"error": "Guess is required."}), 400

    today_date = date.today()
    today_string = today_date.isoformat()
    puzzle = puzzle_for_date(today_string)

    conn = get_db()
    cursor = conn.cursor()

    player = cursor.execute(
        "SELECT * FROM players WHERE username = ?",
        (username,)
    ).fetchone()

    if player is None:
        conn.close()
        return jsonify({"error": "Player not found."}), 404

    existing = cursor.execute("""
        SELECT id FROM game_history
        WHERE username = ? AND puzzle_date = ?
    """, (username, today_string)).fetchone()

    if existing is not None:
        conn.close()
        return jsonify({
            "error": "You have already played today's puzzle.",
            "played_today": True,
            "current_streak": player["current_streak"],
            "best_streak": player["best_streak"]
        }), 409

    correct = guess.casefold() == str(puzzle["answer"]).strip().casefold()

    current_streak = player["current_streak"]
    best_streak = player["best_streak"]

    previous_day_played = False

    if player["last_played_date"]:
        last_date = date.fromisoformat(player["last_played_date"])
        previous_day_played = (today_date - last_date).days == 1

    if correct:
        current_streak = current_streak + 1 if previous_day_played else 1
        best_streak = max(best_streak, current_streak)
    else:
        current_streak = 0

    total_games = player["total_games"] + 1
    wins = player["wins"] + (1 if correct else 0)
    losses = player["losses"] + (0 if correct else 1)

    cursor.execute("""
        INSERT INTO game_history
        (username, puzzle_date, puzzle_id, guess, correct, answer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        username,
        today_string,
        puzzle["id"],
        guess,
        1 if correct else 0,
        str(puzzle["answer"])
    ))

    cursor.execute("""
        UPDATE players
        SET current_streak = ?,
            best_streak = ?,
            total_games = ?,
            wins = ?,
            losses = ?,
            last_played_date = ?
        WHERE username = ?
    """, (
        current_streak,
        best_streak,
        total_games,
        wins,
        losses,
        today_string,
        username
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "correct": correct,
        "result": "win" if correct else "loss",
        "guess": guess,
        "answer": str(puzzle["answer"]),
        "current_streak": current_streak,
        "best_streak": best_streak,
        "total_games": total_games,
        "wins": wins,
        "losses": losses,
        "played_today": True,
        "message": (
            f"Correct! Your streak is now {current_streak}."
            if correct
            else "Not this time. Your streak has been reset."
        )
    })


@app.route("/api/stats")
def stats():
    username = request.args.get("username", "").strip().lower()

    if not username:
        return jsonify({"error": "Username is required."}), 400

    conn = get_db()
    player = conn.execute(
        "SELECT * FROM players WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()

    if player is None:
        return jsonify({"error": "Player not found."}), 404

    return jsonify({
        "username": player["username"],
        "current_streak": player["current_streak"],
        "best_streak": player["best_streak"],
        "total_games": player["total_games"],
        "wins": player["wins"],
        "losses": player["losses"]
    })


# ---------------------------------------------------------
# DEVELOPMENT SELF-TEST
# ---------------------------------------------------------

def run_self_test():
    print("\n" + "=" * 55)
    print("STREAK BACKEND SELF-TEST")
    print("=" * 55)

    client = app.test_client()

    response = client.get("/api/health")
    print("1. HEALTH:", response.status_code, response.get_json())

    test_user = "selftest_user"

    response = client.post(
        "/api/player",
        json={"username": test_user}
    )
    print("2. PLAYER:", response.status_code, response.get_json())

    response = client.get(
        "/api/today",
        query_string={"username": test_user}
    )
    print("3. TODAY:", response.status_code, response.get_json())

    print("=" * 55)
    print("SELF-TEST COMPLETE")
    print("=" * 55)


if __name__ == "__main__":
    init_db()

    print("=" * 55)
    print("STREAK BACKEND")
    print("=" * 55)
    print("Database: streak.db")
    print("API: http://127.0.0.1:5000")
    print("")
    print("Endpoints:")
    print("GET  /")
    print("GET  /api/health")
    print("POST /api/player")
    print("GET  /api/today")
    print("POST /api/guess")
    print("GET  /api/stats")
    print("=" * 55)

    app.run(host="0.0.0.0", port=5000, debug=False)
