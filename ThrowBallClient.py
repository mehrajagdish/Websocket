import asyncio
import json
import time
from pynput import keyboard
import websockets
import multiprocessing as mp
from EventInfo import EventInfo
from EventInfo import Header

Event = mp.Manager().Value('i', 0)


def on_enter_press(key):
    if key == keyboard.Key.enter:
        print("Enter pressed")
        Event.value = 1
        time.sleep(1)
        Event.value = 0


def throw_ball(sent_to):
    header = Header("Trigger", sent_to, "throwBall", "001")
    data = {"value": "1"}
    event = EventInfo(header, data)

    eventJson = json.dumps(event, default=vars)
    return eventJson


async def client():
    uri = "ws://localhost:3000"
    disconnected = False
    while True:
        async with websockets.connect(uri) as websocket:
            print("Connection successful")
            while not disconnected:
                try:
                    await websocket.connected
                    if bool(Event.value):
                        await websocket.send(throw_ball("Player App"))
                        await websocket.send(throw_ball("Detector"))
                        time.sleep(1)

                except websockets.ConnectionClosed:
                    print("error")
                    disconnected = True
                    break

        print("connection lost... reconnecting")
        disconnected = False
        time.sleep(5)


listener = keyboard.Listener(on_press=on_enter_press)

listener.start()
asyncio.run(client())
