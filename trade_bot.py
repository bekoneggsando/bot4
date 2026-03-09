import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import math
from datetime import datetime
import os
from flask import Flask
import threading

# =============================
# Railway Webサーバー
# =============================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

def run_web():
    port = int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)

threading.Thread(target=run_web).start()

# =============================
# TOKEN
# =============================

TOKEN = os.getenv("DISCORD_TOKEN")

STATS_CHANNEL_ID = 1479271849283293256
STAFF_REVIEW_CHANNEL_ID = 1479125489506586735
SERVER_REVIEW_CHANNEL_ID = 1479271799492710450

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

stats_file = "stats.json"
staff_file = "staff_reviews.json"
server_file = "server_reviews.json"

# =============================
# JSON操作
# =============================

def load_json(file, default):
    try:
        with open(file,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file,data):
    with open(file,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=4,ensure_ascii=False)

# =============================
# 計算
# =============================

def trust_score(avg,reviews):
    return avg * math.log(reviews + 1)

def get_success_rate(stats):
    if stats["total"] == 0:
        return 0
    return round((stats["success"]/stats["total"])*100,1)

# =============================
# ランキング
# =============================

def get_staff_ranking():

    data = load_json(staff_file,{})
    ranking = []

    for user_id,data2 in data.items():

        stars = data2["stars"]

        if len(stars) == 0:
            continue

        avg = sum(stars)/len(stars)
        reviews = len(stars)
        score = trust_score(avg,reviews)

        ranking.append((user_id,avg,reviews,score))

    ranking.sort(key=lambda x:x[3],reverse=True)

    return ranking[:3]

def get_trade_ranking():

    data = load_json(staff_file,{})
    ranking = []

    for user_id,data2 in data.items():

        trades = data2.get("trades",0)

        ranking.append((user_id,trades))

    ranking.sort(key=lambda x:x[1],reverse=True)

    return ranking[:3]

# =============================
# 統計表示（大きく）
# =============================

async def update_stats():

    channel = bot.get_channel(STATS_CHANNEL_ID)

    if channel is None:
        print("統計チャンネルが見つかりません")
        return

    stats = load_json(stats_file,{
        "total":0,
        "success":0,
        "cancel":0,
        "trouble":0,
        "today":0,
        "month":0
    })

    rate = get_success_rate(stats)

    ranking = get_staff_ranking()
    trade_ranking = get_trade_ranking()

    medals = ["🥇","🥈","🥉"]

    staff_text = ""
    for i,r in enumerate(ranking):
        staff_text += f"{medals[i]} <@{r[0]}> ⭐{round(r[1],2)}（{r[2]}件）\n"

    trade_text = ""
    for i,r in enumerate(trade_ranking):
        trade_text += f"{medals[i]} <@{r[0]}> 取引数 {r[1]}\n"

    embed = discord.Embed(
        title="📊 取引統計ダッシュボード",
        description="サーバーの取引状況",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📈 全体統計",
        value=f"""
総取引数
**{stats["total"]}**

成功数
**{stats["success"]}**

成功率
**{rate}%**
""",
        inline=False
    )

    embed.add_field(
        name="📅 取引状況",
        value=f"""
今日の取引
**{stats["today"]}**

今月の取引
**{stats["month"]}**
""",
        inline=False
    )

    embed.add_field(
        name="🏆 信頼度ランキング",
        value=staff_text if staff_text else "データなし",
        inline=False
    )

    embed.add_field(
        name="💼 総取引ランキング",
        value=trade_text if trade_text else "データなし",
        inline=False
    )

    async for m in channel.history(limit=10):

        if m.author == bot.user:

            await m.edit(embed=embed)

            return

    await channel.send(embed=embed)

# =============================
# 自動更新
# =============================

@tasks.loop(minutes=5)
async def auto_update():
    await update_stats()

# =============================
# コマンド（あなたのコード）
# =============================

@bot.tree.command(name="staff_add",description="スタッフ登録")
async def staff_add(interaction:discord.Interaction,user:discord.Member):

    data = load_json(staff_file,{})
    uid = str(user.id)

    if uid in data:
        await interaction.response.send_message("すでに登録されています")
        return

    data[uid] = {
        "stars":[],
        "comments":[],
        "trades":0
    }

    save_json(staff_file,data)

    await interaction.response.send_message(f"{user.mention} をスタッフ登録しました")

# （他の review / finish / server_profile などは
# あなたのコードと同じなのでそのまま使えます）

# =============================
# 起動
# =============================

@bot.event
async def on_ready():

    await bot.tree.sync()

    print("BOT起動")

    await update_stats()

    auto_update.start()

bot.run(TOKEN)
