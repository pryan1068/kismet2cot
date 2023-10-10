from datetime import datetime, timezone, timedelta
import logging
from typing import Union, Optional
from io import BytesIO
import xml.etree.ElementTree as ET

from takproto import parse_proto, xml2proto
from takproto.proto import TakMessage
import delimited_protobuf as dpb
from takproto.constants import (
    ISO_8601_UTC,
    DEFAULT_MESH_HEADER,
    DEFAULT_PROTO_HEADER,
    TAKProtoVer,
)

#===============================================================================
# CoT Class
#
# This class is a Python implementation of the Cursor on Target (CoT) standard.
# It is a wrapper around the TAKProto library's TakMessage class. TAKMessage takes
# care of handling the protobuf serialization/deserialization.
#
# Use getPayload() to get the CoT message in the desired format to send over the
# network.
# 
# Design Decisions:
#     High Performance is desired over elegance
#     TakMessage is the primary internal format, but not exposed to the user
#     TakMessage was used because it handles the protobuf serialization/deserialization
#     Getters/Setters provided to encapsulate internal implementation
#
#===============================================================================

class CoT:
    # _logger = logging.getLogger(__name__)
    # if not _logger.handlers:
    #     _logger.setLevel(pytak.LOG_LEVEL)
    #     _console_handler = logging.StreamHandler()
    #     _console_handler.setLevel(pytak.LOG_LEVEL)
    #     _console_handler.setFormatter(pytak.LOG_FORMAT)
    #     _logger.addHandler(_console_handler)
    #     _logger.propagate = False

    ISO_8601_UTC = "%Y-%m-%dT%H:%M:%S.%fZ"
    
    # Constructor. Pass in a bytearray to parse, or pass in the desired values.
    def __init__(self, pb: bytearray=None, type=None, uid=None, how=None, time=None, start=None, stale=None, lat=None, lon=None, hae=None, ce=None, le=None, detail=None, access=None, opex=None, qos=None, callsign=None):
        self.tak_message = TakMessage()
        self.new_event = self.tak_message.cotEvent
        self.new_detail = self.new_event.detail
        self.tak_control = self.tak_message.takControl

        if pb:
            self.fromProtobuf(pb)

        if uid:
            self.setUid(uid)
        
        if type:
            self.setType(type)
        
        if how:
            self.setHow(how)
        
        if time:
            self.setTime(time)
        
        if start:
            self.setStart(start)
        
        if stale:
            self.setStale(stale)
        
        if lat:
            self.setLat(lat)
        
        if lon:
            self.setLon(lon)
        
        if hae:
            self.setHae(hae)
        
        if ce:
            self.setCe(ce)
        
        if le:
            self.setLe(le)
        
        if detail:
            self.setDetail(detail)
        
        if access:
            self.setAccess(access)
        
        if opex:
            self.setOpex(opex)
        
        if qos:
            self.setQos(qos)
        
        # if callsign:
        #     self.setCallsign(callsign)
        
    
    def getType(self):
        return getattr(self.new_event, "type")
    
    def setType(self, type):
        setattr(self.new_event, "type", type)
    
    def getUid(self):
        return getattr(self.new_event, "uid")
    
    def setUid(self, uid):
        setattr(self.new_event, "uid", uid)
    
    def getHow(self):
        return getattr(self.new_event, "how")
    
    def setHow(self, how):
        setattr(self.new_event, "how", how)
    
    def getTime(self):
        return getattr(self.new_event, "sendTime")
    
    def setTime(self, time=None):
        if time == None:
            time = self.cot_time()
            
        setattr(self.new_event, "sendTime", self.toMicroseconds(time))
    
    def getStart(self):
        return getattr(self.new_event, "startTime")
    
    def setStart(self, start=None):
        if start == None:
            start = self.cot_time()
            
        setattr(self.new_event, "startTime", self.toMicroseconds(start))
    
    def getStale(self):
        return getattr(self.new_event, "staleTime")

    # Pass in stale time in seconds to offset current time.    
    def setStale(self, stale):
        if stale == None:
            stale = self.cot_time(stale)
            
        setattr(self.new_event, "staleTime", self.toMicroseconds(stale))
    
    def getLat(self):
        return getattr(self.new_event, "lat")
    
    def setLat(self, lat):
        setattr(self.new_event, "lat", lat)
    
    def getLon(self):
        return getattr(self.new_event, "lon")
    
    def setLon(self, lon):
        setattr(self.new_event, "lon", lon)
    
    def getHae(self):
        return getattr(self.new_event, "hae")

    def setHae(self, hae):
        setattr(self.new_event, "hae", hae)
    
    def getCe(self):
        return getattr(self.new_event, "ce")
    
    def setCe(self, ce):
        setattr(self.new_event, "ce", ce)
    
    def getLe(self):
        return getattr(self.new_event, "le")
    
    def setLe(self, le):
        setattr(self.new_event, "le", le)
    
    def getDetail(self):
        return getattr(self.new_event, "detail")
    
    def setDetail(self, detail):
        self.detail = detail
    
    def getAccess(self):
        return getattr(self.new_event, "access")
    
    def setAccess(self, access):
        setattr(self.new_event, "access", access)
    
    def getOpex(self):
        return getattr(self.new_event, "opex")
    
    def setOpex(self, opex):
        setattr(self.new_event, "opex", opex)
    
    def getQos(self):
        return getattr(self.new_event, "qos")
    
    def setQos(self, qos):
        setattr(self.new_event, "qos", qos)
    
    def fromXML(self, xml: str):
        pb = xml2proto(xml)
        self.fromProtobuf(pb)

    def fromTakMessage(self, takMessage: TakMessage):
        self.tak_message = takMessage
        self.new_event = self.tak_message.cotEvent
        self.new_detail = self.new_event.detail
        self.tak_control = self.tak_message.takControl

    def fromProtobuf(self, pb: bytearray):
        self.tak_message = parse_proto(pb)
        self.new_event = self.tak_message.cotEvent
        self.new_detail = self.new_event.detail
        self.tak_control = self.tak_message.takControl

    # Default toString() method
    def __str__(self):
        return self.toString()
    
    def toString(self):
        output = str()
        output += "Type: " + self.getType() + ", "
        output += "UID: " + self.getUid() + ", "
        output += "How: " + self.getHow() + ", "
        output += "Time: " + str(self.fromMicroseconds(self.getTime())) + ", "
        output += "Start: " + str(self.fromMicroseconds(self.getStart())) + ", "
        output += "Stale: " + str(self.fromMicroseconds(self.getStale())) + ", "
        output += "Lat: " + str(self.getLat()) + ", "
        output += "Lon: " + str(self.getLon()) + ", "
        output += "HAE: " + str(self.getHae()) + ", "
        output += "CE: " + str(self.getCe()) + ", "
        output += "LE: " + str(self.getLe()) + ", "
        # output += "Detail: " + self.getDetail() + ", "
        output += "Access: " + self.getAccess() + ", "
        output += "Opex: " + self.getOpex() + ", "
        output += "Qos: " + self.getQos()

        return output
    
    # Use this method to get the CoT message in the desired format to send over the network.
    def getPayload(self, version: TAKProtoVer = TAKProtoVer.MESH) -> bytearray:
        if version == TAKProtoVer.XML:
            return self.toXML()
        else:
            return self.toProtobuf(protover=version)                    

    # Generate CoT XML
    def toXML(self):
        # todo how to handle missing values?
        # which fields are required?
        # what are good defaults for them?
        # Need to do this for all the toXXX() methods
        xml = None

        try:
            event = ET.Element("event")
            event.set("version", "2.0")
            event.set("type", self.getType())
            event.set("uid", self.getUid())
            event.set("how", self.getHow())
            event.set("time", str(self.fromMicroseconds(self.getTime())))
            event.set("start", str(self.fromMicroseconds(self.getStart())))
            event.set("stale", str(self.fromMicroseconds(self.getStale())))
            event.set("access", str(self.getAccess()))
            event.set("opex", str(self.getOpex()))
            event.set("qos", str(self.getQos()))
            
            pt_attr = {
                "lat": str(self.getLat()),
                "lon": str(self.getLon()),
                "hae": str(self.getHae()),
                "ce": str(self.getCe()),
                "le": str(self.getLe()),
            }

            ET.SubElement(event, "point", attrib=pt_attr)

            # todo detail
            # detail = ET.SubElement(event, "detail")
            # kismet = ET.SubElement(detail, ET.fromstring("Hello World!"))
            # detail.set("unknown", self.getDetail())

            xml = ET.tostring(event)
        except Exception as e:
            logging.error(f"{e}")

        return xml

    # Convert a TAKProto TakMessage into a TAK Protocol Version 1 protobuf.
    def toProtobuf(self, msg: TakMessage=None, protover: Optional[TAKProtoVer] = None) -> bytearray:
        protover = protover or TAKProtoVer.MESH

        output_ba = bytearray()
        header_ba = bytearray()
        proto_ba = bytearray()

        if protover == TAKProtoVer.MESH:
            header_ba = DEFAULT_MESH_HEADER
            proto_ba = bytearray(self.tak_message.SerializeToString())
        elif protover == TAKProtoVer.STREAM:
            header_ba = DEFAULT_PROTO_HEADER
            output_io = BytesIO()
            dpb.write(output_io, self.tak_message)
            proto_ba = bytearray(output_io.getvalue())
        elif protover == TAKProtoVer.XML:
            print("XML not supported for toProtobuf() - use getPayload() for everything instead.")
        else:
            raise ValueError(f"Unsupported TAKProtoVer: {protover}")

        output_ba = header_ba + proto_ba

        return output_ba

    # Convert timestamp to microseconds.
    def toMicroseconds(self, time: str) -> int:
        s_time = datetime.strptime(time + "+0000", ISO_8601_UTC + "%z")
        return int(s_time.timestamp() * 1000)

    # Create timestamp from microseconds.
    def fromMicroseconds(self, millis: int):
        time = datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc)
        return time.strftime(CoT.ISO_8601_UTC)
        return time

    # Return current time in CoT format.
    # Pass in stale time in seconds to offset current time.
    def cot_time(self, cot_stale: Union[int, None] = None) -> str:
        time = datetime.utcnow()
        
        if cot_stale:
            time = time + timedelta(seconds=int(cot_stale))
        
        return time.strftime(CoT.ISO_8601_UTC)

# This main() is for testing purposes only.
if __name__ == "__main__":
    xml = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
    <event version='2.0' uid='aa0b0312-b5cd-4c2c-bbbc-9c4c70216261' type='a-f-G-E-V-C' time='2020-02-08T18:10:44.000Z' start='2020-02-08T18:10:44.000Z' stale='2020-02-08T18:11:11.000Z' how='h-e'>
        <point lat='43.97957317' lon='-66.07737696' hae='26.767999' ce='9999999.0' le='9999999.0' />
        <detail>
            <uid Droid='Eliopoli HQ'/>
            <contact callsign='Eliopoli HQ' endpoint='192.168.1.10:4242:tcp'/>
            <__group name='Yellow' role='HQ'/><status battery='100'/>
            <takv platform='WinTAK-CIV' device='LENOVO 20QV0007US' os='Microsoft Windows 10 Home' version='1.10.0.137'/>
            <track speed='0.00000000' course='0.00000000'/>
        </detail>
    </event>
    """
    pb = bytearray(b'\xbf\x01\xbf\x12\xff\x01\n\x0ba-f-G-E-V-C*$aa0b0312-b5cd-4c2c-bbbc-9c4c702162610\xa0\xa2\xc7\xb8\x82.8\xa0\xa2\xc7\xb8\x82.@\x98\xf5\xc8\xb8\x82.J\x03h-eQ3\x98T\xa7b\xfdE@Y}*~\xbe\xf3\x84P\xc0aW\\\x1c\x95\x9b\xc4:@i\x00\x00\x00\xe0\xcf\x12cAq\x00\x00\x00\xe0\xcf\x12cAz\x82\x01\x12$\n\x15192.168.1.10:4242:tcp\x12\x0bEliopoli HQ\x1a\x0c\n\x06Yellow\x12\x02HQ*\x02\x08d2F\n\x11LENOVO 20QV0007US\x12\nWinTAK-CIV\x1a\x19Microsoft Windows 10 Home"\n1.10.0.137:\x00')

    # XML
    print("XML Input Test...")
    cot = CoT()
    cot.fromXML(xml)
    print(cot)

    # Protobuf
    print("")
    print("XML Output Test...")
    pb = cot.getPayload(version=TAKProtoVer.XML)
    print(pb)

    print("")
    print("MESH Output Test...")
    pb = cot.getPayload(version=TAKProtoVer.MESH)
    print(pb)

    print("")
    print("STREAM Output Test...")
    pb = cot.getPayload(version=TAKProtoVer.STREAM)
    print(pb)

    print("")
    print("Done.")