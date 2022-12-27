# Free Epic Games Discord Bot
This Discord Bot will notify you when there are new free games in the Epic Games Store.\
Heavily inspired by https://freestuffbot.xyz/

I made this because I didn't like that there was a delay that was hours long because of the amount of servers the FreeStuff bot had to ping.\
Also because I wanted to start making my own Discord bots.

## Installation
### With Docker
Build: `docker build . -t free-epic-games` \
Run: `docker run -it --name free-epic-games free-epic-games` \
Or in one line: `docker run -it --name free-epic-games $(docker build . -t free-epic-games -q)`

### Without Docker
Install the nessesary dependencies: `pip install -r requirements.txt`\
Run `main.py`

## Usage
After installation, put in your bot token, token will get saved in a .env file, and it will search for free games!

There are some variables you probably want to edit:\
`locale_country_code = "NL"`: uses the correct country for the api, this will get the correct currency symbol. \
`iso_country_code = "NL"`: uses the correct country for the api, this will get the correct date and currency. \
`client = commands.Bot(command_prefix='!')`: you can edit the command prefix to something you like. \
`channel_name = "free-games-bot"`: specify in which channel the messages get sent to (channel does not automatically get made). \
`check_delay = 5`: the amount of minutes the bot will wait before trying to find new games again.
