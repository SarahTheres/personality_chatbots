from typing import List

from telegram import Poll, PollOption, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, \
	InlineKeyboardButton, parsemode
import dataIO

# === METHODS FOR QUESTIONNAIRE ACCESS ===

# returns a questionnaire based on its id
from objects import Questionnaire, Question, Answer


def get_questionnaire(participant_id, questionnaire_id) -> Questionnaire:
	for questionnaire in dataIO.TODAYS_QUESTIONNAIRES:
		if questionnaire == questionnaire_id:
			return dataIO.TODAYS_QUESTIONNAIRES[questionnaire]
	else:
		print(__name__ + ": Participant{0} questionnaire could not be found".format(participant_id))
		raise Exception("Questionnaire ID was not found")  # TODO: catch this!


# returns a question object for a given index and questionnaire
def get_question(participant_id, question_index, questionnaire_id) -> Question:
	question = get_questionnaire(participant_id, questionnaire_id).questions[question_index]

	if question:
		return question
	else:
		print(__name__ + ": Participant{0} question could not be found".format(participant_id))
		raise Exception("Question ID not found.")


# returns the answering options as a String of texts for a given question object
def get_answer_options(question: Question):
	answer_options = []
	for answer in question.answers:
		answer_options.append(answer.answer)

	return answer_options


# returns question's next value for a given question index, questionnaire id and danswer as text
def get_answer_next(participant_id, question_index, questionnaire_id, given_answer):
	question = get_question(participant_id, question_index, questionnaire_id)

	if question:
		for answer in question.answers:
			if answer.answer == given_answer:
				return answer.next

		print(__name__ + ": Participant {0} answer for question nr {1} in questionnaire {2} could not be found".format(
			participant_id, question_index, questionnaire_id))
		return ""
	else:
		print(
			__name__ + ": Participant {0} question for question nr {1} in questionnaire {2} could not be found".format(
				participant_id, question_index, questionnaire_id))
		return ""


# === METHODS FOR SENDING QUESTIONS ===

def send_abort_question(update, context, question):
	participant_id = get_user_id(update)
	if update.callback_query is None:
		update.message.reply_text(question)
	else:
		update.callback_query.bot.send_message(participant_id, question)


# sends a single choice question
def send_singlechoice_question(update, context, question, answers: List[Answer]):
	participant_id = get_user_id(update)
	buttonarray = []
	user = dataIO.get_user(participant_id)[1]
	username = user.username
	for a in answers:
		if not a.meta:
			meta = a.answer
		else:
			meta = a.meta
		buttonarray.append(InlineKeyboardButton(a.answer, callback_data=meta))

	if update.callback_query is None:
		print(__name__ + ": Participant {0} is in single choice question".format(participant_id))
		if "{name}" in question:
			question = question.replace("{name}", username)
		if "\n" in question:
			print(__name__ + ": Participant {0} there is a line break".format(participant_id))
			questionparts = question.split("\n")
			update.message.reply_text(
				text=questionparts[0],
				parse_mode=parsemode.ParseMode.HTML,
			)
			update.message.reply_text(
				text = questionparts[1],
				parse_mode=parsemode.ParseMode.HTML,
				reply_markup=InlineKeyboardMarkup.from_column(buttonarray)
			)

		else:
			print(__name__ + ": Participant {0} there is no line break".format(participant_id))
			update.message.reply_text(
				text = question,
				parse_mode=parsemode.ParseMode.HTML,
				reply_markup=InlineKeyboardMarkup.from_column(buttonarray)
			)
	else:
		if "{name}" in question:
			question = question.replace("{name}", username)
		if "\n" in question:
			print(__name__ + ": Participant {0} there is a line break".format(participant_id))
			questionparts = question.split("\n")
			update.callback_query.bot.send_message(
				chat_id=participant_id,
				text=questionparts[0],
				parse_mode=parsemode.ParseMode.HTML
			)
			update.callback_query.bot.send_message(
				chat_id=participant_id,
				text=questionparts[1],
				parse_mode=parsemode.ParseMode.HTML,
				reply_markup=InlineKeyboardMarkup.from_column(buttonarray)
			)
		else:
			print(__name__ + ": Participant {0} there is no line break".format(participant_id))
			update.callback_query.bot.send_message(
				chat_id=participant_id,
				text=question,
				parse_mode=parsemode.ParseMode.HTML,
				reply_markup=InlineKeyboardMarkup.from_column(buttonarray)
			)
	print(__name__ + ": Participant {0} was sent a single choice question".format(participant_id))


# sends a freetext question
def send_freetext_question(update, context, question):
	participant_id = get_user_id(update)
	# update.message.reply_text(question)
	update.callback_query.bot.send_message(participant_id, question, parse_mode=parsemode.ParseMode.HTML)

	print(__name__ + ": Participant {0} was sent a freetext question".format(participant_id))

# not needed at the moment, not working!!
# sends a multiple choice question as poll
def send_multiplechoice_question(update, context, id, question, answers):
	update.bot.send_poll(
		chat_id=id,
		question=question,
		options=answers,
		is_anonymous=True,
		allows_multiple_answers=True,
	)
	print(__name__ + ": Participant {0} is sent a multiple choice question".format(update.message.chat_id))


# sends a limesurvey link
def send_limesurvey_question(update, context, question, post: bool):
	participant_id = get_user_id(update)
	lresult = dataIO.get_limesurvey_link(participant_id, post=post)
	if not lresult[0]: # user has already finished onboarding
		return "skip"
	question_text = question + " \n " + lresult[1]
	print(__name__ + ": Participant {0} will be sent limesurvey questionnaire".format(participant_id))

	if update.callback_query is None:
		update.message.reply_text(
			question_text
		)
	else:
		update.callback_query.bot.send_message(
			chat_id=participant_id,
			text=question_text
		)


def get_user_id(update):
	"""
	Returns the user ID independent of the type of update
	:param update: The update as received from the dispatcher.
	:return: A user ID.
	"""
	if update.message is None:
		query = update.callback_query
		return query.message.chat.id
	else:
		return update.message.chat_id