import time
import logging

# pytak imports
import pytak

# kismet imports
import websockets
import json
import requests
from requests.auth import HTTPBasicAuth
from cot import CoT

class KismetReceiver(pytak.QueueWorker):
    _logger = logging.getLogger(__name__)

    # Keys and Aliases for the data we want to receive from kismet
    basenameKey="kismet.device.base.name"
    basenameAlias="device.name"
    lastGeopointKey="kismet.device.base.location/kismet.common.location.last/kismet.common.location.geopoint"
    lastGeopointAlias="location.geopoint"
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
        while True:
            response = None
            while response == None:
                try:
                    # Kismet user and password that you assigned the first time you ran it
                    KISMET_USER = self.config["KISMET_USER"]
                    KISMET_PASSWORD = self.config["KISMET_PASSWORD"]
                    basic = HTTPBasicAuth(KISMET_USER, KISMET_PASSWORD)
                    
                    # Where is kismet running at?
                    kismetHost = self.config["KISMET_HOST"]
                    kismetPort = self.config["KISMET_PORT"]
                    # url = 'http://localhost:2501/session/check_session'
                    url = "".join(['http://', kismetHost, ":", kismetPort, '/session/check_session'])
                    response = requests.get(url, auth=basic)

                except Exception as e:
                    self._logger.error(f"Connect failed to kismet {url}. IS IT RUNNING? Retrying...")
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
                # Now request the detections from kismet
                async with websockets.connect(devicesRequest, extra_headers=myheaders) as websocket:
                    self._logger.info("Connected to kismet.")
                    self._logger.debug("open=%s", websocket.open)
                    self._logger.debug("request_headers=%s", websocket.request_headers)
                    self._logger.debug("response_headers=%s", websocket.response_headers)

                    # Send the filtered list of what we want to see
                    await websocket.send(json.dumps(req));

                    inputRecords = 0
                    outputRecords = 0
                    async for detection in websocket:
                        inputRecords += 1
                        self._logger.debug(f"kismet #{inputRecords}={detection}")

                        # convert the kismet data into cot
                        cot = CoT()
                        await self.kismet2cot(detection, cot)

                        self._logger.debug("cot=%s", cot.toString())
                        if cot.isValid() == False:
                            self._logger.debug("Invalid cot generated from kismet - skipping")
                            continue

                        # Convert the cot data into xml so pytak can send it out
                        xml = cot.toXML()
                        outputRecords += 1
                        self._logger.debug(f"xml #{outputRecords}={xml}")

                        if not xml:
                            self._logger.debug("xml is empty.")
                            continue

                        # Output the cot data into the tx_queue so the TXWorker can pick it up and send it out
                        await self.put_queue(xml)
            except websockets.exceptions.InvalidStatusCode as code:
                self._logger.error('code={code.status_code}')
                if code.status_code == 401:
                    self._logger.fatal("======================================================================================")
                    self._logger.fatal(f"Verify username({KISMET_USER}) and password({KISMET_PASSWORD}) are matching in kismet")
                    self._logger.fatal("======================================================================================")
                    exit(1)
            except Exception as e:
                print(e)
                self._logger.error(f"Connect failed to {devicesRequest}. Retrying...")
                time.sleep(3)

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
        # detail = "Manf=" + manf + " SSID=" + ssid + " RSSI=" + rssi + " MAC=" + macAddr
        # cot.setDetail(detail)

        return cot

    # If the key is in the obj, return the value. Otherwise, return the default.
    # Ensure the value returned is always a string.
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

