import json
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
    return namedtuple('X', eventInfoDict.keys())(*eventInfoDict.values())


def getEventInfoObject(eventInfoJson):
    return json.loads(eventInfoJson, object_hook=customEventInfoDecoder)


def getEventInfoDict(eventInfoJson):
    return json.loads(eventInfoJson)

