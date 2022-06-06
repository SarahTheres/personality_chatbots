import importlib
import logging
import os
import sys
from datetime import datetime as dt, date

import pygal

import telegram
from telegram import bot, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, Update, CallbackQuery, \
	parsemode
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, PicklePersistence,
						  CallbackQueryHandler, Dispatcher, CallbackContext)

import message_timer
import dataIO
from dataIO import *
from feedback import *
from personality_order import *
from logger_floggich import StreamToLogger
from objects import Participant, Choice, Question
from question import send_singlechoice_question, \
	send_limesurvey_question, send_freetext_question, \
	send_multiplechoice_question, get_user_id, send_abort_question
from support import send_support_message
from user_settings import get_survey_code, get_post_survey_code, get_ES_duration_days, \
	get_days_until_post_questionnaire, get_weekends_omitted, get_date_for_post_questionnaire, \
	get_es_daily_message, get_start_message, get_fs_daily_message, \
	get_offboarding_message, get_days_until_considered_unresponsive, get_unresponsive_message, get_conv_not_complete

# === LOGGING SETUP ===
# STDOUT and STDERR will both be redirected into a text file in ./logs
# INFO logging: use print()
sle = None
sli = None

if __name__ == '__main__' and not sys.argv.count("debug") > 0:
	logfolder = './logs'
	if not os.path.exists(logfolder):
		os.makedirs(logfolder)

	logging.basicConfig(
		level=logging.DEBUG,
		format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
		filename=(logfolder + "/log_" + dt.now().strftime('%d-%m-%Y_%H-%M-%S') + ".log"),
		filemode='a'
	)

	stdout_logger = logging.getLogger('STDOUT')
	sli = StreamToLogger(stdout_logger, logging.INFO)
	sys.stdout = sli

	stderr_logger = logging.getLogger('STDERR')
	sle = StreamToLogger(stderr_logger, logging.ERROR)
	sys.stderr = sle

# === GLOBAL VARIABLES ===
# states for managing which method will be called next during conversation
ASKING, ASKING_OTHER, ASKING_OTHER_MAX, ES_DONE, DONE, NAME, QUESTIONNAIRE_ID, TIMES, WAITING_CODE, NO_CONSENT, EXCLUDED, COMPLETED, CONSENT, ABORT, ERROR, END = range(16)

# states for timer and reminders
USER_TIMERS = {}
USER_QID = {}
USERNAMES = {}
ES_START_BTN = {}
#PREVIOUS_ANSWER_ID = {}

def gc(id: int) -> bool:
	"""
	Prevents the bot from interacting with groups.
	:param id: The ID to be checked it if belongs to a group.
	:return: True if message comes from a group besides the support group.
	"""
	return id < 0 and not id == dataIO.BOT_CONFIG['Study_settings']['telegram-support-group']


# === CONVERSATION METHODS ===
# checks if the limesurvey code the user entered is correct: repeats until user enters correct code.
def check_code(update, context):
	user_answer: str = str(update.message.text).lower().strip()
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	survey_code1 = user.survey_code1
	survey_code2 = user.survey_code2
	survey_code3 = user.survey_code3
	survey_code4 = user.survey_code4
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	if user_answer.lower() == get_survey_code()[0].lower() and survey_code1 == 0:
		set_survey_codes(participant_id, 1)
		print(__name__ + "Participant {0} successfully entered survey code".format(participant_id))
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["correct-code"])
		update_stage(update, context)
		ES_START_BTN[participant_id] = 0
		return DONE
	elif user_answer.lower() == get_survey_code()[1].lower() and survey_code2 == 0:
		set_survey_codes(participant_id, 2)
		print(__name__ + "Participant {0} successfully entered survey code".format(participant_id))
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["correct-code"])
		update_stage(update, context)
		ES_START_BTN[participant_id] = 0
		return DONE
	elif user_answer.lower() == get_survey_code()[2].lower() and survey_code3 == 0:
		set_survey_codes(participant_id, 3)
		print(__name__ + "Participant {0} successfully entered survey code".format(participant_id))
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["correct-code"])
		update_stage(update, context)
		ES_START_BTN[participant_id] = 0
		return DONE
	elif user_answer.lower() == get_survey_code()[3].lower() and survey_code4 == 0 and survey_code1 == 1 and survey_code2 == 1 and survey_code3 == 1:
		set_survey_codes(participant_id, 4)
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["correct-code"])
		update_stage(update, context)
		ES_START_BTN[participant_id] = 0
		return DONE
	else:
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["incorrect-code"])
		send_question(update, context)
		return WAITING_CODE

# todo what happens here? error handling

# this method is called when the user should be excluded from study
def exclude(update, context):
	participant_id = get_user_id(update)

	success, res = set_participant_progress(participant_id, 0, 0, 0)

	if success:
		print(__name__ + ": Participant {0} is excluded from the study".format(participant_id))
		update.message.reply_text(BOT_CONFIG["User_conversation"]["excluded"])
		return EXCLUDED
	else:
		print(__name__ + ": Participant {0} DB Error {1]".format(participant_id, res))
		return False


# todo what happens here? error handling


def es_done(update, context):
	"""
	this method is called when the experience sampling questionnaire is completed for today
	"""
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	username = user.username
	stage_es = user.stage_es + 1
	set_user_stages(participant_id, 0, stage_es, 0)
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	print(__name__ + ": Participant {0} has completed today's experience sampling ".format(participant_id))

	# check if this was the participant's last experience sampling
	active_days = user_duration(int(participant_id))
	#if active_days[0] and get_ES_duration_days() <= active_days[1] and stage_es == 4:
	if user.active and stage_es == 4: #TODO: 2 for tests, 4 for real study
		print(__name__ + ": User %s has been active for %s, es duration is %s days" % (
			participant_id, str(active_days[1]), str(get_ES_duration_days())))
		set_user_stages(participant_id, 0, 0, 1)

	es_done_message = BOT_CONFIG["User_conversation-" + personality]["es_done"]
	if "{name}" in es_done_message:
		es_done_message = es_done_message.replace("{name}", username)
	bot.send_message(participant_id, es_done_message, reply_markup=ReplyKeyboardRemove())
	ES_START_BTN[participant_id] = 0
	set_conv_complete(participant_id, 1)
	return DONE


def fs_done(update, context):
	"""
	this method is called when the feedback questionnaire is completed for today
	"""
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["questionnaire"])
	bot.send_message(participant_id, BOT_CONFIG["Study_settings"]["link_survey_" + personality])
	bot.send_message(participant_id, "After finishing the questionnaire, you will get a code.")

	update_user_status(update, context, dataIO.TODAYS_QUESTIONS['fs_code-' + personality])
	return send_question(update, context)


def post_questionnaire(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["questionnaire-last"])
	bot.send_message(participant_id, BOT_CONFIG["Study_settings"]["link_post_study"])
	bot.send_message(participant_id, "After finishing the questionnaire, you will get a code.")

	update_user_status(update, context, dataIO.TODAYS_QUESTIONS['fs_code-' + personality])
	return send_question(update, context)


def update_stage(update, context):
	participant_id = get_user_id(update)
	update_bot_states(update, context)
	ES_START_BTN[participant_id] = 0
	return DONE


def update_bot_states(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	username = user.username
	order = user.personality_order
	round = user.round
	post_code = user.survey_code4
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	if round == 2 and not post_code == 1:
		return post_questionnaire(update, context)
	elif round == 2 and post_code == 1:
		return end_offboarding(update, context)
	else:
		fs_done_message = BOT_CONFIG["User_conversation-" + personality]["fs_done"]
		set_conv_complete(participant_id, 1)
		if "{name}" in fs_done_message:
			fs_done_message = fs_done_message.replace("{name}", username)
		bot.send_message(participant_id, fs_done_message, reply_markup=ReplyKeyboardRemove())
		set_user_stages(participant_id, 1, 0, 0)

		bot_personality_states(participant_id, round + 1, order)
		return set_round(participant_id, round + 1)


def bot_personality_states(participant_id: int, round: int, order: int):
	if round == 0:
		if order == 0:
			bot_d = 1
			bot_e = 0
			bot_i = 0
		elif order == 1:
			bot_i = 1
			bot_d = 0
			bot_e = 0
		else:
			bot_e = 1
			bot_i = 0
			bot_d = 0

	elif round == 1:
		if order == 0:
			bot_d = 2
			bot_e = 1
			bot_i = 0
		elif order == 1:
			bot_i = 2
			bot_d = 1
			bot_e = 0
		else:
			bot_e = 2
			bot_i = 1
			bot_d = 0

	else:
		if order == 0:
			bot_d = 2
			bot_e = 2
			bot_i = 1
		elif order == 1:
			bot_i = 2
			bot_d = 2
			bot_e = 1
		else:
			bot_e = 2
			bot_i = 2
			bot_d = 1

	set_bot_states(participant_id, bot_d, bot_e, bot_i)


# todo what happens here? error handling
# this method is called in case the study is completed
def end_offboarding(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	survey_code1 = user.survey_code1
	survey_code2 = user.survey_code2
	survey_code3 = user.survey_code3
	survey_code4 = user.survey_code4
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["off-boarding-done"])

	if survey_code1 == 1 and survey_code2 == 1 and survey_code3 == 1 and survey_code4 == 1:
		set_conv_complete(participant_id, 1)
		bot.send_message(participant_id, BOT_CONFIG["Study_settings"]["link_prolific_complete"])

	set_user_active(participant_id, False)
	return END


def abort(update, context):
	participant_id = get_user_id(update)
	print(__name__ + ": Participant {0} wants to abort the  study ".format(participant_id))
	modifiedquestion = dataIO.TODAYS_QUESTIONS['noconsent_es01']
	update_user_status(update, context, modifiedquestion)
	send_question(update, context)


def no_abort(update, context):
	participant_id = get_user_id(update)

	print(__name__ + ": Participant {0} wants to abort the  study ".format(participant_id))
	bot.send_message(chat_id=update.message.chat_id, text=BOT_CONFIG["User_conversation"]["no-abort"])

	return ES_DONE


# this method is called in case of error
def error(update: Update, callback: CallbackContext):
	participant_id = get_user_id(update)

	print(__name__ + ": Participant {0} encountered an error ".format(participant_id))
	bot.send_message(chat_id=update.message.chat_id, text=BOT_CONFIG["User_conversation"]["error"])
	raise callback.error


# == CONVERSATION HELPERS ===
def update_user_status(update, context, current_question: Question = None):
	participant_id = get_user_id(update)
	context.user_data['active_question'] = current_question


def get_user_status(context) -> Question:
	return context.user_data['active_question']


def send_id(update, context):
	participant_id = get_user_id(update)
	text = "Your ID is {0}".format(participant_id)
	bot.send_message(chat_id=participant_id, text=text)


def send_document(chat_id, which):
	"""
	Sends a document from the 'files' folder to a participant.

	:param chat_id: The chat ID of the participant's conversation.
	:param which: The name of the document as referred to in config.json
	:return: None
	"""
	bot.send_document(chat_id=chat_id,
					  document=open(os.path.join(root_dir, 'files', BOT_CONFIG["Study_settings"][which]), 'rb'))


# ==== QUESTIONNAIRE CONVERSATION METHODS ====
# Sends the next question
def send_question(update, context):
	"""
	Sends the question that has been set in the user context. Conversationstatus is set according to question type.
	:return: A conversation status.
	"""
	participant_id = get_user_id(update)
	question = get_user_status(context)
	user = dataIO.get_user(participant_id)[1]
	stage_es = user.stage_es

	if question is not None:
		# get the answer options as list of Strings
		answers = question.answers
		# standard single choice question
		if question.question_type == "single-choice":
			question_msg_sc = question.question
			if "es01" in question.id:
				set_prev_qid(participant_id, answers[1].next)
				#PREVIOUS_ANSWER_ID[participant_id] = answers[1].next
			if "(this time/we spoke)" in question.question:
				if stage_es == 1:
					question_msg_sc = question.question.replace("(this time/we spoke)", "this time")
				else:
					question_msg_sc = question.question.replace("(this time/we spoke)", "we spoke")
			send_singlechoice_question(update, context, question_msg_sc, answers)
			return ASKING
		# standard freetext question
		elif question.question_type == "free-text":
			question_msg_ft = question.question
			if "(this time/we spoke)" in question.question:
				if stage_es == 1:
					question_msg_ft = question.question.replace("(this time/we spoke)", "this time")
				else:
					question_msg_ft = question.question.replace("(this time/we spoke)", "we spoke")
			bot.send_message(participant_id, question_msg_ft, parse_mode=parsemode.ParseMode.HTML)
			if "init02-" in question.id or "init02name-" in question.id:
				return NAME
			elif "init01-" in question.id or "init0103-" in question.id:
				return QUESTIONNAIRE_ID
			elif "fs_code-" in question.id:
				return WAITING_CODE
			else:
				return ASKING_OTHER
		elif question.question_type == "free-text-max":
			bot.send_message(participant_id, question.question, parse_mode=parsemode.ParseMode.HTML)
			return ASKING_OTHER_MAX
		# questions to set preferred times
		elif question.question_type == "times":
			send_singlechoice_question(update, context, question.question, answers)
			return TIMES
	else:
		print(__name__ + ": Participant {0} question could not be found ".format(participant_id))


# save the user notifcation times
def save_notifcation_times(update, context):
	query = update.callback_query
	user_answer = query.data
	participant_id = get_user_id(update)

	if user_answer.split(':')[0] == "start":
		set_survey_times(participant_id, earliest=user_answer.split(':')[1])
	elif user_answer.split(':')[0] == "stop":
		set_survey_times(participant_id, latest=user_answer.split(':')[1])
	else:
		print(__name__ + "Setting user times failed. Received answer:" + user_answer)
		return False

	# proceed with saving the user's answer in the database as usual
	return save_answer_and_next(update, context, user_answer)


def save_username(update, context):
	participant_id = get_user_id(update)
	user_answer: str = str(update.message.text)

	if not user_answer == "":
		USERNAMES[participant_id] = user_answer
		message = "Should I call you " + user_answer + " then?"
		bot.send_message(participant_id, message, reply_markup=InlineKeyboardMarkup([
			[InlineKeyboardButton("Yes", callback_data="name_true")],
			[InlineKeyboardButton("No", callback_data="name_false")]
		]
		))
	else:
		print(__name__ + "Setting username failed. Received answer:" + user_answer)
		return False


def username_next(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	if update.callback_query:
		query: CallbackQuery = update.callback_query
		if query.data == "name_true":
			if participant_id in USERNAMES:
				set_username(participant_id, USERNAMES[participant_id])
			invalidate_query(update, context)
			return save_answer_and_next(update, context, USERNAMES[participant_id])
		elif query.data == "name_false":
			invalidate_query(update, context)
			update_user_status(update, context, dataIO.TODAYS_QUESTIONS['init02name-' + personality])
			return send_question(update, context)


def save_questionnaire_id(update, context):
	participant_id = get_user_id(update)
	user_answer: str = str(update.message.text)

	if not user_answer == "":
		USER_QID[participant_id] = user_answer
		message = "Do you confirm that " + user_answer + " is your survey ID?"
		if get_user_qid_new(user_answer):
			bot.send_message(participant_id, message, reply_markup=InlineKeyboardMarkup([
				[InlineKeyboardButton("Yes", callback_data="questionnaire_id_true")],
				[InlineKeyboardButton("No", callback_data="questionnaire_id_false")]
			]
			))
		else:
			bot.send_message(participant_id, "This ID already exists.")
			update_user_status(update, context, dataIO.TODAYS_QUESTIONS['init0103-' + personality])
			return send_question(update, context)

	else:
		print(__name__ + "Setting username failed. Received answer:" + user_answer)
		return False


def questionnaire_id_next(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	if update.callback_query:
		query: CallbackQuery = update.callback_query
		if query.data == "questionnaire_id_true":
			if participant_id in USER_QID:
				set_questionnaire_id(participant_id, USER_QID[participant_id])
			update_user_status(update, context, dataIO.TODAYS_QUESTIONS['init02-' + personality])
			invalidate_query(update, context)
			return send_question(update, context)
		elif query.data == "questionnaire_id_false":
			update_user_status(update, context, dataIO.TODAYS_QUESTIONS['init0103-' + personality])
			invalidate_query(update, context)
			return send_question(update, context)


def invalidate_query(update, context):
	"""
	Use this to answer() a Callback Query and make the buttons disappear.
	"""
	if update.callback_query:
		query: CallbackQuery = update.callback_query
		query.answer()
		query.edit_message_reply_markup(InlineKeyboardMarkup([]))


def save_answer_and_next(update, context, user_answer=None):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)
	# at the ESM stage, the user timer can be used to store additional info: number of reminders, initial question time
	if str(participant_id) in USER_TIMERS:
		save_answer_db(Choice(str(participant_id), get_user_status(context).id, dt.now(),
							  user_answer,
							  USER_TIMERS[str(participant_id)].sent_reminders,
							  USER_TIMERS[str(participant_id)].message_time))
		print(__name__ + ": Participant {0}: ES answer was successfully saved".format(participant_id))
	else:
		save_answer_db(Choice(str(participant_id), str(get_user_status(context).id), dt.now(), user_answer))
		print(__name__ + ": Participant {0}: answer was successfully saved".format(participant_id))

	# Send the user's answer back and remove the inline keyboard
	if update.callback_query:
		query: CallbackQuery = update.callback_query
		if query.data == "start_es_sampling" or query.data == "start_new_es":
			return start_experience_sampling(update, context)
		elif query.data == "start_feedback":
			return start_feedback(update, context)
		elif query.data == "remove_from_study":
			return reset_and_delete(update, context)
		elif query.data == "name_true":
			print("username set")
		elif "start:" in query.data or "stop:" in query.data:
			if "start:" in query.data:
				query.bot.send_message(query.from_user.id, "Your answer: " + query.data.split("start:",1)[1])
				invalidate_query(update, context)
			else:
				query.bot.send_message(query.from_user.id, "Your answer: " + query.data.split("stop:",1)[1])
				invalidate_query(update, context)
		else:
			query.bot.send_message(query.from_user.id, "Your answer: " + query.data)
			invalidate_query(update, context)
	else:
		print("test")

	next_question_id = ""
	for a in get_user_status(context).answers:
		if a.meta == user_answer or a.answer == user_answer or len(
				get_user_status(context).answers) == 1:
			next_question_id = a.next

	if not next_question_id == "" and not next_question_id == "variable":
		return determine_next_step(update, context, user_answer, next_question_id)
	elif not next_question_id == "" and next_question_id == "variable":
		return determine_next_step(update, context, user_answer, user.prev_qid) #PREVIOUS_ANSWER_ID[participant_id])
	else:
		print(__name__ + ": Participant {0}: next step could not be determined, will repeat question".format(
			participant_id))
		bot.send_message(chat_id=participant_id, text=BOT_CONFIG["User_conversation-" + personality]["invalid-btn-input"])
		send_question(update, context)
		return ASKING


# determine the next step based on the answer's next type
def determine_next_step(update, context, user_answer, next):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	# questionnaire is completed
	if next == "time_done":
		print(__name__ + ": Participant {0}: this was the last question in questionnaire".format(participant_id))
		time_done_message = BOT_CONFIG["User_conversation-" + personality]["time_done"]
		time_done_message = time_done_message.replace("{start}", user.earliest)
		time_done_message = time_done_message.replace("{end}", user.latest)
		bot.send_message(participant_id, time_done_message)
		start_questions(update, context, True)
		return ASKING
	elif next == "fs_done":
		return fs_done(update, context)
	elif next == "code":
		return WAITING_CODE
	elif next == "es_done":
		return es_done(update, context)
	elif next in dataIO.TODAYS_QUESTIONS.keys():
		update_user_status(update, context, dataIO.TODAYS_QUESTIONS[next])
		return send_question(update, context)

	# if the user has completed the offboarding questionnaire
	elif next == "completed":
		print(__name__ + ": Participant {0} has answered last question in offboarding questionnaire".format(
			participant_id))
		end_offboarding(update, context)
		return COMPLETED

	else:
		print(__name__ + ": Participant {0}: next step could not be determined, will repeat question".format(
			participant_id))
		bot.send_message(chat_id=participant_id, text=BOT_CONFIG["User_conversation-" + personality]["invalid-btn-input"])
		return send_question(update, context)


# === STARTING QUESTIONNAIRE METHODS ===
def evaluate_timed_question_response(update, context):
	if not update.callback_query is None:
		query = update.callback_query
		query.edit_message_reply_markup(InlineKeyboardMarkup([]))
		participant_id = get_user_id(update)
		set_conv_complete(participant_id, 0)
		if query.data == "start_es_sampling" or query.data == "start_new_es":
			return start_experience_sampling(update, context)
		elif query.data == "start_feedback":
			return start_feedback(update, context)
		elif query.data == "remove_from_study":
			return reset_and_delete(update, context)
		else:
			return False


# starts the experience sampling questionnaire
def start_experience_sampling(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	# spam protection
	if gc(participant_id):
		return True  # So Bots dont get into any state

	update_user_status(update, context, dataIO.TODAYS_QUESTIONS['es0101-' + personality])
	print(__name__ + ': Participant {0} was sent first ES question today'.format(participant_id))

	# user started replying > cancel reminders
	if str(participant_id) in USER_TIMERS:
		print(__name__ + ': Participant {0} started ES for today; cancelling reminders'.format(
			participant_id))
		USER_TIMERS[str(participant_id)].timer_cancelled = True

	return send_question(update, context)


# starts the experience sampling questionnaire
def start_welcome(update, context):
	participant_id = get_user_id(update)

	# spam protection
	if gc(participant_id):
		return True  # So Bots dont get into any state

	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	set_participant_progress(participant_id, active=1)
	update_user_status(update, context, dataIO.TODAYS_QUESTIONS['init01-' + personality])

	set_user_stages(participant_id, 0, 1, 0)
	return send_question(update, context)


def start_questions(update, context, time_done):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	# spam protection
	if gc(participant_id):
		return True  # So Bots dont get into any state

	if time_done:
		update_user_status(update, context, dataIO.TODAYS_QUESTIONS['es0101t-' + personality])
	else:
		update_user_status(update, context, dataIO.TODAYS_QUESTIONS['es0101-' + personality])

	return send_question(update, context)


def start_feedback(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	smiley_path = calc_stress(participant_id, personality)[0]
	no_stressors = calc_stress(participant_id, personality)[1]

	# spam protection
	if gc(participant_id):
		return True  # So Bots dont get into any state

	stressors_chart_path = "feedback_images/stressors-" + personality + str(participant_id) + ".png"
	severity_chart_path = "feedback_images/severity-" + personality + str(participant_id) + ".png"
	sa_mood_chart_path = "feedback_images/sa-mood-" + personality + str(participant_id) + ".png"

	if personality == "ext":
		bot.send_message(participant_id, "Here comes a little image visualising my opinion on your stress over the last days. But this is just what I think. I hope you like it! 😋")
		bot.send_photo(participant_id, photo=open(smiley_path, 'rb'))

	if not no_stressors:
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["desc_chart1"])
		bot.send_photo(participant_id, photo=open(stressors_chart_path, 'rb'))
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["desc_chart2"])
		bot.send_photo(participant_id, photo=open(severity_chart_path, 'rb'))
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["calc_mood"])

		sentiment_list = free_text_stress(participant_id)
		for mood in range(len(sentiment_list)):
			if sentiment_list[mood] == -2:
				x = "no_free_text"
			elif sentiment_list[mood] >= 0.05:
				x = "positive_mood"
			elif sentiment_list[mood] <= - 0.05:
				x = "negative_mood"
			else:
				x = "neutral_mood"
			mood_message = BOT_CONFIG["User_conversation-" + personality][x]
			if "{day}" in mood_message:
				msg = mood_message.replace("{day}", str(mood + 1))
				bot.send_message(participant_id, msg)
		bot.send_photo(participant_id, photo=open(sa_mood_chart_path, 'rb'))
	else:
		bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["no_stressors"])

	# user started replying > cancel reminders
	if str(participant_id) in USER_TIMERS:
		print(__name__ + ': Participant {0} started FS for today; cancelling reminders'.format(
			participant_id))
		USER_TIMERS[str(participant_id)].timer_cancelled = True

	update_user_status(update, context, dataIO.TODAYS_QUESTIONS['fs0101-' + personality])
	return send_question(update, context)


def start_onboarding(update, context):
	participant_id = get_user_id(update)

	# spam protection
	if gc(participant_id):
		return True

	# welcome register this user
	res, info = register_new_participant(Participant(str(participant_id)))

	if res:
		set_user_stages(participant_id, 1, 0, 0)
		personality_order(participant_id)
		return start_welcome(update, context)

	# user has already sent /start once since id was found in db
	else:
		print(__name__ + ": Participant {0}: {1}".format(participant_id, info))
		# if user has already filled out initial questionnaire and should be in ES mode
		if not dataIO.get_user(participant_id)[0]:  # if user is not in database, it's a database error
			send_support_message(bot, __name__ + ": Database error.")
		else:
			user = dataIO.get_user(participant_id)[1]
			if user.active:
				personality = get_personality(user.bot_d, user.bot_e, user.bot_i)
				bot.send_message(participant_id, BOT_CONFIG["User_conversation-" + personality]["already_started"])


def reset_to_es_done(update, context):
	"""
	Set user back to after finishing the daily questionnaires without deleting data.
	"""
	participant_id = get_user_id(update)
	set_current_question(participant_id, reset=True)
	update_user_status(participant_id, context)
	set_participant_progress(participant_id, 1, 0, 1)
	return es_done(update, context)


def reset_to_beginning(update, context):
	"""
	Set the user back to before the initial questionnaire without deleting data.
	"""
	participant_id = get_user_id(update)
	set_current_question(participant_id, reset=True)
	update_user_status(participant_id, context)
	set_participant_progress(participant_id, 0, 0, 0)
	return ConversationHandler.END


def reset_and_delete(update, context):
	"""
	Completely remove the user and all their data.
	"""
	participant_id = get_user_id(update)
	set_current_question(participant_id, reset=True)
	update_user_status(participant_id, context)
	send_support_message(bot, "User %s has set a reset request and has been deleted." % participant_id)

	bot.send_message(participant_id, "You have been completely removed from all data sets. Bye.")
	remove_user(participant_id)

	return ConversationHandler.END


def reset(update: Update, context: CallbackContext):
	#return reset_and_delete(update, context)
	"""if context.args:
		if len(context.args) == 1:
			arg = context.args[0]
			if arg == 'es':
				return reset_to_es_done(update, context)
			elif arg == 'start':
				return reset_to_beginning(update, context)
			elif arg == 'erase':
				return reset_and_delete(update, context)
	return shush(update, context)"""


def delete_reminders(participant_id: str = "", message_id: int = 0):
	for m in dataIO.reminder_message(participant_id, message_id)[1]:
		if participant_id:
			print(__name__ + "Deleting reminder message for participant {0}".format(participant_id))
			bot.edit_message_reply_markup(participant_id, m)


def get_consent(update, context):
	query = update.callback_query
	user_answer = query.data
	query.answer()
	participant_id = get_user_id(update)

	if user_answer == "yes":
		set_participant_progress(participant_id, active=1)

	return save_answer_and_next(update, context, user_answer)


# starts the offboarding questionnaire
def start_offboarding(update, context):
	participant_id = get_user_id(update)

	# spam protection
	if gc(participant_id):
		return True

	print(__name__ + ": Participant {0}: offboarding successfully started".format(participant_id))
	update_user_status(update, context, dataIO.TODAYS_QUESTIONS[BOT_CONFIG['Study_settings']['post_question_id']])
	invalidate_query(update, context)

	return send_question(update, context)


def get_es_answer(update, context):
	if update.callback_query:
		query: CallbackQuery = update.callback_query
		return save_answer_and_next(update, context, query.data)
	else:
		shush(update, context)
		send_question(update, context)
		return ASKING


def get_es_text_answer_max(update, context):
	user_answer: str = str(update.message.text)
	if len(user_answer) < 10:
		return answer_too_short(update, context, ASKING_OTHER_MAX
								)
	else:
		return save_answer_and_next(update, context, user_answer)


def get_es_text_answer(update, context):
	user_answer: str = str(update.message.text)
	if len(user_answer) < 2:
		return answer_too_short(update, context, ASKING_OTHER)
	else:
		return save_answer_and_next(update, context, user_answer)


def answer_too_short(update, context, state):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)
	bot.send_message(get_user_id(update), BOT_CONFIG["User_conversation-" + personality]["answer_too_short"])
	return state


# === TIMER METHODS ===
def send_message_cancellable(chat_id, message, callback, btn, *args):
	ES_START_BTN[int(chat_id)] = 1
	print(__name__, "Timer expired for user {0}, checking if message needs to be sent".format(chat_id))
	disconnected = days_since_last_es_response(chat_id)

	if chat_id in USER_TIMERS and not USER_TIMERS[chat_id].timer_cancelled:
		if disconnected[0] and not disconnected[1] == 0: # TODO: set to 0 user did not answer anything today
			print(__name__, "Sending timed message to {0}".format(chat_id))
			USER_TIMERS[chat_id].sent_reminders += 1
			if not btn == "":
				msg = bot.send_message(chat_id, message, reply_markup=InlineKeyboardMarkup([
						[InlineKeyboardButton(btn, callback_data=callback)]
					]
					))
			else:
				msg = bot.send_message(chat_id, message)
			delete_reminders(chat_id, msg.message_id)
		else:
			print(__name__, "Participant did answer to another question of yesterday: message was not sent to {0}".format(chat_id))



# === MAIN ===
def shush(update: Update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)
	if not context.user_data['active_question'] is None:
		bot.send_message(get_user_id(update), BOT_CONFIG["User_conversation-" + personality]["invalid-input"])
	else:
		bot.send_message(get_user_id(update), "not-active")
		bot.send_message(get_user_id(update), BOT_CONFIG["User_conversation-" + personality]["invalid-input"])
#update.message.delete()


def invalid_btn_input(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)
	bot.send_message(get_user_id(update), BOT_CONFIG["User_conversation-" + personality]["invalid-btn-input"])


def done_message(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	sc1 = user.survey_code1
	sc2 = user.survey_code1
	sc3 = user.survey_code1
	personality = get_personality(user.bot_d, user.bot_e, user.bot_i)

	if not user.active:
		bot.send_message(get_user_id(update), "You have already finished the study.")
	elif user.active and ES_START_BTN[participant_id] == 0 and (sc1 == 0 or sc2 == 0 or sc3 == 0):
		bot.send_message(get_user_id(update), BOT_CONFIG["User_conversation-" + personality]["done_message"])
	elif user.active and sc1 == 1 or sc2 == 1 or sc3 == 1:
		check_code(update, context)
	else:
		invalid_btn_input(update, context)


def study_finished(update, context):
	bot.send_message(get_user_id(update), "You have already finished the study.")


def helpText(update, context):
	update.message.reply_text("Start the bot with /start or using the button below.")


def get_survey_id(update, context):
	participant_id = get_user_id(update)
	user = dataIO.get_user(participant_id)[1]
	questionnaire_id = user.questionnaire_id

	if not questionnaire_id is None:
		bot.send_message(participant_id, questionnaire_id)
	else:
		bot.send_message(participant_id, "You don't have a survey ID yet.")


def get_personality(default, ext, int):
	if default == 1:
		personality = "default"
	elif ext == 1:
		personality = "ext"
	elif int == 1:
		personality = "int"
	else:
		personality = ""
		print("no personality active")
	return personality



def update_times():
	"""
	Go through reminder times in bot_data and delete them if they already passed.
	If there are times that are today, keep them.
	:return:
	"""
	if 'reminder_times' in dp.bot_data:
		for key in dp.bot_data['reminder_times'].keys(): # k: participant, v: timers
			newtimes = []
			for t in dp.bot_data['reminder_times'][key]:
				if t > dt.today():
					newtimes.append(t)
			dp.bot_data['reminder_times'][key] = newtimes


def set_times_for_user(participant: Participant):
	if 'reminder_times' not in dp.bot_data:  # if dict does not exist, create empty
		dp.bot_data['reminder_times'] = {}
	update_times()  # clean up existing data
	if participant._id in dp.bot_data['reminder_times']:
		if len(dp.bot_data['reminder_times'][participant._id]) == 0:
			dp.bot_data['reminder_times'][participant._id] = message_timer.create_es_times(int(participant.earliest),
																						   int(participant.latest),
																						   reminders=True)
	else:
		dp.bot_data['reminder_times'][participant._id] = message_timer.create_es_times(int(participant.earliest),
																					   int(participant.latest),
																					   reminders=True)


def experience_sampling_routine():
	# Start experience sampling if today is a weekday or if all days are ES days
	if not get_weekends_omitted() or (get_weekends_omitted() and dt.now().weekday() < 5):
		print(__name__ + 'Today is the {0}. day of the week'.format(dt.now().weekday() + 1))

		# start ES for current day
		# get all users currently in ES state
		participants = get_active_participants()
		print(__name__ + ': Requested active participants. Success: {0}'.format(participants[0]))
		if participants[0]:
			for participant in participants[1]:
				# check if all necessary fields are set (should normally be the case)
				if participant.latest and participant.earliest and participant._id:
					print(__name__ + ': All properties required for ES are set for participant {0}'.format(
						participant._id))
					es_duration = user_duration(int(participant._id))

					if participant.stage_start == 1 or not participant.stage_es == 0 or participant.stage_fs == 1:
						print(
							__name__ + ': Successfully received active duration in ES stage for participant {0}: {1} days'.format(
								participant._id, es_duration[1]))

						# uncomment these lines if the post questionnaire should be sent after a given delay.
						# # check if the experience sampling stage and waiting time are over and we need to start offboarding
						# if no_of_offboarding_days <= es_duration[1]:
						# 	print(
						# 		__name__ + ': ES stage is over for participant {0} at {1} days'.format(participant._id,
						# 																			es_duration[0]))

						# 	# start offboarding
						# 	user_timer = message_timer.schedule_es_message(
						# 		participant._id,
						# 		int(participant.earliest),
						# 		int(participant.latest),
						# 		send_message_cancellable,
						# 		[participant._id, get_offboarding_message()],
						# 		False
						# 	)
						# 	USER_TIMERS[participant._id] = user_timer

						# ES is not done - we set a new timer
						# elif if code above is not commented
						if True:
							# check when the participant last responded to a question
							disconnected = days_since_last_es_response(participant._id)
							message = ""
							callback = "callback"
							btn = "Start"

							if disconnected[0] and disconnected[1] > get_days_until_considered_unresponsive():
								print(
									__name__ + ':Participant {0} has not responded for {1} days, adding action message'.format(
										participant._id, disconnected[1]))

								if participant.unresponsive > 1:
									message = "We're sorry, but you were again inactive for too long. We will now remove you from the study."
									callback = "remove_from_study"
									btn = "Okay"
								else:
									set_unresponsive(participant._id, 1)
									personality = get_personality(participant.bot_d, participant.bot_e, participant.bot_i)
									message = get_unresponsive_message(personality)
									if participant.stage_start == 1:
										message = get_unresponsive_message(personality) + ":\n\n" + get_start_message(personality, participant.username)
										btn = "Start questions"
										callback = "start_new_es"
										set_user_stages(participant._id, 0, 1, 0)
									elif participant.stage_fs == 1:
										message = get_unresponsive_message(personality) + ":\n\n" + get_fs_daily_message(personality, participant.username)
										btn = "See report"
										callback = "start_feedback"
									elif not participant.stage_es == 0:
										message = get_unresponsive_message(personality) + ":\n\n" + get_es_daily_message(personality, participant.username)
										btn = "Start questions"
										callback = "start_es_sampling"
							else:
								message = ""
								callback = ""
								btn = "Start"
								personality = get_personality(participant.bot_d, participant.bot_e, participant.bot_i)
								if participant.stage_start == 1:
									message = get_start_message(personality, participant.username)
									btn = "Start questions"
									callback = "start_new_es"
									set_user_stages(participant._id, 0, 1, 0)
								elif participant.stage_fs == 1:
									message = get_fs_daily_message(personality, participant.username)
									btn = "See report"
									callback = "start_feedback"
								elif not participant.stage_es == 0:
									message = get_es_daily_message(personality, participant.username)
									btn = "Start questions"
									callback = "start_es_sampling"

								if participant.conv_complete == 0:
									callback = ""
									btn = ""
									message = get_conv_not_complete(personality)

							print(
								__name__ + ': Schedule today\'s ES message for participant {0}'.format(
									participant._id))

							set_times_for_user(participant)

							user_timer = message_timer.schedule_es_message(send_message_cancellable,
																		   [participant._id, message, callback, btn],
																		   dp.bot_data['reminder_times'][participant._id]
																		   )
							USER_TIMERS[participant._id] = user_timer

				else:
					print(
						__name__ + ': Participant {0} is active, but some properties necessary for ES are missing'.format(
							participant._id))

def set_personalities_to_zero(update, context):
	personality_id = get_user_id(update)
	set_personality_order_counters(0,0)
	set_personality_order_counters(1,0)
	set_personality_order_counters(2,0)
	bot.send_message(personality_id, "Pers orders set to 0")

# function for all routines that should be run every day
def daily_routines():
	print(__name__ + ': Starting daily routines')
	delete_reminders()  # todo: aus context entfernen
	importlib.reload(dataIO)  # todo: does not work yet

	# delayed call of daily routines at 5am the next day
	message_timer.set_daily_routine_timer(daily_routines, 5, 0)

	experience_sampling_routine()


if __name__ == '__main__':
	# developer token
	token = 'REMOVED'

	# Make User-Specific Data persistent
	qq_persistence = PicklePersistence(filename='specbasetest')
	updater = Updater(token, use_context=True, persistence=qq_persistence)

	dp: Dispatcher = updater.dispatcher

	bot = telegram.Bot(token)

	# Add conversation handler with different states
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', start_onboarding),
					  CommandHandler('es', start_questions),
					  CommandHandler('fs', start_feedback),
					  CommandHandler('finish', start_offboarding),
					  CommandHandler('help', helpText),
					  CommandHandler('reset', reset),
					  CommandHandler('remove', reset_and_delete),
					  CommandHandler('surveyid', get_survey_id),
					  CommandHandler('personalityzero', set_personalities_to_zero)
					  ],
		allow_reentry=True,
		states={
			ASKING: [CommandHandler('reset', reset),
					 CallbackQueryHandler(get_es_answer),
					 MessageHandler(Filters.text, invalid_btn_input)],
			ASKING_OTHER: [CommandHandler('reset', reset),
						   MessageHandler(Filters.text, get_es_text_answer),
						   CallbackQueryHandler(evaluate_timed_question_response)],
			ASKING_OTHER_MAX: [CommandHandler('reset', reset),
							   MessageHandler(Filters.text, get_es_text_answer_max),
							   CallbackQueryHandler(evaluate_timed_question_response)],
			TIMES: [CommandHandler('reset', reset),
					CallbackQueryHandler(save_notifcation_times),
					MessageHandler(Filters.text, invalid_btn_input)],
			NAME: [CommandHandler('reset', reset),
				   MessageHandler(Filters.text, save_username),
				   CallbackQueryHandler(username_next)],
			QUESTIONNAIRE_ID: [CommandHandler('reset', reset),
							   MessageHandler(Filters.text, save_questionnaire_id),
							   CallbackQueryHandler(questionnaire_id_next)],
			ABORT: [CommandHandler('reset', reset),
					CallbackQueryHandler(get_es_answer)],
			NO_CONSENT: [MessageHandler(Filters.regex("^No*"), abort),
						 MessageHandler(Filters.text, save_answer_and_next)],
			WAITING_CODE: [CommandHandler('reset', reset),
						   MessageHandler(Filters.text, check_code),
						   CallbackQueryHandler(evaluate_timed_question_response)],
			EXCLUDED: [MessageHandler(Filters.text, exclude)],
			ES_DONE: [CommandHandler('reset', reset),
					  CallbackQueryHandler(evaluate_timed_question_response),
					  CommandHandler('es', start_questions),
					  CommandHandler('id', send_id),
					  CommandHandler('abort', abort),
					  MessageHandler(Filters.text, invalid_btn_input)
					  ],
			DONE: [CommandHandler('reset', reset),
				   MessageHandler(Filters.text, done_message),
				   CallbackQueryHandler(evaluate_timed_question_response)],
			COMPLETED: [CommandHandler('reset', reset),
						MessageHandler(Filters.text, end_offboarding)],
			ERROR: [MessageHandler(Filters.text, reset)],
			END: [CommandHandler('reset', reset),
				  MessageHandler(Filters.text, study_finished)],
			CONSENT: [CallbackQueryHandler(get_consent),
					  CommandHandler('reset', reset)]
		},
		fallbacks=[MessageHandler(Filters.text, shush)],
		persistent=True,
		name='statebase'
	)
	dp.add_error_handler(MessageHandler(Filters.text, error))
	dp.add_handler(conv_handler)

	# immediate call on startup
	daily_routines()

	# set info for error logging
	if sle:
		sle.set_bot_info(bot, dataIO.BOT_CONFIG['Study_settings']['telegram-support-group'])

	# Start the Bot
	updater.start_polling()

	# Run the bot until you press Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT. This should be used most of the time, since
	# start_polling() is non-blocking and will stop the bot gracefully.
	updater.idle()
