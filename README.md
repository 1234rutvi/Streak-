# 🔥 Streak

### One puzzle. One guess. Every day.

Streak is a tiny daily guessing game built around one simple idea:

> **You get one chance every day. Protect your streak.**

Each day, every player receives the same daily puzzle. The player gets exactly one guess. A correct answer increases the streak, while a wrong answer resets it to zero.

The game keeps track of the player's progress even after they close the browser and come back later.

---

## 🎮 How It Works

```text
                    ┌─────────────────┐
                    │   Open Streak   │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Enter Username  │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Today's Puzzle  │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │   One Guess     │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Server Checks   │
                    │     Answer      │
                    └────────┬────────┘
                       ┌─────┴─────┐
                       ↓           ↓
                    CORRECT      WRONG
                       ↓           ↓
                   Streak +1    Streak = 0
                       └─────┬─────┘
                             ↓
                    ┌─────────────────┐
                    │  Result Screen  │
                    └─────────────────┘
---

## ✨ Features

- 🧩 One puzzle every day
- 🎯 One guess per player per day
- 🔥 Current streak tracking
- 🏆 Best streak tracking
- 📊 Total games, wins and losses
- 👤 Simple username-based player identification
- 💾 Persistent game data using SQLite
- 🔒 Server-side answer validation
- 🚫 Duplicate guesses are prevented
- 📅 Date-based daily puzzle selection
- 🎉 Dedicated result screen after submitting a guess
- 💗 Responsive light-pink user interface
- ⌨️ Enter key support for submitting answers

---

## 🧠 The Game Rules

Streak intentionally follows a very small set of rules.

### ✅ Correct Guess

If the player answers correctly:

```text
Correct Answer
      ↓
Streak increases by 1
      ↓
Best streak updated if necessary
👩‍💻 Author

Rutvi Rathod

Data Science | Analytics | Python
