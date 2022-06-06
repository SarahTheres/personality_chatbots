import threading
import random
from datetime import datetime as dt, timedelta

import typing

from user_settings import get_repeat_notification_day, get_time_h_between_notifcations, get_ES_duration_days, \
	get_days_until_post_questionnaire


def create_es_times(earliest_time: int, latest_time: int, arguments=None, reminders: bool = False) -> dt.date:
	"""
    Sets timers for a user, given time constraints and a function to execute at the specified time

    :param user: chat ID the timers belong to
    :param earliest_time: hour of day where we can start sending messages
    :param latest_time: hour of day where we should stop sending messages
    :param send_message_function: function to execute when timer expires
    :param arguments: arguments to pass to send_message_function
    :param reminders: should the timer have reminders or only be sent once?
    :return: UserTimer: timer object including reminders, function to execute on expiration, and that function's arguments
    """
	if arguments is None:
		arguments = []
	send_time = get_random_time(earliest_time, latest_time)
	if arguments.count("test") > 0:
		send_time = dt.today() + timedelta(seconds=20)
	latest_send_time = dt.today().replace(hour=latest_time, minute=0, second=0)
	longest_delay = round(latest_send_time.timestamp() - dt.today().timestamp())
	print(__name__ + ': Maximum delay until end time: {0}.'.format(longest_delay))

	times: typing.List[dt.date] = []

	if reminders:
		while (len(times) <= get_repeat_notification_day() and  # as long as the reminders don't exceed lastes_time
			   send_time + timedelta(hours=len(times) * get_time_h_between_notifcations()) < dt.today().replace(
					hour=latest_time, minute=0, second=0)):
			new_time = send_time + timedelta(hours=len(times) * get_time_h_between_notifcations())
			times.append(new_time)
			print(__name__ + ': Adding time for reminder no. {0} with at {1}.'.format(len(times), new_time))
	else:
		new_time = send_time + timedelta(hours=len(times) * get_time_h_between_notifcations())
		times.append(new_time)
		print(__name__ + ': Adding time for reminder no. {0} with at {1}.'.format(len(times), new_time))

	return times


def schedule_es_message(send_message_function, arguments: typing.List, times: typing.List[dt]) -> 'UserTimer':
	"""
    Sets timers for a user, given time constraints and a function to execute at the specified time

    :param send_message_function: function to execute when timer expires
    :param arguments: arguments to pass to send_message_function
    :return: UserTimer: timer object including reminders, function to execute on expiration, and that function's arguments
    """
	ut = UserTimer(times[0])
	for t in times:
		new_delay = (t - dt.today()).total_seconds()
		new_timer = threading.Timer(new_delay, send_message_function, arguments)
		new_timer.daemon = True
		new_timer.start()
		ut.timers.append(new_timer)
		print(__name__ + ': Adding timer/reminder no. {0} with a delay of {1} seconds.'.format(len(ut.timers), new_delay))
	return ut


def get_random_time(earliest_hour: int, latest_hour: int) -> dt:
	"""Returns a random datetime object for the current day

    Arguments:
        earliest_hour {int} -- earliest hour to be selected in 24h format
        latest_hour {int} -- latest hour to be selected in 24h format

    Raises:
        ValueError: earliest hour and latest hour must be in the range 0-23 and latest must be after earliest

    Returns:
        datetime -- Random datetime object given the hour constraints
    """

	# check that earliest_hour is before the latest_hour
	if (earliest_hour < latest_hour):

		# make sure ranges are within suitable bounds
		earliest_hour = max(earliest_hour, 0)
		latest_hour = min(latest_hour, 23)

		# get next day
		today = dt.today()
		# get random hour and minute
		hour = random.randrange(int(earliest_hour), int(latest_hour))  # [earliest_hour, latest_hour)
		minute = random.randint(0, 59)  # [0, 59]
		today_times = today.replace(hour=hour, minute=minute)

		print(__name__ + ': Defined time for timer: {0}'.format(today_times))

		return today_times

	else:
		print(__name__ + ': Earliest hour was after latest hour: {0} after {1}'.format(earliest_hour, latest_hour))
		raise ValueError("earliest hour must be before latest hour")


def get_specific_time_next_day(hour: int, minute: int) -> dt:
	"""Returns a datetime object that represents a specific hour and minute on the next day

    Arguments:
        hour {int} -- hour to be set on datetime object
        minute {int} -- minute to be set on datetime object

    Raises:
        ValueError: hour range must be 0 to 23
        ValueError: minute range must be 0 to 59

    Returns:
        datetime -- datetime object with given hour and minute on the next day
    """

	# error check for input
	if 0 > hour or hour > 23:
		raise ValueError("hour range is 0 to 23")
	if 0 > minute or minute > 59:
		raise ValueError("minute range is 0 to 59")

	tomorrow = dt.today() + timedelta(days=1)
	tomorrow_times = tomorrow.replace(hour=hour, minute=minute, second=0)

	print(__name__ + ': Defined time for timer next day: {0}'.format(tomorrow_times))
	return tomorrow_times


def set_daily_routine_timer(daily_routines, hour: int, minute: int) -> threading.Timer:
	timer = threading.Timer(get_specific_time_next_day(hour, minute).timestamp() - dt.today().timestamp(),
							daily_routines)
	timer.daemon = True
	timer.start()
	return timer


class UserTimer:
	def __init__(self, initial_message_time):
		self.timers = []
		# self.next_message = next_message
		self.message_time = initial_message_time
		self.sent_reminders = -1
		# the cancelled flag is necessary for timers that have already started
		self.timer_cancelled = False
# current_reminder_time = message_time
# while (current_reminder_time)
