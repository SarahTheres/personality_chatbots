import csv
import datetime
import json
import os
import string
import sys
import tkinter as tk
import typing
from tkinter import filedialog
from typing import Dict, Tuple
from urllib import parse

import jsonpickle
import pymongo
import pymongo.errors

from objects import Participant, Choice, Questionnaire, QuestionnaireJson, Question

root_dir = os.path.dirname(os.path.realpath(__file__))  # set current dir

BOT_CONFIG = None
""" Contains the content of ./config.json. daily_routine() has to be called before! """

TODAYS_QUESTIONNAIRES: Dict[str, Questionnaire] = {}
""" Contains a dict {QuestionnaireID, Questionnaire} of questionnaires that are valid for the current date. 
daily_routine() has to be called before!
"""

TODAYS_QUESTIONS: Dict[str, Question] = {}
""" Contains a dict {QuestionID, Question} of all questions that are valid for the current date for easy reference. 
daily_routine() has to be called before! 
"""

_pickler = jsonpickle.Pickler()
_unpickler = jsonpickle.Unpickler()


def _import_global_data() -> str:
	global BOT_CONFIG
	BOT_CONFIG = json.load(open("config.json"))
	return __name__ + ':Read config.json into BOT_CONFIG'


def _scan_for_questions():
	global TODAYS_QUESTIONNAIRES
	TODAYS_QUESTIONNAIRES = {}

	temp: typing.List[QuestionnaireJson] = []
	# get valid questions from json
	# scan all files in .\questions
	for f in os.listdir((os.path.join(root_dir, "questions"))):
		filepath = os.path.join(root_dir, "questions", f)
		if os.path.isfile(filepath):
			temp.extend(jsonpickle.decode(open(filepath).read()))
	for n in temp:
		q = Questionnaire()
		q.feed_json(n)
		if q.best_before > datetime.datetime.now():
			TODAYS_QUESTIONNAIRES[q.id] = q
	for q in TODAYS_QUESTIONNAIRES.values():
		for qs in q.questions:
			TODAYS_QUESTIONS[qs.id] = qs

	return __name__ + ':Successfully read current questions into TODAYS_QUESTIONS. ' \
					  'Found %s Questions in %s Questionnaires.' % (len(TODAYS_QUESTIONS), len(TODAYS_QUESTIONNAIRES))


def tokens_left() -> str:
	posttokendb = _get_collection('coll_tokens_post')
	post_no = posttokendb.count({})
	pretokendb = _get_collection('coll_tokens_pre')
	pre_no = pretokendb.count({})
	return __name__ + ": Nr of pre-tokens left: %s. Nr of post-tokens left: %s" % (pre_no, post_no)


def user_summary() -> str:
	coll_users = _get_collection('coll_participants')
	total = coll_users.count({})
	active = coll_users.count({"active": True})
	finished = coll_users.count({"post_complete": True})
	return __name__ + ": Total Nr of users in Database: %s\nof which active: %s\nof which finished: %s" % (total, active, finished)


def answer_summary() -> str:
	coll_answers = _get_collection("coll_answers")
	esnr = coll_answers.find({
		'question_id': {'$regex': '^(es)'}
	})
	count = 0
	anslist = list(esnr)

	day: datetime = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)

	for i in range(len(anslist)):
		timestamp = _unpickler.restore(anslist[i]).timestamp.date()
		if timestamp == day:
			count += 1

	return __name__ + ": Total Nr of ES Questions answered yesterday: %s" % count


def daily_routine() -> str:
	"""
    Performs a scan for json-files in the ./questions/ directory and extracts all valid questionnaires into
    dataIO.TODAYS_QUESTIONS as well as reading settings from ./config.json and stores it in dataIO.BOT_CONFIG
    """
	dataimport = _import_global_data()
	questionimport = _scan_for_questions()
	tokencheck = tokens_left()
	users = user_summary()
	es_amswers = answer_summary()
	print(dataimport)
	print(questionimport)
	print(users)
	print(es_amswers)
	return __name__ + ": Performed daily routine:\n%s\n%s\n%s\n%s\n%s" % (dataimport, questionimport, tokencheck, users, es_amswers)


def user_duration(participant_id: int) -> Tuple[bool, int]:
	"""
    Returns the date on which the user started answering ES Questions.

    :param participant_id: The participant in question.
    :return: A Tuple[bool: success, int: nr of Days since first ES Choice, -1 if none found]:
    """
	idstring = str(participant_id)
	res = _get_collection("coll_answers").find(
		{'participant_id': idstring, 'question_id': {'$regex': '^(es)'}}).sort('timestamp', pymongo.ASCENDING)
	reslist = list(res)
	if (len(reslist)) > 0:
		days = datetime.datetime.utcnow().date() - _unpickler.restore(reslist[0]).timestamp.date()
		return True, days.days

	print(__name__ + ': No ES answers were found for user %s' % participant_id)
	return False, -1


def days_since_last_es_response(participant_id: int) -> Tuple[bool, int]:
	"""
    Returns how many days ago a participant last answered an ES Question.

    :param participant_id: The participant in question.
    :return: A Tuple[bool: success, int: nr of Days since last ES Choice, -1 if none found]:
    """
	idstring = str(participant_id)
	res = _get_collection("coll_answers").find(
		{'participant_id': idstring}).sort('timestamp', pymongo.DESCENDING)
	reslist = list(res)
	if (len(reslist)) > 0:
		firstans: datetime = datetime.datetime.utcnow().date() - _unpickler.restore(reslist[0]).timestamp.date()
		return True, firstans.days

	print(__name__ + ': No ES answers were found for user %s' % participant_id)
	return False, -1


# todo: helper method to check if an answer to a question_id has already been given by a user_id on a defined date
def _answer_already_exists() -> bool:
	return False


# fetch Database Data
def _dd():
	return BOT_CONFIG["Database_settings"]


# Get a Pymongo Collection object to work with
def _get_collection(coll_name: str) -> pymongo.collection:
	myclient = pymongo.MongoClient(
		"mongodb://%s:%s@%s:27017/chatbot" % (parse.quote_plus(_dd()['user']), parse.quote_plus(_dd()['pw']), _dd()['host']))
	mydb = myclient[_dd()['name']]
	return mydb[_dd()[coll_name]]


def token_feeder_cli(cli_arg, postpre):
	post: bool = postpre == 'post'
	path = os.path.join(root_dir, cli_arg)
	if not os.path.isfile(path):
		sys.exit("No file found at the provided path " + path)
	_feed_tokens(path, post)


def remove_user(tid: str):
	tid = str(tid)
	uc = _get_collection('coll_participants')
	uc.delete_one({"_id": tid})
	ad = _get_collection('coll_answers')
	print(__name__ + ": Deleted %s answers from User %s" % (ad.delete_many({'participant_id': tid}).deleted_count, tid))
	rd = _get_collection('coll_reminder_messages')
	print(__name__ + ": Deleted %s reminders from User %s" % (rd.delete_many({'participant_id': tid}).deleted_count, tid))


def _token_feeder_ui():
	root = tk.Tk()
	root.withdraw()

	_feed_tokens(filedialog.askopenfilename(), False)


def _feed_tokens(file_path: str, post: bool):
	print(post)
	insertdoc = []
	print(post)
	with open(file_path) as tf:
		reader = csv.DictReader(tf)

		for t in reader:
			insertdoc.append({'_id': t['token']})

	print(__name__ + ':Limesurvey tokens found:' + str(len(insertdoc)))

	if post:
		tokendb = _get_collection('coll_tokens_post')
	else:
		tokendb = _get_collection('coll_tokens_pre')
	tokendb.insert_many(insertdoc)

	print(__name__ + ':Successfully inserted tokens into token db.')


def register_new_participant(participant: Participant) -> Tuple[bool, str]:
	"""
    Takes a Participant object and saves it to the database.

    :param participant: The new participant
    :return: Tuple[bool: Success, str: info]:
    """
	user_db = _get_collection('coll_participants')

	try:
		if user_db.count({'_id': str(participant._id)}) == 0:
			user_db.insert_one(_pickler.flatten(participant))
			print(__name__ + ':User %s was successfully added.' % participant._id)
			return True, "User was successfully added."
		else:
			print(__name__ + ':User %s already exists.' % participant._id)
			return False, "User already exists."
	except pymongo.errors.ServerSelectionTimeoutError:
		print(__name__ + ':Could not add User to database.')
		return False, "Could not connect to database. Timeout."


def get_personality_order_counters() -> Tuple[bool, Participant]:
	"""
    Returns a Participant object for a given Telegram ID

    :param participant_id: The Telegram ID of the desired user.
    :return: A Tuple (bool: Participant found, Participant: if found)
    """

	personality_db = _get_collection('coll_personality_orders')
	id = ""

	for doc in personality_db.find({}):
		id = doc.get('_id')

	pers_res = personality_db.find_one({'_id': id})

	if pers_res is not None:
		return True, _unpickler.restore(pers_res)
	else:
		return False, PersonalityOrder('0')


def set_personality_order_counters(personality: int, counter: int):
	"""
    Saves personality order counters to the database.

	:param personality: Order 0: order_dei, 1: order_ide, 2: order_eid
    :return: Tuple[bool: Success, str: info]:
    """

	personality_db = _get_collection('coll_personality_orders')
	id = ""

	for doc in personality_db.find({}):
		id = doc.get('_id')

	if personality is not None:
		if personality == 0:
			counterName = "order_dei"
		elif personality == 1:
			counterName = "order_ide"
		else:
			counterName = "order_eid"

		res = personality_db.update_one({'_id': id}, {"$set": {counterName: counter}})
		if not res.acknowledged:
			print(__name__ + ':Update failed')
			return False, "Error updating personality order counters"
	print(__name__ + ':Successfully updated personality counters')
	return True, "Personality counters successfully set."


def set_survey_times(participant_id: str, earliest: int = 0, latest: int = 0) -> Tuple[bool, str]:
	"""
    Sets notification times for a participant. If the time is not known yet, it can be ommitted.

    :param latest: Latest time the participant wishes to be notified, can be ommitted.
    :param earliest: Earliest time the participant wishes to be notified, can be ommitted.
    :param participant_id: the participant's Telegram ID
    :return: -> Tuple[bool: success, str: info]:
    """
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if earliest != 0:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"earliest": earliest}})
		if not res.acknowledged:
			print(__name__ + ':Could not update survey times for user %s' % participant_id)
			return False, "Error updating user"
	if latest != 0:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"latest": latest}})
		if not res.acknowledged:
			print(__name__ + ':Could not update survey times for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':User notification times successfully set for user %s' % participant_id)
	return True, "User notification times successfully set."


def set_username(participant_id: str, username: str = "") -> Tuple[bool, str]:
	"""
    Sets username of participant.

    :param participant_id: the participant's Telegram ID
    :param username: Name user types in
    :return: -> Tuple[bool: success, str: info]:
    """
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if username != "":
		res = coll_users.update_one({'_id': idstring}, {"$set": {"username": username}})
		if not res.acknowledged:
			print(__name__ + ':Could not update username for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':Username successfully set for user %s' % participant_id)
	return True, "Username successfully set."


def set_questionnaire_id(participant_id: str, questionnaire_id: str = "") -> Tuple[bool, str]:
	"""
    Sets questionnaire_id of participant.

    :param participant_id: the participant's Telegram ID
    :param questionnaire_id: Name user types in
    :return: -> Tuple[bool: success, str: info]:
    """
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if questionnaire_id != "":
		res = coll_users.update_one({'_id': idstring}, {"$set": {"questionnaire_id": questionnaire_id}})
		if not res.acknowledged:
			print(__name__ + ':Could not update questionnaire_id for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':questionnaire_id successfully set for user %s' % participant_id)
	return True, "questionnaire_id successfully set."


def set_personality_order(participant_id: str, order: int) -> Tuple[bool, str]:
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if order is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"personality_order": order}})
		if not res.acknowledged:
			print(__name__ + ':Could not update personality order for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':Personality order successfully set for user %s' % participant_id)
	return True, "Order successfully set."


def set_round(participant_id: str, round: int) -> Tuple[bool, str]:
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if round is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"round": round}})
		if not res.acknowledged:
			print(__name__ + ':Could not update round for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':Round successfully set for user %s' % participant_id)
	return True, "Round successfully set."


def set_unresponsive(participant_id: str, unresponsive: int) -> Tuple[bool, str]:
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if unresponsive is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"unresponsive": unresponsive}})
		if not res.acknowledged:
			print(__name__ + ':Could not update unresponsive for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':unresponsive successfully set for user %s' % participant_id)
	return True, "unresponsive successfully set."


def set_conv_complete(participant_id: str, conv_complete: int) -> Tuple[bool, str]:
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if conv_complete is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"conv_complete": conv_complete}})
		if not res.acknowledged:
			print(__name__ + ':Could not update conv_complete for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':conv_complete successfully set for user %s' % participant_id)
	return True, "unresponsive successfully set."


def set_prev_qid(participant_id: str, prev_qid: int) -> Tuple[bool, str]:
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if prev_qid is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"prev_qid": prev_qid}})
		if not res.acknowledged:
			print(__name__ + ':Could not update prev_qid for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':prev_qid successfully set for user %s' % participant_id)
	return True, "unresponsive successfully set."


def set_user_active(participant_id: str, active: bool) -> Tuple[bool, str]:
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if active is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"active": active}})
		if not res.acknowledged:
			print(__name__ + ':Could not update active for user %s' % participant_id)
			return False, "Error updating user"
	print(__name__ + ':Round successfully set for active state %s' % participant_id)
	return True, "Active state successfully set."


def set_survey_codes(participant_id: str, code: int) -> Tuple[bool, str]:
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	sc = "survey_code" + str(code)
	res = coll_users.update_one({'_id': idstring}, {"$set": {sc: 1}})
	if not res.acknowledged:
		print(__name__ + ':Could not update survey_codes for user %s' % participant_id)
		return False, "Error updating survey_codes for user"
	print(__name__ + ':survey_codes successfully set for user %s' % participant_id)
	return True, "survey_codes successfully set."


def set_bot_states(participant_id: str, bot_d: int = 0, bot_e: int = 0, bot_i: int = 0) -> Tuple[bool, str]:
	"""
    Sets states of the bots.

    :param participant_id: the participant's Telegram ID
    :param bot_d: State of default bot
    :param bot_e: State of extraverted bot
    :param bot_i: State of introverted bot
    :return: -> Tuple[bool: success, str: info]:
    """
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if bot_d is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"bot_d": bot_d}})
		if not res.acknowledged:
			print(__name__ + ':Could not update state for bot_d of user %s' % participant_id)
			return False, "Error updating state of bot_d"
	if bot_e is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"bot_e": bot_e}})
		if not res.acknowledged:
			print(__name__ + ':Could not update state for bot_e of user %s' % participant_id)
			return False, "Error updating state of bot_e"
	if bot_i is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"bot_i": bot_i}})
		if not res.acknowledged:
			print(__name__ + ':Could not update state for bot_i of user %s' % participant_id)
			return False, "Error updating state of bot_i"
	print(__name__ + ': Bot-states successfully set for user %s' % participant_id)
	return True, "Bot-states successfully set."

def set_user_stages(participant_id: str, stage_start: int = 0, stage_es: int = 0, stage_fs: int = 0) -> Tuple[bool, str]:
	"""
    Sets user's stage.

    :param participant_id: the participant's Telegram ID
    :param stage_start
    :param stage_es
    :param stage_fs
    :return: -> Tuple[bool: success, str: info]:
    """
	idstring = str(participant_id)
	coll_users = _get_collection('coll_participants')
	if stage_start is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"stage_start": stage_start}})
		if not res.acknowledged:
			print(__name__ + ':Could not update stage_start of user %s' % participant_id)
			return False, "Error updating stage_start"
	if stage_es is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"stage_es": stage_es}})
		if not res.acknowledged:
			print(__name__ + ':Could not update stage_es of user %s' % participant_id)
			return False, "Error updating stage_es"
	if stage_fs is not None:
		res = coll_users.update_one({'_id': idstring}, {"$set": {"stage_fs": stage_fs}})
		if not res.acknowledged:
			print(__name__ + ':Could not update stage_fs of user %s' % participant_id)
			return False, "Error updating stage_fs"
	print(__name__ + ': User-states successfully set for user %s' % participant_id)
	return True, "Stages successfully set."

def get_user(participant_id: int) -> Tuple[bool, Participant]:
	"""
    Returns a Participant object for a given Telegram ID

    :param participant_id: The Telegram ID of the desired user.
    :return: A Tuple (bool: Participant found, Participant: if found)
    """
	coll_users = _get_collection('coll_participants')
	user_res = coll_users.find_one({'_id': str(participant_id)})
	if user_res is not None:
		print(__name__ + ':Successfully found user %s' % str(participant_id))
		return True, _unpickler.restore(user_res)
	else:
		print(__name__ + ':Could not find user %s' + str(participant_id))
		return False, Participant('0')


def get_user_qid_new(qid: str) -> bool:
	"""
    Returns a Participant object for a given Telegram ID

    :param participant_id: The Telegram ID of the desired user.
    :return: A Tuple (bool: Participant found, Participant: if found)
    """
	coll_users = _get_collection('coll_participants')
	user_res = coll_users.find_one({'questionnaire_id': qid})
	if user_res is None:
		print(__name__ + ':Questionnaire ID not used yet')
		return True
	else:
		print(__name__ + ':Questionnaire ID already exists')
		return False


def number_of_es_answers(participant_id: int) -> Tuple[bool, int]:
	"""
    Returns the number of ES questions the user has already answered.
    :param participant_id: The participants chat ID.
    :return: The number of ES questions answered.
    """
	coll_answers = _get_collection('coll_answers')
	return True, coll_answers.count_documents({
		'participant_id': str(participant_id),
		'question_id': {
			'$regex': '^es.*'
		}
	})


def reminder_message(participant_id: str = "", message_id: int = 0) -> Tuple[bool, typing.List[str]]:
	"""
    A method to store reminder messages. If there are already reminders stored for a user, they will be removed.
    :param participant_id:
    :param message_id:
    :return:
    """
	ret_reminders: typing.List[str] = []

	coll_reminders = _get_collection('coll_reminder_messages')
	query = {}
	if participant_id:
		query = {
			'participant_id': str(participant_id)
		}
	reminders = coll_reminders.find(query)

	for r in reminders:
		ret_reminders.append(r['message_id'])
	print(__name__ + ":Found " + str(reminders.retrieved) + " active reminders for user " + participant_id)

	delete_res = coll_reminders.delete_many(query)
	print(__name__ + ": Deleted " + str(delete_res.deleted_count) + " reminders from the DB for user " + participant_id)

	if message_id not in reminders and message_id != 0:
		coll_reminders.insert_one({
			'participant_id': str(participant_id),
			'message_id': message_id
		})

	return True, ret_reminders


def set_participant_progress(participant_id: int, init_done: int = 2, post_done: int = 2, active: int = 2) -> Tuple[
	bool, str]:
	"""
    Sets information about the progress of the participant within the ES journey. For all parameters:
    0 means False, 1 means True, 2 means NO CHANGE

    :param participant_id: The Telegram ID of the user that completed the initializaiton process.
    :param active: This user is active and receives questions and notifications.
    :param post_done: This user has finished the post-questionnaire.
    :param init_done: This user has finished the pre-questionnaire.
    :return: Tuple[bool: success, str: info]:    """
	idstring = str(participant_id)
	if (init_done + post_done + active) < 0 or (init_done + post_done + active) > 6:
		return False, "For all parameters: 0 means False, 1 means True, 2 means NO CHANGE"

	ib = {
		0: False,
		1: True,
		2: "no change"
	}

	coll_users = _get_collection('coll_participants')
	if not init_done == 2:
		coll_users.update_one({'_id': idstring}, {"$set": {"init_complete": ib[init_done]}})
	if not post_done == 2:
		coll_users.update_one({'_id': idstring}, {"$set": {"post_complete": ib[post_done]}})
	if not active == 2:
		coll_users.update_one({'_id': idstring}, {"$set": {"active": ib[active]}})

	print(__name__ + ':User %s was updated to init(%s), post(%s), active(%s)' % (
		participant_id, ib[init_done], ib[post_done], ib[active]))
	return True, "User was updated"


def set_current_question(participant_id: int, questionnaire_id: str = "", question_id: str = "",
						 question_index: int = -1, reset: bool = False) -> Tuple[bool, str]:
	"""
    Sets the current question ID for a given user. If all questions have been answered, this is to be set to "".

    :param participant_id: The Telegram ID of the user that has been sent the question.
    :param questionnaire_id: The Questionnaire ID of the questionnaire the user is currently being asked.
    :param question_id: The Question ID of the question the user is currently being asked.
    :param reset: If True, all parameters concerning the current question(naire) are deleted.
    :param question_index:  The Question Index of the question the user is currently being asked.
    :return: -> Tuple[bool: success, str: info]:
    """

	idstring = str(participant_id)
	default_status = {'questionnaire_id': "", 'question_id': "", 'question_index': -1}
	coll_users = _get_collection('coll_participants')
	if reset:
		coll_users.update_one({'_id': idstring}, {"$set": {
			"questionnaire_id": default_status['questionnaire_id'],
			"question_id": default_status['question_id'],
			"question_index": default_status['question_index']
		}})
		print(__name__ + ':Status of user %s was set to %s' % (participant_id, default_status))

	if not questionnaire_id == "":
		print(__name__ + ':Questionnaire ID of user %s was set to %s' % (participant_id, questionnaire_id))
		coll_users.update_one({'_id': idstring}, {"$set": {"questionnaire_id": questionnaire_id}})
	if not question_id == "":
		print(__name__ + ':Question ID of user %s was set to %s' % (participant_id, question_id))
		coll_users.update_one({'_id': idstring}, {"$set": {"question_id": question_id}})
	if not question_index == -1:
		print(__name__ + ':Question Index of user %s was set to %s' % (participant_id, question_index))
		coll_users.update_one({'_id': idstring}, {"$set": {"question_index": question_index}})

	return True, "User was updated: " + str(default_status)


def get_active_participants() -> Tuple[bool, typing.List[Participant]]:
	"""
    Returns an Array of all active participants, i.e. Participant.active = True

    :return: {result: bool, Participant[]}, result is False if there are no active participants
    """
	coll_users = _get_collection('coll_participants')
	active_p = []
	for o in coll_users.find({"active": True}):
		active_p.append(_unpickler.restore(o))
	if len(active_p) > 0:
		print(__name__ + ':Found %s active participants' % len(active_p))
		return True, active_p
	print(__name__ + ':Found no active participants')
	return False, []

def get_fs_participants() -> Tuple[bool, typing.List[Participant]]:
	"""
    Returns an Array of all participants in fs state

    :return: {result: bool, Participant[]}, result is False if there are no active participants
    """
	coll_users = _get_collection('coll_participants')
	fs_participants = []
	for o in coll_users.find({"stage_fs": 1}):
		fs_participants.append(_unpickler.restore(o))
	if len(fs_participants) > 0:
		print(__name__ + ':Found %s active participants' % len(fs_participants))
		return True, fs_participants
	print(__name__ + ':Found no active participants')
	return False, []

def save_answer_db(answer: Choice) -> Tuple[bool, str]:
	"""
    Saves an answered question to the database appending a timestamp.

    :param answer: A Choice object including the user's choice.
    :return: Tuple[bool: success, str: info]:
    """
	try:
		if _answer_already_exists():
			pass
		else:
			answer.timestamp = datetime.datetime.utcnow()  # timestamp MUST be in this format
			print(__name__ + ':Saving answer to question %s for user %s' % (answer.question_id, answer.participant_id))
			_get_collection("coll_answers").insert_one(_pickler.flatten(answer))
			return True, "Answer was successfully added to the database."
	# todo: check if combination of user_id, question_id, timestamp already in db
	except pymongo.errors.ServerSelectionTimeoutError:
		return False, "Could not connect to database. Timeout."
	except pymongo.errors.OperationFailure:
		return False, "User not authorized."


def get_answers() -> typing.List[Choice]:
	"""
	Reads all Choices from the coll_answers collection and returns them in a list.
	:return: A list of all Choices from all users.
	"""
	ret: typing.List[Choice] = []
	col = _get_collection('coll_answers')
	res = col.find()
	for r in res:
		ret.append(_unpickler.restore(r))

	return ret

def get_stress_per_day(participant_id: int, days_passed: int) -> Tuple[int, int, int]:
	"""
    Returns the number of stressors per day

    :param participant_id: The Telegram ID of the desired user.
    :param days_passed
    :return: int: stressors
    """
	coll_answers = _get_collection("coll_answers")
	ans = coll_answers.find({
		'question_id': {'$regex': '^(es)'},
		'answer': 'Yes',
		'participant_id': str(participant_id)
	}).sort('timestamp', pymongo.ASCENDING)

	ans_yes = 0
	anslist = list(ans)

	day: datetime = datetime.datetime.utcnow().date() - datetime.timedelta(days=days_passed)

	for i in range(len(anslist)):
		timestamp = _unpickler.restore(anslist[i]).timestamp.date()
		if timestamp == day:
			ans_yes += 1

	stressful = get_ss_per_day(participant_id, day, ans_yes)
	severity = get_severity_per_day(participant_id, day)
	free_text_answers = get_free_text_answers_per_day(participant_id, day)

	return ans_yes, stressful, severity, free_text_answers

def get_ss_per_day(participant_id: int, day: datetime, yes: int) -> int:
	"""
    Returns the number of subjective severity stressors

    :param participant_id: The Telegram ID of the desired user.
    :return: int: stressors
    """
	coll_answers = _get_collection("coll_answers")
	not_stressful = coll_answers.find({'question_id': {'$regex': '^(ss)'},
								'answer': 'Not at all', 'participant_id': str(participant_id)})

	stressful = yes
	nstlist = list(not_stressful)
	for i in range(len(nstlist)):
		timestamp = _unpickler.restore(nstlist[i]).timestamp.date()
		if timestamp == day:
			stressful = yes - 1

	return stressful

def get_severity_per_day(participant_id: int, day: datetime) -> int:
	"""
    Returns the severity of stressors per day

    :param participant_id: The Telegram ID of the desired user.
    :return: int: severity (each stressor has 7 primary appraisal questions with a range from 1-4)
    """
	coll_answers = _get_collection("coll_answers")
	severity1 = coll_answers.find({'question_id': {'$regex': '^(pa)'},
								'answer': 'Not at all', 'participant_id': str(participant_id)})
	severity2 = coll_answers.find({'question_id': {'$regex': '^(pa)'},
								'answer': 'A little', 'participant_id': str(participant_id)})
	severity3 = coll_answers.find({'question_id': {'$regex': '^(pa)'},
								'answer': 'Some', 'participant_id': str(participant_id)})
	severity4 = coll_answers.find({'question_id': {'$regex': '^(pa)'},
								'answer': 'A lot', 'participant_id': str(participant_id)})

	severity = 0
	sevlist1 = list(severity1)
	sevlist2 = list(severity2)
	sevlist3 = list(severity3)
	sevlist4 = list(severity4)

	for i in range(len(sevlist1)):
		timestamp = _unpickler.restore(sevlist1[i]).timestamp.date()
		if timestamp == day:
			severity += 1

	for i in range(len(sevlist2)):
		timestamp = _unpickler.restore(sevlist2[i]).timestamp.date()
		if timestamp == day:
			severity += 2

	for i in range(len(sevlist3)):
		timestamp = _unpickler.restore(sevlist3[i]).timestamp.date()
		if timestamp == day:
			severity += 3

	for i in range(len(sevlist4)):
		timestamp = _unpickler.restore(sevlist4[i]).timestamp.date()
		if timestamp == day:
			severity += 4

	return severity


def get_free_text_answers_per_day(participant_id: int, day: datetime):
	coll_answers = _get_collection("coll_answers")
	free_text_answer = coll_answers.find({'question_id': {'$regex': '^(ft-)'}, 'participant_id': str(participant_id)})

	all_answers = list(free_text_answer)
	answers_per_day = []

	for i in range(len(all_answers)):
		timestamp = _unpickler.restore(all_answers[i]).timestamp.date()
		if timestamp == day:
			answers_per_day.append(all_answers[i]['answer'])

	return answers_per_day
