from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
from datetime import datetime, date, timedelta
import os

app = Flask(__name__)
CORS(app)

DATABASE = "streak.db"


# =========================================================
# PUZZLES
# =========================================================

PUZZLES = [
    {
        "id": 1,
        "type": "number",
        "question": "What comes next in the sequence: 2, 4, 8, 16, ?",
        "answer": "32"
    },
    {
        "id": 2,
        "type": "logic",
        "question": "A farmer has 10 animals consisting only of chickens and cows. There are 28 legs in total. How many cows are there?",
        "answer": "4"
    },
    {
        "id": 3,
        "type": "math",
        "question": "What is 15 × 6?",
        "answer": "90"
    },
    {
        "id": 4,
        "type": "logic",
        "question": "A clock shows 3:00. What is the angle between the hour and minute hands?",
        "answer": "90"
    },
    {
        "id": 5,
        "type": "number",
        "question": "What comes next: 5, 10, 20, 40, ?",
        "answer": "80"
    },
    {
        "id": 6,
        "type": "math",
        "question": "What is 144 divided by 12?",
        "answer": "12"
    },
    {
        "id": 7,
        "type": "logic",
        "question": "If 3 cats catch 3 mice in 3 minutes, how many cats are needed to catch 100 mice in 100 minutes?",
        "answer": "3"
    },
    {
        "id": 8,
        "type": "number",
        "question": "What is the next number: 1, 4, 9, 16, ?",
        "answer": "25"
    },
    {
        "id": 9,
        "type": "math",
        "question": "What is 25% of 200?",
        "answer": "50"
    },
    {
        "id": 10,
        "type": "logic",
        "question": "A dozen eggs cost ₹60. How much does one egg cost?",
        "answer": "5"
    }
]


# =========================================================
# DATABASE
# =========================================================

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()
    cursor = connection.cursor()

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
            played_at TEXT NOT NULL,
            UNIQUE(username, puzzle_date)
        )
    """)

    connection.commit()
    connection.close()


# =========================================================
# DAILY PUZZLE
# =========================================================

def puzzle_for_date(date_string):
    d = datetime.strptime(date_string, "%Y-%m-%d").date()
    index = d.toordinal() % len(PUZZLES)
    return PUZZLES[index]


# =========================================================
# PLAYER HELPERS
# =========================================================

def get_player(username):
    connection = get_db()

    player = connection.execute(
        """
        SELECT *
        FROM players
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    connection.close()

    return player


def create_or_get_player(username):
    username = username.strip()

    connection = get_db()

    connection.execute(
        """
        INSERT OR IGNORE INTO players (username)
        VALUES (?)
        """,
        (username,)
    )

    connection.commit()

    player = connection.execute(
        """
        SELECT *
        FROM players
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    connection.close()

    return player


def player_response(player):
    today = date.today().isoformat()

    return {
        "id": player["id"],
        "username": player["username"],
        "current_streak": player["current_streak"],
        "best_streak": player["best_streak"],
        "played_today": player["last_played_date"] == today
    }


# =========================================================
# FRONTEND
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# HEALTH
# =========================================================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "success",
        "message": "Streak API is running"
    })


# =========================================================
# CREATE / GET PLAYER
# =========================================================

@app.route("/api/player", methods=["POST"])
def player():

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()

    if not username:
        return jsonify({
            "error": "Username is required"
        }), 400

    if len(username) > 30:
        return jsonify({
            "error": "Username must be 30 characters or less"
        }), 400

    player_data = create_or_get_player(username)

    return jsonify(player_response(player_data))


# =========================================================
# TODAY'S PUZZLE
# =========================================================

@app.route("/api/today", methods=["GET"])
def today():

    username = request.args.get("username", "").strip()

    if not username:
        return jsonify({
            "error": "Username is required"
        }), 400

    player = get_player(username)

    if not player:
        return jsonify({
            "error": "Player not found"
        }), 404

    today_string = date.today().isoformat()

    puzzle = puzzle_for_date(today_string)

    played_today = player["last_played_date"] == today_string

    return jsonify({
        "date": today_string,
        "puzzle": {
            "id": puzzle["id"],
            "type": puzzle["type"],
            "question": puzzle["question"]
        },
        "current_streak": player["current_streak"],
        "best_streak": player["best_streak"],
        "played_today": played_today
    })


# =========================================================
# SUBMIT GUESS
# =========================================================

@app.route("/api/guess", methods=["POST"])
def guess():

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    user_guess = str(data.get("guess", "")).strip()

    if not username:
        return jsonify({
            "error": "Username is required"
        }), 400

    if not user_guess:
        return jsonify({
            "error": "Guess is required"
        }), 400

    player = get_player(username)

    if not player:
        return jsonify({
            "error": "Player not found"
        }), 404

    today_string = date.today().isoformat()

    # Prevent multiple guesses on the same day
    existing_game = None

    connection = get_db()

    existing_game = connection.execute(
        """
        SELECT *
        FROM game_history
        WHERE username = ?
        AND puzzle_date = ?
        """,
        (username, today_string)
    ).fetchone()

    connection.close()

    if existing_game:
        return jsonify({
            "error": "You have already played today's puzzle.",
            "played_today": True,
            "current_streak": player["current_streak"],
            "best_streak": player["best_streak"]
        }), 409

    puzzle = puzzle_for_date(today_string)

    correct_answer = str(puzzle["answer"]).strip()

    is_correct = user_guess.lower() == correct_answer.lower()

    current_streak = player["current_streak"]

    # -----------------------------------------------------
    # Check missed day
    # -----------------------------------------------------

    last_played = player["last_played_date"]

    if last_played:

        try:
            last_date = datetime.strptime(
                last_played,
                "%Y-%m-%d"
            ).date()

            yesterday = date.today() - timedelta(days=1)

            if last_date != yesterday:
                current_streak = 0

        except ValueError:
            current_streak = 0

    # -----------------------------------------------------
    # Update streak
    # -----------------------------------------------------

    if is_correct:
        current_streak += 1
    else:
        current_streak = 0

    best_streak = max(
        player["best_streak"],
        current_streak
    )

    total_games = player["total_games"] + 1

    wins = player["wins"] + (1 if is_correct else 0)

    losses = player["losses"] + (0 if is_correct else 1)

    # -----------------------------------------------------
    # Save everything
    # -----------------------------------------------------

    connection = get_db()

    connection.execute(
        """
        UPDATE players
        SET
            current_streak = ?,
            best_streak = ?,
            total_games = ?,
            wins = ?,
            losses = ?,
            last_played_date = ?
        WHERE username = ?
        """,
        (
            current_streak,
            best_streak,
            total_games,
            wins,
            losses,
            today_string,
            username
        )
    )

    connection.execute(
        """
        INSERT INTO game_history (
            username,
            puzzle_date,
            puzzle_id,
            guess,
            correct,
            answer,
            played_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            today_string,
            puzzle["id"],
            user_guess,
            int(is_correct),
            correct_answer,
            datetime.now().isoformat()
        )
    )

    connection.commit()
    connection.close()

    return jsonify({
        "result": "win" if is_correct else "loss",
        "correct": is_correct,
        "guess": user_guess,
        "answer": correct_answer,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "total_games": total_games,
        "wins": wins,
        "losses": losses,
        "played_today": True,
        "message": (
            f"Correct! Your streak is now {current_streak}."
            if is_correct
            else "Wrong answer. Your streak has been reset."
        )
    })


# =========================================================
# PLAYER STATISTICS
# =========================================================

@app.route("/api/stats", methods=["GET"])
def stats():

    username = request.args.get("username", "").strip()

    if not username:
        return jsonify({
            "error": "Username is required"
        }), 400

    player = get_player(username)

    if not player:
        return jsonify({
            "error": "Player not found"
        }), 404

    return jsonify({
        "username": player["username"],
        "current_streak": player["current_streak"],
        "best_streak": player["best_streak"],
        "total_games": player["total_games"],
        "wins": player["wins"],
        "losses": player["losses"]
    })


# =========================================================
# INITIALIZE DATABASE
# IMPORTANT FOR GUNICORN / RENDER
# =========================================================

init_db()


# =========================================================
# RUN LOCALLY
# =========================================================

if __name__ == "__main__":

    print("=" * 55)
    print("STREAK BACKEND")
    print("=" * 55)
    print("Database:", DATABASE)
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

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
