import importlib

import dataIO

# returns link to the consent information
def get_consent_link():
	return dataIO.BOT_CONFIG["Study_settings"]["link_consent_text"]

# returns the valid code for the pre survey
def get_survey_code():
	return dataIO.BOT_CONFIG["Study_settings"]["survey-code-1"], dataIO.BOT_CONFIG["Study_settings"]["survey-code-2"], dataIO.BOT_CONFIG["Study_settings"]["survey-code-3"], dataIO.BOT_CONFIG["Study_settings"]["survey-code-4"]

# returns the valid code for the post survey
def get_post_survey_code():
	return dataIO.BOT_CONFIG["Study_settings"]["post-survey-code"]

# return the maximum number of daily ESM reminders
def get_repeat_notification_day():
	return dataIO.BOT_CONFIG["Study_settings"]["repeat_notification_day"]

# get time between reminders for ES message in hours
def get_time_h_between_notifcations():
	return dataIO.BOT_CONFIG["Study_settings"]["time_h_between_notifcations"]

# returns the message that should be sent to participants each day during the ES stage
def get_es_daily_message(personality, username):
	msg = dataIO.BOT_CONFIG["User_conversation-" + personality]["ES_daily_message"]
	if "{name}" in msg:
		msg = msg.replace("{name}", username)
	return msg


# returns the message that should be sent to participants each day during the FS stage
def get_fs_daily_message(personality, username):
	msg = dataIO.BOT_CONFIG["User_conversation-" + personality]["fs_start"]
	if "{name}" in msg:
		msg = msg.replace("{name}", username)
	return msg


# returns the message that should be sent to participants as welcome of 2nd and 3rd bot
def get_start_message(personality, username):
	msg = dataIO.BOT_CONFIG["User_conversation-" + personality]["welcome-not-first"]
	if "{name}" in msg:
		msg = msg.replace("{name}", username)
	return msg

# returns the duration of the ES stage in days
def get_ES_duration_days():
	return dataIO.BOT_CONFIG["Study_settings"]["ES_duration_days"]

# returns the message that should be sent to participants for starting the offboarding
def get_offboarding_message():
	return dataIO.BOT_CONFIG["User_conversation"]["offboarding_message"]

# returns the duration of the ES stage in days
def get_days_until_post_questionnaire():
	return dataIO.BOT_CONFIG["Study_settings"]["days_until_post_questionnaire"]

# returns the day where the invite to the post-study questionnaire should be sent
def get_date_for_post_questionnaire():
	_refresh()
	return dataIO.BOT_CONFIG["Study_settings"]["date_for_post_questionnaire"]

# returns the days until a participant is considered unresponsive
def get_days_until_considered_unresponsive():
	return dataIO.BOT_CONFIG["Study_settings"]["days_until_considered_unresponsive"]

# returns the message to send to participants when they are unresponsive
def get_unresponsive_message(personality):
	return dataIO.BOT_CONFIG["User_conversation-" + personality]["unresponsive_message"]

def get_conv_not_complete(personality):
	return dataIO.BOT_CONFIG["User_conversation-" + personality]["conv_not_complete_message"]

# returns the message to send to participants when they are unresponsive
def get_weekends_omitted():
	return dataIO.BOT_CONFIG["Study_settings"]["omit_weekends"] == "False"

# returns the transformed pm time
def get_time(time: int):
	return 24 - (12 - time)

def _refresh():
	importlib.reload(dataIO)