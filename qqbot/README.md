# QQBot

## LMU PWP Server
Log in via ssh. From the home directory, open the project folder:
`cd qqbot`

### First installation
Clone the repository
`git clone repo`

If the default python version on your system is below 3.7, create a virtual environment and activate it.
Currently, the virtual environment on the LMU server is qqbot-venv-3.7.
`source qqbot-venv-3.7/bin/activate`

Install requirements:
`pip3 install -r requirements.txt`

Set up database:
1. Install mongodb
2. Start a mongo daemon process, e.g. via systemd
3. Define a user, password and database
4. Set the credentials to dataIO.py

Run project to test it:
`python3 start.py`

Run project with pm2 as process manager for automatic restarts:
1. Requirement: Node.js installation including npm
2. Install pm2 via npm: `npm install pm2 -g`
3. Copy `start.py` to a file named `start`, without the extension `.py`
4. Run `pm2 start start --interpreter=/home/qqbot/qqbot/qqbot-venv-3.7/bin/python3 --name qqbot`
5. For restart after server reboot: run `pm2 startup` and then execute the printed command as root. This adds pm2 to systemd.

### Update and re-running
1. Pull git updates: `git pull`
2. Copy `start.py` to a file named `start`, without the extension `.py`: `cp start.py start`. This is necessary because pm2 guesses the interpreter from the file extension and this overrides the python version from the virtual environment.
3. Rerun the bot via the process manager `pm2 restart qqbot`

### Checking status
On the server: 
- is the bot still running? `pm2 list` should show the process "qqbot"
- checking existing log files: `ls ~/qqbot/logs`
- check for participants in the database
    - `mongo --port 27017  --authenticationDatabase "admin" -u "qqbot-admin" -p "<password>"`
    - `use QQBase`
    - `db.QQParticipants.find()`

Locally:
- copy log file to your local machine: `scp -P 22022 qqbot@pwp.um.ifi.lmu.de:~/qqbot/logs/<name of log file> <your-local-directory>`
- What to check in the log file?
    - Were timers for participants set? Search for "Requested active participants" and check the following lines
    - Were there any errors?