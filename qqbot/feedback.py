from datetime import datetime as dt, date
import pygal
from pygal.style import Style

from dataIO import *
from user_settings import get_weekends_omitted
from sentiment_analysis import get_sentiment, get_sentiment_one_string_per_day


def stress_days(participant_id: int):
    es_days = get_es_days()

    day1 = get_stress_per_day(participant_id, es_days[0])
    day2 = get_stress_per_day(participant_id, es_days[1])
    day3 = get_stress_per_day(participant_id, es_days[2])

    return day1, day2, day3


def get_es_days() -> Tuple[int, int, int]:
    es_day1 = 3
    es_day2 = 2
    es_day3 = 1

    if get_weekends_omitted():
        today = 1 + int(dt.now().weekday())
        # if today = Monday
        if today == 1:
            # Wednesday
            es_day1 = 5
            # Thursday
            es_day2 = 4
            # Friday
            es_day3 = 3
        # if today = Tuesday
        elif today == 2:
            # Thursday
            es_day1 = 5
            # Friday
            es_day2 = 4
            # Monday
            es_day3 = 1
        elif today == 3:
            # Friday
            es_day1 = 5
            # Monday
            es_day2 = 2
            # Tuesday
            es_day3 = 1

    return es_day1, es_day2, es_day3


def calc_stress(participant_id, personality):
    stressors = []
    severe_stressors = []
    severity = []
    severity_calculated = []

    days = stress_days(participant_id)
    for i in range(len(days)):
        stressors.append(days[i][0])
        severe_stressors.append(days[i][1])
        severity.append(days[i][2])

    for i in range(len(severity)):
        if not severe_stressors[i] == 0:
            calc = severity[i] / severe_stressors[i]
        else:
            calc = 7
        severity_calculated.append(calc)

    if stressors[0] == 0 and stressors[1] == 0 and stressors[2] == 0:
        no_stressors = True
    else:
        no_stressors = False
        visualize_stress(participant_id, personality, stressors, severity_calculated)

    smileys = get_smileys(severity_calculated)
    return smileys, no_stressors


def visualize_stress(participant_id, personality, stressors, severity_calculated):
    stressors_chart_path = "feedback_images/stressors-" + personality + str(participant_id) + ".png"
    severity_chart_path = "feedback_images/severity-" + personality + str(participant_id) + ".png"
    sa_mood_chart_path = "feedback_images/sa-mood-" + personality + str(participant_id) + ".png"

    custom_style = style_chart(personality)

    bar_chart = pygal.Bar(show_y_labels=True, x_title='Days', y_title='Number of Experienced Stressors',
                          style=custom_style[1])
    bar_chart.title = 'Stress Report Chart 1'
    bar_chart.x_labels = map(str, range(1, 4))
    bar_chart.y_labels = 0, 1, 2, 3, 4, 5, 6, 7
    bar_chart.add('Stressors', stressors)
    bar_chart.render_to_png(stressors_chart_path)

    line_chart = pygal.Line(show_y_labels=True, x_title='Days', y_title='Severity of Experienced Stressors',
                            show_dots=custom_style[0], style=custom_style[1])
    line_chart.title = 'Stress Report Chart 2'
    line_chart.x_labels = map(str, range(1, 4))
    line_chart.y_labels = [{'label': 'Not at all', 'value': 7},
                           {'label': 'A little', 'value': 14},
                           {'label': 'Some', 'value': 21},
                           {'label': 'A lot', 'value': 28}]
    line_chart.add('Severity', severity_calculated)
    line_chart.render_to_png(severity_chart_path)

    sentiment = free_text_stress(participant_id)
    for n, i in enumerate(sentiment):
        if i == -2:
            sentiment[n] = 0

    line_chart_mood = pygal.Line(show_y_labels=True, x_title='Days',
                            show_dots=custom_style[0], style=custom_style[1])
    line_chart_mood.title = 'Stress Report Chart 3'
    line_chart_mood.x_labels = map(str, range(1, 4))
    line_chart_mood.y_labels = [{'label': 'Rather negative', 'value': -1},
                           {'label': 'Neutral', 'value': 0},
                           {'label': 'Rather positive', 'value': 1}]
    line_chart_mood.add('Mood', sentiment)
    line_chart_mood.render_to_png(sa_mood_chart_path)


def style_chart(personality):
    dots = False
    if personality == "default":
        dots = True
        custom_style = Style(colors=('#000000', '#000000'))
    elif personality == "ext":
        custom_style = Style(colors=('#FF3232', '#FF3232'))
    else:
        custom_style = Style(colors=('#39A7CC', '#39A7CC'))

    return dots, custom_style


def get_smileys(severity):
    stress_per_days = []
    stress = 0
    for i in severity:
        if i <= 14:
            stress = 1
        elif i <= 21:
            stress = 2
        elif i <= 28:
            stress = 3
        stress_per_days.append(stress)

    path = "smileys/stress" + str(stress_per_days[0]) + "stress" + str(stress_per_days[1]) + "stress" + str(
        stress_per_days[2]) + ".jpg"
    return path


def free_text_stress(participant_id):
    answers = []

    days = stress_days(participant_id)
    for i in range(len(days)):
        answers.append(days[i][3])

    return get_sentiment_one_string_per_day(answers)

