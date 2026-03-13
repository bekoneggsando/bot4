import discord
from discord import app_commands
from discord.ext import commands, tasks
import psycopg2
from psycopg2.extras import RealDictCursor
import math
import datetime
import os

# ================= 設定エリア =================
TOKEN = os.getenv('DISCORD_TOKEN')
DB_URL = os.getenv('DATABASE_URL') 

GUILD_ID = 1478366462144942120          # あなたのサーバーID
SERVER_REVIEW_CH_ID = 1479271799492710450  # サーバーレビュー用
STAFF_REVIEW_CH_ID = 1479125489506586735   # スタッフレビュー用
PANEL_CH_ID = 1479271849283293256          # 統計パネル用
# =============================================

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        # Supabaseへ接続
        # URLを使わず、情報を一つずつ直接指定して接続します
        self.conn = psycopg2.connect(
            host="aws-0-ap-southeast-2.pooler.supabase.com",
            port=6543,
            database="postgres",
            user="postgres.tvgctvjmtkvbqmkgyhot",
            password="Aeyvnl123Aeyvnl12"
            sslmode="require"
        )
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # PostgreSQL用の型を使用
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS deals (
            deal_id SERIAL PRIMARY KEY, 
            staff_id BIGINT, 
            result TEXT, 
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY, 
            deal_id INTEGER, 
            staff_id BIGINT, 
            reviewer_id BIGINT, 
            type TEXT, 
            stars INTEGER, 
            comment TEXT
        )''')
        self.conn.commit()

    async def setup_hook(self):
        self.add_view(PersistentFinishView())
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        self.update_panel.start()

    async def on_ready(self):
        print(f'Logged in as {self.user} (Supabase Connected)')
        await self.refresh_stats_panel()

    @tasks.loop(minutes=5)
    async def update_panel(self):
        await self.refresh_stats_panel()

    async def refresh_stats_panel(self):
        channel = self.get_channel(PANEL_CH_ID)
        if not channel: return
        
        self.cursor.execute("SELECT COUNT(*), SUM(CASE WHEN result='成功' THEN 1 ELSE 0 END), SUM(CASE WHEN result='失敗' THEN 1 ELSE 0 END) FROM deals")
        total, success, fail = self.cursor.fetchone()
        total, success, fail = total or 0, success or 0, fail or 0
        
        self.cursor.execute("SELECT COUNT(*) FROM deals WHERE date_trunc('month', timestamp) = date_trunc('month', current_timestamp)")
        month_count = self.cursor.fetchone()[0]

        embed = discord.Embed(title="📊 サーバー統計パネル", color=discord.Color.blue())
        embed.add_field(name="取引総数", value=f"{total}件", inline=True)
        embed.add_field(name="成功数", value=f"✅ {success}", inline=True)
        embed.add_field(name="失敗数", value=f"❌ {fail}", inline=True)
        embed.add_field(name="今月の取引", value=f"{month_count}件", inline=True)
        
        self.cursor.execute("""
            SELECT d.staff_id, COUNT(d.deal_id), 
            (SELECT COUNT(*) FROM reviews r WHERE r.staff_id = d.staff_id AND r.type='staff'), 
            (SELECT AVG(stars) FROM reviews r WHERE r.staff_id = d.staff_id AND r.type='staff') 
            FROM deals d GROUP BY d.staff_id
        """)
        staff_data = self.cursor.fetchall()
        
        ranked_list = []
        for s_id, t_deals, r_count, a_stars in staff_data:
            a_stars = float(a_stars or 0)
            score = a_stars * math.log1p(r_count or 0) * math.log1p(t_deals or 0)
            ranked_list.append({'id': s_id, 'score': score, 'deals': t_deals})
        
        trust_rank = sorted(ranked_list, key=lambda x: x['score'], reverse=True)[:5]
        trust_text = "\n".join([f"{i+1}位: <@{s['id']}> ({s['score']:.1f})" for i, s in enumerate(trust_rank)]) or "なし"
        embed.add_field(name="🏆 信頼度順", value=trust_text, inline=False)
        
        last_msg = None
        async for message in channel.history(limit=5):
            if message.author == self.user:
                last_msg = message
                break
        if last_msg: await last_msg.edit(embed=embed)
        else: await channel.send(embed=embed)
        self.conn.commit()

bot = MyBot()

class ReviewModal(discord.ui.Modal):
    def __init__(self, deal_id, staff_id, review_type):
        super().__init__(title="レビュー入力")
        self.deal_id, self.staff_id, self.review_type = deal_id, staff_id, review_type
        self.stars_input = discord.ui.TextInput(label="星評価 (1-5)", min_length=1, max_length=1)
        self.comment_input = discord.ui.TextInput(label="コメント", style=discord.TextStyle.paragraph, min_length=5)
        self.add_item(self.stars_input)
        self.add_item(self.comment_input)

    async def on_submit(self, interaction: discord.Interaction):
        star_num = int(self.stars_input.value) if self.stars_input.value.isdigit() else 5
        # %s を使用
        bot.cursor.execute("INSERT INTO reviews (deal_id, staff_id, reviewer_id, type, stars, comment) VALUES (%s, %s, %s, %s, %s, %s)", 
                           (self.deal_id, self.staff_id, interaction.user.id, self.review_type, star_num, self.comment_input.value))
        bot.conn.commit()
        ch_id = SERVER_REVIEW_CH_ID if self.review_type == "server" else STAFF_REVIEW_CH_ID
        channel = bot.get_channel(ch_id)
        if channel:
            await channel.send(embed=discord.Embed(title=f"新着レビュー: {self.review_type}", description=f"評価: {'⭐'*star_num}\n投稿者: {interaction.user.mention}\n内容: {self.comment_input.value}"))
        await interaction.response.send_message("投稿完了！", ephemeral=True)

class PersistentFinishView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="成功", style=discord.ButtonStyle.success, custom_id="f_success")
    async def success(self, interaction: discord.Interaction, button: discord.ui.Button): await self.process(interaction, "成功")
    @discord.ui.button(label="失敗", style=discord.ButtonStyle.danger, custom_id="f_fail")
    async def fail(self, interaction: discord.Interaction, button: discord.ui.Button): await self.process(interaction, "失敗")
    async def process(self, interaction, result):
        bot.cursor.execute("INSERT INTO deals (staff_id, result) VALUES (%s, %s) RETURNING deal_id", (interaction.user.id, result))
        deal_id = bot.cursor.fetchone()[0]
        bot.conn.commit()
        await interaction.response.edit_message(content=f"結果: {result}", view=None)
        if result == "成功":
            view = discord.ui.View()
            b1, b2 = discord.ui.Button(label="サーバー評価"), discord.ui.Button(label="スタッフ評価")
            async def cb1(i): await i.response.send_modal(ReviewModal(deal_id, interaction.user.id, "server"))
            async def cb2(i): await i.response.send_modal(ReviewModal(deal_id, interaction.user.id, "staff"))
            b1.callback, b2.callback = cb1, cb2
            view.add_item(b1); view.add_item(b2)
            await interaction.followup.send("レビューをお願いします", view=view)

@bot.tree.command(name="finish", description="取引終了")
async def finish(interaction: discord.Interaction):
    await interaction.response.send_message("結果選択:", view=PersistentFinishView())

@bot.tree.command(name="profile", description="プロフィール表示")
async def profile(interaction: discord.Interaction, user: discord.Member):
    bot.cursor.execute("SELECT COUNT(*), SUM(CASE WHEN result='成功' THEN 1 ELSE 0 END) FROM deals WHERE staff_id = %s", (user.id,))
    total, success = bot.cursor.fetchone()
    total, success = total or 0, success or 0
    bot.cursor.execute("SELECT COUNT(*), AVG(stars) FROM reviews WHERE staff_id = %s AND type='staff'", (user.id,))
    rev_c, avg_s = bot.cursor.fetchone()
    score = (float(avg_s or 0)) * math.log1p(rev_c or 0) * math.log1p(total)
    embed = discord.Embed(title=f"👤 {user.display_name}", color=discord.Color.green())
    embed.add_field(name="取引数", value=f"{total}回"); embed.add_field(name="評価", value=f"★{float(avg_s or 0):.1f}"); embed.add_field(name="スコア", value=f"{score:.1f}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="view_reviews", description="レビュー閲覧")
@app_commands.choices(type=[app_commands.Choice(name="サーバー", value="server"), app_commands.Choice(name="スタッフ", value="staff")])
async def view_reviews(interaction: discord.Interaction, type: str, stars: int):
    bot.cursor.execute("SELECT stars, comment, reviewer_id FROM reviews WHERE type = %s AND stars = %s ORDER BY id DESC LIMIT 5", (type, stars))
    rows = bot.cursor.fetchall()
    if not rows: return await interaction.response.send_message("なし", ephemeral=True)
    embed = discord.Embed(title=f"星{stars}レビュー")
    for s, c, r_id in rows: embed.add_field(name=f"{'⭐'*s}", value=f"<@{r_id}>: {c}", inline=False)
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
