import json
from EventInfo import EventInfo
from EventInfo import Header
from GenerateRandomVelocity import get_random_velocity


def get_velocity():

    header = Header("Detector", "Unity", "currentBallVelocity", "001")
    data = {"value": get_random_velocity()}
    event = EventInfo(header, data)

    eventJson = json.dumps(event, default=vars)
    return eventJson
