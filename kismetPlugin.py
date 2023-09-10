import asyncio
import pytak

# kismet imports
import websockets
import json
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET

class KismetPlugin:
    # Copy data to the cotqueue
    class MyReceiver(pytak.QueueWorker):
        async def run(self):
            self._logger.debug("Kismet: logging in...")
            # Future: Consider using aiohttp to speed up connecting to kismet if it dow basic auth.

            # Authenticate
            basic = HTTPBasicAuth('login', 'password')
            r = requests.get('http://localhost:2501/session/check_session', auth=basic)
            kismetCookie = r.cookies['KISMET']

            self._logger.debug("status code=%s", r.status_code)
            self._logger.debug("text=%s", r.text)
            self._logger.debug("KISMET=%s", kismetCookie)
            self._logger.debug("json=%s", r.json)

            myheaders = {
                "Cookie":f"KISMET={kismetCookie}"
            }

            devicesRequest = "ws://localhost:2501/devices/monitor.ws"
            req = {
                "monitor": "*",
                "request": 1,
                "rate": 1,
                "fields": [ 
                "kismet.device.base.name",
                "dot11.advertisedssid.ssid",
                "kismet.common.location.geopoint",
                "kismet.historic.location.geopoint",
                "kismet.common.seenby.last_time",
                "dot11.advertisedssid.last_time"
                ]
            }

            async with websockets.connect(devicesRequest, extra_headers=myheaders) as websocket:
                self._logger.debug("open=%s", websocket.open)
                self._logger.debug("request_headers=%s", websocket.request_headers)
                self._logger.debug("response_headers=%s", websocket.response_headers)

                # Send the filtered list of what we want to see
                await websocket.send(json.dumps(req));

                async for data in websocket:
                    # convert the kismet data into cot
                    self._logger.debug("data(kismet)=%s", data)
                    data = kismet2cot(data)
                    self._logger.debug("data(cot)=%s", data)
                    
                    # Input the cot data onto the cotqueue
                    await self.config.cotqueue.put(data)

def kismet2cot(data):
    obj = json.loads(data)
    # print(f'open=[{data}')
    name=obj['kismet.device.base.name']
    # print(f'name=[{name}')

    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("type", "t-x-d-d")
    root.set("uid", name)
    root.set("how", "m-g")
    root.set("time", pytak.cot_time())
    root.set("start", pytak.cot_time())
    root.set("stale", pytak.cot_time(3600))
    return ET.tostring(root)
