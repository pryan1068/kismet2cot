import time
import logging
import xml.etree.ElementTree as ET

# pytak imports
import pytak
from takproto.proto import TakMessage
from takproto import format_time

# kismet imports
import websockets
import json
import requests
from requests.auth import HTTPBasicAuth
from cot import CoT

# ======================================================================================
# KismetReceiver
#
# Follows the pytak QueueWorker pattern from pytak's architecture.
#
# Subscribes to kismet webservice to get device detections in real time.
#
# Converts kismet detections to CoT and sends them out.
#
# See config.ini for configuration settings.
#
# 
#
# ======================================================================================
class KismetReceiver(pytak.QueueWorker):
    # Keys and Aliases for the data we want to receive from kismet
    basenameKey="kismet.device.base.name"
    basenameAlias="device.name"

    # Untested
    # lastGeopointKey="kismet.device.base.location/kismet.common.location.avg.loc/kismet.common.location.geopoint"
    # lastGeopointAlias="location.geopoint"

    lastGeopointKey="kismet.device.base.location/kismet.common.location.last/kismet.common.location.geopoint"
    lastGeopointAlias="location.geopoint"

    rssiKey="kismet.device.base.signal/kismet.common.signal.last_signal"
    rssiAlias="rssi"

    altKey="kismet.device.base.location/kismet.common.location.last/kismet.common.location.alt"
    altAlias="alt"

    manufKey="kismet.device.base.manuf"
    manufAlias="manuf"

    ssidKey="dot11.device/dot11.device.last_beaconed_ssid_record/dot11.advertisedssid.ssid"
    ssidAlias="ssid"

    macAddrKey="kismet.device.base.macaddr"
    macAddrAlias="macAddr"

    fields = [ 
        [basenameKey, basenameAlias],
        [lastGeopointKey, lastGeopointAlias],
        [altKey, altAlias],
        [manufKey, manufAlias],
        [ssidKey, ssidAlias],
        [rssiKey, rssiAlias],
        [macAddrKey, macAddrAlias]
    ]

    # constructor
    def __init__(self, tx_queue, config):
        super().__init__(tx_queue, config)
        self._logger = logging.getLogger(__name__)

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
            # self._logger.debug("KISMET=%s", kismetCookie)

            myheaders = {
                "Cookie":f"KISMET={kismetCookie}"
            }

            # NOTE: Below is a filtered list of what data kismet should send to you. 
            # If we received every piece of data, it would overwhelm comms and we
            # would end up dropping network packets. So only request what you need.
            # See the kismet2cot() function below where this data is used.
            devicesRequest = "ws://localhost:2501/devices/monitor.ws"

            # See https://www.kismetwireless.net/docs/api/devices/#subscription-api for req details
            req = {
                "monitor": "*",
                "request": 1,
                "rate": 1,
                "fields": self.fields
            }

            try:
                # Now request the detections from kismet
                async with websockets.connect(devicesRequest, extra_headers=myheaders) as websocket:
                    self._logger.info("Connected to kismet.")

                    # Send the filtered list of what we want to see
                    await websocket.send(json.dumps(req));

                    inputRecords = 0
                    outputRecords = 0
                    async for detection in websocket:
                        inputRecords += 1
                        self._logger.debug(f"IN (kismet) #{inputRecords}={detection}")

                        xml = await self.kismetToXML(detection)

                        if not xml:
                            # self._logger.debug("xml is empty.")
                            continue

                        outputRecords += 1
                        self._logger.debug(f"OUT (cot) #{outputRecords}={xml}")

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

    # Convert kismet detection into CoT XML
    async def kismetToXML(self, kismetData: str):
        # Deserialize str instance containing a JSON document to a Python object.
        obj: dict = json.loads(kismetData)

        name=self.get(self.basenameAlias, obj, "UNK")
        lat="-0.0"
        lon="-0.0"

        if self.lastGeopointAlias in obj:
            geopoint = obj[self.lastGeopointAlias]
            if geopoint==None or geopoint==0:
                return None
            else:
                lat = str(geopoint[1])
                lon = str(geopoint[0])

        alt=self.get(self.altAlias, obj, "0")
        # heading=self.get(headingAlias, obj, "0")
        manf=self.get(self.manufAlias, obj, "UNK")
        ssid=self.get(self.ssidAlias, obj, "UNK")
        rssi=self.get(self.rssiAlias, obj, "0")
        macAddr=self.get(self.macAddrAlias, obj, "0")
        hae="0"
        le="999999"
        ce="999999"
        xmlDetail = "Manf=" + manf + " SSID=" + ssid + " RSSI=" + rssi + " MAC=" + macAddr + " Alt=" + alt

        xml = None

        try:
            event = ET.Element("event")
            event.set("version", "2.0")
            event.set("type", "a-u-G")
            event.set("uid", name)
            event.set("how", "m-g")
            event.set("time", pytak.cot_time())
            event.set("start", pytak.cot_time())
            event.set("stale", pytak.cot_time(3600))
            
            pt_attr = {
                "lat": lat,
                "lon": lon,
                "hae": hae,
                "ce": ce,
                "le": le,
            }

            ET.SubElement(event, "point", attrib=pt_attr)

            detail = ET.SubElement(event, "detail")
            remarks = ET.SubElement(detail, "remarks")
            remarks.text = xmlDetail

            xml = ET.tostring(event)
        except Exception as e:
            self._logger.debug(f"{e}")

        return xml

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

    # async def kismet2TakMessage(self, kismetData: str):
    #         # Deserialize str instance containing a JSON document to a Python object.
    #         obj: dict = json.loads(kismetData)

    #         name=self.get(self.basenameAlias, obj, "UNK")
    #         lat=0.0
    #         lon=0.0

    #         if self.lastGeopointAlias in obj:
    #             geopoint = obj[self.lastGeopointAlias]
    #             if geopoint==None or geopoint==0:
    #                 lat = 0.0
    #                 lon = 0.0
    #             else:
    #                 lat = float(geopoint[1])
    #                 lon = float(geopoint[0])

    #         alt=self.get(self.altAlias, obj, "0")
    #         # heading=self.get(headingAlias, obj, "0")
    #         manf=self.get(self.manufAlias, obj, "UNK")
    #         ssid=self.get(self.ssidAlias, obj, "UNK")
    #         rssi=self.get(self.rssiAlias, obj, "0")
    #         macAddr=self.get(self.macAddrAlias, obj, "0")

    #         # Populate the CoT event
    #         tak_message = TakMessage()

    #         setattr(tak_message.cotEvent, "type", "a-u-G")
    #         setattr(tak_message.cotEvent, "uid", name)
    #         setattr(tak_message.cotEvent, "sendTime", format_time(pytak.cot_time()))
    #         setattr(tak_message.cotEvent, "startTime", format_time(pytak.cot_time()))
    #         setattr(tak_message.cotEvent, "staleTime", format_time(pytak.cot_time(3600)))
    #         setattr(tak_message.cotEvent, "lat", lat)
    #         setattr(tak_message.cotEvent, "lon", lon)
    #         tak_message.cotEvent.detail.xmlDetail = "Manf=" + manf + " SSID=" + ssid + " RSSI=" + rssi + " MAC=" + macAddr + " Alt=" + alt

    #         return tak_message
    

    # async def kismet2cot(self, data: str, cot: CoT=CoT()):
    #     # Deserialize str instance containing a JSON document to a Python object.
    #     obj: dict = json.loads(data)

    #     name=self.get(self.basenameAlias, obj, "UNK")
    #     lat=0.0
    #     lon=0.0

    #     if self.lastGeopointAlias in obj:
    #         geopoint = obj[self.lastGeopointAlias]
    #         if geopoint==None or geopoint==0:
    #             lat = 0.0
    #             lon = 0.0
    #         else:
    #             lat = float(geopoint[1])
    #             lon = float(geopoint[0])

    #     alt=self.get(self.altAlias, obj, "0")
    #     # heading=self.get(headingAlias, obj, "0")
    #     manf=self.get(self.manufAlias, obj, "UNK")
    #     ssid=self.get(self.ssidAlias, obj, "UNK")
    #     rssi=self.get(self.rssiAlias, obj, "-0")
    #     macAddr=self.get(self.macAddrAlias, obj, "-0")

    #     # Populate the CoT event
    #     cot.setType("a-u-G")
    #     cot.setUid(name)
    #     cot.setTime(cot.cot_time())
    #     cot.setStart(cot.cot_time())
    #     cot.setStale(cot.cot_time(3600))
    #     cot.setLat(lat)
    #     cot.setLon(lon)
    #     detail = "Manf=" + manf + " SSID=" + ssid + " RSSI=" + rssi + " MAC=" + macAddr + " Alt=" + alt
    #     cot.setDetail(detail)

    #     return cot

