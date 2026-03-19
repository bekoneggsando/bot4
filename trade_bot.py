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

# --- チャンネル設定 ---
LOG_CHANNEL_ID = 1479273188839129138      # ログ・計算データ・会話ログ
PANEL_CH_ID = 1479271849283293256         # 統計パネル
SERVER_REVIEW_CH_ID = 1479271799492710450 # サーバーレビュー公開用
STAFF_REVIEW_CH_ID = 1479125489506586735  # スタッフレビュー公開用
TICKET_PANEL_CH_ID = 1479271510995636476  # チケット発行パネル
TICKET_CATEGORY_ID = 1483362870132736111  # チケットを作るカテゴリーID
STAFF_RECRUIT_CH_ID = 1478995230979260486 # スタッフ募集パネルを置くチャンネル
FORUM_CHANNEL_ID = 1483803418085691522
REPORT_CATEGORY_ID = 1479272198199050334  # 通報用
BUG_CATEGORY_ID = 1478923553347993782     # 不具合報告用

# --- 役職設定 ---
STAFF_ROLE_ID = 1478964390530121964       # 仲介スタッフ役職
ADMIN_ROLE_ID = 1478964284955426888       # 運営役職

# --- 称号ランク設定 ---
RANK_ROLES = {
    0: 1483345847847747745,   # 仲介見習い
    5: 1478964573276209253,   # ルーキー（5回〜）
    10: 1478964697469423667,  # 公認（10回〜）
    30: 1478964755279646872,  # ベテラン（30回〜）
    100: 1483075683310632971  # 伝説（100回〜）
}

# --- ファイル・リスト設定 ---
ACHIEVEMENTS_FILE = "achievements.json"
JSON_FILE = "learned_games.json"
GAMES_LIST = [
    # --- PC・コンソール / 大型タイトル ---
    "APEX Legends", "VALORANT(ヴァロラント)", "フォートナイト(Fortnite)", "モンハンワイルズ(MHWs)",
    "モンハンナウ(Monster Hunter Now)", "MHST3(モンハンストーリーズ3)", "ELDEN RING(エルデンリング)",
    "poe(Path of Exile)", "PoE2(Path of Exile 2)", "ディアブロ4", "タルコフ(EFT)",
    "OW2(オーバーウォッチ2)", "LoL(リーグオブレジェンド)", "デルタフォース(Delta Force)",
    "ASA(ARK Survival Ascended)", "ARK Survival Evolved", "GTAオンライン", "Fallout76",
    "Warframe", "PSO2NGS", "ブルプロ(スタレゾ)", "ARC Raiders", "仁王3",
    "サカつく2026", "FIFA26(EA SPORTS FC26)", "イーフト(eFootball 2026)",
    "あつ森(あつまれどうぶつの森)", "ポケモンSV", "ポケモン剣盾", "ポケモンZA",
    "ポケモンBDSP(ダイパリメイク)", "ドラクエ10(DQX)", "FF14", "FF11",
    "バイオハザード レクイエム", "Steal a Brainrot",

    # --- スマホゲーム / ブラウザ・DMM ---
    "モンスト(モンスターストライク)", "パズドラ(パズル＆ドラゴンズ)", "プロスピA(プロ野球スピリッツA)",
    "バウンティ(ワンピース バウンティラッシュ)", "トレクル(ワンピース)", "ドッカンバトル",
    "ドラゴンボール レジェンズ", "原神(Genshin Impact)", "崩壊:スターレイル", "ゼンゼロ(ゼンレスゾーンゼロ)",
    "鳴潮(Wuthering Waves)", "ブルアカ(ブルーアーカイブ)", "学マス(学園アイドルマスター)",
    "メガニケ(勝利の女神:NIKKE)", "ウマ娘 プリティーダービー", "FGO(Fate/Grand Order)",
    "ファンパレ(呪術廻戦)", "まどドラ(まどかマギカ)", "アークナイツ", "エンドフィールド",
    "プロセカ(プロジェクトセカイ)", "マスターデュエル(遊戯王)", "ポケモンGO",
    "ポケポケ(ポケモンTCGポケット)", "ぽこポケ", "DQタクト(ドラクエタクト)",
    "妖怪ウォッチ ぷにぷに", "にゃんこ大戦争", "ツムツム", "ポケコロ", "ポケコロツイン",
    "リヴリーアイランド", "トーラムオンライン", "メイプルストーリー", "メイプルストーリーM",
    "RO(ラグナロクオンライン)", "アラド戦記", "テイルズウィーバー(TW)", "RED STONE",
    "千年戦争アイギス", "御城プロジェクト:RE", "戦国IXA", "とうらぶ(刀剣乱舞)",
    "グラブル(グランブルーファンタジー)", "サモンズボード", "ポコダン", "コトダマン",
    "グラクロ(七つの大罪)", "まおりゅう(転スラ)", "カゲマス(陰の実力者)", "ウィズダフネ",
    "エレスト", "オクトラ(大陸の覇者)", "あやらぶ(あやかしランブル)", "ミナシゴノシゴト",
    "オトギフロンティア", "スイメド", "チョコラン", "ハンゲ", "ロブロックス(ROBLOX)",
    "てんまお(転職魔王)", "剣と魔法のログレス", "ジョジョ オラドラ", "シャドバビヨンド(WB)"
]
# =============================================

# ================= データ管理関数 =================
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

def load_data():
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"official": GAMES_LIST, "pending": {}}

def save_data(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ================= UIクラス (Modal / View) =================

# --- 仲介チケット詳細入力 ---
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
        
        trade_id = random.randint(1000, 9999)
        channel_name = f"🤝仲介-{trade_id}-{interaction.user.name}"

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
        
        await channel.send(f"<@&{STAFF_ROLE_ID}> 新しい仲介依頼が入りました！")
        await channel.send(content=f"{interaction.user.mention} {target_user.mention}", embed=embed)

class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 仲介を依頼する", style=discord.ButtonStyle.primary, custom_id="persistent_ticket_button")
    async def make_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketSetupModal())


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

        # 1. 自分の出品は買えないようにする
        if buyer.id == self.seller.id:
            return await interaction.response.send_message("自分の出品は購入できません！", ephemeral=True)

        # 2. 【重要】まず最初に応答を「保留」にする（タイムアウト対策）
        await interaction.response.defer(ephemeral=True)

        try:
            # 3. ボタンとEmbedの見た目を更新（売約済み状態へ）
            button.disabled = True
            button.label = f"売約済み (購入者: {buyer.name})"
            button.style = discord.ButtonStyle.secondary

            if interaction.message.embeds:
                embed = interaction.message.embeds[0]
                embed.color = discord.Color.light_gray()
                embed.title = f"【売約済み】{embed.title}"
                await interaction.message.edit(embed=embed, view=self)
            else:
                await interaction.message.edit(view=self)

            # 4. 【フォーラム専用】タグを「売約済み」に変更する
            if isinstance(interaction.channel, discord.Thread):
                thread = interaction.channel
                forum = thread.parent
                # Discord側で作った「売約済み」という名前のタグを探す
                sold_tag = discord.utils.get(forum.available_tags, name="売約済み")
                if sold_tag:
                    # 既存のタグを消して「売約済み」だけにする（または追加する場合はリストに加える）
                    await thread.edit(applied_tags=[sold_tag])

            # 5. 取引チケット（チャンネル）作成処理
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                buyer: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
                self.seller: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            staff_role = guild.get_role(STAFF_ROLE_ID)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            category = guild.get_channel(TICKET_CATEGORY_ID)
            ticket_channel = await guild.create_text_channel(
                name=f"🤝-{buyer.name}",
                category=category,
                overwrites=overwrites,
                topic=f"出品者: {self.seller.name} / 購入者: {buyer.name}"
            )

            # 6. チケット内での案内
            info_embed = discord.Embed(title="🤝 取引チケット作成完了", color=discord.Color.blue(), description="スタッフが来るまでお待ちください。")
            info_embed.add_field(name="商品名", value=self.item)
            info_embed.add_field(name="価格", value=self.price)
            info_embed.add_field(name="出品者", value=self.seller.mention)
            info_embed.add_field(name="購入者", value=buyer.mention)
            
            await ticket_channel.send(
                content=f"{self.seller.mention} {buyer.mention} {staff_role.mention if staff_role else ''}",
                embed=info_embed, 
            )

            # 7. 完了報告
            await interaction.followup.send(f"✅ 取引チケットを作成しました！ {ticket_channel.mention}", ephemeral=True)

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            await interaction.followup.send("❌ 処理中にエラーが発生しました。設定（タグ名やカテゴリID）を確認してください。", ephemeral=True)

class SellModal(discord.ui.Modal):
    def __init__(self, game_name, images=None):
        super().__init__(title="【フォーラム】出品登録")
        self.game_name = game_name
        self.images = images or []

    item_name = discord.ui.TextInput(label='商品名', placeholder='例：伝説スキン多数', max_length=50)
    price = discord.ui.TextInput(label='希望価格', placeholder='例：5000')
    pay_method = discord.ui.TextInput(label='支払い方法', placeholder='例：PayPay')
    description = discord.ui.TextInput(
        label='詳細説明', 
        style=discord.TextStyle.paragraph, 
        placeholder='商品の詳細や注意点を記入してください', 
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        forum_channel = interaction.guild.get_channel(FORUM_CHANNEL_ID)
        if not isinstance(forum_channel, discord.ForumChannel):
            return await interaction.followup.send("❌ フォーラムチャンネルの設定ミスです。", ephemeral=True)

        # --- 【新機能】タグの自動判定 ---
        applied_tags = []
        # フォーラムに設定されている既存のタグをループで確認
        for tag in forum_channel.available_tags:
            # ゲーム名と完全に一致するタグがあれば追加
            if tag.name == self.game_name:
                applied_tags.append(tag)
                break
        # -------------------------------

        # メインEmbedの作成
        embed = discord.Embed(title=f"📢 出品情報", color=discord.Color.gold())
        embed.add_field(name="🎮 ゲーム", value=self.game_name, inline=True)
        embed.add_field(name="💰 価格", value=f"{self.price.value}円", inline=True)
        embed.add_field(name="💳 支払い", value=self.pay_method.value, inline=True)
        
        if self.images:
            embed.set_image(url=self.images[0])

        thread_title = f"【{self.game_name}】{self.item_name.value}"
        
        # フォーラム投稿作成 (applied_tags を指定)
        result = await forum_channel.create_thread(
            name=thread_title,
            embed=embed,
            applied_tags=applied_tags, # ここでタグを付与！
            view=InternalBuyView(self.item_name.value, self.price.value, self.pay_method.value, interaction.user)
        )
        
        post_thread = result.thread

        # 2枚目以降の画像を送信
        if len(self.images) > 1:
            for i, img_url in enumerate(self.images[1:], 2):
                sub_embed = discord.Embed(title=f"📸 詳細画像 {i}", color=discord.Color.blue())
                sub_embed.set_image(url=img_url)
                await post_thread.send(embed=sub_embed)

        await interaction.followup.send(f"✅ タグ「{self.game_name}」を付けて出品しました！", ephemeral=True)


# --- レビュー・評価システム ---
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

class FinishView(discord.ui.View):
    def __init__(self, staff_id=None): 
        super().__init__(timeout=None)
        self.staff_id = staff_id

    async def update_rank(self, member, count):
        new_role_id = None
        for threshold in sorted(RANK_ROLES.keys(), reverse=True):
            if count >= threshold:
                new_role_id = RANK_ROLES[threshold]
                break
        
        if not new_role_id: return None

        new_role = member.guild.get_role(new_role_id)
        if not new_role: return None

        # ニックネーム変更
        try:
            raw_name = member.display_name
            if "]" in raw_name:
                raw_name = raw_name.split("]")[-1].strip()
            new_nick = f"[{new_role.name}] {raw_name}"
            await member.edit(nick=new_nick[:32])
        except Exception as e:
            print(f"❌ 名前変更に失敗: {e}")

        # 役職付け替え
        if new_role not in member.roles:
            all_rank_ids = list(RANK_ROLES.values())
            roles_to_remove = [r for r in member.roles if r.id in all_rank_ids]
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
            await member.add_roles(new_role)
            return new_role.name
        return None

    def get_staff_id_from_topic(self, topic):
        if not topic: return None
        match = re.search(r'依頼者:(\d+)', topic)
        return int(match.group(1)) if match else None

    async def process_record(self, interaction, result):
        trade_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        log_data = f"取引ID: {trade_id}\n取引ログ: {interaction.channel.name}\n結果: {result}\nスタッフID: {self.staff_id}\n\n"
        
        async for m in interaction.channel.history(limit=1000, oldest_first=True):
            log_data += f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author}: {m.content}\n"
            if m.attachments:
                for attachment in m.attachments:
                    log_data += f"    📎 添付ファイルURL: {attachment.url}\n"
        
        log_file = discord.File(fp=io.BytesIO(log_data.encode()), filename=f"log-{interaction.channel.name}.txt")

        embed = discord.Embed(
            title="🤝 取引完了記録", 
            description=f"{'✅' if result=='成功' else '❌'} 取引結果: **{result}**", 
            color=0x2ecc71 if result=="成功" else 0xe74c3c
        )
        embed.add_field(name="担当スタッフ", value=interaction.user.mention)
        embed.set_footer(text=f"Staff_ID: {self.staff_id}")
        
        log_ch = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_ch: await log_ch.send(embed=embed, file=log_file)
        
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

    @discord.ui.button(label="成功 ✅", style=discord.ButtonStyle.success, custom_id="finish_success")
    async def success(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        count = add_achievement(interaction.user.id)
        rank_name = await self.update_rank(interaction.user, count)
        await self.process_record(interaction, "成功")

        msg = f"✅ 取引成功！累計実績: **{count}回**"
        if rank_name:
            msg += f"\n🎉 **称号更新！** あなたは新たに【**{rank_name}**】になりました！"
        await interaction.followup.send(msg)

    @discord.ui.button(label="失敗 ❌", style=discord.ButtonStyle.danger, custom_id="finish_fail")
    async def fail(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.staff_id is None:
            self.staff_id = self.get_staff_id_from_topic(interaction.channel.topic)
        await self.process_record(interaction, "失敗")


# --- スタッフ応募システム ---
class StaffApplyModal(discord.ui.Modal, title="仲介スタッフ応募フォーム"):
    age = discord.ui.TextInput(label="年齢（または学生/社会人）", placeholder="例: 18歳 / 社会人", required=True)
    experience = discord.ui.TextInput(label="仲介経験の有無", style=discord.TextStyle.paragraph, required=True)
    time = discord.ui.TextInput(label="活動可能な時間帯", placeholder="例: 平日20時〜24時", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"スタッフ応募-{interaction.user.name}", overwrites=overwrites
        )

        embed = discord.Embed(title="📝 スタッフ応募届", color=discord.Color.orange())
        embed.add_field(name="応募者", value=interaction.user.mention)
        embed.add_field(name="年齢/属性", value=self.age.value)
        embed.add_field(name="経験", value=self.experience.value, inline=False)
        embed.add_field(name="時間帯", value=self.time.value, inline=False)
        
        await channel.send(content=f"<@&{ADMIN_ROLE_ID}> 新しいスタッフ応募が届きました。", embed=embed)
        await interaction.response.send_message(f"✅ 応募用チャンネルを作成しました: {channel.mention}", ephemeral=True)

class StaffRecruitView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="スタッフに応募する", style=discord.ButtonStyle.success, custom_id="staff_apply_button")
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaffApplyModal())


# ================= Bot本体 =================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(TicketLaunchView())
        self.add_view(FinishView())
        self.add_view(StaffRecruitView())
        
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        
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
                await m.edit(embed=embed)
                return
        await channel.send(embed=embed)

bot = MyBot()

# ================= イベント・コマンド =================

@bot.event
async def on_ready():
    # 1. 起動メッセージとステータス設定
    print(f"✅ {bot.user} 起動完了")
    await bot.change_presence(activity=discord.Game("仲介システム稼働中"))

    # 2. チケットパネルの設置確認（エラーで止まらないように保護）
    try:
        channel = bot.get_channel(TICKET_PANEL_CH_ID)
        if channel:
            already = False
            # 過去10件のメッセージをスキャン
            async for m in channel.history(limit=10):
                if m.author == bot.user and m.embeds:
                    # タイトルが含まれているかチェック
                    if "仲介チケット発行" in (m.embeds[0].title or ""):
                        already = True
                        print("ℹ️ チケットパネルは既に存在します。")
                        break
            
            # まだパネルがない場合のみ送信
            if not already:
                embed = discord.Embed(
                    title="🎫 仲介チケット発行", 
                    description="下のボタンから作成してください。", 
                    color=0x2ecc71
                )
                await channel.send(embed=embed, view=TicketLaunchView())
                print("🆕 チケットパネルを新しく設置しました。")
        else:
            print(f"⚠️ 警告: ID {TICKET_PANEL_CH_ID} のチャンネルが見つかりません。")

    except discord.errors.Forbidden:
        print("🚫 権限エラー: メッセージ履歴を読む権限がBotにありません。")
    except Exception as e:
        print(f"⚠️ 予期せぬエラーが発生しました: {e}")

    print("----------------------------------------")

@bot.event
async def on_message(message):
    if message.author.bot: return

    if message.channel.name.startswith("🤝仲介-") and message.attachments:
        log_ch = bot.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']):
                    embed = discord.Embed(
                        title=f"📸 画像ログ: {message.channel.name}",
                        description=f"送信者: {message.author.mention}\n[メッセージへ移動]({message.jump_url})",
                        color=0x3498db,
                        timestamp=message.created_at
                    )
                    embed.set_image(url=attachment.url)
                    await log_ch.send(embed=embed)

    await bot.process_commands(message)


# --- 補完機能 ---
async def game_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    # 入力された文字(current)が含まれるゲーム名だけを抽出（最大25個まで）
    choices = [
        app_commands.Choice(name=game, value=game)
        for game in GAMES_LIST
        if current.lower() in game.lower()
    ]
    # 入力がない場合は最初の25個を表示、入力がある場合は一致するものを最大25個表示
    return choices[:25]

# --- スラッシュコマンド ---
# --- スラッシュコマンド (複数画像・補完対応版) ---
@bot.tree.command(name="sell", description="フォーラムに商品を出品します")
@app_commands.describe(
    game_name="ゲーム名を選択",
    image1="メイン画像（一覧のサムネイルになります）",
    image2="詳細画像2",
    image3="詳細画像3"
)
@app_commands.autocomplete(game_name=game_autocomplete)
async def sell(
    interaction: discord.Interaction, 
    game_name: str, 
    image1: discord.Attachment = None, 
    image2: discord.Attachment = None,
    image3: discord.Attachment = None
):
    # 画像URLを抽出
    images = [img.url for img in [image1, image2, image3] if img]
    
    # 学習ロジック（既存のものを利用）
    data = load_data()
    if game_name not in data["official"]:
        data["pending"][game_name] = data["pending"].get(game_name, 0) + 1
        if data["pending"][game_name] >= 2:
            data["official"].append(game_name)
            data["pending"].pop(game_name, None)
        save_data(data)

    await interaction.response.send_modal(SellModal(game_name, images))
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
        content_to_search = f"{emb.title} {emb.description} {emb.footer.text if emb.footer else ''}"
        if 検索ワード in content_to_search:
            found_logs.append(f"📅 {msg.created_at.strftime('%Y/%m/%d')}\n**{emb.title}**\n{emb.description}\n[ログメッセージへ飛ぶ]({msg.jump_url})")
            if len(found_logs) >= 5: break

    if not found_logs:
        return await interaction.followup.send(f"🔍 「{検索ワード}」に一致する記録は見つかりませんでした。")

    result_embed = discord.Embed(title=f"🔍 検索結果: {検索ワード}", description="\n\n".join(found_logs), color=discord.Color.blue())
    await interaction.followup.send(embed=result_embed)

@bot.tree.command(name="close", description="【スタッフ専用】チケットを閉じます（ログ保存後に使用）")
async def close(interaction: discord.Interaction):
    if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ このコマンドはスタッフのみ実行できます。", ephemeral=True)

    await interaction.response.send_message("このチャンネルを5秒後に削除します。ログの保存は忘れましたか？")
    await asyncio.sleep(5)
    await interaction.channel.delete()

@bot.tree.command(name="send_staff_recruit", description="指定のチャンネルにスタッフ募集パネルを送信します")
async def send_staff_recruit(interaction: discord.Interaction):
    channel = bot.get_channel(STAFF_RECRUIT_CH_ID)
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

@bot.tree.command(name="find", description="販売中の商品を検索します")
@app_commands.describe(game_name="検索したいゲーム名を入力")
@app_commands.autocomplete(game_name=game_autocomplete)
async def find(interaction: discord.Interaction, game_name: str):
    await interaction.response.defer(ephemeral=True)

    exhibit_channel = interaction.channel 
    found_count = 0
    
    # 検索結果をまとめるメインEmbed
    embed_result = discord.Embed(
        title=f"🔎 「{game_name}」の出品一覧",
        description=f"現在販売中のアイテムを表示しています（最新5件）\n{'─'*25}",
        color=0x2ecc71 # 鮮やかな緑
    )

    async for message in exhibit_channel.history(limit=100):
        if message.author == bot.user and message.embeds:
            embed = message.embeds[0]
            
            # 【判定】ゲーム名が含まれていて、かつ色が「金(gold)」のものだけ
            if f"【{game_name}】" in (embed.title or "") and embed.color == discord.Color.gold():
                # 商品名（タイトルの装飾を除去して抽出）
                clean_title = embed.title.replace(f"【{game_name}】", "").replace("📢", "").strip()
                
                # 価格と支払い方法を綺麗に並べる
                price_val = embed.fields[1].value if len(embed.fields) > 1 else "不明"
                pay_val = embed.fields[2].value if len(embed.fields) > 2 else "不明"
                
                # フィールドを追加（inline=False で縦に並べる）
                embed_result.add_field(
                    name=f"📦 {clean_title}",
                    value=(
                        f"┣ 💰 **価格**: `{price_val}`\n"
                        f"┣ 💳 **支払**: `{pay_val}`\n"
                        f"┗ 🔗 [**商品をチェック / 購入する**]({message.jump_url})\n"
                        f"{'─'*25}"
                    ),
                    inline=False
                )
                found_count += 1
        
        if found_count >= 5: break

    if found_count == 0:
        return await interaction.followup.send(f"❌ 「{game_name}」で現在販売中の商品は見つかりませんでした。")

    # フッターに検索日時などを入れる
    embed_result.set_footer(text=f"検索ユーザー: {interaction.user.display_name} | {found_count}件ヒット")
    
    await interaction.followup.send(embed=embed_result)

# --- 2. ボタンを表示するViewクラス ---
class TicketMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=Noneでボタンを永続化

    @discord.ui.button(label="通報・違反報告 🚨", style=discord.ButtonStyle.danger, custom_id="report_ticket")
    async def report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReportModal())

    @discord.ui.button(label="不具合・バグ報告 🛠️", style=discord.ButtonStyle.secondary, custom_id="bug_ticket")
    async def bug_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BugModal())

# --- 3. 通報用入力フォーム ---
class ReportModal(discord.ui.Modal, title="ユーザー通報・違反報告"):
    target_user = discord.ui.TextInput(label="通報対象のユーザー名・ID", placeholder="例: abc_user#0000", required=True)
    reason = discord.ui.TextInput(label="通報理由", style=discord.TextStyle.paragraph, placeholder="違反内容を具体的に記入してください。", required=True)
    evidence = discord.ui.TextInput(label="証拠", placeholder="証拠となるメッセージや画像URLがあれば入力してください。", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        content = f"**【🚨 通報受理】**\n**通報者:** {interaction.user.mention}\n**対象者:** {self.target_user.value}\n**理由:** {self.reason.value}\n**証拠:** {self.evidence.value}"
        await create_custom_ticket(interaction, "🚨通報", REPORT_CATEGORY_ID, content, discord.Color.red())

# --- 4. 不具合用入力フォーム ---
class BugModal(discord.ui.Modal, title="不具合・バグ報告"):
    location = discord.ui.TextInput(label="発生場所", placeholder="例: /sellコマンド、購入ボタン", required=True)
    description = discord.ui.TextInput(label="内容", style=discord.TextStyle.paragraph, placeholder="何が起きたか詳しく教えてください。", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        content = f"**【🛠️ 不具合報告】**\n**報告者:** {interaction.user.mention}\n**場所:** {self.location.value}\n**内容:** {self.description.value}"
        await create_custom_ticket(interaction, "🛠️不具合", BUG_CATEGORY_ID, content, discord.Color.orange())

# --- 5. チケット作成の共通処理 ---
async def create_custom_ticket(interaction: discord.Interaction, prefix, category_id, content, color):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    category = guild.get_channel(category_id)
    
    if not category:
        return await interaction.followup.send("❌ 管理用カテゴリが見つかりません。IDを確認してください。", ephemeral=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    ticket_channel = await guild.create_text_channel(
        name=f"{prefix}-{interaction.user.name}",
        category=category,
        overwrites=overwrites
    )
    
    embed = discord.Embed(title=f"{prefix}チケット作成完了", color=color, description=content)
    await ticket_channel.send(content=f"{interaction.user.mention} 運営が内容を確認いたします。", embed=embed)
    await interaction.followup.send(f"✅ {prefix}チケットを作成しました: {ticket_channel.mention}", ephemeral=True)

# --- 6. 設置用コマンド ---
@bot.command()
async def setup_support(ctx):
    embed = discord.Embed(
        title="🚨 サポート・通報窓口",
        description="トラブルや不具合はこちらのボタンから報告してください。\n※チケットは運営とあなたにしか見えません。",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketMenuView())


# 起動
bot.run(TOKEN)
