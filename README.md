# QSIM — Quasar Simulation Bot

QSIM is a standalone Project Infernal bot for Quasar Simulation only.

It does not touch V.E.R.A.
It does not touch dossiers.
It does not touch archives.
It does not touch Tupperbox.
It does not need Dicecord.

## What it does

QSIM runs the full Quasar Simulation directly:

- 3 random Simulation Glyphs per attempt
- the six official Project Infernal custom emojis
- 10 weekly attempts per member
- highest Probability Index is saved
- weekly leaderboard
- admin reset for the next weekly event

## Official Glyph Library

- N7 Logo: `<:N7Stained:1519928704552275968>`
- N7 Helmet: `<:N7Helmet:1519921763214164010>`
- N7 Spectre: `<:N7Spectre:1519922691568828498>`
- Platinum: `<:Platinum:1519922428665397248>`
- Insanity III: `<:InsanityIIITrophy:1519921452009390110>`
- M35 Mako: `<:M35Mako:1519922319009775626>`

## Probability Index

- **Quantum Convergence** — Three matching Simulation Glyphs.
- **Partial Synchronization** — Any two matching Simulation Glyphs.
- **Null Reading** — No matching Simulation Glyphs.

## Commands

### `/quasar`

Runs one Quasar Simulation attempt.

Each member gets 10 attempts per weekly event.

### `/quasar_profile`

Shows the member's attempts used, attempts remaining, highest archived result, and weekly counts.

### `/quasar_leaderboard`

Shows the current weekly top 10.

If two or more members share the highest Probability Index, follow your guide and run Quantum Recalibration manually.

### `/quasar_help`

Shows the rules and glyph library.

### `/quasar_reset`

Admin-only command. Starts a new weekly event and gives everyone 10 fresh attempts.

Users with Discord Administrator permission can use it. You can also set an admin role name in `.env`.

## Setup

### 1. Create a Discord application

1. Open the Discord Developer Portal.
2. Create an application named `QSIM`.
3. Add a bot.
4. Copy the bot token.

### 2. Invite the bot

Use OAuth2 URL Generator.

Scopes:
- `bot`
- `applications.commands`

Bot permissions:
- Send Messages
- Embed Links
- Use Slash Commands

### 3. Install Python packages

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment

Copy `.env.example` to `.env`.

```bash
cp .env.example .env
```

Fill in:

```env
DISCORD_TOKEN=your_token_here
GUILD_ID=your_server_id_here
ADMIN_ROLE_NAME=Admin
DB_PATH=qsim_quasar.db
```

### 5. Run QSIM

```bash
python bot.py
```

## Testing with your dummy account

1. Confirm `/quasar` appears for the dummy account.
2. Run `/quasar`.
3. Confirm exactly 3 glyphs appear.
4. Run `/quasar_profile`.
5. Confirm attempts decrease correctly.
6. Run `/quasar_leaderboard`.
7. Use your admin account to run `/quasar_reset`.
8. Confirm the dummy account has 10 attempts again.

## Notes

The bot stores data in SQLite, inside `qsim_quasar.db`.

Keep that file backed up if you want to preserve weekly records.
