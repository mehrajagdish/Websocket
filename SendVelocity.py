import json
from EventInfo import EventInfo, Header, Data, BayInfo
from GenerateRandomVelocity import get_random_velocity
from EventEnums import Events, Devices


def get_velocity():
    bayInfo = BayInfo(isForAllBays=False, bayId="001")
    header = Header(Devices.DETECTOR.value, [Devices.UNITY.value], Events.CURRENT_BALL_VELOCITY.value, bayInfo)
    data = Data({"value": get_random_velocity()})
    event = EventInfo(header, data)

    eventJson = json.dumps(event, default=vars)
    return eventJson
