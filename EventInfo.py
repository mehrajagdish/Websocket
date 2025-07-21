import json
import keyword
from collections import namedtuple


class BayInfo:
    def __init__(self, isForAllBays: bool, bayId: str):
        self.isForAllBays = isForAllBays
        self.bayId = bayId


class Header:
    def __init__(self, sent_by: str, sent_to: list[str], event_name: str, bay_info: BayInfo):
        self.sentBy = sent_by
        self.sentTo = sent_to
        self.eventName = event_name
        self.bayInfo = bay_info


class Data:
    def __init__(self, value):
        self.value = value


class EventInfo:
    def __init__(self, header: Header, data: Data):
        self.header = header
        self.data = data


def customEventInfoDecoder(eventInfoDict):
    renamed_dict = {}
    for key, value in eventInfoDict.items():
        # Rename reserved keywords like 'from', 'class', 'def' etc.
        if keyword.iskeyword(key):
            renamed_dict[key + '_value'] = value
        else:
            renamed_dict[key] = value
    return namedtuple('X', renamed_dict.keys())(*renamed_dict.values())


def getEventInfoObject(eventInfoJson):
    return json.loads(eventInfoJson, object_hook=customEventInfoDecoder)


def getEventInfoDict(eventInfoJson):
    return json.loads(eventInfoJson)

