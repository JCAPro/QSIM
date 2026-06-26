import os
import random
import sqlite3
from datetime import datetime, timezone
from typing import Final

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN: Final[str | None] = os.getenv("DISCORD_TOKEN")
GUILD_ID_RAW: Final[str | None] = os.getenv("GUILD_ID")
DB_PATH: Final[str] = os.getenv("DB_PATH", "qsim_quasar.db")
ADMIN_ROLE_NAME: Final[str] = os.getenv("ADMIN_ROLE_NAME", "Admin")

MAX_WEEKLY_ATTEMPTS: Final[int] = 10

GLYPHS: Final[list[tuple[str, str]]] = [
    ("N7 Logo", "<:N7Stained:1519928704552275968>"),
    ("N7 Helmet", "<:N7Helmet:1519921763214164010>"),
    ("N7 Spectre", "<:N7Spectre:1519922691568828498>"),
    ("Platinum", "<:Platinum:1519922428665397248>"),
    ("Insanity III", "<:InsanityIIITrophy:1519921452009390110>"),
    ("M35 Mako", "<:M35Mako:1519922319009775626>"),
]

RESULTS: Final[dict[int, tuple[str, str]]] = {
    3: ("Quantum Convergence", "Three matching Simulation Glyphs."),
    2: ("Partial Synchronization", "Any two matching Simulation Glyphs."),
    1: ("Null Reading", "No matching Simulation Glyphs."),
}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS weekly_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                week_number INTEGER NOT NULL,
                started_at TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS player_weekly (
                week_number INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                attempts_used INTEGER NOT NULL DEFAULT 0,
                best_index INTEGER NOT NULL DEFAULT 0,
                best_result TEXT,
                best_glyphs TEXT,
                quantum_convergences INTEGER NOT NULL DEFAULT 0,
                partial_synchronizations INTEGER NOT NULL DEFAULT 0,
                null_readings INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (week_number, guild_id, user_id)
            )
        """)
        row = con.execute("SELECT * FROM weekly_state WHERE id = 1").fetchone()
        if not row:
            con.execute(
                "INSERT INTO weekly_state (id, week_number, started_at) VALUES (1, 1, ?)",
                (datetime.now(timezone.utc).isoformat(),)
            )


def current_week() -> int:
    with db() as con:
        row = con.execute("SELECT week_number FROM weekly_state WHERE id = 1").fetchone()
        return int(row["week_number"])


def next_week() -> int:
    with db() as con:
        row = con.execute("SELECT week_number FROM weekly_state WHERE id = 1").fetchone()
        week = int(row["week_number"]) + 1
        con.execute(
            "UPDATE weekly_state SET week_number = ?, started_at = ? WHERE id = 1",
            (week, datetime.now(timezone.utc).isoformat())
        )
        return week


def index_from_roll(glyph_names: list[str]) -> int:
    unique_count = len(set(glyph_names))
    if unique_count == 1:
        return 3
    if unique_count == 2:
        return 2
    return 1


def roll_glyphs() -> list[tuple[str, str]]:
    return [random.choice(GLYPHS) for _ in range(3)]


def ensure_player(guild_id: int, user_id: int, display_name: str) -> sqlite3.Row:
    week = current_week()
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        con.execute("""
            INSERT OR IGNORE INTO player_weekly
            (week_number, guild_id, user_id, display_name, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (week, guild_id, user_id, display_name, now))
        con.execute("""
            UPDATE player_weekly
            SET display_name = ?, updated_at = ?
            WHERE week_number = ? AND guild_id = ? AND user_id = ?
        """, (display_name, now, week, guild_id, user_id))
        return con.execute("""
            SELECT * FROM player_weekly
            WHERE week_number = ? AND guild_id = ? AND user_id = ?
        """, (week, guild_id, user_id)).fetchone()


def save_roll(guild_id: int, user_id: int, display_name: str, glyphs: list[tuple[str, str]], result_index: int) -> sqlite3.Row:
    week = current_week()
    now = datetime.now(timezone.utc).isoformat()
    glyph_text = " ".join(emoji for _, emoji in glyphs)
    result_name = RESULTS[result_index][0]

    row = ensure_player(guild_id, user_id, display_name)
    if int(row["attempts_used"]) >= MAX_WEEKLY_ATTEMPTS:
        return row

    new_attempts = int(row["attempts_used"]) + 1
    best_index = int(row["best_index"])
    best_result = row["best_result"]
    best_glyphs = row["best_glyphs"]

    if result_index > best_index:
        best_index = result_index
        best_result = result_name
        best_glyphs = glyph_text

    qc = int(row["quantum_convergences"]) + (1 if result_index == 3 else 0)
    ps = int(row["partial_synchronizations"]) + (1 if result_index == 2 else 0)
    nr = int(row["null_readings"]) + (1 if result_index == 1 else 0)

    with db() as con:
        con.execute("""
            UPDATE player_weekly
            SET display_name = ?,
                attempts_used = ?,
                best_index = ?,
                best_result = ?,
                best_glyphs = ?,
                quantum_convergences = ?,
                partial_synchronizations = ?,
                null_readings = ?,
                updated_at = ?
            WHERE week_number = ? AND guild_id = ? AND user_id = ?
        """, (
            display_name, new_attempts, best_index, best_result, best_glyphs,
            qc, ps, nr, now, week, guild_id, user_id
        ))
        return con.execute("""
            SELECT * FROM player_weekly
            WHERE week_number = ? AND guild_id = ? AND user_id = ?
        """, (week, guild_id, user_id)).fetchone()


def build_quasar_embed(
    member: discord.Member | discord.User,
    glyphs: list[tuple[str, str]],
    result_index: int,
    player_row: sqlite3.Row,
) -> discord.Embed:
    result_name, result_desc = RESULTS[result_index]
    attempts_used = int(player_row["attempts_used"])
    remaining = MAX_WEEKLY_ATTEMPTS - attempts_used
    glyph_display = "   ".join(emoji for _, emoji in glyphs)

    if result_index == 3:
        color = 0xF2C94C
    elif result_index == 2:
        color = 0x56CCF2
    else:
        color = 0x2F80ED

    embed = discord.Embed(
        title="QUASAR SIMULATION",
        description=(
            "**V.E.R.A. Quantum Probability Simulator**\n"
            '"Probability cannot be predicted. Only observed."\n\n'
            f"## {glyph_display}\n"
            f"**Probability Index:** {result_name}\n"
            f"{result_desc}"
        ),
        color=color
    )
    embed.add_field(
        name="Simulation Attempts",
        value=f"{attempts_used} / {MAX_WEEKLY_ATTEMPTS} used\n{remaining} remaining",
        inline=True
    )
    embed.add_field(
        name="Highest Archived Index",
        value=f"{player_row['best_result'] or 'No archived result yet'}\n{player_row['best_glyphs'] or ''}",
        inline=True
    )
    embed.set_footer(text="Simulation complete. Results archived. — V.E.R.A.")
    return embed


def member_is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(role.name == ADMIN_ROLE_NAME for role in member.roles)


@bot.event
async def on_ready() -> None:
    init_db()
    if GUILD_ID_RAW:
        guild = discord.Object(id=int(GUILD_ID_RAW))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"QSIM synced commands to guild {GUILD_ID_RAW}.")
    else:
        await bot.tree.sync()
        print("QSIM synced global commands.")
    print(f"QSIM online as {bot.user}.")


@bot.tree.command(name="quasar", description="Run one Quasar Simulation attempt.")
async def quasar(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("QSIM can only be used inside the server.", ephemeral=True)
        return

    member = interaction.user
    row = ensure_player(interaction.guild.id, member.id, member.display_name)

    if int(row["attempts_used"]) >= MAX_WEEKLY_ATTEMPTS:
        await interaction.response.send_message(
            "━━━━━━━━━━━━━━━━━━\n"
            "**QUASAR SIMULATION LOCKED**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "You have used all **10** Simulation Attempts for this weekly event.\n"
            f"Highest archived Probability Index: **{row['best_result'] or 'None'}**\n\n"
            "The Galatana Memory Core will preserve your highest result.\n"
            "— V.E.R.A.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=False, thinking=True)

    glyphs = roll_glyphs()
    glyph_names = [name for name, _ in glyphs]
    result_index = index_from_roll(glyph_names)
    updated = save_roll(interaction.guild.id, member.id, member.display_name, glyphs, result_index)
    embed = build_quasar_embed(member, glyphs, result_index, updated)

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="quasar_profile", description="Check your current weekly Quasar Simulation record.")
async def quasar_profile(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("QSIM can only be used inside the server.", ephemeral=True)
        return

    row = ensure_player(interaction.guild.id, interaction.user.id, interaction.user.display_name)
    attempts_used = int(row["attempts_used"])
    remaining = MAX_WEEKLY_ATTEMPTS - attempts_used

    embed = discord.Embed(
        title="QUASAR PROFILE",
        description=(
            f"**Crew Member:** {interaction.user.mention}\n"
            f"**Attempts Used:** {attempts_used} / {MAX_WEEKLY_ATTEMPTS}\n"
            f"**Attempts Remaining:** {remaining}\n\n"
            f"**Highest Probability Index:** {row['best_result'] or 'No archived result yet'}\n"
            f"{row['best_glyphs'] or ''}"
        ),
        color=0x2F80ED
    )
    embed.add_field(name="Quantum Convergence", value=str(row["quantum_convergences"]), inline=True)
    embed.add_field(name="Partial Synchronization", value=str(row["partial_synchronizations"]), inline=True)
    embed.add_field(name="Null Reading", value=str(row["null_readings"]), inline=True)
    embed.set_footer(text="Only your highest Probability Index counts for the weekly event. — V.E.R.A.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="quasar_leaderboard", description="View this week's Quasar Simulation standings.")
async def quasar_leaderboard(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("QSIM can only be used inside the server.", ephemeral=True)
        return

    week = current_week()
    with db() as con:
        rows = con.execute("""
            SELECT *
            FROM player_weekly
            WHERE week_number = ? AND guild_id = ? AND attempts_used > 0
            ORDER BY best_index DESC, quantum_convergences DESC, partial_synchronizations DESC, attempts_used ASC, updated_at ASC
            LIMIT 10
        """, (week, interaction.guild.id)).fetchall()

    if not rows:
        await interaction.response.send_message("No Quasar Simulation records have been archived this week.", ephemeral=True)
        return

    lines = []
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"**{idx}. {row['display_name']}** — {row['best_result']} "
            f"({row['attempts_used']}/{MAX_WEEKLY_ATTEMPTS} attempts)\n"
            f"{row['best_glyphs'] or ''}"
        )

    embed = discord.Embed(
        title="QUASAR WEEKLY STANDINGS",
        description="\n\n".join(lines),
        color=0x56CCF2
    )
    embed.set_footer(text="If two or more crew members share the highest Probability Index, V.E.R.A. initiates Quantum Recalibration.")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="quasar_help", description="Show Quasar Simulation rules.")
async def quasar_help(interaction: discord.Interaction) -> None:
    glyph_library = "\n".join(f"• {emoji} **{name}**" for name, emoji in GLYPHS)

    embed = discord.Embed(
        title="QUASAR SIMULATION RULES",
        description=(
            "**V.E.R.A. Quantum Probability Simulator**\n"
            '"Probability cannot be predicted. Only observed."\n\n'
            "**Simulation Rules**\n"
            "• Each crew member receives **10 Simulation Attempts** during the weekly event.\n"
            "• Every simulation generates **3 Simulation Glyphs**.\n"
            "• Only your highest Probability Index achieved during the event counts.\n"
            "• The highest Probability Index at the conclusion of the event becomes the Weekly Quasar Simulation Champion.\n\n"
            "**Simulation Glyph Library**\n"
            f"{glyph_library}\n\n"
            "**Probability Index**\n"
            "• **Quantum Convergence** — Three matching Simulation Glyphs.\n"
            "• **Partial Synchronization** — Any two matching Simulation Glyphs.\n"
            "• **Null Reading** — No matching Simulation Glyphs.\n\n"
            "**Quantum Recalibration**\n"
            "If two or more crew members achieve the same highest Probability Index, tied participants advance to a Simulation Finalist Round."
        ),
        color=0x2F80ED
    )
    embed.set_footer(text="Simulation complete. Results archived. — V.E.R.A.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="quasar_reset", description="Admin only: reset Quasar for a new weekly event.")
async def quasar_reset(interaction: discord.Interaction) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("QSIM can only be reset inside the server.", ephemeral=True)
        return

    if not member_is_admin(interaction.user):
        await interaction.response.send_message("Access denied. Admin authorization required.", ephemeral=True)
        return

    new_week = next_week()
    await interaction.response.send_message(
        "━━━━━━━━━━━━━━━━━━\n"
        "**QUASAR WEEKLY RESET COMPLETE**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"New archive cycle initialized: **Week {new_week}**\n"
        "All crew members now have **10 Simulation Attempts** available.\n\n"
        "— V.E.R.A.",
        ephemeral=True
    )


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Add it to your .env file.")

bot.run(TOKEN)
