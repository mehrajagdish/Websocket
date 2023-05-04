import json
from collections import namedtuple


class Header:
    def __init__(self, sent_by, sent_to, event_name, bay_id):
        self.sentBy = sent_by
        self.sentTo = sent_to
        self.eventName = event_name
        self.bayId = bay_id


class EventInfo:
    def __init__(self, header, data):
        self.header = header
        self.data = data


def customEventInfoDecoder(eventInfoDict):
    return namedtuple('X', eventInfoDict.keys())(*eventInfoDict.values())


def getEventInfoObject(eventInfoJson):
    return json.loads(eventInfoJson, object_hook=customEventInfoDecoder)


def getEventInfoDict(eventInfoJson):
    return json.loads(eventInfoJson)
