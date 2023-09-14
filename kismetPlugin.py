import asyncio
import pytak
import time

# kismet imports
import websockets
import json
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET

# Kismet user and password that you assigned the first time you ran it
USER='user'
PW='password'

class KismetPlugin:
    # Copy data to the cotqueue
    class MyReceiver(pytak.QueueWorker):
        async def run(self):
            self._logger.debug("Kismet: logging in...")
            # Future: Consider using aiohttp to speed up connecting to kismet if it dow basic auth.

            # Authenticate
            r = None
            while r == None:
                try:
                    basic = HTTPBasicAuth(USER, PW)
                    url = 'http://localhost:2501/session/check_session'
                    r = requests.get(url, auth=basic)

                except Exception as e:
                    print(e)
                    self._logger.error(f"Connect failed to {url}. Retrying in 3 seconds...")
                    time.sleep(3)

            self._logger.debug("status code=%s", r.status_code)
            self._logger.debug("text=%s", r.text)
            self._logger.debug("json=%s", r.json)
            kismetCookie = get('KISMET', r.cookies, 'INVALID KEY')
            self._logger.debug("KISMET=%s", kismetCookie)

            myheaders = {
                "Cookie":f"KISMET={kismetCookie}"
            }

            # NOTE: Below is a filtered list of what data kismet should send. 
            # If we received every piece of data, it would overwhelm comms and we
            # would end up dropping network packets. So only request what you need.
            # See the kismet2cot() function below where this data is used.
            devicesRequest = "ws://localhost:2501/devices/monitor.ws"
            req = {
                "monitor": "*",
                "request": 1,
                "rate": 1,
                "fields": [ 
                    "kismet.device.base.name",
                    "kismet.common.location.geopoint",
                    "kismet.common.location.alt",
                    "kismet.device.base.manuf",
                    "dot11.advertisedssid.ssid",
                    "kismet.common.signal.max_signal"
                ]
            }

            try:
                async with websockets.connect(devicesRequest, extra_headers=myheaders) as websocket:
                    self._logger.debug("open=%s", websocket.open)
                    self._logger.debug("request_headers=%s", websocket.request_headers)
                    self._logger.debug("response_headers=%s", websocket.response_headers)

                    # Send the filtered list of what we want to see
                    await websocket.send(json.dumps(req));

                    async for data in websocket:
                        # self._logger.debug("data(kismet)=%s", data)

                        # convert the kismet data into cot
                        data = await kismet2cot(data)

                        # self._logger.debug("data(cot)=%s", data)
                        
                        # Input the cot data onto the cotqueue
                        await self.config.cotqueue.put(data)
            except websockets.exceptions.InvalidStatusCode as code:
                print('code=', code.status_code)
                if code.status_code == 401:
                    print("======================================================================")
                    print(f"Verify username({USER}) and password({PW}) are matching in kismet")
                    print("======================================================================")

async def kismet2cot(data):
    # print("data=", data)
    obj = json.loads(data)
    # print("obj=", obj)

    # NOTE: If you want to use other data from kismet, you need to add those to the filter
    # that is defined in the run() method above.
    name=get('kismet.device.base.name', obj, "UNK")
    geopoint=get('kismet.common.location.geopoint', obj, ["0.0", "0.0"])
    alt=get('kismet.common.location.alt', obj, "0")
    heading=get('kismet.common.location.heading', obj, "0")
    manf=get('kismet.device.base.manuf', obj, "UNK")
    ssid=get('dot11.advertisedssid.ssid', obj, "UNK")
    rssi=get('kismet.common.signal.max_signal', obj, "0")

    # name="UNK"
    # geopoint={"0.0", "0.0"}
    # alt="0"
    # heading="0"
    # manf="UNK"
    # ssid="UNK"
    # rssi="0"

    event = ET.Element("event")
    event.set("version", "2.0")
    event.set("type", "t-x-d-d")
    event.set("uid", ssid)
    event.set("how", "m-g")
    event.set("time", pytak.cot_time())
    event.set("start", pytak.cot_time())
    event.set("stale", pytak.cot_time(3600))

    point = ET.SubElement(event, "point")
    if len(geopoint) == 1:
        print("ONE")
        point.set("lat", "0.0")
        point.set("lon", "0.0")
    else:
        print("TWO")
        point.set("lat", list(geopoint)[0])
        point.set("lon", list(geopoint)[1])

    point.set("hae", alt) # <<<< THIS NEEDS VALIDATED
    point.set("ce", "0")

    detail = ET.SubElement(event, "detail")
    emitter = ET.SubElement(detail, "emitter")
    emitter.set("Emitter", ssid)
    emitter.set("Manf", manf)
    emitter.set("RSSI", rssi)

    # print(ET.dump(event))

    return ET.tostring(event)

def get(key, obj, default):
    # print('key=', key, ' default=', default, ' obj=', obj)
    if key in obj:
        value = obj[key]
        if value == None or value == 0 or type(value) == None:
            value = "UNK"
        # else:
            # print("return=", value, ' type=', type(value))
    else:
        # print("return=", default)
        value = default

    return value