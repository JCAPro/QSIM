import asyncio
import os
import random
import sqlite3
from datetime import datetime, timezone
from typing import Final, Literal

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN: Final[str | None] = os.getenv("DISCORD_TOKEN")
GUILD_ID_RAW: Final[str | None] = os.getenv("GUILD_ID")
DB_PATH: Final[str] = os.getenv("DB_PATH", "brass_bandit.db")
ADMIN_ROLE_NAME: Final[str] = os.getenv("ADMIN_ROLE_NAME", "Admin")
OWNER_ID_RAW: Final[str | None] = os.getenv("OWNER_ID", "1433465822533386250")

MAX_WEEKLY_PULLS: Final[int] = 10

# Exact World of Hiveren server emoji names/IDs supplied by the server owner.
SYMBOLS: Final[list[tuple[str, str]]] = [
    ("Rooney", "<:Rooney:1554662855486480414>"),
    ("Nixxon", "<:Nixxon:1554662953318481920>"),
    ("Mixxie", "<:Mixxie:1554663016799404032>"),
    ("Minerva", "<:Minerva:1554663081991209021>"),
    ("Lance", "<:Lance:1554663140308951120>"),
    ("Elias", "<:Elias:1554663194117800007>"),
    ("Celmore", "<:Celmore:1554663244252319774>"),
    ("THE SEVEN CHAMPIONS", "<:THESEVENChampions:1555038250484105267>"),
]
LEGENDARY_SYMBOL_NAME: Final[str] = "THE SEVEN CHAMPIONS"

# Ranking values are deliberately simple so the old highest-result system remains intact.
RESULTS: Final[dict[int, tuple[str, str, str]]] = {
    4: ("Legendary Jackpot", "THE SEVEN CHAMPIONS aligned across all three reels.", "The machine has witnessed a legend."),
    3: ("Jackpot", "Three matching symbols.", "Three of a kind. The Bandit pays attention."),
    2: ("Double", "Any two matching symbols.", "Two reels agree. Not bad at all."),
    1: ("No Match", "No matching symbols.", "The gears turn. Fortune keeps moving."),
}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def column_names(con: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}


def add_column_if_missing(con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column not in column_names(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    """Create the Brass Bandit schema and safely migrate an existing Quasar database."""
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS weekly_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                week_number INTEGER NOT NULL,
                started_at TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS bandit_settings (
                guild_id INTEGER PRIMARY KEY,
                event_tracking INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS player_weekly (
                week_number INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                event_eligible INTEGER NOT NULL DEFAULT 1,
                attempts_used INTEGER NOT NULL DEFAULT 0,
                best_index INTEGER NOT NULL DEFAULT 0,
                best_result TEXT,
                best_glyphs TEXT,
                quantum_convergences INTEGER NOT NULL DEFAULT 0,
                partial_synchronizations INTEGER NOT NULL DEFAULT 0,
                null_readings INTEGER NOT NULL DEFAULT 0,
                legendary_jackpots INTEGER NOT NULL DEFAULT 0,
                jackpots INTEGER NOT NULL DEFAULT 0,
                doubles INTEGER NOT NULL DEFAULT 0,
                misses INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (week_number, guild_id, user_id)
            )
        """)

        # Existing Quasar installs already have player_weekly. These additions are non-destructive.
        add_column_if_missing(con, "player_weekly", "event_eligible", "INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(con, "player_weekly", "legendary_jackpots", "INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(con, "player_weekly", "jackpots", "INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(con, "player_weekly", "doubles", "INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(con, "player_weekly", "misses", "INTEGER NOT NULL DEFAULT 0")

        row = con.execute("SELECT * FROM weekly_state WHERE id = 1").fetchone()
        if not row:
            con.execute(
                "INSERT INTO weekly_state (id, week_number, started_at) VALUES (1, 1, ?)",
                (datetime.now(timezone.utc).isoformat(),),
            )


def tracking_enabled(guild_id: int) -> bool:
    with db() as con:
        row = con.execute("SELECT event_tracking FROM bandit_settings WHERE guild_id = ?", (guild_id,)).fetchone()
        return True if row is None else bool(row["event_tracking"])


def set_tracking(guild_id: int, enabled: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        con.execute(
            "INSERT INTO bandit_settings (guild_id, event_tracking, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET event_tracking = excluded.event_tracking, updated_at = excluded.updated_at",
            (guild_id, 1 if enabled else 0, now),
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
            (week, datetime.now(timezone.utc).isoformat()),
        )
        return week


def result_from_roll(symbol_names: list[str]) -> int:
    if all(name == LEGENDARY_SYMBOL_NAME for name in symbol_names):
        return 4
    unique_count = len(set(symbol_names))
    if unique_count == 1:
        return 3
    if unique_count == 2:
        return 2
    return 1


def roll_symbols() -> list[tuple[str, str]]:
    return [random.choice(SYMBOLS) for _ in range(3)]


def spinning_line() -> str:
    return "   ".join(random.choice(SYMBOLS)[1] for _ in range(3))


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


def save_roll(
    guild_id: int,
    user_id: int,
    display_name: str,
    symbols: list[tuple[str, str]],
    result_index: int,
) -> sqlite3.Row:
    week = current_week()
    now = datetime.now(timezone.utc).isoformat()
    symbol_text = " ".join(emoji for _, emoji in symbols)
    result_name = RESULTS[result_index][0]

    row = ensure_player(guild_id, user_id, display_name)
    if int(row["attempts_used"]) >= MAX_WEEKLY_PULLS:
        return row

    new_attempts = int(row["attempts_used"]) + 1
    eligible = 1 if tracking_enabled(guild_id) else 0
    best_index = int(row["best_index"])
    best_result = row["best_result"]
    best_glyphs = row["best_glyphs"]

    if result_index > best_index:
        best_index = result_index
        best_result = result_name
        best_glyphs = symbol_text

    legendary = int(row["legendary_jackpots"]) + (1 if result_index == 4 else 0)
    jackpots = int(row["jackpots"]) + (1 if result_index == 3 else 0)
    doubles = int(row["doubles"]) + (1 if result_index == 2 else 0)
    misses = int(row["misses"]) + (1 if result_index == 1 else 0)

    with db() as con:
        con.execute("""
            UPDATE player_weekly
            SET display_name = ?, event_eligible = ?, attempts_used = ?, best_index = ?, best_result = ?, best_glyphs = ?,
                legendary_jackpots = ?, jackpots = ?, doubles = ?, misses = ?, updated_at = ?
            WHERE week_number = ? AND guild_id = ? AND user_id = ?
        """, (
            display_name, eligible, new_attempts, best_index, best_result, best_glyphs,
            legendary, jackpots, doubles, misses, now, week, guild_id, user_id,
        ))
        return con.execute("""
            SELECT * FROM player_weekly
            WHERE week_number = ? AND guild_id = ? AND user_id = ?
        """, (week, guild_id, user_id)).fetchone()


def machine_embed(member: discord.Member | discord.User, stage: str, line: str, progress: str) -> discord.Embed:
    embed = discord.Embed(
        title="🎰 THE BRASS BANDIT",
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "**Gilded Gear Fortune Machine**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"**Player:** {member.mention}\n"
            f"**Machine:** {stage}\n\n"
            f"## {line}\n\n"
            f"`{progress}`"
        ),
        color=0xB87333,
    )
    embed.set_footer(text="Gears turning... fortune pending...")
    return embed


def result_embed(
    member: discord.Member | discord.User,
    symbols: list[tuple[str, str]],
    result_index: int,
    player_row: sqlite3.Row,
) -> discord.Embed:
    result_name, result_desc, flavor = RESULTS[result_index]
    pulls_used = int(player_row["attempts_used"])
    remaining = MAX_WEEKLY_PULLS - pulls_used
    symbol_display = "   ".join(emoji for _, emoji in symbols)

    colors = {4: 0xFFD700, 3: 0xD4AF37, 2: 0xCD7F32, 1: 0x7A5C43}
    title = "👑 LEGENDARY JACKPOT 👑" if result_index == 4 else "🎰 THE BRASS BANDIT"

    embed = discord.Embed(
        title=title,
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "**THE REELS HAVE STOPPED**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"**Player:** {member.mention}\n"
            f"**Event Tracking:** {'WEEKLY EVENT' if tracking_enabled(int(player_row['guild_id'])) else 'NONE'}\n\n"
            f"## {symbol_display}\n\n"
            f"**Result: {result_name}**\n"
            f"{result_desc}\n\n"
            f"*{flavor}*"
        ),
        color=colors[result_index],
    )
    embed.add_field(
        name="Weekly Pulls",
        value=f"**{pulls_used} / {MAX_WEEKLY_PULLS}** used\n**{remaining}** remaining",
        inline=True,
    )
    embed.add_field(
        name="Best Pull",
        value=f"**{player_row['best_result'] or 'None yet'}**\n{player_row['best_glyphs'] or ''}",
        inline=True,
    )
    if result_index == 4:
        embed.add_field(
            name="👑 The Seven Have Aligned",
            value="A **Legendary Jackpot** has been recorded. This pull outranks every standard jackpot.",
            inline=False,
        )
    elif result_index == 3:
        embed.add_field(
            name="🏆 Jackpot",
            value="Three matching champions landed on the reels.",
            inline=False,
        )

    if remaining == 0:
        embed.add_field(
            name="Session Complete",
            value=(
                f"👑 Legendary Jackpots: **{player_row['legendary_jackpots']}**\n"
                f"🏆 Jackpots: **{player_row['jackpots']}**\n"
                f"✨ Doubles: **{player_row['doubles']}**\n"
                f"🎲 No Matches: **{player_row['misses']}**"
            ),
            inline=False,
        )
        embed.set_footer(text="All 10 weekly pulls used. The Brass Bandit remembers your best fortune.")
    else:
        embed.set_footer(text="Pull recorded. The Brass Bandit awaits your next try.")
    return embed


def profile_embed(member: discord.Member | discord.User, row: sqlite3.Row) -> discord.Embed:
    used = int(row["attempts_used"])
    remaining = MAX_WEEKLY_PULLS - used
    embed = discord.Embed(
        title="🎰 BRASS BANDIT RECORD",
        description=(
            f"**Player:** {member.mention}\n"
            f"**Event Tracking:** {'WEEKLY EVENT' if tracking_enabled(int(row['guild_id'])) else 'NONE'}\n"
            f"**Pulls Used:** {used} / {MAX_WEEKLY_PULLS}\n"
            f"**Pulls Remaining:** {remaining}\n\n"
            f"**Best Pull:** {row['best_result'] or 'None yet'}\n"
            f"{row['best_glyphs'] or ''}"
        ),
        color=0xB87333,
    )
    embed.add_field(name="👑 Legendary", value=str(row["legendary_jackpots"]), inline=True)
    embed.add_field(name="🏆 Jackpots", value=str(row["jackpots"]), inline=True)
    embed.add_field(name="✨ Doubles", value=str(row["doubles"]), inline=True)
    embed.add_field(name="🎲 No Matches", value=str(row["misses"]), inline=True)
    embed.set_footer(text="Only your highest pull determines your weekly standing.")
    return embed


def member_is_admin(member: discord.Member) -> bool:
    """Owner-only clearance for Brass Bandit control commands."""
    if not OWNER_ID_RAW:
        return False
    try:
        return member.id == int(OWNER_ID_RAW)
    except (TypeError, ValueError):
        return False


def top_rows(guild_id: int, limit: int = 10) -> list[sqlite3.Row]:
    week = current_week()
    with db() as con:
        return con.execute("""
            SELECT * FROM player_weekly
            WHERE week_number = ? AND guild_id = ? AND attempts_used > 0 AND event_eligible = 1
            ORDER BY best_index DESC,
                     legendary_jackpots DESC,
                     jackpots DESC,
                     doubles DESC,
                     attempts_used ASC,
                     updated_at ASC
            LIMIT ?
        """, (week, guild_id, limit)).fetchall()


@bot.event
async def on_ready() -> None:
    init_db()
    if GUILD_ID_RAW:
        guild = discord.Object(id=int(GUILD_ID_RAW))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"The Brass Bandit synced commands to guild {GUILD_ID_RAW}.")
    else:
        await bot.tree.sync()
        print("The Brass Bandit synced global commands.")
    print(f"The Brass Bandit online as {bot.user}.")


@bot.tree.command(name="bandit", description="Pull The Brass Bandit's reels once.")
async def bandit(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("The Brass Bandit can only be played inside the server.", ephemeral=True)
        return

    member = interaction.user
    row = ensure_player(interaction.guild.id, member.id, member.display_name)
    if int(row["attempts_used"]) >= MAX_WEEKLY_PULLS:
        await interaction.response.send_message(
            f"🎰 You've already used all **{MAX_WEEKLY_PULLS}** Brass Bandit pulls this week.\n"
            f"Your best pull is **{row['best_result'] or 'None'}** {row['best_glyphs'] or ''}",
            ephemeral=True,
        )
        return

    # Keep pulls 1-9 private so the channel does not fill with ten permanent
    # Brass Bandit result cards per player. The reel animation still runs exactly
    # as before, but in an ephemeral interaction visible only to the player.
    await interaction.response.send_message(
        embed=machine_embed(member, "Winding the mechanism...", spinning_line(), "■□□□□□□□□□"),
        ephemeral=True,
    )
    await asyncio.sleep(0.8)
    await interaction.edit_original_response(
        embed=machine_embed(member, "Feeding the brass reels...", spinning_line(), "■■■■□□□□□□")
    )
    await asyncio.sleep(0.8)
    await interaction.edit_original_response(
        embed=machine_embed(member, "Fortune locking into place...", spinning_line(), "■■■■■■■□□□")
    )
    await asyncio.sleep(0.8)

    symbols = roll_symbols()
    names = [name for name, _ in symbols]
    result_index = result_from_roll(names)
    updated = save_roll(interaction.guild.id, member.id, member.display_name, symbols, result_index)

    # Show every individual pull result privately. On pull 10, publish exactly
    # one permanent weekly result card containing the player's final record/best
    # pull. This is the only normal channel message created by solo Bandit play.
    await interaction.edit_original_response(embed=result_embed(member, symbols, result_index, updated))
    if int(updated["attempts_used"]) >= MAX_WEEKLY_PULLS:
        # The interaction started ephemeral, and Discord cannot convert that original
        # response into a public message. Publish the completed 10-pull session as a
        # normal follow-up, then remove the private final-pull card so the player is
        # left with exactly one permanent public result.
        await interaction.followup.send(
            embed=profile_embed(member, updated),
            ephemeral=False
        )
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass


@bot.tree.command(name="bandit_profile", description="Check your current Brass Bandit weekly record.")
async def bandit_profile(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("The Brass Bandit can only be used inside the server.", ephemeral=True)
        return
    row = ensure_player(interaction.guild.id, interaction.user.id, interaction.user.display_name)
    await interaction.response.send_message(embed=profile_embed(interaction.user, row), ephemeral=True)


@bot.tree.command(name="bandit_leaderboard", description="View this week's Brass Bandit standings.")
async def bandit_leaderboard(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("The Brass Bandit can only be used inside the server.", ephemeral=True)
        return

    rows = top_rows(interaction.guild.id, 10)
    if not rows:
        await interaction.response.send_message("Nobody has challenged The Brass Bandit this week yet.", ephemeral=True)
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for idx, row in enumerate(rows, start=1):
        marker = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
        lines.append(
            f"{marker} **{row['display_name']}** — **{row['best_result']}** "
            f"({row['attempts_used']}/{MAX_WEEKLY_PULLS} pulls)\n{row['best_glyphs'] or ''}"
        )

    top_index = int(rows[0]["best_index"])
    tied = [r for r in rows if int(r["best_index"]) == top_index]
    tie_note = ""
    if len(tied) > 1:
        tie_note = (
            "\n\n**⚙️ Fortune Tied**\n"
            "Multiple players share the highest result. Use your established finalist/tiebreak round if needed."
        )

    embed = discord.Embed(
        title="🎰 THE BRASS BANDIT — WEEKLY STANDINGS",
        description="\n\n".join(lines) + tie_note,
        color=0xB87333,
    )
    embed.set_footer(text="Highest pull first. Legendary Jackpots outrank standard Jackpots.")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="bandit_help", description="Show The Brass Bandit's rules and reel symbols.")
async def bandit_help(interaction: discord.Interaction) -> None:
    symbol_library = "\n".join(f"• {emoji} **{name}**" for name, emoji in SYMBOLS)
    embed = discord.Embed(
        title="🎰 THE BRASS BANDIT — RULES",
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "**The Gilded Gear's Fortune Machine**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• Every player receives **{MAX_WEEKLY_PULLS} pulls** each week.\n"
            "• Every pull spins **3 reels**.\n"
            "• Your **highest result** is used for the weekly standings.\n"
            "• Each reel chooses independently from all eight symbols.\n\n"
            "**Reel Symbols**\n"
            f"{symbol_library}\n\n"
            "**Results**\n"
            "👑 **Legendary Jackpot** — THE SEVEN CHAMPIONS ×3.\n"
            "🏆 **Jackpot** — Any other three matching symbols.\n"
            "✨ **Double** — Any two matching symbols.\n"
            "🎲 **No Match** — Three different symbols.\n\n"
            "The Seven Champions symbol is not weighted or rigged; it spins with the same chance as every other symbol."
        ),
        color=0xB87333,
    )
    embed.set_footer(text="Ten pulls. Eight symbols. One very stubborn machine.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="bandit_tracking", description="Admin only: turn Brass Bandit weekly event tracking on or off.")
async def bandit_tracking(interaction: discord.Interaction, status: Literal["on", "off"]) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Event controls are only available inside the server.", ephemeral=True)
        return
    if not member_is_admin(interaction.user):
        await interaction.response.send_message("Access denied. Admin authorization required.", ephemeral=True)
        return
    enabled = status == "on"
    set_tracking(interaction.guild.id, enabled)
    await interaction.response.send_message(
        f"⚙️ **Brass Bandit weekly event tracking is now {'ON' if enabled else 'OFF'}.**\n"
        + ("New pulls will count toward the weekly standings." if enabled else "The machine still plays normally, but new pulls will not be eligible for the weekly standings."),
        ephemeral=True,
    )


@bot.tree.command(name="bandit_status", description="Admin only: check The Brass Bandit's live event-tracking switch.")
async def bandit_status(interaction: discord.Interaction) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Event controls are only available inside the server.", ephemeral=True)
        return
    if not member_is_admin(interaction.user):
        await interaction.response.send_message("Access denied. Admin authorization required.", ephemeral=True)
        return
    enabled = tracking_enabled(interaction.guild.id)
    embed = discord.Embed(
        title="🎰 THE BRASS BANDIT // EVENT STATUS",
        description=(
            f"**Event Tracking:** {'WEEKLY EVENT' if enabled else 'NONE'}\n"
            f"**Tracking Switch:** {'ON' if enabled else 'OFF'}\n\n"
            + ("New pulls are eligible for the weekly standings." if enabled else "The machine remains playable, but new pulls are not eligible for weekly standings.")
        ),
        color=0xB87333,
    )
    embed.set_footer(text="The Brass Bandit • Event Control Gauge")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="bandit_archive", description="Admin only: generate this week's Brass Bandit archive summary.")
async def bandit_archive(interaction: discord.Interaction) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Archive summaries can only be generated inside the server.", ephemeral=True)
        return
    if not member_is_admin(interaction.user):
        await interaction.response.send_message("Access denied. Admin authorization required.", ephemeral=True)
        return

    rows = top_rows(interaction.guild.id, 10)
    if not rows:
        await interaction.response.send_message("No Brass Bandit records are available yet.", ephemeral=True)
        return

    champion = rows[0]
    top_index = int(champion["best_index"])
    tied = [r for r in rows if int(r["best_index"]) == top_index]
    if len(tied) > 1:
        champion_block = f"Tied fortune leaders: {', '.join(r['display_name'] for r in tied)}\n\n"
    else:
        champion_block = f"Weekly Brass Bandit Champion: {champion['display_name']}\n\n"

    standings = "\n".join(
        f"{idx}. {row['display_name']} — {row['best_result']} {row['best_glyphs'] or ''}"
        for idx, row in enumerate(rows[:5], start=1)
    )
    archive_text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "🎰 THE BRASS BANDIT — WEEKLY RESULTS\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{champion_block}"
        "Top Fortunes\n"
        f"{standings}\n\n"
        '"Fortune favors whoever keeps pulling the lever."\n'
        "━━━━━━━━━━━━━━━━━━"
    )
    await interaction.response.send_message(
        "Copy this into your Hall of Champions / weekly results post:\n\n"
        f"```text\n{archive_text}\n```",
        ephemeral=True,
    )


@bot.tree.command(name="bandit_reset", description="Admin only: reset The Brass Bandit for a new weekly event.")
async def bandit_reset(interaction: discord.Interaction) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("The Brass Bandit can only be reset inside the server.", ephemeral=True)
        return
    if not member_is_admin(interaction.user):
        await interaction.response.send_message("Access denied. Admin authorization required.", ephemeral=True)
        return

    new_week = next_week()
    await interaction.response.send_message(
        "━━━━━━━━━━━━━━━━━━\n"
        "**🎰 THE BRASS BANDIT HAS BEEN RESET**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Weekly round **{new_week}** is now open.\n"
        f"Every player has **{MAX_WEEKLY_PULLS} fresh pulls** available.\n\n"
        "Good luck. The machine makes no promises.",
        ephemeral=True,
    )


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Add it to your Render Environment Variables.")

bot.run(TOKEN)
