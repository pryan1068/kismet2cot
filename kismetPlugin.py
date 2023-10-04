import asyncio
import pytak
from datetime import datetime
import time

# kismet imports
import websockets
import json
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from typing import Optional

import takproto
from takproto.constants import (
    ISO_8601_UTC,
    DEFAULT_MESH_HEADER,
    DEFAULT_PROTO_HEADER,
    TAKProtoVer,
)
from takproto.proto import TakMessage
import delimited_protobuf as dpb
from io import BytesIO

from multicast import CoTMulticast

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
                    # Kismet user and password that you assigned the first time you ran it
                    KISMET_USER = self.config["KISMET_USER"]
                    KISMET_PASSWORD = self.config["KISMET_PASSWORD"]
                    basic = HTTPBasicAuth(KISMET_USER, KISMET_PASSWORD)
                    url = 'http://localhost:2501/session/check_session'
                    r = requests.get(url, auth=basic)

                except Exception as e:
                    # print(e)
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
                    [basenameKey, basenameAlias],
                    [lastGeopointKey, lastGeopointAlias],
                    [altKey, altAlias],
                    [manufKey, manufAlias],
                    [ssidKey, ssidAlias],
                    [rssiKey, rssiAlias],
                    [macAddrKey, macAddrAlias]
                ]
            }

            try:
                mc = CoTMulticast(asyncio.Queue())
                async with websockets.connect(devicesRequest, extra_headers=myheaders) as websocket:
                    self._logger.debug("open=%s", websocket.open)
                    self._logger.debug("request_headers=%s", websocket.request_headers)
                    self._logger.debug("response_headers=%s", websocket.response_headers)

                    # Send the filtered list of what we want to see
                    await websocket.send(json.dumps(req));

                    async for data in websocket:
                        self._logger.debug("data(kismet)=%s", data)

                        # convert the kismet data into cot
                        data = await kismet2cot(data)
                        self._logger.info("data(cot)=%s", data)
                        mc.send(data)
                        
                        # Input the cot data onto the cotqueue
                        await self.config.cotqueue.put(data)
            except websockets.exceptions.InvalidStatusCode as code:
                print('code=', code.status_code)
                if code.status_code == 401:
                    print("======================================================================")
                    print(f"Verify username({KISMET_USER}) and password({KISMET_PASSWORD}) are matching in kismet")
                    print("======================================================================")

async def kismet2cot(data):
    # Get the data from kismet
    obj = json.loads(data)
    name=get(basenameAlias, obj, "UNK")

    lat=0.0
    lon=0.0

    if lastGeopointAlias in obj:
        geopoint = obj[lastGeopointAlias]
        if geopoint==None or geopoint==0:
            lat = 0.0
            lon = 0.0
        else:
            lat = float(geopoint[1])
            lon = float(geopoint[0])

    alt=get(altAlias, obj, "0")
    # heading=get(headingAlias, obj, "0")
    manf=get(manufAlias, obj, "UNK")
    ssid=get(ssidAlias, obj, "UNK")
    rssi=get(rssiAlias, obj, "0")
    macAddr=get(macAddrAlias, obj, "0")

    # Populate the CoT event
    tak_message = TakMessage()
    # tak_control = tak_message.takControl
    # tak_control.contactUid = "uid"
    new_event = tak_message.cotEvent
    setattr(new_event, "type", "a-u-G")
    # setattr(new_event, "access", "m-g")
    # setattr(new_event, "qos", "m-g")
    # setattr(new_event, "opex", "m-g")
    setattr(new_event, "uid", name)
    setattr(new_event, "how", "m-g")
    setattr(new_event, "sendTime", format_time(pytak.cot_time()))
    setattr(new_event, "startTime", format_time(pytak.cot_time()))
    setattr(new_event, "staleTime", format_time(pytak.cot_time(3600)))
    setattr(new_event, "lat", lat)
    setattr(new_event, "lon", lon)
    setattr(new_event, "hae", 1.0)
    setattr(new_event, "ce", 999999.0)
    setattr(new_event, "le", 999999.0)

    new_detail = new_event.detail
    setattr(new_detail.contact, "endpoint", "192.168.0.20:4242:tcp")
    setattr(new_detail.contact, "callsign", "hopper")
    # setattr(new_detail.group, "name", "value")
    # setattr(new_detail.group, "role", "value")
    # new_detail.status.battery = int(100)
    # setattr(new_detail.track, "speed", float(40))
    # setattr(new_detail.track, "course", float(360))

    protover = TAKProtoVer.MESH
    output = msg2proto(tak_message, protover)
    return output

    
def format_time(time: str) -> int:
    """Format timestamp as microseconds."""
    s_time = datetime.strptime(time + "+0000", ISO_8601_UTC + "%z")
    return int(s_time.timestamp() * 1000)

def msg2proto(msg, protover: Optional[TAKProtoVer] = None) -> bytearray:
    """Convert a TakMessage into a TAK Protocol Version 1 protobuf."""
    protover = protover or TAKProtoVer.MESH

    output_ba = bytearray()
    header_ba = bytearray()
    proto_ba = bytearray()

    if protover == TAKProtoVer.MESH:
        header_ba = DEFAULT_MESH_HEADER
        proto_ba = bytearray(msg.SerializeToString())
    elif protover == TAKProtoVer.STREAM:
        header_ba = DEFAULT_PROTO_HEADER
        output_io = BytesIO()
        dpb.write(output_io, msg)
        proto_ba = bytearray(output_io.getvalue())
    else:
        raise ValueError(f"Unsupported TAKProtoVer: {protover}")

    output_ba = header_ba + proto_ba
    return output_ba




async def kismet2cotOLD(data):
    # print("data=", data)
    obj = json.loads(data)
    # print("obj=", obj)

    # NOTE: If you want to use other data from kismet, you need to add those to the filter
    # that is defined in the run() method above.
    name=get(basenameAlias, obj, "UNK")

    lat="0"
    lon="0"

    if lastGeopointAlias in obj:
        geopoint = obj[lastGeopointAlias]
        if geopoint==None or geopoint==0:
            lat = "0.0"
            lon = "0.0"
        else:
            lat = str(geopoint[1])
            lon = str(geopoint[0])

    alt=get(altAlias, obj, "0")
    # heading=get(headingAlias, obj, "0")
    manf=get(manufAlias, obj, "UNK")
    ssid=get(ssidAlias, obj, "UNK")
    rssi=get(rssiAlias, obj, "0")
    macAddr=get(macAddrAlias, obj, "0")

    # name="UNK"
    # lat="0.0"
    # lon="0.0"
    # alt="0"
    # heading="0"
    # manf="UNK"
    # ssid="UNK"
    # rssi="0"

    event = ET.Element("event")
    event.set("version", "2.0")
    event.set("type", "a-f-u")
    event.set("uid", name)
    event.set("how", "m-g")
    event.set("time", pytak.cot_time())
    event.set("start", pytak.cot_time())
    event.set("stale", pytak.cot_time(3600))

    point = ET.SubElement(event, "point")
    point.set("lat", lat)
    point.set("lon", lon)

    point.set("hae", "1") # <<<< THIS NEEDS VALIDATED
    point.set("ce", "10")
    point.set("le", "10")

    detail = ET.SubElement(event, "detail")
    contact = ET.SubElement(detail, "contact")
    contact.set("callsign", "hopper")
    contact.set("endpoint", "192.168.0.20:4242:tcp")
    # <contact callsign='Eliopoli HQ' endpoint='192.168.1.10:4242:tcp'/>


    # emitter = ET.SubElement(detail, "emitter")
    # emitter.set("Emitter", ssid)
    # emitter.set("Manf", manf)
    # emitter.set("RSSI", rssi)
    # emitter.set("Mac", macAddr)

    # print(ET.dump(event))
    # ET.dump(event)

    # buf = takproto.xml2proto(ET.tostring(event))
    buf = ET.tostring(event)

    return buf

def get(key, obj, default):
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