import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import math
import datetime

# ================= 設定エリア =================
# Railwayの「Variables」で DISCORD_TOKEN という名前で値を設定してください
TOKEN = os.getenv('DISCORD_TOKEN')

# 以下のIDは、あなたのサーバーのものに書き換えてください
GUILD_ID = 1478366462144942120          # サーバーID
SERVER_REVIEW_CH_ID = 1479271799492710450  # サーバーレビュー用
STAFF_REVIEW_CH_ID = 1479125489506586735   # スタッフレビュー用
PANEL_CH_ID = 1479271849283293256          # 統計パネル用
# =============================================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = sqlite3.connect('mediation.db')
        self.cursor = self.db.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS deals (
            deal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER,
            result TEXT,
            timestamp DATETIME
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER,
            staff_id INTEGER,
            reviewer_id INTEGER,
            type TEXT,
            stars INTEGER,
            comment TEXT
        )''')
        self.db.commit()

    async def setup_hook(self):
        # 1. 永続的なボタン（View）を登録
        self.add_view(PersistentFinishView())
        
        # 2. サーバー（ギルド）に対してコマンドを強制同期
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        
        # 3. 統計パネルのループを開始
        self.update_panel.start()
        print(f"Server ID: {GUILD_ID} にコマンドを同期しました")

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        try:
            await self.refresh_stats_panel()
            print("統計パネルの初回更新が完了しました。")
        except Exception as e:
            print(f"パネル更新中にエラーが発生しました: {e}")

    @tasks.loop(minutes=5)
    async def update_panel(self):
        await self.refresh_stats_panel()

    async def refresh_stats_panel(self):
        channel = bot.get_channel(PANEL_CH_ID)
        if not channel:
            print(f"警告: チャンネル(ID:{PANEL_CH_ID})が見つかりません。")
            return

        self.cursor.execute("SELECT COUNT(*), SUM(CASE WHEN result='成功' THEN 1 ELSE 0 END), SUM(CASE WHEN result='失敗' THEN 1 ELSE 0 END) FROM deals")
        total, success, fail = self.cursor.fetchone()
        total, success, fail = total or 0, success or 0, fail or 0
        
        now = datetime.datetime.now()
        this_month = now.strftime('%Y-%m')
        self.cursor.execute("SELECT COUNT(*) FROM deals WHERE strftime('%Y-%m', timestamp) = ?", (this_month,))
        month_count = self.cursor.fetchone()[0]

        embed = discord.Embed(title="📊 サーバー統計パネル", color=discord.Color.blue())
        embed.add_field(name="取引総数", value=f"{total}件", inline=True)
        embed.add_field(name="成功数", value=f"✅ {success}", inline=True)
        embed.add_field(name="失敗数", value=f"❌ {fail}", inline=True)
        embed.add_field(name="今月の取引", value=f"{month_count}件", inline=True)

        self.cursor.execute("""
            SELECT d.staff_id, 
                   COUNT(d.deal_id) as total_deals,
                   (SELECT COUNT(*) FROM reviews r WHERE r.staff_id = d.staff_id AND r.type='staff') as review_count,
                   (SELECT AVG(stars) FROM reviews r WHERE r.staff_id = d.staff_id AND r.type='staff') as avg_stars
            FROM deals d GROUP BY d.staff_id
        """)
        staff_data = self.cursor.fetchall()
        
        ranked_list = []
        for s_id, t_deals, r_count, a_stars in staff_data:
            a_stars = a_stars or 0
            score = a_stars * math.log1p(r_count) * math.log1p(t_deals)
            ranked_list.append({'id': s_id, 'score': score, 'deals': t_deals, 'stars': a_stars, 'revs': r_count})
        
        trust_rank = sorted(ranked_list, key=lambda x: x['score'], reverse=True)[:5]
        trust_text = "\n".join([f"{i+1}位: <@{s['id']}> (Score: {s['score']:.1f})" for i, s in enumerate(trust_rank)]) or "データなし"
        embed.add_field(name="🏆 信頼度ランキング", value=trust_text, inline=False)

        deal_rank = sorted(ranked_list, key=lambda x: x['deals'], reverse=True)[:5]
        deal_text = "\n".join([f"{i+1}位: <@{s['id']}> ({s['deals']}件)" for i, s in enumerate(deal_rank)]) or "データなし"
        embed.add_field(name="📈 取引数ランキング", value=deal_text, inline=False)
        embed.set_footer(text=f"最終更新: {now.strftime('%Y-%m-%d %H:%M:%S')}")

        last_msg = None
        async for message in channel.history(limit=5):
            if message.author == self.user:
                last_msg = message
                break
        
        if last_msg:
            await last_msg.edit(embed=embed)
        else:
            await channel.send(embed=embed)

bot = MyBot()

# --- レビューモーダル ---
class ReviewModal(discord.ui.Modal):
    def __init__(self, deal_id, staff_id, review_type):
        title = "サーバーレビュー" if review_type == "server" else "スタッフレビュー"
        super().__init__(title=title)
        self.deal_id = deal_id
        self.staff_id = staff_id
        self.review_type = review_type

        self.stars_input = discord.ui.TextInput(label="星評価 (1-5)", placeholder="5", min_length=1, max_length=1)
        self.comment_input = discord.ui.TextInput(label="コメント", style=discord.TextStyle.paragraph, min_length=5)
        self.add_item(self.stars_input)
        self.add_item(self.comment_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.stars_input.value.isdigit() or not (1 <= int(self.stars_input.value) <= 5):
            return await interaction.response.send_message("評価は1〜5の数字で入力してください。", ephemeral=True)
        
        star_num = int(self.stars_input.value)
        
        bot.cursor.execute("INSERT INTO reviews (deal_id, staff_id, reviewer_id, type, stars, comment) VALUES (?, ?, ?, ?, ?, ?)",
                           (self.deal_id, self.staff_id, interaction.user.id, self.review_type, star_num, self.comment_input.value))
        bot.db.commit()

        ch_id = SERVER_REVIEW_CH_ID if self.review_type == "server" else STAFF_REVIEW_CH_ID
        channel = bot.get_channel(ch_id)
        if channel:
            embed = discord.Embed(title=f"新着{self.title}", color=discord.Color.gold())
            embed.add_field(name="評価", value="⭐" * star_num)
            embed.add_field(name="投稿者", value=interaction.user.mention)
            if self.review_type == "staff":
                embed.add_field(name="対象スタッフ", value=f"<@{self.staff_id}>")
            embed.add_field(name="コメント", value=self.comment_input.value, inline=False)
            await channel.send(embed=embed)

        await interaction.response.send_message("レビューを投稿しました！", ephemeral=True)

# --- 取引終了ボタン ---
class PersistentFinishView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="成功", style=discord.ButtonStyle.success, custom_id="finish_success")
    async def success(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_finish(interaction, "成功")

    @discord.ui.button(label="失敗", style=discord.ButtonStyle.danger, custom_id="finish_fail")
    async def fail(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_finish(interaction, "失敗")

    async def process_finish(self, interaction, result):
        bot.cursor.execute("INSERT INTO deals (staff_id, result, timestamp) VALUES (?, ?, ?)",
                           (interaction.user.id, result, datetime.datetime.now()))
        deal_id = bot.cursor.lastrowid
        bot.db.commit()

        await interaction.response.edit_message(content=f"取引を「{result}」で記録しました。", view=None)

        if result == "成功":
            view = discord.ui.View()
            btn_server = discord.ui.Button(label="サーバーをレビュー", style=discord.ButtonStyle.primary)
            btn_staff = discord.ui.Button(label="スタッフをレビュー", style=discord.ButtonStyle.secondary)
            
            # ↓ ここに def をしっかり追加しました
            async def server_callback(i: discord.Interaction):
                if i.user.id == interaction.user.id:
                    return await i.response.send_message("自分自身はレビューできません。", ephemeral=True)
                await i.response.send_modal(ReviewModal(deal_id, interaction.user.id, "server"))

            async def staff_callback(i: discord.Interaction):
                if i.user.id == interaction.user.id:
                    return await i.response.send_message("自分自身はレビューできません。", ephemeral=True)
                await i.response.send_modal(ReviewModal(deal_id, interaction.user.id, "staff"))

            btn_server.callback = server_callback
            btn_staff.callback = staff_callback
            view.add_item(btn_server)
            view.add_item(btn_staff)
            
            await interaction.followup.send("レビューをお願いします！", view=view)

# --- スラッシュコマンド ---

@bot.tree.command(name="finish", description="取引終了")
async def finish(interaction: discord.Interaction):
    await interaction.response.send_message("取引結果を選択してください：", view=PersistentFinishView())

@bot.tree.command(name="profile", description="スタッフプロフィール表示")
async def profile(interaction: discord.Interaction, user: discord.Member):
    bot.cursor.execute("""
        SELECT 
            COUNT(*), 
            SUM(CASE WHEN result='成功' THEN 1 ELSE 0 END),
            SUM(CASE WHEN result='失敗' THEN 1 ELSE 0 END)
        FROM deals WHERE staff_id = ?
    """, (user.id,))
    total, success, fail = bot.cursor.fetchone()
    total, success, fail = total or 0, success or 0, fail or 0
    
    bot.cursor.execute("SELECT COUNT(*), AVG(stars) FROM reviews WHERE staff_id = ? AND type='staff'", (user.id,))
    rev_count, avg_stars = bot.cursor.fetchone()
    rev_count, avg_stars = rev_count or 0, avg_stars or 0
    
    rate = (success / total * 100) if total > 0 else 0
    score = avg_stars * math.log1p(rev_count) * math.log1p(total)

    embed = discord.Embed(title=f"👤 スタッフプロフィール: {user.display_name}", color=discord.Color.green())
    embed.add_field(name="総取引数", value=f"{total}回", inline=True)
    embed.add_field(name="成功 / 失敗", value=f"✅{success} / ❌{fail}", inline=True)
    embed.add_field(name="成功率", value=f"{rate:.1f}%", inline=True)
    embed.add_field(name="平均評価", value=f"★{avg_stars:.1f}", inline=True)
    embed.add_field(name="レビュー数", value=f"{rev_count}件", inline=True)
    embed.add_field(name="信用スコア", value=f"{score:.1f}", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="view_reviews", description="指定した星の数のレビューを表示")
@app_commands.choices(type=[
    app_commands.Choice(name="サーバーレビュー", value="server"),
    app_commands.Choice(name="スタッフレビュー", value="staff")
])
async def view_reviews(interaction: discord.Interaction, type: str, stars: int):
    if not (1 <= stars <= 5):
        return await interaction.response.send_message("星は1〜5で指定してください。", ephemeral=True)

    bot.cursor.execute("SELECT stars, comment, reviewer_id FROM reviews WHERE type = ? AND stars = ? ORDER BY id DESC LIMIT 5", (type, stars))
    rows = bot.cursor.fetchall()
    
    if not rows:
        return await interaction.response.send_message(f"星{stars}のレビューは見つかりませんでした。", ephemeral=True)
    
    embed = discord.Embed(title=f"🔍 星{stars}のレビュー一覧 ({'サーバー' if type == 'server' else 'スタッフ'})", color=discord.Color.orange())
    for s, c, r_id in rows:
        embed.add_field(name=f"評価: {'⭐'*s}", value=f"内容: {c}\n投稿者: <@{r_id}>", inline=False)
    
    await interaction.response.send_message(embed=embed)

bot.run("TOKEN")
