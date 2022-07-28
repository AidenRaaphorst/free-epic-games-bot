import os
import time
import requests
import json.decoder
from dotenv import load_dotenv  # If not installed, run: pip install python-dotenv

import discord  # If not installed, run: pip install discord
from discord.ext import tasks
from discord.ext import commands


# User can edit these variables
iso_country_code = "NL"  # Use your country code for the correct time and currency
client = commands.Bot(command_prefix='!')
channel_name = "free-games-bot"
check_delay = 5  # Minutes

if not os.path.exists('.env'):
    BOT_TOKEN = input("Insert Discord Bot Token: ")
    print()
    with open('.env', 'w') as f:
        f.write(f"TOKEN={BOT_TOKEN}")

load_dotenv()
TOKEN = os.getenv("TOKEN")
old_games = []
old_games_file_name = "old_games.json"


@client.event
async def on_ready():
    print(f"{get_time()}: {client.user} has logged in")

    try:
        load_old_games()
        print(f"{get_time()}: Loaded old embeds")
    except FileNotFoundError as e:
        print(f"{get_time()}: Error: \"{e}\"")
        # print(f"{get_time()}: Error: Couldn't find & load file '{old_games_file_name}'")

    await client.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{client.command_prefix}freegames"
        )
    )

    check_and_send_embeds.start(discord.utils.get(client.get_all_channels(), name=channel_name))


@tasks.loop(minutes=check_delay)
async def check_and_send_embeds(channel: discord.TextChannel):
    global old_games

    games = get_free_games()

    # No games found
    if not games:
        print(f"{get_time()}: No free games found in Epic Games Store")
        return

    # No new games found
    if old_games:
        if get_free_games()[0]['title'] == old_games[0]['title']:
            print(f"{get_time()}: No new free games found")
            return

    # New games found
    old_games = games
    save_old_games()

    print(f"{get_time()}: New free games found: ")
    for embed in make_embeds(games):
        print(embed.title.title())
        await channel.send(embed=embed)


@client.command()
async def freegames(ctx: discord.Message):
    embeds = make_embeds(get_free_games())

    if not embeds:
        await ctx.reply("No free games found", mention_author=False)
        return

    for embed in embeds:
        await ctx.reply(embed=embed, mention_author=False)


def make_embeds(games: list):
    embeds = []
    for game in games:
        title = game['title']
        description = game['description'].replace(". ", ".\n> ")
        og_price = game['price']['totalPrice']['fmtPrice']['originalPrice']
        end_date = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['endDate']
        image = game['keyImages'][0]['url']

        embed = discord.Embed(
            title=title,
            description=f"> {description}\n\n"
                        f"~~{og_price}~~ **Free** until {str(end_date).split('T')[0]}\n",
            color=0x2f3136
        )
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/a/a7/Epic_Games_logo.png")
        embed.set_image(url=image)
        embed.set_footer(text="via Ardyon's Discord Bot")

        embeds.append(embed)
    return embeds


def get_free_games():
    free_games = []
    epic_games_store_data = requests.get(
        f"https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?country={iso_country_code}"
    ).json()
    games = epic_games_store_data['data']['Catalog']['searchStore']['elements']
    for game in games:
        discount_price = game['price']['totalPrice']['discountPrice']
        og_price = game['price']['totalPrice']['originalPrice']

        if discount_price == 0 and og_price > 0:
            free_games.append(game)

    return free_games


def save_old_games():
    global old_games

    with open(old_games_file_name, 'w') as f:
        json.dump(old_games, f)


def load_old_games():
    global old_games

    with open(old_games_file_name) as f:
        old_games = json.load(f)


def get_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


client.run(TOKEN)
