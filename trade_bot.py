import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import re
import math

# ================= 設定エリア =================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1478366462144942120  

# チャンネル設定
LOG_CHANNEL_ID = 1479273188839129138      # すべての計算用データが集まる場所（非公開推奨）
PANEL_CH_ID = 1479271849283293256         # 統計パネル
SERVER_REVIEW_CH_ID = 1479271799492710450 # サーバーレビュー公開用
STAFF_REVIEW_CH_ID = 1479125489506586735  # スタッフレビュー公開用
# =============================================

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        self.update_panel.start()

    async def on_ready(self):
        print(f'✅ ログイン完了: {self.user}')

    @tasks.loop(minutes=5)
    async def update_panel(self):
        """統計パネル更新ロジック（LOG_CHANNELから集計）"""
        channel = self.get_channel(PANEL_CH_ID)
        log_ch = self.get_channel(LOG_CHANNEL_ID)
        if not channel or not log_ch: return

        stats = {"total": 0, "success": 0, "fail": 0, "staff": {}}
        async for msg in log_ch.history(limit=1000):
            # 埋め込みメッセージがない場合は飛ばす
            if not msg.embeds: continue
            
            emb = msg.embeds[0]
            
            # --- 🛡️ ここが修正の核心！ ---
            # タイトルがない（None）メッセージを無視するようにします
            if not emb.title: 
                continue 
            # ---------------------------

            if "取引完了記録" in emb.title:
                stats["total"] += 1
                # 説明文（description）も空の場合に備えて安全に処理
                desc = emb.description or ""
                res = "成功" if "✅" in desc else "失敗"
                
                if res == "成功": stats["success"] += 1
                else: stats["fail"] += 1
                
                try:
                    # フッターやフィールドのデータも空でないか確認しながら取得
                    footer_text = emb.footer.text if emb.footer else ""
                    s_id_str = footer_text.replace("Staff_ID: ", "")
                    if s_id_str.isdigit():
                        s_id = int(s_id_str)
                        if s_id not in stats["staff"]:
                            # フィールド[0]がない場合も考慮
                            s_name = emb.fields[0].value if emb.fields else "不明なスタッフ"
                            stats["staff"][s_id] = {"total": 0, "stars": [], "name": s_name}
                        stats["staff"][s_id]["total"] += 1
                except Exception as e:
                    print(f"集計スキップ: {e}")
                    continue
            
            elif "新着レビュー" in emb.title:
                try:
                    # フィールドが足りない場合に備えてチェック
                    if len(emb.fields) >= 2:
                        s_id_match = re.search(r'\d+', emb.fields[1].value)
                        if s_id_match:
                            s_id = int(s_id_match.group())
                            stars = len(emb.fields[0].value)
                            if s_id in stats["staff"]:
                                stats["staff"][s_id]["stars"].append(stars)
                except:
                    continue

        # --- (この下にパネルを作成して送信するコードが続きます) ---

        embed = discord.Embed(title="📊 サーバー統計パネル", color=discord.Color.blue())
        embed.add_field(name="取引総数", value=f"{stats['total']}件", inline=True)
        embed.add_field(name="成功 / 失敗", value=f"✅ {stats['success']} / ❌ {stats['fail']}", inline=True)
        
        ranked_list = []
        for s_id, data in stats["staff"].items():
            avg = sum(data["stars"]) / len(data["stars"]) if data["stars"] else 0
            score = avg * math.log1p(len(data["stars"])) * math.log1p(data["total"])
            ranked_list.append({'id': s_id, 'score': score})
        
        trust_rank = sorted(ranked_list, key=lambda x: x['score'], reverse=True)[:5]
        trust_text = "\n".join([f"{i+1}位: <@{s['id']}> (Score: {s['score']:.1f})" for i, s in enumerate(trust_rank)]) or "なし"
        embed.add_field(name="🏆 信頼度ランキング", value=trust_text, inline=False)
        
        async for m in channel.history(limit=10):
            if m.author == self.user and m.embeds and "統計パネル" in m.embeds[0].title:
                await m.edit(embed=embed)
                return
        await channel.send(embed=embed)

# --- レビューモーダル ---
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
        
        # 1. 公開用embed
        public_embed = discord.Embed(title=f"新着{self.title}", color=discord.Color.gold())
        public_embed.add_field(name="評価", value=star_str)
        public_embed.add_field(name="投稿者", value=interaction.user.mention)
        if self.review_type == "staff":
            public_embed.add_field(name="対象スタッフ", value=f"<@{self.staff_id}>")
        public_embed.add_field(name="コメント", value=self.comment.value, inline=False)

        # 2. 公開チャンネルへ送信
        target_ch_id = SERVER_REVIEW_CH_ID if self.review_type == "server" else STAFF_REVIEW_CH_ID
        target_ch = interaction.client.get_channel(target_ch_id)
        if target_ch: await target_ch.send(embed=public_embed)

        # 3. 集計用ログチャンネルへも送信（計算用データ）
        log_ch = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_ch: await log_ch.send(embed=public_embed)

        await interaction.response.send_message("レビューを公開しました！", ephemeral=True)

# --- 共通のFinishロジック ---
class FinishView(discord.ui.View):
    def __init__(self, staff_id):
        super().__init__(timeout=None)
        self.staff_id = staff_id

    @discord.ui.button(label="成功", style=discord.ButtonStyle.success)
    async def success(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.record(interaction, "成功")

    @discord.ui.button(label="失敗", style=discord.ButtonStyle.danger)
    async def fail(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.record(interaction, "失敗")

    async def record(self, interaction, result):
        log_ch = interaction.client.get_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(title="🤝 取引完了記録", description=f"{'✅' if result=='成功' else '❌'} 取引結果: **{result}**", color=0x2ecc71 if result=="成功" else 0xe74c3c)
        embed.add_field(name="担当スタッフ", value=interaction.user.mention)
        embed.set_footer(text=f"Staff_ID: {self.staff_id}")
        await log_ch.send(embed=embed)
        
        await interaction.response.edit_message(content=f"記録しました: {result}", view=None)
        if result == "成功":
            view = discord.ui.View()
            b1 = discord.ui.Button(label="サーバーをレビュー", style=discord.ButtonStyle.primary)
            b2 = discord.ui.Button(label="スタッフをレビュー", style=discord.ButtonStyle.secondary)
            async def cb1(i): await i.response.send_modal(ReviewModal(self.staff_id, "server"))
            async def cb2(i): await i.response.send_modal(ReviewModal(self.staff_id, "staff"))
            b1.callback = cb1; b2.callback = cb2
            view.add_item(b1); view.add_item(b2)
            await interaction.followup.send("利用者様はこちらから評価をお願いします！", view=view)

bot = MyBot()

@bot.tree.command(name="finish", description="取引終了")
async def finish(interaction: discord.Interaction):
    await interaction.response.send_message("結果を選択：", view=FinishView(interaction.user.id))



@bot.tree.command(name="view_reviews", description="評価を検索して表示します")
@app_commands.choices(対象=[
    app_commands.Choice(name="サーバー評価", value="server"),
    app_commands.Choice(name="スタッフ評価", value="staff")
])
async def view_reviews(interaction: discord.Interaction, 対象: str, 星の数: int, スタッフ: discord.Member = None):
    if not (1 <= 星の数 <= 5):
        return await interaction.response.send_message("星は1〜5の間で指定してください。", ephemeral=True)

    await interaction.response.defer()
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if not log_ch:
        return await interaction.followup.send("ログチャンネルが見つかりません。")

    found_reviews = []
    target_stars = "⭐" * 星の数
    # タイトルのキーワード設定
    target_keyword = "サーバー" if 対象 == "server" else "スタッフ"

    async for msg in log_ch.history(limit=1000):
        if not msg.embeds:
            continue
        
        emb = msg.embeds[0]
        
        # 🛡️ エラー防止：タイトルがない場合は飛ばす
        if not emb.title:
            continue

        # 1. 「レビュー」または「評価」という文字が含まれ、かつ「対象（サーバー/スタッフ）」が含まれるか
        if ("レビュー" in emb.title or "評価" in emb.title) and target_keyword in emb.title:
            
            # 2. 星の数が一致するか
            if len(emb.fields) >= 1 and target_stars in emb.fields[0].value:
                
                # 3. スタッフ指定がある場合、そのスタッフのIDが含まれているか
                if 対象 == "staff" and スタッフ:
                    # フィールド[1]に対象スタッフのメンションまたはIDがあるかチェック
                    if len(emb.fields) >= 2 and str(スタッフ.id) not in emb.fields[1].value:
                        continue # 指定スタッフと違う場合はスキップ

                # 表示用データの抽出
                reviewer = "不明"
                if len(emb.fields) >= 2:
                    reviewer = emb.fields[1].value
                
                comment = "コメントなし"
                if len(emb.fields) >= 3:
                    comment = emb.fields[2].value
                elif emb.description: # フィールドにない場合descriptionを探す
                    comment = emb.description

                found_reviews.append(f"👤 **投稿者**: {reviewer}\n**評価**: {target_stars}\n💬 **内容**: {comment}")
                
                if len(found_reviews) >= 5: # 最大5件
                    break

    if not found_reviews:
        staff_name = f" ({スタッフ.display_name})" if スタッフ else ""
        return await interaction.followup.send(f"条件に合う{target_keyword}評価{staff_name}は見つかりませんでした。")

    result_text = f"🔍 **{target_keyword}の評価検索結果（星{星の数}）**\n\n" + "\n\n---\n\n".join(found_reviews)
    
    if len(result_text) > 2000:
        result_text = result_text[:1990] + "..."

    await interaction.followup.send(result_text)

# --- この下に bot.run(TOKEN) が来るようにする ---

@bot.tree.command(name="profile", description="スタッフの実績と最近のレビューを表示します")
async def profile(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer()
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    
    if not log_ch:
        return await interaction.followup.send("⚠️ ログチャンネルが設定されていないか、見つかりません。")

    total, success, stars = 0, 0, []
    recent_comments = []
    
    # 直近1000件のログをスキャン
    async for msg in log_ch.history(limit=1000):
        if not msg.embeds:
            continue
        
        emb = msg.embeds[0]
        
        # エラー防止：タイトルやフッターがない場合はスキップ
        if not emb.title or not emb.footer or not emb.footer.text:
            continue

        # 1. 取引実績の集計 (タイトルに「取引完了記録」が含まれ、フッターにスタッフIDがある)
        if "取引完了記録" in emb.title and str(user.id) in emb.footer.text:
            total += 1
            desc = emb.description or ""
            if "✅" in desc:
                success += 1
        
        # 2. スタッフレビューの集計 (タイトルに「スタッフ」と「レビュー/評価」が含まれる)
        elif "スタッフ" in emb.title and ("レビュー" in emb.title or "評価" in emb.title):
            # フィールド[1]に対象スタッフのIDが含まれているか
            if len(emb.fields) >= 2 and str(user.id) in emb.fields[1].value:
                # 星評価を取得
                star_val = emb.fields[0].value or ""
                stars.append(len(star_val))
                
                # 最新3件のコメントを保存
                if len(recent_comments) < 3:
                    # コメントはフィールド[2]またはdescriptionから取得
                    comment = "なし"
                    if len(emb.fields) >= 3:
                        comment = emb.fields[2].value
                    elif emb.description:
                        comment = emb.description
                    
                    recent_comments.append(f"{star_val} 「{comment}」")

    # 統計計算
    avg_stars = sum(stars) / len(stars) if stars else 0
    # 信頼スコア計算 (対数を使って実績が多いほど加点)
    trust_score = avg_stars * math.log1p(len(stars)) * math.log1p(total)
    success_rate = (success / total * 100) if total > 0 else 0

    # プロフィールEmbed作成
    embed = discord.Embed(
        title=f"👤 スタッフプロフィール: {user.display_name}",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now()
    )
    
    embed.add_field(name="📦 仲介実績", value=f"累計: **{total}**回\n成功: **{success}**回", inline=True)
    embed.add_field(name="⭐ 平均評価", value=f"**★{avg_stars:.1f}**\n({len(stars)}件のレビュー)", inline=True)
    embed.add_field(name="💎 信頼スコア", value=f"**{trust_score:.1f}**", inline=True)
    
    # レビューコメント欄
    review_display = "\n".join(recent_comments) if recent_comments else "レビューはまだありません。"
    embed.add_field(name="💬 最近のレビューコメント", value=review_display, inline=False)
    
    embed.set_footer(text=f"仲介成功率: {success_rate:.1f}%")
    
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)

    await interaction.followup.send(embed=embed)

bot.run(TOKEN)
