import json
from EventInfo import EventInfo
from EventInfo import Header
from GenerateRandomVelocity import get_random_velocity
from EventEnums import Events, Devices


def get_velocity():

    header = Header(Devices.DETECTOR.value, Devices.UNITY.value, Events.CURRENT_BALL_VELOCITY.value, "001")
    data = {"value": get_random_velocity()}
    event = EventInfo(header, data)

    eventJson = json.dumps(event, default=vars)
    return eventJson
