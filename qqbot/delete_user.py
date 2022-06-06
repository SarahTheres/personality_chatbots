import dataIO
import sys

if not len(sys.argv) == 2:
	sys.exit("Usage: python %s <TelegramID>" % __file__)
dataIO.remove_user(sys.argv[1])
