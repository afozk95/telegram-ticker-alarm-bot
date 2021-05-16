from utils import read_json
from bot import Bot


bot_info_path = "/home/afofa/Desktop/furkan/code/personal/telegram-ticker-alarm-bot/bot_info.json"
bot_info = read_json(bot_info_path)
bot = Bot(bot_info)
bot.start()
