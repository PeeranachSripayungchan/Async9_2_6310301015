import time
import random
import json
import asyncio
import aiomqtt
from enum import Enum

student_id = "6310301015"

class MachineStatus(Enum):
    pressure = round(random.uniform(2000,3000), 2)
    temperature = round(random.uniform(25.0,40.0), 2)

class MachineMaintStatus(Enum):
    filter = random.choice(["clear", "clogged"])
    noise = random.choice(["quiet", "noisy"])

class WashingMachine:
    def __init__(self, serial):
        self.MACHINE_STATUS = 'OFF'
        self.SERIAL = serial
        self.Task = None

    def Cancel(self):
        if self.Task != None:
            self.Task.cancel()
            self.Task = None

async def publish_message(w, client, app, action, name, value):
    print(f"{time.ctime()} - [{w.SERIAL}] {name}:{value}")
    await asyncio.sleep(2)
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : w.SERIAL,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUBLISH - [{w.SERIAL}] - {payload['name']} > {payload['value']}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{w.SERIAL}"
                        , payload=json.dumps(payload))
    
async def Roaming(w, name):
    print(f"{time.ctime()} - PUBLISH - [{w.SERIAL} - {w.MACHINE_STATUS}] {name} START")
    await asyncio.sleep(3600)

async def Running(w, action):
    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] {action} START")

    if action == "FILLWATER":
        # Simulate filling water
        await asyncio.sleep(10)  # Adjust the time as needed


async def CoroWashingMachine(w, client):
    while True:
        wait_next = round(10*random.random(),2)
        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to start... {wait_next} seconds.")
        await asyncio.sleep(wait_next)
        if w.MACHINE_STATUS == 'OFF':
            continue
        if w.MACHINE_STATUS in ['READY', 'HEATMAKER']:
            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")

            if w.MACHINE_STATUS == 'READY':
                await publish_message(w, client, "app", "get", "STATUS", "READY")
                await publish_message(w, client, "app", "get", "STATUS", "FILLWATER")
                w.Task = asyncio.create_task(Running(w, "FILLWATER"))
            else:
                await publish_message(w, client, "app", "get", "STATUS", "HEATMAKER")
                w.Task = asyncio.create_task(Running(w, "HEATMAKER"))

            wait_coro = asyncio.wait_for(w.Task, timeout = 10)

            try:
                await wait_coro
            except asyncio.TimeoutError:
                print(f"{time.ctime()} - [{w.SERIAL}] FILLWATER TIMEOUT")
                await publish_message(w, client, "app", "get", "FAULT", "TIMEOUT")
                w.MACHINE_STATUS = 'FAULT'
                await publish_message(w, client, "app", "get", "STATUS", w.MACHINE_STATUS)
                continue

            except asyncio.CancelledError:
                print(f"{time.ctime()} - [{w.SERIAL}] {w.MACHINE_STATUS} Cancelled")
                if w.MACHINE_STATUS == 'READY':
                    w.MACHINE_STATUS = 'HEATMAKER'
                    await publish_message(w, client, "app", "get", "STATUS", "HEATMAKER")



            # door close

            # fill water untill full level detected within 10 seconds if not full then timeout 

            # heat water until temperature reach 30 celcius within 10 seconds if not reach 30 celcius then timeout

            # wash 10 seconds, if out of balance detected then fault

            # rinse 10 seconds, if motor failure detect then fault

            # spin 10 seconds, if motor failure detect then fault

            # ready state set 

            # When washing is in FAULT state, wait until get FAULTCLEARED

            w.MACHINE_STATUS = 'OFF'
            await publish_message(w, client, "app", "get", "STATUS", w.MACHINE_STATUS)
            continue
            

async def listen(w, client):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        async for message in messages:
            m_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}"):
                # set washing machine status
                print(f"{time.ctime()} - MQTT - [{m_decode['serial']}]:{m_decode['name']} => {m_decode['value']}")
                if (m_decode['name']=="STATUS" and m_decode['value']=="READY"):
                    w.MACHINE_STATUS = 'READY'
'''                
async def cancel_me():
    print('cancel_me(): before sleep')

    try:
        # Wait for 1 hour
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print('cancel_me(): cancel sleep')
        raise
    finally:
        print('cancel_me(): after sleep')]

async def make_request_with_timeout():
    try:
        async with asyncio.timeout(1):
            # Structured block affected by the timeout:
            await make_request()
            await make_another_request()
    except TimeoutError:
        log("There was a timeout")
    # Outer code not affected by the timeout:
    await unrelated_code()
'''
async def main():
    w = WashingMachine(serial='SN-001')
    async with aiomqtt.Client("broker.hivemq.com") as client:
        await asyncio.gather(listen(w, client) , CoroWashingMachine(w, client))
        
asyncio.run(main())