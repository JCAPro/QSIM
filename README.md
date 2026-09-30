# 🎰 The Brass Bandit

**The Brass Bandit** is a custom steampunk slot-machine game built for the **World of Hiveren** Discord community.

Originally developed from the QSIM Quasar game, The Brass Bandit has been rebuilt around **The Legend of Hiveren** while preserving the animated reel system, 10-pull weekly competition, and simple gameplay that made the original game popular.

## 🎰 How It Works

Use `/bandit` to pull the lever.

The Brass Bandit spins **three animated reels** using eight symbols based on the Seven Champions of Hiveren.

Each player receives **10 pulls per weekly cycle**.

The bot records the player's strongest result during the week, allowing everyone to compete for the best pull.

The reel animation updates the existing game message as the reels spin and stop, keeping the channel cleaner while preserving the animated slot-machine effect.

## 🎭 Official Reel Symbols

The Brass Bandit uses eight Hiveren reel symbols:

- Rooney — `<:Rooney:1554662855486480414>`
- Nixxon — `<:Nixxon:1554662953318481920>`
- Mixxie — `<:Mixxie:1554663016799404032>`
- Minerva — `<:Minerva:1554663081991209021>`
- Lance — `<:Lance:1554663140308951120>`
- Elias — `<:Elias:1554663194117800007>`
- Celmore — `<:Celmore:1554663244252319774>`
- **THE SEVEN CHAMPIONS** — `<:THE_SEVEN_CHAMPIONS:1554811042284970025>`

**THE SEVEN CHAMPIONS** is the special jackpot symbol.

## 🎟️ Weekly Pulls

Every player receives:

**10 pulls per weekly cycle**

The game keeps track of:

- Pulls used
- Pulls remaining
- Current result
- Best pull
- Weekly standings

A weaker pull will not replace a stronger result already recorded for that player.

## 🏆 Results

Each pull is evaluated according to the combination of symbols appearing on the three reels.

Matching symbols produce stronger results, while special combinations involving **THE SEVEN CHAMPIONS** can produce some of the game's highest outcomes.

The player's strongest pull is preserved as their **Best Pull** for the current weekly cycle.

## 👑 Legendary Jackpot

Landing:

**THE SEVEN CHAMPIONS • THE SEVEN CHAMPIONS • THE SEVEN CHAMPIONS**

produces the ultimate Brass Bandit jackpot.

All seven Champions. All three reels.

**The machine has spoken.**

## 🏆 Weekly Competition

Players compete throughout the weekly cycle to achieve the strongest recorded pull.

The leaderboard tracks the best performances and identifies ties when multiple players finish with equivalent top results.

At the beginning of a new cycle, an administrator can reset the weekly competition and restore everyone's 10 available pulls.

## ⚙️ Commands

- `/bandit` — Pull the lever and play The Brass Bandit.
- `/bandit_profile` — Check your weekly record and remaining pulls.
- `/bandit_leaderboard` — View the current weekly standings.
- `/bandit_help` — View the rules and reel symbols.
- `/bandit_archive` — Owner/admin only. Generate a weekly archive summary.
- `/bandit_reset` — Owner/admin only. Begin a new weekly cycle.

## 🎞️ Animated Reels

The animated reels are a core feature of The Brass Bandit.

When a player uses `/bandit`, the machine cycles through Hiveren symbols before each reel gradually stops and the final combination is revealed.

The animation and final result are handled through the same game message whenever possible rather than generating a separate message for every stage of the spin.

This preserves the slot-machine presentation while reducing channel clutter during active Brass Bandit weeks.

## 🌎 World of Hiveren

The Brass Bandit is designed specifically for the **World of Hiveren** Discord community and features characters from **The Legend of Hiveren**.

### The Seven Champions

**Lance • Minerva • Elias • Celmore • Nixxon • Rooney • Mixxie**

## 🛠️ Render Setup

### Environment Variables

```env
DISCORD_TOKEN=your_brass_bandit_bot_token
GUILD_ID=1433479610749812848
ADMIN_ROLE_NAME=Admin
OWNER_ID=1433465822533386250
DB_PATH=qsim_quasar.db
```

The existing `qsim_quasar.db` path is intentionally retained to preserve compatibility with the current deployed database.

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
python bot.py
```

## 📦 Requirements

```txt
discord.py>=2.4.0
python-dotenv>=1.0.1
```

Install dependencies with:

```bash
pip install
