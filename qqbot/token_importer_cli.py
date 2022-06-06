import dataIO
import sys

if not len(sys.argv) == 3:
    sys.exit("Usage: python token_importer_cli.py <relative path to .csv file> pre|post")
if not (sys.argv[2] == 'post' or sys.argv[2] == 'pre'):
    sys.exit("Usage: python token_importer_cli.py <relative path to .csv file> pre|post")

dataIO.token_feeder_cli(sys.argv[1], sys.argv[2])
