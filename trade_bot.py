# ==========================================================
# TRADE BOT COMPLETE SYSTEM
# PART 1
# ==========================================================

import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import datetime
import math
from flask import Flask
from threading import Thread

# ==========================================================
# CONFIG
# ==========================================================

TOKEN = os.getenv("TOKEN")

STAFF_ROLE_ID = 1478964390530121964
STATS_CHANNEL_ID = 1479271849283293256
LOG_CHANNEL_ID = 1480455928699555992

DATABASE_NAME = "tradebot.db"

# ==========================================================
# BOT SETUP
# ==========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

db = None
stats_message = None

# ==========================================================
# DATABASE
# ==========================================================

async def init_database():

    global db

    db = await aiosqlite.connect(DATABASE_NAME)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS trades(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_id INTEGER,
        user_id INTEGER,
        rating INTEGER,
        comment TEXT,
        date TEXT
    )
    """)

    await db.commit()

# ==========================================================
# GENERATE STATS EMBED
# ==========================================================

async def generate_stats_embed():

    embed = discord.Embed(
        title="📊 仲介取引統計",
        color=0x00ffcc
    )

    # ======================================
    # 信頼度ランキング
    # ======================================

    cursor = await db.execute("""
    SELECT staff_id, AVG(rating), COUNT(*)
    FROM trades
    GROUP BY staff_id
    ORDER BY AVG(rating) DESC
    LIMIT 10
    """)

    rows = await cursor.fetchall()

    trust_text = ""

    for i, row in enumerate(rows, start=1):

        staff = bot.get_user(row[0])
        rating = round(row[1], 2)
        count = row[2]

        if staff:
            trust_text += f"{i}. {staff.name} ⭐{rating} ({count}件)\n"

    if trust_text == "":
        trust_text = "データなし"

    embed.add_field(
        name="🏆 信頼度ランキング",
        value=trust_text,
        inline=False
    )

    # ======================================
    # 取引数ランキング
    # ======================================

    cursor = await db.execute("""
    SELECT staff_id, COUNT(*)
    FROM trades
    GROUP BY staff_id
    ORDER BY COUNT(*) DESC
    LIMIT 10
    """)

    rows = await cursor.fetchall()

    trade_text = ""

    for i, row in enumerate(rows, start=1):

        staff = bot.get_user(row[0])
        count = row[1]

        if staff:
            trade_text += f"{i}. {staff.name} {count}件\n"

    if trade_text == "":
        trade_text = "データなし"

    embed.add_field(
        name="📊 取引数ランキング",
        value=trade_text,
        inline=False
    )

    embed.set_footer(text="TradeBot Statistics")

    return embed

# ==========================================================
# STATS LOOP
# ==========================================================

@tasks.loop(minutes=5)
async def update_stats():

    global stats_message

    if stats_message:

        embed = await generate_stats_embed()

        await stats_message.edit(
            content=None,
            embed=embed
        )

# ==========================================================
# BOT READY
# ==========================================================

@bot.event
async def on_ready():

    global stats_message

    print("BOT STARTING")

    await init_database()
    await bot.tree.sync()

    channel = bot.get_channel(STATS_CHANNEL_ID)

    if channel:

        embed = await generate_stats_embed()

        stats_message = await channel.send(embed=embed)

    update_stats.start()

    print("BOT READY")

# ==========================================================
# START
# ==========================================================

# ==========================================================
# PART 2
# FINISH SYSTEM / REVIEW UI
# ==========================================================

# ==========================================================
# TRADE SAVE
# ==========================================================

async def save_trade(staff_id, user_id, rating, comment):

    today = datetime.date.today().isoformat()

    await db.execute(
        """
        INSERT INTO trades(staff_id,user_id,rating,comment,date)
        VALUES(?,?,?,?,?)
        """,
        (staff_id, user_id, rating, comment, today)
    )

    await db.commit()


# ==========================================================
# FAILURE SAVE
# ==========================================================

async def save_failure(reason, comment):

    today = datetime.date.today().isoformat()

    await db.execute(
        """
        INSERT INTO failures(reason,comment,date)
        VALUES(?,?,?)
        """,
        (reason, comment, today)
    )

    await db.commit()


# ==========================================================
# FAILURE VIEW
# ==========================================================

class FailureReasonView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def process(self, interaction, reason):

        await save_failure(reason, "")

        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        if log_channel:

            embed = discord.Embed(
                title="取引失敗",
                description=reason,
                color=discord.Color.red()
            )

            embed.add_field(
                name="ユーザー",
                value=interaction.user.mention
            )

            await log_channel.send(embed=embed)

        await interaction.response.send_message(
            "改善点を記録しました。"
        )

    @discord.ui.button(label="対応が遅い", style=discord.ButtonStyle.gray)
    async def slow(self, interaction, button):

        await self.process(interaction, "対応が遅い")

    @discord.ui.button(label="条件不一致", style=discord.ButtonStyle.gray)
    async def condition(self, interaction, button):

        await self.process(interaction, "条件不一致")

    @discord.ui.button(label="トラブル", style=discord.ButtonStyle.gray)
    async def trouble(self, interaction, button):

        await self.process(interaction, "トラブル")

    @discord.ui.button(label="その他", style=discord.ButtonStyle.gray)
    async def other(self, interaction, button):

        await self.process(interaction, "その他")


# ==========================================================
# STAFF REVIEW VIEW
# ==========================================================

class StaffReviewView(discord.ui.View):

    def __init__(self, staff_id):
        super().__init__(timeout=None)
        self.staff_id = staff_id

    async def process(self, interaction, rating):

        await save_trade(
            self.staff_id,
            interaction.user.id,
            rating,
            ""
        )

        await interaction.response.send_message(
            "レビューありがとうございました！"
        )

    @discord.ui.button(label="⭐1", style=discord.ButtonStyle.gray)
    async def r1(self, interaction, button):

        await self.process(interaction, 1)

    @discord.ui.button(label="⭐2", style=discord.ButtonStyle.gray)
    async def r2(self, interaction, button):

        await self.process(interaction, 2)

    @discord.ui.button(label="⭐3", style=discord.ButtonStyle.gray)
    async def r3(self, interaction, button):

        await self.process(interaction, 3)

    @discord.ui.button(label="⭐4", style=discord.ButtonStyle.gray)
    async def r4(self, interaction, button):

        await self.process(interaction, 4)

    @discord.ui.button(label="⭐5", style=discord.ButtonStyle.green)
    async def r5(self, interaction, button):

        await self.process(interaction, 5)


# ==========================================================
# FINISH VIEW
# ==========================================================

class FinishView(discord.ui.View):

    def __init__(self, staff_id):
        super().__init__(timeout=None)
        self.staff_id = staff_id

    @discord.ui.button(label="成功", style=discord.ButtonStyle.green)
    async def success(self, interaction, button):

        await interaction.response.send_message(
            "スタッフ評価をしてください",
            view=StaffReviewView(self.staff_id)
        )

    @discord.ui.button(label="失敗", style=discord.ButtonStyle.red)
    async def fail(self, interaction, button):

        await interaction.response.send_message(
            "失敗理由を選択してください",
            view=FailureReasonView()
        )


# ==========================================================
# FINISH COMMAND
# ==========================================================

@bot.tree.command(
    name="finish",
    description="取引を終了します"
)
async def finish(interaction: discord.Interaction):

    # スタッフのみ使用可能
    if not discord.utils.get(interaction.user.roles, id=STAFF_ROLE_ID):

        await interaction.response.send_message(
            "このコマンドは仲介スタッフのみ使用できます",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "取引結果を選択してください",
        view=FinishView(interaction.user.id)
    )

# ==========================================================
# PART 3
# PROFILE / REVIEW STATS / REVIEW VIEW
# ==========================================================

# ==========================================================
# STAFF REVIEW STATS
# ==========================================================

async def get_staff_review_stats(staff_id):

    async with db.execute(
        """
        SELECT rating FROM trades
        WHERE staff_id=?
        """,
        (staff_id,)
    ) as cur:

        rows = await cur.fetchall()

    ratings = [r[0] for r in rows if r[0] is not None]

    if len(ratings) == 0:

        return {
            "count": 0,
            "avg": 0,
            "stars": {1:0,2:0,3:0,4:0,5:0}
        }

    avg = round(sum(ratings)/len(ratings),2)

    star_count = {
        1: ratings.count(1),
        2: ratings.count(2),
        3: ratings.count(3),
        4: ratings.count(4),
        5: ratings.count(5)
    }

    return {
        "count": len(ratings),
        "avg": avg,
        "stars": star_count
    }


# ==========================================================
# STAFF PROFILE COMMAND
# ==========================================================

@bot.tree.command(
    name="staffprofile",
    description="スタッフのプロフィールを見る"
)
async def staffprofile(
    interaction: discord.Interaction,
    member: discord.Member
):

    stats = await get_staff_review_stats(member.id)

    async with db.execute(
        """
        SELECT COUNT(*) FROM trades
        WHERE staff_id=?
        """,
        (member.id,)
    ) as cur:

        trades = (await cur.fetchone())[0]

    embed = discord.Embed(
        title=f"{member.name} スタッフプロフィール",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="取引数",
        value=str(trades)
    )

    embed.add_field(
        name="レビュー数",
        value=str(stats["count"])
    )

    embed.add_field(
        name="平均評価",
        value=f"⭐{stats['avg']}"
    )

    star_text = ""

    for i in range(5,0,-1):

        star_text += f"{i}⭐ : {stats['stars'][i]}\n"

    embed.add_field(
        name="星内訳",
        value=star_text,
        inline=False
    )

    await interaction.response.send_message(embed=embed)


# ==========================================================
# STAFF REVIEWS LIST
# ==========================================================

@bot.tree.command(
    name="reviews_staff",
    description="スタッフレビューを見る"
)
async def reviews_staff(
    interaction: discord.Interaction,
    member: discord.Member
):

    async with db.execute(
        """
        SELECT rating,date FROM trades
        WHERE staff_id=?
        ORDER BY id DESC
        LIMIT 10
        """,
        (member.id,)
    ) as cur:

        rows = await cur.fetchall()

    if not rows:

        await interaction.response.send_message(
            "レビューがありません"
        )

        return

    text = ""

    for r in rows:

        text += f"⭐{r[0]} | {r[1]}\n"

    embed = discord.Embed(
        title=f"{member.name} のレビュー",
        description=text,
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed)
# ==========================================================
# PART 4
# RANKING SYSTEM
# ==========================================================

# ==========================================================
# GET ALL STAFF IDS
# ==========================================================

async def get_all_staff_ids():

    async with db.execute(
        """
        SELECT DISTINCT staff_id FROM trades
        """
    ) as cur:

        rows = await cur.fetchall()

    return [r[0] for r in rows]


# ==========================================================
# STAFF TRADE COUNT
# ==========================================================

async def get_staff_trade_count(staff_id):

    async with db.execute(
        """
        SELECT COUNT(*) FROM trades
        WHERE staff_id=?
        """,
        (staff_id,)
    ) as cur:

        row = await cur.fetchone()

    return row[0]


# ==========================================================
# STAFF AVG RATING
# ==========================================================

async def get_staff_avg_rating(staff_id):

    async with db.execute(
        """
        SELECT AVG(rating) FROM trades
        WHERE staff_id=? AND rating IS NOT NULL
        """,
        (staff_id,)
    ) as cur:

        row = await cur.fetchone()

    if row[0] is None:
        return 0

    return round(row[0], 2)


# ==========================================================
# STAFF TRUST RANKING
# ==========================================================

async def build_staff_trust_ranking(guild):

    staff_ids = await get_all_staff_ids()

    ranking = []

    for staff_id in staff_ids:

        rating = await get_staff_avg_rating(staff_id)

        member = guild.get_member(staff_id)

        if member:

            ranking.append((member.name, rating))

    ranking.sort(key=lambda x: x[1], reverse=True)

    return ranking


# ==========================================================
# STAFF TRADE RANKING
# ==========================================================

async def build_trade_ranking(guild):

    staff_ids = await get_all_staff_ids()

    ranking = []

    for staff_id in staff_ids:

        count = await get_staff_trade_count(staff_id)

        member = guild.get_member(staff_id)

        if member:

            ranking.append((member.name, count))

    ranking.sort(key=lambda x: x[1], reverse=True)

    return ranking


# ==========================================================
# STAFF TRUST COMMAND
# ==========================================================

@bot.tree.command(
    name="staffranking",
    description="スタッフ信頼度ランキング"
)
async def staffranking(interaction: discord.Interaction):

    ranking = await build_staff_trust_ranking(interaction.guild)

    if not ranking:

        await interaction.response.send_message(
            "データがありません"
        )

        return

    text = ""

    pos = 1

    for name, score in ranking[:10]:

        text += f"{pos}位 {name} ⭐{score}\n"

        pos += 1

    embed = discord.Embed(
        title="🏆 スタッフ信頼度ランキング",
        description=text,
        color=discord.Color.purple()
    )

    await interaction.response.send_message(embed=embed)


# ==========================================================
# TRADE COUNT COMMAND
# ==========================================================

@bot.tree.command(
    name="traderanking",
    description="取引数ランキング"
)
async def traderanking(interaction: discord.Interaction):

    ranking = await build_trade_ranking(interaction.guild)

    if not ranking:

        await interaction.response.send_message(
            "データがありません"
        )

        return

    text = ""

    pos = 1

    for name, count in ranking[:10]:

        text += f"{pos}位 {name} : {count}件\n"

        pos += 1

    embed = discord.Embed(
        title="📊 取引数ランキング",
        description=text,
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)
# ==========================================================
# PART 5
# ADMIN / SYSTEM COMMANDS
# ==========================================================

# ==========================================================
# ADMIN CHECK
# ==========================================================

def is_admin(user: discord.Member):

    return user.guild_permissions.administrator

# ==========================================================
# ADD TRADE COMMAND
# ==========================================================

@bot.tree.command(
    name="addtrade",
    description="取引を手動追加（管理者）"
)
async def addtrade(
    interaction: discord.Interaction,
    staff: discord.Member,
    success: bool
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "管理者専用コマンドです",
            ephemeral=True
        )

        return

    today = datetime.date.today().isoformat()

    await db.execute(
        """
        INSERT INTO trades(staff,success,user,date)
        VALUES(?,?,?,?)
        """,
        (
            staff.id,
            1 if success else 0,
            interaction.user.id,
            today
        )
    )

    await db.commit()

    await interaction.response.send_message(
        "取引を追加しました"
    )

# ==========================================================
# PART 5
# ADMIN / SYSTEM COMMANDS
# ==========================================================

# ==========================================================
# ADMIN CHECK
# ==========================================================

def is_admin(user: discord.Member):

    return user.guild_permissions.administrator


# ==========================================================
# ADD TRADE COMMAND
# ==========================================================

@bot.tree.command(
    name="addtrade",
    description="取引を手動追加（管理者）"
)
async def addtrade(
    interaction: discord.Interaction,
    staff: discord.Member,
    rating: int
):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "管理者専用コマンドです",
            ephemeral=True
        )

        return

    today = datetime.date.today().isoformat()

    await db.execute(
        """
        INSERT INTO trades(staff_id,user_id,rating,comment,date)
        VALUES(?,?,?,?,?)
        """,
        (
            staff.id,
            interaction.user.id,
            rating,
            "admin add",
            today
        )
    )

    await db.commit()

    await interaction.response.send_message(
        "取引を追加しました"
    )


# ==========================================================
# RESET STATS
# ==========================================================

@bot.tree.command(
    name="resetstats",
    description="統計リセット（管理者）"
)
async def resetstats(interaction: discord.Interaction):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "管理者専用コマンドです",
            ephemeral=True
        )

        return

    await db.execute("DELETE FROM trades")
    await db.execute("DELETE FROM failures")

    await db.commit()

    await interaction.response.send_message(
        "統計をリセットしました"
    )


# ==========================================================
# FORCE STATS UPDATE
# ==========================================================

@bot.tree.command(
    name="forcestats",
    description="統計更新（管理者）"
)
async def forcestats(interaction: discord.Interaction):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "管理者専用コマンドです",
            ephemeral=True
        )

        return

    await update_stats()

    await interaction.response.send_message(
        "統計を更新しました"
    )


# ==========================================================
# BOT INFO
# ==========================================================

@bot.tree.command(
    name="help_tradebot",
    description="BOTコマンド一覧"
)
async def help_tradebot(interaction: discord.Interaction):

    embed = discord.Embed(
        title="仲介BOTコマンド一覧",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="取引",
        value="""
/finish
""",
        inline=False
    )

    embed.add_field(
        name="プロフィール",
        value="""
/staffprofile
""",
        inline=False
    )

    embed.add_field(
        name="レビュー",
        value="""
/reviews_staff
""",
        inline=False
    )

    embed.add_field(
        name="ランキング",
        value="""
/staffranking
/traderanking
""",
        inline=False
    )

    embed.add_field(
        name="管理者",
        value="""
/addtrade
/resetstats
/forcestats
""",
        inline=False
    )

    await interaction.response.send_message(embed=embed)


# ==========================================================
# SYSTEM READY MESSAGE
# ==========================================================

@bot.event
async def on_connect():

    print("Bot connected")


@bot.event
async def on_disconnect():

    print("Bot disconnected")


# ==========================================================
# END
# ==========================================================

bot.run(TOKEN)
