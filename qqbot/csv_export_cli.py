import dataIO
import csv
import sys
from objects import Choice
import os

if not len(sys.argv) == 2:
	sys.exit('Usage: ' + __file__ + ' <target file>')
out = open(sys.argv[1], 'w', newline='')
csvwriter = csv.DictWriter(out, fieldnames=list(Choice.__dataclass_fields__.keys()), extrasaction='ignore')
csvwriter.writeheader()
for a in dataIO.get_answers():
	csvwriter.writerow(a.__dict__)

print("Done. Enter the following in a command line on your machine:")
print("scp -P 22022 qqbot@pwp.um.ifi.lmu.de:%s ." % os.path.join(os.path.dirname(os.path.realpath(__file__)), sys.argv[1]))
