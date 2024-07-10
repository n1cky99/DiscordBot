import nextcord
from nextcord.ext import commands
import pytz

bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())
bucharest_timezone = pytz.timezone('Europe/Bucharest')