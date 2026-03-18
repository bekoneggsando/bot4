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
import json
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
        
        # --- スタッフ呼び出し設定 ---
        # あなたのサーバーの「スタッフロール」のIDに書き換えてください
        STAFF_ROLE_ID = 1478964390530121964 
        
        # チャンネルの最初にスタッフへの通知を送る
        await channel.send(f"<@&{STAFF_ROLE_ID}> 新しい仲介依頼が入りました！")
        await channel.send(content=f"{interaction.user.mention} {target_user.mention}", embed=embed)

# ==========================================
# 1. まず「Modal（入力画面）」を書く
# ==========================================
class StaffApplyModal(discord.ui.Modal, title="仲介スタッフ応募フォーム"):
    age = discord.ui.TextInput(label="年齢（または学生/社会人）", placeholder="例: 18歳 / 社会人", required=True)
    experience = discord.ui.TextInput(label="仲介経験の有無", placeholder="例: 他サーバーで10件ほど経験あり", style=discord.TextStyle.paragraph, required=True)
    time = discord.ui.TextInput(label="活動可能な時間帯", placeholder="例: 平日20時〜24時、休日は全日", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        ADMIN_ROLE_ID = 1478964284955426888 # 運営ロールID
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"スタッフ応募-{interaction.user.name}",
            overwrites=overwrites
        )

        embed = discord.Embed(title="📝 スタッフ応募届", color=discord.Color.orange())
        embed.add_field(name="応募者", value=interaction.user.mention)
        embed.add_field(name="年齢/属性", value=self.age.value)
        embed.add_field(name="経験", value=self.experience.value, inline=False)
        embed.add_field(name="時間帯", value=self.time.value, inline=False)
        
        await channel.send(content=f"<@&{ADMIN_ROLE_ID}> 新しいスタッフ応募が届きました。面接を開始してください。", embed=embed)
        await interaction.response.send_message(f"✅ 応募用チャンネルを作成しました: {channel.mention}", ephemeral=True)

# ==========================================
# 2. 次に「View（ボタン）」を書く
# ==========================================
class StaffRecruitView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="スタッフに応募する", style=discord.ButtonStyle.success, custom_id="staff_apply_button")
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaffApplyModal())

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

# --- 2. クラス本体 ---
class FinishView(discord.ui.View):
    def __init__(self, staff_id=None): 
        super().__init__(timeout=None)
        self.staff_id = staff_id

    # 称号の付け替え（古い称号を消して新しいのを付ける）
    async def update_rank(self, member, count):
        new_role_id = None
        # 現在の回数でなれる最高のランクを探す
        for threshold in sorted(RANK_ROLES.keys(), reverse=True):
            if count >= threshold:
                new_role_id = RANK_ROLES[threshold]
                break
        
        if not new_role_id: return None

        new_role = member.guild.get_role(new_role_id)
        
        # 【重要】全ての称号用IDリストを作成
        all_rank_ids = list(RANK_ROLES.values())
        # 今持っている役職の中から、称号用の役職（ただし新しい役職以外）を抜き出す
        roles_to_remove = [r for r in member.roles if r.id in all_rank_ids and r.id != new_role_id]

        # 古い称号（見習い含む）を削除
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
        
        # 新しい称号を付与
        if new_role and new_role not in member.roles:
            await member.add_roles(new_role)
            return new_role.name
        return None

    # 「成功 ✅」ボタンが押されたとき
    @discord.ui.button(label="成功 ✅", style=discord.ButtonStyle.success, custom_id="finish_success")
    async def success(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 最初に応答を「保留（考え中）」にする
        await interaction.response.defer()

        # 実績を +1 する
        count = add_achievement(interaction.user.id)
        
        # 称号を更新する（見習いからの卒業もここで行う）
        rank_name = await self.update_rank(interaction.user, count)

        # 取引ログを保存（以前の process_record を呼び出す）
        # ※process_record 内の defer() は消しておいてください！
        await self.process_record(interaction, "成功")

        # 完了メッセージを followup で送信
        msg = f"✅ 取引成功！累計実績: **{count}回**"
        if rank_name:
            msg += f"\n🎉 **称号更新！** あなたは新たに【**{rank_name}**】になりました！"
        
        await interaction.followup.send(msg)

    @discord.ui.button(label="失敗 ❌", style=discord.ButtonStyle.danger, custom_id="finish_fail")
    async def fail(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.staff_id is None:
            self.staff_id = self.get_staff_id_from_topic(interaction.channel.topic)
        await self.process_record(interaction, "失敗")

    async def update_rank(self, member, count):
        # 1. ランク判定
        new_role_id = None
        for threshold in sorted(RANK_ROLES.keys(), reverse=True):
            if count >= threshold:
                new_role_id = RANK_ROLES[threshold]
                break
        
        if not new_role_id:
            return None

        new_role = member.guild.get_role(new_role_id)
        if not new_role:
            print(f"⚠️ エラー: ID {new_role_id} の役職が見つかりません")
            return None

        # 2. ニックネーム変更（ここがチャット欄での見え方！）
        try:
            # 今の名前から余計な [称号] を一度消して、新しく付け直す
            raw_name = member.display_name
            if "]" in raw_name:
                raw_name = raw_name.split("]")[-1].strip()
            
            new_nick = f"[{new_role.name}] {raw_name}"
            
            # 32文字を超えるとエラーになるのでカット
            await member.edit(nick=new_nick[:32])
            print(f"✅ {member.name} の名前を {new_nick} に変更しました")
        except Exception as e:
            # ここでエラー内容をコンソールに出すようにします
            print(f"❌ 名前変更に失敗: {e}")

        # 3. 役職の付け替え
        if new_role not in member.roles:
            # 全ての称号用IDをリスト化して、今の役職から外す
            all_rank_ids = list(RANK_ROLES.values())
            roles_to_remove = [r for r in member.roles if r.id in all_rank_ids]
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
            
            await member.add_roles(new_role)
            return new_role.name
        return None


    
    def get_staff_id_from_topic(self, topic):
        if not topic:
            return None
        match = re.search(r'依頼者:(\d+)', topic)
        return int(match.group(1)) if match else None

    async def process_record(self, interaction, result):
        # ★ここを追記！ 今の日時を使ってIDを作成する
        trade_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # これで、下の log_data の中で trade_id が使えるようになります
        log_data = f"取引ID: {trade_id}\n取引ログ: {interaction.channel.name}\n結果: {result}\nスタッフID: {self.staff_id}\n\n"
        
        # ...残りの処理...
        log_ch = interaction.client.get_channel(LOG_CHANNEL_ID)
        
       # --- 会話ログ作成 ---
        log_data = f"取引ID: {trade_id}\n取引ログ: {interaction.channel.name}\n結果: {result}\nスタッフID: {self.staff_id}\n\n"
        
        async for m in interaction.channel.history(limit=1000, oldest_first=True):
            # メッセージ内容を書き込む
            log_data += f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author}: {m.content}\n"
            
            # --- ここから追加：画像があればURLを追記する ---
            if m.attachments:
                for attachment in m.attachments:
                    log_data += f"   📎 添付ファイルURL: {attachment.url}\n"
            # ------------------------------------------
        
        # この後、log_file = discord.File(...) と続くはずです
        
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

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(TicketLaunchView())
        self.add_view(FinishView(None))
        self.add_view(StaffRecruitView())
        
        # GUILD_ID を使用（もしエラーが出るならここを数字に書き換え）
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        
        # ループを開始
        self.update_panel.start()
        print("✅ コマンド同期 & ループ開始完了")

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
                    if s_id not in stats["staff"]: 
                        stats["staff"][s_id] = {"total": 0, "stars": [], "name": emb.fields[0].value}
                    stats["staff"][s_id]["total"] += 1
                except: continue
            elif "新着レビュー" in emb.title:
                try:
                    import re
                    s_id = int(re.search(r'\d+', emb.fields[1].value).group())
                    if s_id in stats["staff"]: 
                        stats["staff"][s_id]["stars"].append(len(emb.fields[0].value))
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

@bot.event # ここが client なら @client.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)

    # 重複を消すための大事な処理
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    
    print(f"✅ {bot.user} 起動完了")

    # チケットパネル
    channel = bot.get_channel(TICKET_PANEL_CH_ID)
    if channel:
        already = False
        async for m in channel.history(limit=10):
            if m.author == bot.user and m.embeds and "仲介チケット発行" in m.embeds[0].title:
                already = True
                break
        if not already:
            await channel.send(
                embed=discord.Embed(title="🎫 仲介チケット発行", description="下のボタンから作成してください。", color=0x2ecc71), 
                view=TicketLaunchView()
            )


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

@bot.event
async def on_message(message):
    # Bot自身のメッセージは無視
    if message.author.bot:
        return

    # チャンネル名が「🤝仲介-」で始まり、かつ画像がある場合のみ実行
    if message.channel.name.startswith("🤝仲介-") and message.attachments:
        log_ch = bot.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            for attachment in message.attachments:
                # 画像形式（jpg, png, gif, webp）かチェック
                if any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']):
                    embed = discord.Embed(
                        title=f"📸 画像ログ: {message.channel.name}",
                        description=f"送信者: {message.author.mention}\n[メッセージへ移動]({message.jump_url})",
                        color=0x3498db,
                        timestamp=message.created_at
                    )
                    embed.set_image(url=attachment.url)
                    await log_ch.send(embed=embed)

    # これを忘れると他のコマンド（/finishなど）が動かなくなるので必須
    await bot.process_commands(message)

@bot.tree.command(name="close", description="【スタッフ専用】チケットを閉じます（ログ保存後に使用）")
async def close(interaction: discord.Interaction):
    # スタッフロールを持っているか、管理者権限があるかチェック
    STAFF_ROLE_ID = 1479125489506586735 
    if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ このコマンドはスタッフのみ実行できます。", ephemeral=True)

    await interaction.response.send_message("このチャンネルを5秒後に削除します。ログの保存は忘れましたか？")
    await asyncio.sleep(5)
    await interaction.channel.delete()

# ==========================================
# 4. 一番下にコマンド（send_staff_recruit など）
# ==========================================
@bot.tree.command(name="send_staff_recruit", description="指定のチャンネルにスタッフ募集パネルを送信します")
async def send_staff_recruit(interaction: discord.Interaction):
    target_ch_id = 1478995230979260486
    channel = bot.get_channel(target_ch_id)
    
    if not channel:
        return await interaction.response.send_message("❌ 指定されたチャンネルが見つかりませんでした。", ephemeral=True)

    embed = discord.Embed(title="📢 仲介スタッフ募集", color=discord.Color.gold())
    embed.description = (
        "当サーバーでは、サーバーの規模拡大に伴い **仲介スタッフ** を募集しています。\n\n"
        "**🛠 仕事内容**\n"
        "・ユーザー同士の取引の仲介\n"
        "・取引内容の確認\n"
        "・支払い・商品の受け渡し確認\n"
        "・取引トラブルの対応\n\n"
        "**✅ 応募条件**\n"
        "・サーバールールを守れる方\n"
        "・責任を持って仲介を行える方\n"
        "・Discordを頻繁に確認できる方\n"
        "・信頼できると判断された方\n\n"
        "※詐欺防止のため **面接・審査** があります"
    )
    
    await channel.send(embed=embed, view=StaffRecruitView())
    await interaction.response.send_message(f"✅ {channel.mention} に募集パネルを送信しました。", ephemeral=True)

# ここは必ず左端（スペースなし）にする

import json

ACHIEVEMENTS_FILE = "achievements.json"

# 称号ランクの役職ID（★ここを自分のサーバーのIDに書き換えてください）
RANK_ROLES = {
    0: 1483345847847747745,   # ★「仲介見習い」のID
    5: 1478964573276209253,   # ルーキー（5回〜）
    10: 1478964697469423667,  # 公認（10回〜）
    30: 1478964755279646872,  # ベテラン（30回〜）
    100: 1483075683310632971  # 伝説（100回〜）
}

def add_achievement(user_id):
    data = {}
    if os.path.exists(ACHIEVEMENTS_FILE):
        with open(ACHIEVEMENTS_FILE, "r") as f:
            data = json.load(f)
    
    user_id_str = str(user_id)
    data[user_id_str] = data.get(user_id_str, 0) + 1
    
    with open(ACHIEVEMENTS_FILE, "w") as f:
        json.dump(data, f, indent=4)
    return data[user_id_str]

import discord
from discord import app_commands

# インテントの設定
intents = discord.Intents.default()
intents.members = True # メンバーをいじるので必須
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client) # ← これが必要です！

# --- この後に SellModal や InternalBuyView を書く ---
# --- 設定：スタッフ役職のIDを入れてください ---
STAFF_ROLE_ID = 1478964390530121964  # 仲介スタッフの役職ID
TICKET_CATEGORY_ID = 1483362870132736111           # チケットを作るカテゴリーID（任意）

# --- ゲームリストの定義 (ここから) ---
GAMES_LIST = [
    "モンスターストライク", "プロスピA", "バウンティラッシュ", "FGO",
    "ポケコロツイン(ポケツイ)", "リヴリーアイランド", "原神", "ポケモンGO",
    "VALORANT(ヴァロラント)", "フォートナイト(Fortnite)", "APEX Legends",
    "あつまれ どうぶつの森(あつ森)", "ドラクエ10(DQX)", "FF14",
    "ポケモン剣盾(ソードシールド)", "ポケモンSV(スカーレットバイオレット)"
]
# --- ゲームリストの定義 (ここまで) ---

# JSONファイル名
JSON_FILE = "learned_games.json"

def load_data():
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    # ファイルがない、または壊れている場合は初期リストを返す
    return {"official": GAMES_LIST, "pending": {}}

# --- JSONを保存する関数（これを足す！） ---
def save_data(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 1. 出品フォーム ---
class SellModal(discord.ui.Modal):
    # ① ここで game_name を受け取れるようにする
    def __init__(self, game_name):
        super().__init__(title=f"【{game_name}】出品登録")
        self.game_name = game_name # ② これを忘れるとエラーになる！

    # 入力欄の設定（ここはあなたのコードのままでOK）
    item_name = discord.ui.TextInput(label='商品名', placeholder='例：伝説スキン多数')
    price = discord.ui.TextInput(label='希望価格', placeholder='例：5000')
    pay_method = discord.ui.TextInput(label='支払い方法', placeholder='例：PayPay')

    async def on_submit(self, interaction: discord.Interaction):
        # ここで「self.game_name」を使って学習機能が動くようになります！
        data = load_data()
        
        # --- 学習ロジック ---
        if self.game_name not in data["official"]:
            count = data["pending"].get(self.game_name, 0) + 1
            if count >= 2:
                data["official"].append(self.game_name)
                if self.game_name in data["pending"]:
                    del data["pending"][self.game_name]
            else:
                data["pending"][self.game_name] = count
            save_data(data)
        # --- 追加ここまで ---

        # ここから下の Embed の title に {self.game_name} を入れるとさらに良し！
        embed = discord.Embed(title=f"📢 【{self.game_name}】アカウント販売募集", color=discord.Color.gold())
        embed.add_field(name="商品名", value=self.item_name.value, inline=False)
        embed.add_field(name="価格", value=self.price.value, inline=True)
        embed.add_field(name="支払い方法", value=self.pay_method.value, inline=True)
        embed.add_field(name="出品者", value=interaction.user.mention, inline=False)
        embed.set_footer(text="購入希望者は下のボタンを押してください")

        # 以下、以前の InternalBuyView などの送信処理へ続く...

        # 購入ボタンに情報をセット
        view = InternalBuyView(self.item_name.value, self.price.value, self.pay_method.value, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)

# --- 2. 購入ボタンとチケット自動作成 ---
class InternalBuyView(discord.ui.View):
    def __init__(self, item, price, pay, seller):
        super().__init__(timeout=None)
        self.item = item
        self.price = price
        self.pay = pay
        self.seller = seller

    @discord.ui.button(label="購入を希望する 🙋", style=discord.ButtonStyle.primary, custom_id="buy_int")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        buyer = interaction.user
        guild = interaction.guild

        # 自分自身の出品は買えないようにする
        if buyer.id == self.seller.id:
            return await interaction.response.send_message("自分の出品は購入できません！", ephemeral=True)

        await interaction.response.send_message("取引チケットを作成しています...", ephemeral=True)

        # 【重要】権限設定：出品者、購入者、スタッフ以外は見れない
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            buyer: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            self.seller: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # スタッフ役職も入れる
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # チャンネル作成
        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        ticket_channel = await guild.create_text_channel(
            name=f"🤝-{buyer.name}",
            category=category,
            overwrites=overwrites,
            topic=f"出品者: {self.seller.name} / 購入者: {buyer.name}"
        )

        # チケット内での案内メッセージ
        info_embed = discord.Embed(title="🤝 取引チケット作成完了", color=discord.Color.blue(), description="スタッフが来るまでお待ちください。")
        info_embed.add_field(name="商品名", value=self.item)
        info_embed.add_field(name="価格", value=self.price)
        info_embed.add_field(name="出品者", value=self.seller.mention)
        info_embed.add_field(name="購入者", value=buyer.mention)
        
        # ここで以前作った「成功/失敗ボタン(FinishView)」を出す
        # ※FinishView()はあなたのコードにあるクラス名に合わせてください
        await ticket_channel.send(
            content=f"{self.seller.mention} {buyer.mention} {staff_role.mention if staff_role else ''}",
            embed=info_embed, 
        )

# ここを bot.tree に変える
@bot.tree.command(name="sell", description="ゲーム名を選んで出品します")
async def sell(interaction: discord.Interaction, game_name: str):
    # 【ここを修正！】カッコの中に game_name を入れる
    await interaction.response.send_modal(SellModal(game_name=game_name))


bot.run(TOKEN)

