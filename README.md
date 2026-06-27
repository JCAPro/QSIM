[README.md](https://github.com/user-attachments/files/29401948/README.md)
# QSIM — Quasar Simulation Bot v3.1

This is the polished launch version of QSIM.

It still only handles Quasar. V.E.R.A. remains untouched.

## v3.1 additions

- Short spinning reel animation before the final reveal.
- More polished V.E.R.A.-style embeds.
- Better leaderboard formatting with top-three markers.
- Tie detection for Quantum Recalibration.
- `/quasar_archive` admin command that generates a copy-ready V.E.R.A. archive summary.
- Same rules, same emojis, same 10 weekly attempts.

## Commands

- `/quasar` — Run one simulation attempt.
- `/quasar_profile` — Check your weekly record.
- `/quasar_leaderboard` — Show weekly standings.
- `/quasar_help` — Show rules.
- `/quasar_archive` — Owner/admin only. Generate a copy-ready V.E.R.A. archive update.
- `/quasar_reset` — Owner/admin only. Start a new weekly cycle.

## Render setup

Environment variables:

```env
DISCORD_TOKEN=your_new_qsim_bot_token
GUILD_ID=1433479610749812848
ADMIN_ROLE_NAME=Admin
OWNER_ID=1433465822533386250
DB_PATH=qsim_quasar.db
```

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python bot.py
```

## Official Glyph Library

- N7 Logo: `<:N7Stained:1519928704552275968>`
- N7 Helmet: `<:N7Helmet:1519921763214164010>`
- N7 Spectre: `<:N7Spectre:1519922691568828498>`
- Platinum: `<:Platinum:1519922428665397248>`
- Insanity III: `<:InsanityIIITrophy:1519921452009390110>`
- M35 Mako: `<:M35Mako:1519922319009775626>`

## Probability Index

- Quantum Convergence — Three matching Simulation Glyphs.
- Partial Synchronization — Any two matching Simulation Glyphs.
- Null Reading — No matching Simulation Glyphs.
