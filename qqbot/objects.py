import datetime
from dataclasses import dataclass, field
from typing import List, Dict

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


@dataclass
class Participant(object):
    _id: str
    username: str = ""
    pretoken: str = ""
    posttoken: str = ""
    init_complete: bool = False
    post_complete: bool = False
    questionnaire_id: str = ""
    question_id: str = ""
    question_index: int = -1
    survey_code1: int = 0
    survey_code2: int = 0
    survey_code3: int = 0
    survey_code4: int = 0
    active: bool = False
    earliest: int = 0
    latest: int = 0
    # 0: not active, 1: active, 2: finished
    bot_d: int = 0
    bot_e: int = 0
    bot_i: int = 0
    # 0: not active, 1: active
    stage_start: int = 0
    stage_es: int = 0 # active days
    stage_fs: int = 0
    # 0: dei, 1: ide, 2: eid
    personality_order: int = -1
    round: int = 0
    unresponsive: int = 0
    conv_complete: int = 0
    prev_qid: str = ""


@dataclass
class Choice(object):
    participant_id: str
    question_id: str
    timestamp: datetime.datetime.today()
    answer: str
    reminder_count: int = 0
    initial_message_time: datetime.datetime = None


@dataclass
class Question(object):
    id: str
    index: int
    question: str
    question_type: str
    answers: List['Answer']


@dataclass
class Answer(object):
    index: int
    answer: str
    next: str
    meta: str = ""

@dataclass
class PersonalityOrder(object):
    order_dei: int = 0
    order_ide: int = 0
    order_eid: int = 0

@dataclass
class QuestionnaireJson(object):
    id: str
    title: str
    schedule: str
    questions: List[Question]
    release_date_str: str = ""
    best_before_date_str: str = ""
    optional: bool = False


@dataclass
class Questionnaire(object):
    id: str = ""
    title: str = ""
    schedule: str = ""
    questions: List[Question] = field(default_factory=list)
    release_date: datetime.datetime = None
    best_before: datetime.datetime = None
    optional: bool = False

    def feed_json(self, json_obj: QuestionnaireJson):
        for k in vars(self).keys():
            if k in vars(json_obj).keys():
                vars(self)[k] = vars(json_obj)[k]
        self.best_before = datetime.datetime.strptime(json_obj.best_before_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        self.release_date = datetime.datetime.strptime(json_obj.release_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")

