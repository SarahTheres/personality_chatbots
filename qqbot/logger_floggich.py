import logging
from telegram import Bot


# taken from https://www.electricmonk.nl/log/2011/08/14/redirect-stdout-and-stderr-to-a-logger-in-python/
class StreamToLogger(object):
	"""
	Fake file-like stream object that redirects writes to a logger instance.
	"""

	def __init__(self, logger, log_level=logging.INFO, thebot: Bot = None, support_id: int = 0):
		self.logger = logger
		self.log_level = log_level
		self.linebuf = ''
		self.bot = thebot
		self.sid = support_id

	def write(self, buf):
		for line in buf.rstrip().splitlines():
			if self.log_level == logging.ERROR and self.sid != 0 and self.bot is not None:
				self.bot.send_message(chat_id=self.sid, text=line)
			self.logger.log(self.log_level, line.rstrip())

	def flush(self):
		pass

	def set_bot_info(self, thebot: Bot, support_id: int):
		print("Got Bot info %s %s" % (thebot, support_id))
		self.bot = thebot
		self.sid = support_id
