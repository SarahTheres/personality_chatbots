import urllib.parse

from telegram import Bot
import importlib

def send_support_message(bot: Bot, msg: str):
	importlib.invalidate_caches()
	dataIO = importlib.import_module('dataIO')
	sid = dataIO.BOT_CONFIG['Study_settings']['telegram-support-group']
	bot.send_message(sid, ("This is %s speaking:\n" + msg) % bot.username)
