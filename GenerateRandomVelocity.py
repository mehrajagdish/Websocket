import random


def get_random_velocity():
    vx = random.randint(-70, 70)
    vy = random.randint(-70, 70)
    vz = random.randint(0, 70)
    data = {
        "vX": vx,
        "vY": vy,
        "vZ": vz
    }
    return data
