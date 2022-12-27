import os
import time
import json.decoder
from datetime import datetime

from dotenv import load_dotenv

import discord
from discord.ext import tasks, commands
from requests_html import HTMLSession


intents = discord.Intents.default()
intents.message_content = True

# User can edit these variables
locale_country_code = "NL"  # Use your country code for the correct currency symbol
iso_country_code = "NL"  # Use your country code for the correct time and currency
client = commands.Bot(intents=intents, command_prefix='!')
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
    log(f"{client.user} has logged in\n")
    print(f"Check Delay: '{check_delay}' minutes")
    print(f"Channel Name: '{channel_name}'")
    print(f"ISO Country Code: '{iso_country_code}'")
    print(f"Bot Prefix: '{client.command_prefix}'")
    print()

    try:
        load_old_games()
        log(f"Loaded '{old_games_file_name}'")
    except FileNotFoundError:
        log(f"Couldn't find or load file '{old_games_file_name}'")

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
        log("No free games found in Epic Games Store")
        return

    # No new games found
    if old_games:
        if get_free_games()[0]['title'] == old_games[0]['title']:
            log("No new free games found")
            return

    # New games found
    old_games = games
    save_old_games()

    log("New free games found: ")
    for embed in make_embeds(games):
        print(f" - {embed.title.title()}")
        await channel.send(embed=embed)


@client.command()
async def freegames(ctx: discord.Message):
    embeds = make_embeds(get_free_games())

    if not embeds:
        await ctx.reply("No free games found", mention_author=False)
        return

    for embed in embeds:
        await ctx.reply(embed=embed, mention_author=False)

    log(f"User '{ctx.author}' executed 'freegames'")


@client.command()
async def clear(ctx: discord.Message, amount: int = 0):
    await ctx.channel.purge(limit=amount+1)
    log(f"User '{ctx.author}' executed 'clear', deleted {amount+1} message(s) including command message")


def make_embeds(games: list):
    embeds = []
    for game in games:
        title = game['title']
        description = game['description']\
            .replace("\n", "")\
            .replace(". ", ".\n> ")\
            .replace("! ", "!\n> ")\
            .replace("? ", "?\n> ")\
            .removesuffix("\n> ")
        og_price = game['price']['totalPrice']['fmtPrice']['originalPrice']
        slug = game['productSlug']

        image = ""
        key_images = game['keyImages']
        for key_image in key_images:
            if "wide" in key_image['type'].lower():
                image = key_image['url']
                break

        # Convert UTC time in RFC 3339 format to Unix format
        end_date = game['price']['lineOffers'][0]['appliedRules'][0]['endDate']
        utc_dt = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S.%fZ')
        end_timestamp = (utc_dt - datetime(1970, 1, 1)).total_seconds().__int__()

        embed = discord.Embed(
            title=title,
            description=f"> {description}\n\n"
                        f"~~{og_price}~~ **Free** until <t:{end_timestamp}:f>\n",
            color=0x2f3136
        )
        embed.add_field(name="Open in browser", value=f"**https://store.epicgames.com/p/{slug}**")
        embed.add_field(name="Open in Epic Launcher", value=f"**<com.epicgames.launcher://store/p/{slug}>**")
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/a/a7/Epic_Games_logo.png")
        embed.set_image(url=image)
        embed.set_footer(text="via Ardyon's Discord Bot")

        embeds.append(embed)
    return embeds


def get_free_games():
    free_games = []
    session = HTMLSession()
    epic_games_store_data = session.get(
        f"https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?country={iso_country_code}"
    ).json()

    games = epic_games_store_data['data']['Catalog']['searchStore']['elements']
    for game in games:
        title = game['title']
        slug = game['productSlug']
        if title == "Mystery Game":
            continue

        # Get sandboxId
        variables = json.dumps({
            "pageSlug": slug,
            "locale": locale_country_code
        })
        extensions = json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "781fd69ec8116125fa8dc245c0838198cdf5283e31647d08dfa27f45ee8b1f30"
            }
        })
        r = session.get(
            f'https://store.epicgames.com/graphql?operationName=getMappingByPageSlug'
            f'&variables={variables}&extensions={extensions}'
        ).json()
        sandbox_id = r['data']['StorePageMapping']['mapping']['sandboxId']

        # Get offerId
        variables = json.dumps({
            "allowCountries": "",
            "category": "games/edition",
            "country": iso_country_code,
            "locale": locale_country_code,
            "namespace": sandbox_id,
            "sortBy": "pcReleaseDate",
            "sortDir": "DESC",
            "codeRedemptionOnly": False
        })
        extensions = json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "ff4dea7ebf14b25dc1cbedffe1d90620318a7bffea481fea02ac6e87310326f4"
            }
        })
        r = session.get(
            f'https://store.epicgames.com/graphql?operationName=getRelatedOfferIdsByCategory'
            f'&variables={variables}&extensions={extensions}'
        ).json()
        offer_id = r['data']['Catalog']['catalogOffers']['elements'][0]['id']

        # Get product info
        variables = json.dumps({
            "locale": locale_country_code,
            "country": iso_country_code,
            "offerId": offer_id,
            "sandboxId": sandbox_id
        })
        extensions = json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "6797fe39bfac0e6ea1c5fce0ecbff58684157595fee77e446b4254ec45ee2dcb"
            }
        })
        game_info = session.get(
            f'https://store.epicgames.com/graphql?operationName=getCatalogOffer'
            f'&variables={variables}&extensions={extensions}'
        ).json()

        free_games.append(game_info['data']['Catalog']['catalogOffer'])

    return free_games


def save_old_games():
    global old_games

    with open(old_games_file_name, 'w') as f:
        json.dump(old_games, f, indent=4)


def load_old_games():
    global old_games

    with open(old_games_file_name) as f:
        old_games = json.load(f)


def get_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def log(msg: str):
    print(f"[{get_time()}] {msg}")


client.run(TOKEN)
