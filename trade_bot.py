# ==========================================================
# TRADE BOT COMPLETE SYSTEM
# PART 1
# ==========================================================

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

TOKEN = discord_token

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

# ==========================================================
# KEEP ALIVE
# ==========================================================

app = Flask("")

@app.route("/")
def home():
    return "Bot Online"

def run_web():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==========================================================
# DATABASE INIT
# ==========================================================

async def init_database():

    global db

    db = await aiosqlite.connect(DATABASE_NAME)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS trades(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff INTEGER,
        success INTEGER,
        user INTEGER,
        date TEXT
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS staff_reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff INTEGER,
        rating INTEGER,
        comment TEXT,
        date TEXT
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS server_reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rating INTEGER,
        comment TEXT,
        date TEXT
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS failures(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reason TEXT,
        comment TEXT,
        date TEXT
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS stats_cache(
        name TEXT,
        value INTEGER
    )
    """)

    await db.commit()

# ==========================================================
# UTILS
# ==========================================================

async def get_total_trades():

    async with db.execute(
        "SELECT COUNT(*) FROM trades"
    ) as cur:

        row = await cur.fetchone()

    return row[0]

async def get_success_trades():

    async with db.execute(
        "SELECT COUNT(*) FROM trades WHERE success=1"
    ) as cur:

        row = await cur.fetchone()

    return row[0]

async def get_fail_trades():

    async with db.execute(
        "SELECT COUNT(*) FROM trades WHERE success=0"
    ) as cur:

        row = await cur.fetchone()

    return row[0]

async def get_today_trades():

    today = datetime.date.today().isoformat()

    async with db.execute(
        "SELECT COUNT(*) FROM trades WHERE date=?",
        (today,)
    ) as cur:

        row = await cur.fetchone()

    return row[0]

async def get_month_trades():

    month = datetime.date.today().strftime("%Y-%m")

    async with db.execute(
        "SELECT COUNT(*) FROM trades WHERE date LIKE ?",
        (f"{month}%",)
    ) as cur:

        row = await cur.fetchone()

    return row[0]

# ==========================================================
# REVIEW STATS
# ==========================================================

async def get_staff_reviews(staff_id):

    async with db.execute(
        "SELECT rating FROM staff_reviews WHERE staff=?",
        (staff_id,)
    ) as cur:

        rows = await cur.fetchall()

    return [r[0] for r in rows]

async def get_server_reviews():

    async with db.execute(
        "SELECT rating FROM server_reviews"
    ) as cur:

        rows = await cur.fetchall()

    return [r[0] for r in rows]

# ==========================================================
# RANKING SCORE
# ==========================================================

async def calculate_staff_score(staff_id):

    ratings = await get_staff_reviews(staff_id)

    async with db.execute(
        "SELECT COUNT(*) FROM trades WHERE staff=?",
        (staff_id,)
    ) as cur:

        trades = (await cur.fetchone())[0]

    if len(ratings) == 0:

        return 0

    avg = sum(ratings) / len(ratings)

    score = (avg * math.log(len(ratings)+1)) + (trades * 0.2)

    return score

# ==========================================================
# EMBEDS
# ==========================================================

def create_stats_embed(total, success, fail, today, month):

    rate = 0

    if total > 0:

        rate = round(success/total*100,2)

    embed = discord.Embed(
        title="📊取引統計",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="総取引",
        value=str(total),
        inline=True
    )

    embed.add_field(
        name="成功",
        value=str(success),
        inline=True
    )

    embed.add_field(
        name="失敗",
        value=str(fail),
        inline=True
    )

    embed.add_field(
        name="成功率",
        value=f"{rate}%",
        inline=False
    )

    embed.add_field(
        name="今日の取引",
        value=str(today),
        inline=True
    )

    embed.add_field(
        name="今月の取引",
        value=str(month),
        inline=True
    )

    return embed

# ==========================================================
# BOT READY
# ==========================================================

@bot.event
async def on_ready():

    print("BOT STARTING")

    await init_database()

    await bot.tree.sync()

    update_stats.start()

    print("BOT READY")

# ==========================================================
# STATS LOOP
# ==========================================================

@tasks.loop(minutes=2)
async def update_stats():

    channel = bot.get_channel(STATS_CHANNEL_ID)

    if not channel:

        return

    total = await get_total_trades()
    success = await get_success_trades()
    fail = await get_fail_trades()
    today = await get_today_trades()
    month = await get_month_trades()

    embed = create_stats_embed(
        total,
        success,
        fail,
        today,
        month
    )

    try:

        await channel.purge(limit=1)

    except:

        pass

    await channel.send(embed=embed)

# ==========================================================
# START
# ==========================================================

keep_alive()

bot.run(TOKEN)
# ==========================================================
# PART 2
# FINISH SYSTEM / REVIEW UI
# ==========================================================

# ==========================================================
# TRADE SAVE
# ==========================================================

async def save_trade(staff_id, success, user_id):

    today = datetime.date.today().isoformat()

    await db.execute(
        """
        INSERT INTO trades(staff,success,user,date)
        VALUES(?,?,?,?)
        """,
        (staff_id, success, user_id, today)
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
# SERVER REVIEW SAVE
# ==========================================================

async def save_server_review(rating):

    today = datetime.date.today().isoformat()

    await db.execute(
        """
        INSERT INTO server_reviews(rating,comment,date)
        VALUES(?,?,?)
        """,
        (rating, "", today)
    )

    await db.commit()

# ==========================================================
# STAFF REVIEW SAVE
# ==========================================================

async def save_staff_review(staff_id, rating):

    today = datetime.date.today().isoformat()

    await db.execute(
        """
        INSERT INTO staff_reviews(staff,rating,comment,date)
        VALUES(?,?,?,?)
        """,
        (staff_id, rating, "", today)
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
# SERVER REVIEW VIEW
# ==========================================================

class ServerReviewView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def process(self, interaction, rating):

        await save_server_review(rating)

        await interaction.response.send_message(
            "スタッフを評価してください",
            view=StaffReviewView()
        )

    @discord.ui.button(label="⭐1", style=discord.ButtonStyle.gray)
    async def r1(self, interaction, button):

        await self.process(interaction,1)

    @discord.ui.button(label="⭐2", style=discord.ButtonStyle.gray)
    async def r2(self, interaction, button):

        await self.process(interaction,2)

    @discord.ui.button(label="⭐3", style=discord.ButtonStyle.gray)
    async def r3(self, interaction, button):

        await self.process(interaction,3)

    @discord.ui.button(label="⭐4", style=discord.ButtonStyle.gray)
    async def r4(self, interaction, button):

        await self.process(interaction,4)

    @discord.ui.button(label="⭐5", style=discord.ButtonStyle.green)
    async def r5(self, interaction, button):

        await self.process(interaction,5)

# ==========================================================
# STAFF REVIEW VIEW
# ==========================================================

class StaffReviewView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def process(self, interaction, rating):

        staff_member = None

        for m in interaction.channel.members:

            if discord.utils.get(m.roles, id=STAFF_ROLE_ID):

                staff_member = m

        if staff_member:

            await save_staff_review(staff_member.id, rating)

            await save_trade(
                staff_member.id,
                1,
                interaction.user.id
            )

        await interaction.response.send_message(
            "レビューありがとうございました！"
        )

    @discord.ui.button(label="⭐1", style=discord.ButtonStyle.gray)
    async def r1(self, interaction, button):

        await self.process(interaction,1)

    @discord.ui.button(label="⭐2", style=discord.ButtonStyle.gray)
    async def r2(self, interaction, button):

        await self.process(interaction,2)

    @discord.ui.button(label="⭐3", style=discord.ButtonStyle.gray)
    async def r3(self, interaction, button):

        await self.process(interaction,3)

    @discord.ui.button(label="⭐4", style=discord.ButtonStyle.gray)
    async def r4(self, interaction, button):

        await self.process(interaction,4)

    @discord.ui.button(label="⭐5", style=discord.ButtonStyle.green)
    async def r5(self, interaction, button):

        await self.process(interaction,5)

# ==========================================================
# FINISH VIEW
# ==========================================================

class FinishView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="成功", style=discord.ButtonStyle.green)
    async def success(self, interaction, button):

        await interaction.response.send_message(
            "サーバー評価をしてください",
            view=ServerReviewView()
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

    await interaction.response.send_message(
        "取引結果を選択してください",
        view=FinishView()
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
        SELECT rating FROM staff_reviews
        WHERE staff=?
        """,
        (staff_id,)
    ) as cur:

        rows = await cur.fetchall()

    ratings = [r[0] for r in rows]

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
# SERVER REVIEW STATS
# ==========================================================

async def get_server_review_stats():

    async with db.execute(
        """
        SELECT rating FROM server_reviews
        """
    ) as cur:

        rows = await cur.fetchall()

    ratings = [r[0] for r in rows]

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
        WHERE staff=?
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
# SERVER PROFILE COMMAND
# ==========================================================

@bot.tree.command(
    name="serverprofile",
    description="サーバー評価を見る"
)
async def serverprofile(interaction: discord.Interaction):

    stats = await get_server_review_stats()

    embed = discord.Embed(
        title="サーバー評価",
        color=discord.Color.gold()
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
        SELECT rating,date FROM staff_reviews
        WHERE staff=?
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
# SERVER REVIEWS LIST
# ==========================================================

@bot.tree.command(
    name="reviews_server",
    description="サーバーレビューを見る"
)
async def reviews_server(interaction: discord.Interaction):

    async with db.execute(
        """
        SELECT rating,date FROM server_reviews
        ORDER BY id DESC
        LIMIT 10
        """
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
        title="サーバーレビュー",
        description=text,
        color=discord.Color.green()
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
        SELECT DISTINCT staff FROM trades
        """
    ) as cur:

        rows = await cur.fetchall()

    return [r[0] for r in rows]

# ==========================================================
# STAFF TRUST RANKING
# ==========================================================

async def build_staff_trust_ranking(guild):

    staff_ids = await get_all_staff_ids()

    ranking = []

    for staff in staff_ids:

        score = await calculate_staff_score(staff)

        member = guild.get_member(staff)

        if member:

            ranking.append((member.name, score))

    ranking.sort(key=lambda x: x[1], reverse=True)

    return ranking

# ==========================================================
# STAFF TRADE COUNT
# ==========================================================

async def get_staff_trade_count(staff):

    async with db.execute(
        """
        SELECT COUNT(*) FROM trades
        WHERE staff=?
        """,
        (staff,)
    ) as cur:

        row = await cur.fetchone()

    return row[0]

# ==========================================================
# STAFF SUCCESS RATE
# ==========================================================

async def get_staff_success_rate(staff):

    async with db.execute(
        """
        SELECT COUNT(*) FROM trades
        WHERE staff=? AND success=1
        """,
        (staff,)
    ) as cur:

        success = (await cur.fetchone())[0]

    async with db.execute(
        """
        SELECT COUNT(*) FROM trades
        WHERE staff=?
        """,
        (staff,)
    ) as cur:

        total = (await cur.fetchone())[0]

    if total == 0:

        return 0

    return round(success/total*100,2)

# ==========================================================
# STAFF TRADE RANKING
# ==========================================================

async def build_trade_ranking(guild):

    staff_ids = await get_all_staff_ids()

    ranking = []

    for staff in staff_ids:

        count = await get_staff_trade_count(staff)

        member = guild.get_member(staff)

        if member:

            ranking.append((member.name, count))

    ranking.sort(key=lambda x: x[1], reverse=True)

    return ranking

# ==========================================================
# STAFF SUCCESS RATE RANKING
# ==========================================================

async def build_success_ranking(guild):

    staff_ids = await get_all_staff_ids()

    ranking = []

    for staff in staff_ids:

        rate = await get_staff_success_rate(staff)

        member = guild.get_member(staff)

        if member:

            ranking.append((member.name, rate))

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

        text += f"{pos}位 {name} ⭐{round(score,2)}\n"

        pos += 1

    embed = discord.Embed(
        title="スタッフ信頼度ランキング",
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
        title="取引数ランキング",
        description=text,
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)

# ==========================================================
# SUCCESS RATE COMMAND
# ==========================================================

@bot.tree.command(
    name="successranking",
    description="成功率ランキング"
)
async def successranking(interaction: discord.Interaction):

    ranking = await build_success_ranking(interaction.guild)

    if not ranking:

        await interaction.response.send_message(
            "データがありません"
        )

        return

    text = ""

    pos = 1

    for name, rate in ranking[:10]:

        text += f"{pos}位 {name} : {rate}%\n"

        pos += 1

    embed = discord.Embed(
        title="成功率ランキング",
        description=text,
        color=discord.Color.orange()
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
    await db.execute("DELETE FROM staff_reviews")
    await db.execute("DELETE FROM server_reviews")

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
# BOT RELOAD
# ==========================================================

@bot.tree.command(
    name="reloadbot",
    description="BOT再読み込み（管理者）"
)
async def reloadbot(interaction: discord.Interaction):

    if not is_admin(interaction.user):

        await interaction.response.send_message(
            "管理者専用コマンドです",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "BOTを再起動してください（Railwayなど）"
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
        /serverprofile
        """,
        inline=False
    )

    embed.add_field(
        name="レビュー",
        value="""
        /reviews_staff
        /reviews_server
        """,
        inline=False
    )

    embed.add_field(
        name="ランキング",
        value="""
        /staffranking
        /traderanking
        /successranking
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
