import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import re
import math
import io
import asyncio
import random

# ================= 設定エリア =================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1478366462144942120  

# チャンネル設定
LOG_CHANNEL_ID = 1479273188839129138      # ログ・計算データ・会話ログ
PANEL_CH_ID = 1479271849283293256         # 統計パネル
SERVER_REVIEW_CH_ID = 1479271799492710450 # サーバーレビュー公開用
STAFF_REVIEW_CH_ID = 1479125489506586735  # スタッフレビュー公開用
TICKET_PANEL_CH_ID = 1479271510995636476  # チケット発行パネル
# =============================================

# --- 1. 取引詳細入力フォーム ---
class TicketSetupModal(discord.ui.Modal, title="仲介チケット作成 - 詳細入力"):
    target_name = discord.ui.TextInput(label="取引相手のユーザー名", placeholder="例: user_name", min_length=2, max_length=32, required=True)
    trade_item = discord.ui.TextInput(label="取引内容", placeholder="例: アカウントなど", required=True)
    price = discord.ui.TextInput(label="取引価格", placeholder="例: 5,000円", required=True)
    payment = discord.ui.TextInput(label="支払い方法", placeholder="例: PayPayなど", required=True)
    memo = discord.ui.TextInput(label="備考", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        target_user = guild.get_member_named(self.target_name.value)
        
        if target_user is None:
            return await interaction.response.send_message(f"❌ 「{self.target_name.value}」が見つかりません。", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            target_user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        trade_id = random.randint(1000, 9999) # ID生成
        channel_name = f"🤝仲介-{trade_id}-{interaction.user.name}" # 名前作成

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=f"取引ID:{trade_id} | 依頼者:{interaction.user.id} | 相手:{target_user.id}"
        )

        await interaction.response.send_message(f"✅ チケットを作成しました: {channel.mention}", ephemeral=True)
        
        embed = discord.Embed(title="🤝 新規仲介依頼", color=0x3498db, timestamp=datetime.datetime.now())
        embed.add_field(name="👤 依頼者", value=interaction.user.mention, inline=True)
        embed.add_field(name="👥 取引相手", value=target_user.mention, inline=True)
        embed.add_field(name="📦 内容", value=self.trade_item.value, inline=False)
        embed.add_field(name="💰 価格", value=self.price.value, inline=True)
        embed.add_field(name="💳 支払い", value=self.payment.value, inline=True)
        if self.memo.value: embed.add_field(name="📝 備考", value=self.memo.value, inline=False)
        
        await channel.send(content=f"{interaction.user.mention} {target_user.mention}", embed=embed)

# --- 2. チケット発行ボタン ---
class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 仲介を依頼する", style=discord.ButtonStyle.primary, custom_id="persistent_ticket_button")
    async def make_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketSetupModal())

# --- 3. レビューモーダル ---
class ReviewModal(discord.ui.Modal):
    def __init__(self, staff_id, review_type):
        title = "サーバー評価" if review_type == "server" else "スタッフ評価"
        super().__init__(title=title)
        self.staff_id = staff_id
        self.review_type = review_type
        self.stars = discord.ui.TextInput(label="評価 (1-5)", placeholder="5", min_length=1, max_length=1)
        self.comment = discord.ui.TextInput(label="コメント", style=discord.TextStyle.paragraph, min_length=5)
        self.add_item(self.stars)
        self.add_item(self.comment)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.stars.value.isdigit() or not (1 <= int(self.stars.value) <= 5):
            return await interaction.response.send_message("1-5で入力してください", ephemeral=True)

        star_str = "⭐" * int(self.stars.value)
        public_embed = discord.Embed(title=f"新着{self.title}", color=discord.Color.gold())
        public_embed.add_field(name="評価", value=star_str)
        public_embed.add_field(name="投稿者", value=interaction.user.mention)
        if self.review_type == "staff": public_embed.add_field(name="対象スタッフ", value=f"<@{self.staff_id}>")
        public_embed.add_field(name="コメント", value=self.comment.value, inline=False)

        target_ch = interaction.client.get_channel(SERVER_REVIEW_CH_ID if self.review_type == "server" else STAFF_REVIEW_CH_ID)
        if target_ch: await target_ch.send(embed=public_embed)
        log_ch = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_ch: await log_ch.send(embed=public_embed)

        await interaction.response.send_message("レビューを公開しました！", ephemeral=True)

# --- 4. 終了・ログ保存View ---
class FinishView(discord.ui.View):
    def __init__(self, staff_id=None): 
        super().__init__(timeout=None)
        self.staff_id = staff_id

    @discord.ui.button(label="成功 ✅", style=discord.ButtonStyle.success, custom_id="finish_success")
    async def success(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.staff_id is None:
            self.staff_id = self.get_staff_id_from_topic(interaction.channel.topic)
        await self.process_record(interaction, "成功")

    @discord.ui.button(label="失敗 ❌", style=discord.ButtonStyle.danger, custom_id="finish_fail")
    async def fail(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.staff_id is None:
            self.staff_id = self.get_staff_id_from_topic(interaction.channel.topic)
        await self.process_record(interaction, "失敗")

    def get_staff_id_from_topic(self, topic):
        if not topic:
            return None
        match = re.search(r'依頼者:(\d+)', topic)
        return int(match.group(1)) if match else None

    async def process_record(self, interaction, result):
        await interaction.response.defer()
        log_ch = interaction.client.get_channel(LOG_CHANNEL_ID)
        
        # --- 会話ログ作成 ---
        log_data = f"取引ログ: {interaction.channel.name}\n結果: {result}\nスタッフID: {self.staff_id}\n\n"
        async for m in interaction.channel.history(limit=1000, oldest_first=True):
            log_data += f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author}: {m.content}\n"
        
        log_file = discord.File(fp=io.BytesIO(log_data.encode()), filename=f"log-{interaction.channel.name}.txt")

        # 完了記録送信
        embed = discord.Embed(
            title="🤝 取引完了記録", 
            description=f"{'✅' if result=='成功' else '❌'} 取引結果: **{result}**", 
            color=0x2ecc71 if result=="成功" else 0xe74c3c
        )
        embed.add_field(name="担当スタッフ", value=interaction.user.mention)
        embed.set_footer(text=f"Staff_ID: {self.staff_id}")
        
        if log_ch:
            await log_ch.send(embed=embed, file=log_file)
        
        await interaction.followup.send(f"記録しました: {result}")
        
        if result == "成功":
            view = discord.ui.View()
            b1 = discord.ui.Button(label="サーバーをレビュー", style=discord.ButtonStyle.primary)
            b2 = discord.ui.Button(label="スタッフをレビュー", style=discord.ButtonStyle.secondary)
            
            async def cb1(i): await i.response.send_modal(ReviewModal(self.staff_id, "server"))
            async def cb2(i): await i.response.send_modal(ReviewModal(self.staff_id, "staff"))
            
            b1.callback = cb1
            b2.callback = cb2
            view.add_item(b1)
            view.add_item(b2)
            await interaction.followup.send("評価をお願いします！", view=view)

# --- 5. Bot本体 ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(TicketLaunchView())
        self.add_view(FinishView(None))
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        self.update_panel.start()
        print("✅ コマンド同期完了")

    async def on_ready(self):
        print(f'✅ {self.user} 起動完了')
        channel = self.get_channel(TICKET_PANEL_CH_ID)
        if channel:
            already = False
            async for m in channel.history(limit=10):
                if m.author == self.user and m.embeds and "仲介チケット発行" in m.embeds[0].title:
                    already = True; break
            if not already:
                await channel.send(embed=discord.Embed(title="🎫 仲介チケット発行", description="下のボタンから作成してください。", color=0x2ecc71), view=TicketLaunchView())

    @tasks.loop(minutes=5)
    async def update_panel(self):
        channel = self.get_channel(PANEL_CH_ID)
        log_ch = self.get_channel(LOG_CHANNEL_ID)
        if not channel or not log_ch: return
        stats = {"total": 0, "success": 0, "fail": 0, "staff": {}}
        async for msg in log_ch.history(limit=1000):
            if not msg.embeds or not msg.embeds[0].title: continue
            emb = msg.embeds[0]
            if "取引完了記録" in emb.title:
                stats["total"] += 1
                if "✅" in (emb.description or ""): stats["success"] += 1
                else: stats["fail"] += 1
                try:
                    s_id = int(emb.footer.text.replace("Staff_ID: ", ""))
                    if s_id not in stats["staff"]: stats["staff"][s_id] = {"total": 0, "stars": [], "name": emb.fields[0].value}
                    stats["staff"][s_id]["total"] += 1
                except: continue
            elif "新着レビュー" in emb.title:
                try:
                    s_id = int(re.search(r'\d+', emb.fields[1].value).group())
                    if s_id in stats["staff"]: stats["staff"][s_id]["stars"].append(len(emb.fields[0].value))
                except: continue

        embed = discord.Embed(title="📊 サーバー統計パネル", color=discord.Color.blue())
        embed.add_field(name="取引総数", value=f"{stats['total']}件", inline=True)
        embed.add_field(name="成功 / 失敗", value=f"✅ {stats['success']} / ❌ {stats['fail']}", inline=True)
        ranked = sorted([{'id': k, 'score': (sum(v["stars"])/len(v["stars"]) if v["stars"] else 0) * math.log1p(len(v["stars"])) * math.log1p(v["total"])} for k, v in stats["staff"].items()], key=lambda x: x['score'], reverse=True)[:5]
        embed.add_field(name="🏆 信頼度ランキング", value="\n".join([f"{i+1}位: <@{s['id']}> ({s['score']:.1f})" for i, s in enumerate(ranked)]) or "なし", inline=False)
        async for m in channel.history(limit=10):
            if m.author == self.user and m.embeds and "統計パネル" in m.embeds[0].title:
                await m.edit(embed=embed); return
        await channel.send(embed=embed)

bot = MyBot()

@bot.tree.command(name="finish", description="取引終了")
async def finish(interaction: discord.Interaction):
    await interaction.response.send_message("結果を選択：", view=FinishView(interaction.user.id))

@bot.tree.command(name="profile", description="スタッフ実績表示")
async def profile(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer()
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    total, success, stars, recent = 0, 0, [], []
    async for msg in log_ch.history(limit=1000):
        if not msg.embeds or not msg.embeds[0].title: continue
        emb = msg.embeds[0]
        if str(user.id) in (emb.footer.text if emb.footer else "") and "取引完了記録" in emb.title:
            total += 1
            if "✅" in (emb.description or ""): success += 1
        elif ("レビュー" in emb.title or "評価" in emb.title) and any(str(user.id) in f.value for f in emb.fields):
            s_count = emb.fields[0].value.count("⭐")
            if s_count > 0:
                stars.append(s_count)
                if len(recent) < 3: recent.append(f"{'⭐'*s_count} 「{emb.fields[-1].value}」")
    
    avg = sum(stars)/len(stars) if stars else 0
    score = avg * math.log1p(len(stars)) * math.log1p(total)
    embed = discord.Embed(title=f"👤 プロフィール: {user.display_name}", color=discord.Color.green())
    embed.add_field(name="実績", value=f"累計: {total}\n成功: {success}")
    embed.add_field(name="評価", value=f"★{avg:.1f}\n({len(stars)}件)")
    embed.add_field(name="スコア", value=f"💎 {score:.1f}")
    embed.add_field(name="最新レビュー", value="\n".join(recent) or "なし", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="search_log", description="取引IDまたはユーザー名で過去のログを検索します")
async def search_log(interaction: discord.Interaction, 検索ワード: str):
    await interaction.response.defer()
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    found_logs = []
    
    async for msg in log_ch.history(limit=1000):
        if not msg.embeds: continue
        emb = msg.embeds[0]
        # ID、ユーザー名、または取引結果に検索ワードが含まれているか確認
        content_to_search = f"{emb.title} {emb.description} {emb.footer.text if emb.footer else ''}"
        if 検索ワード in content_to_search:
            found_logs.append(f"📅 {msg.created_at.strftime('%Y/%m/%d')}\n**{emb.title}**\n{emb.description}\n[ログメッセージへ飛ぶ]({msg.jump_url})")
            if len(found_logs) >= 5: break

    if not found_logs:
        return await interaction.followup.send(f"🔍 「{検索ワード}」に一致する記録は見つかりませんでした。")

    result_embed = discord.Embed(title=f"🔍 検索結果: {検索ワード}", description="\n\n".join(found_logs), color=discord.Color.blue())
    await interaction.followup.send(embed=result_embed)
bot.run(TOKEN)
