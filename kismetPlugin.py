import asyncio
import pytak
import time

# kismet imports
import websockets
import json
import requests
from requests.auth import HTTPBasicAuth

# TAK imports
from takproto.constants import (
    ISO_8601_UTC,
    DEFAULT_MESH_HEADER,
    DEFAULT_PROTO_HEADER,
    TAKProtoVer,
)
from takproto.proto import TakMessage

from multicast import Multicast
from cot import CoT

class KismetReceiver(pytak.QueueWorker):
    # Keys and Aliases for the data we want to receive from kismet
    basenameKey="kismet.device.base.name"
    basenameAlias="device.name"
    lastGeopointKey="kismet.device.base.location/kismet.common.location.last/kismet.common.location.geopoint"
    lastGeopointAlias="location.geopoint"
    # Very strange: signal only works if I use an underbar vice a period on last node:
    rssiKey="kismet.device.base.signal/kismet.common.signal.last_signal"
    rssiAlias="signal.last.signal"
    altKey="kismet.common.location.alt"
    altAlias="alt"
    manufKey="kismet.device.base.manuf"
    manufAlias="manuf"
    ssidKey="dot11.device/dot11.device.advertised.ssid.map/dot11.advertisedssid.ssid"
    ssidAlias="dot11.advertisedssid.ssid"
    macAddrKey="kismet_device_base_macaddr"
    macAddrAlias="macAddr"

    async def run(self):
        self._logger.debug("Kismet: logging in...")
        # Future: Consider using aiohttp to speed up connecting to kismet if it does basic auth.

        # Authenticate with kismet
        response = None
        while response == None:
            try:
                # Kismet user and password that you assigned the first time you ran it
                KISMET_USER = self.config["KISMET_USER"]
                KISMET_PASSWORD = self.config["KISMET_PASSWORD"]
                basic = HTTPBasicAuth(KISMET_USER, KISMET_PASSWORD)
                url = 'http://localhost:2501/session/check_session'
                response = requests.get(url, auth=basic)

            except Exception as e:
                # print(e)
                self._logger.error(f"Connect failed to {url}. Retrying in 3 seconds...")
                time.sleep(3)

        # Use the kismet cookie for subsequent requests
        kismetCookie = self.get('KISMET', response.cookies, 'INVALID KEY')
        self._logger.debug("KISMET=%s", kismetCookie)

        myheaders = {
            "Cookie":f"KISMET={kismetCookie}"
        }

        # NOTE: Below is a filtered list of what data kismet should send to you. 
        # If we received every piece of data, it would overwhelm comms and we
        # would end up dropping network packets. So only request what you need.
        # See the kismet2cot() function below where this data is used.
        devicesRequest = "ws://localhost:2501/devices/monitor.ws"

        req = {
            "monitor": "*",
            "request": 1,
            "rate": 1,
            "fields": [ 
                [self.basenameKey, self.basenameAlias],
                [self.lastGeopointKey, self.lastGeopointAlias],
                [self.altKey, self.altAlias],
                [self.manufKey, self.manufAlias],
                [self.ssidKey, self.ssidAlias],
                [self.rssiKey, self.rssiAlias],
                [self.macAddrKey, self.macAddrAlias]
            ]
        }

        try:
            # Temporary hack to get things working
            # Replace with queue based message passing
            mc = Multicast(asyncio.Queue())

            # Now request the data from kismet
            async with websockets.connect(devicesRequest, extra_headers=myheaders) as websocket:
                self._logger.debug("open=%s", websocket.open)
                self._logger.debug("request_headers=%s", websocket.request_headers)
                self._logger.debug("response_headers=%s", websocket.response_headers)

                # Send the filtered list of what we want to see
                await websocket.send(json.dumps(req));

                async for data in websocket:
                    self._logger.debug("kismet=%s", data)

                    # convert the kismet data into cot
                    cot = CoT()
                    await self.kismet2cot(data, cot)
                    self._logger.info("cot=%s", cot.toString())

                    # protover = TAKProtoVer.MESH
                    # pb = cot.toProtobuf(cot.tak_message, protover)
                    pb = cot.getPayload()                    
                    mc.send(pb)
                    
                    # Input the cot data onto the cotqueue
                    await self.config.cotqueue.put(data)
        except websockets.exceptions.InvalidStatusCode as code:
            print('code=', code.status_code)
            if code.status_code == 401:
                print("======================================================================")
                print(f"Verify username({KISMET_USER}) and password({KISMET_PASSWORD}) are matching in kismet")
                print("======================================================================")
        except Exception as e:
            print(e)
            self._logger.fatal(f"Connect failed to {devicesRequest}.")

    async def kismet2cot(self, data: str, cot: CoT=CoT()):
        # Deserialize str instance containing a JSON document to a Python object.
        obj: dict = json.loads(data)

        name=self.get(self.basenameAlias, obj, "UNK")
        lat=0.0
        lon=0.0

        if self.lastGeopointAlias in obj:
            geopoint = obj[self.lastGeopointAlias]
            if geopoint==None or geopoint==0:
                lat = 0.0
                lon = 0.0
            else:
                lat = float(geopoint[1])
                lon = float(geopoint[0])

        alt=self.get(self.altAlias, obj, "0")
        # heading=self.get(headingAlias, obj, "0")
        manf=self.get(self.manufAlias, obj, "UNK")
        ssid=self.get(self.ssidAlias, obj, "UNK")
        rssi=self.get(self.rssiAlias, obj, "0")
        macAddr=self.get(self.macAddrAlias, obj, "0")

        # Populate the CoT event
        cot.setType("a-u-G")
        cot.setUid(name)
        cot.setTime(cot.cot_time())
        cot.setStart(cot.cot_time())
        cot.setStale(cot.cot_time(3600))
        cot.setLat(lat)
        cot.setLon(lon)

        return cot

    def get(self, key: str, obj: dict, default):
        # print('key=', key, ' default=', default, ' obj=', obj)
        if key in obj:
            value = obj[key]
            if value == None or type(value) == None:
                value = default
        else:
            value = default

        if not isinstance(value, str):
            value = str(value)

        # print("return=", value)
        return value

