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
#     Default values are provided for all fields
#     All time fields are stored internally as UTC datetime instances
#
#===============================================================================

class CoT:
    ISO_8601_UTC = "%Y-%m-%dT%H:%M:%S.%fZ"
    
    # Constructor. Pass in a bytearray to parse, or pass in the desired values.
    # TODO what are the preferred Types for datetime args passed in? str or datetime?
    def __init__(self, pb: bytearray=None, type: str=None, uid: str=None, how: str=None, time=None, start=None, stale=None, lat: float=None, lon: float=None, hae: float=None, ce: float=None, le: float=None, detail: str=None, access: str=None, opex: str=None, qos: str=None, callsign: str=None):
        self._logger = logging.getLogger(__name__)

        self.tak_message = TakMessage()

        # default state time is 60 minutes
        self.staleOffsetInMinutes = 60
        
        self.setDefaultValues()

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
    def setDefaultValues(self):
        self.setType("a-u")
        self.setUid("default")
        self.setHow("m-c")
        self.setTime(datetime.now(timezone.utc))
        self.setStart(datetime.now(timezone.utc))
        self.setStale(self.getStart() + timedelta(seconds=self.staleOffsetInMinutes))
        self.setLat(0)
        self.setLon(0)
        self.setHae(0)
        self.setCe(9999999.0)
        self.setLe(9999999.0)
        self.setDetail("")
        self.setAccess("true")
        self.setOpex("false")
        self.setQos("0")
        self.setRemarks("")
    
    def isValid(self):
        rc = True

        # Required fields:
        if self.getType() == None:
            self._logger.debug(f"Type: {self.getType()} is invalid.")
            rc = False
        
        if self.getLat() == None or self.getLat() == 0:
            self._logger.debug(f"Lat: {self.getLat()} is invalid.")
            rc = False
        
        if self.getLon() == None or self.getLon() == 0:
            self._logger.debug(f"Lon: {self.getLon()} is invalid.")
            rc = False
        
        if self.getHae() == None:
            self._logger.debug(f"HAE: {self.getHae()} is invalid.")
            rc = False
        
        if self.getCe() == None:
            self._logger.debug(f"CE: {self.getCe()} is invalid.")
            rc = False
        
        if self.getLe() == None:
            self._logger.debug(f"LE: {self.getLe()} is invalid.")
            rc = False
        
        return rc

    def getType(self):
        return getattr(self.tak_message.cotEvent, "type")
    
    def setType(self, type):
        setattr(self.tak_message.cotEvent, "type", type)
    
    def getUid(self):
        return getattr(self.tak_message.cotEvent, "uid")
    
    def setUid(self, uid):
        setattr(self.tak_message.cotEvent, "uid", uid)
    
    def getHow(self):
        return getattr(self.tak_message.cotEvent, "how")
    
    def setHow(self, how):
        setattr(self.tak_message.cotEvent, "how", how)
    
    def getTime(self):
        return getattr(self.tak_message.cotEvent, "sendTime")
    
    def setTime(self, time=None):
        if time == None:
            self.time = datetime.now(timezone.utc)
            
        setattr(self.tak_message.cotEvent, "sendTime", self.toMicroseconds(time))
    
    def getStart(self):
        return getattr(self.tak_message.cotEvent, "startTime")
    
    def setStart(self, start=None):
        if start == None:
            self.start = self.cot_time()
            
        setattr(self.tak_message.cotEvent, "startTime", self.toMicroseconds(start))
    
    def getStale(self):
        return getattr(self.tak_message.cotEvent, "staleTime")

    # Pass in stale time in seconds to offset current time.    
    def setStale(self, stale):
        if stale == None:
            stale = self.cot_time(stale)
            
        setattr(self.tak_message.cotEvent, "staleTime", self.toMicroseconds(stale))
        self.setStale()
    
    def getLat(self):
        return getattr(self.tak_message.cotEvent, "lat")
    
    def setLat(self, lat):
        setattr(self.tak_message.cotEvent, "lat", lat)
    
    def getLon(self):
        return getattr(self.tak_message.cotEvent, "lon")
    
    def setLon(self, lon):
        setattr(self.tak_message.cotEvent, "lon", lon)
    
    def getHae(self):
        return getattr(self.tak_message.cotEvent, "hae")

    def setHae(self, hae):
        setattr(self.tak_message.cotEvent, "hae", hae)
    
    def getCe(self):
        return getattr(self.tak_message.cotEvent, "ce")
    
    def setCe(self, ce):
        setattr(self.tak_message.cotEvent, "ce", ce)
    
    def getLe(self):
        return getattr(self.tak_message.cotEvent, "le")
    
    def setLe(self, le):
        setattr(self.tak_message.cotEvent, "le", le)
    
    def getDetail(self):
        return getattr(self.tak_message.cotEvent, "detail").xmlDetail
    
    def setDetail(self, detail):
        # TODO: Need to figure out how to handle this better.
        # detail might have Contact and others that TAKMessage has code for, so xmlDetail is wrong for them.
        # See functions.py in PyTAK for more info.
        pass
        self.tak_message.cotEvent.detail.xmlDetail = detail
    
    def getAccess(self):
        return getattr(self.tak_message.cotEvent, "access")
    
    def setAccess(self, access):
        setattr(self.tak_message.cotEvent, "access", access)
    
    def getOpex(self):
        return getattr(self.tak_message.cotEvent, "opex")
    
    def setOpex(self, opex):
        setattr(self.tak_message.cotEvent, "opex", opex)
    
    def getQos(self):
        return getattr(self.tak_message.cotEvent, "qos")
    
    def setQos(self, qos):
        setattr(self.tak_message.cotEvent, "qos", qos)
    
    def getRemarks(self):
        return self.getRemarks()

    def setRemarks(self, remarks):
        self.remarks = remarks
    
    def fromXML(self, xml: str):
        pb = xml2proto(xml)
        self.fromProtobuf(pb)

    def fromTakMessage(self, takMessage: TakMessage):
        self.tak_message = takMessage

    def fromProtobuf(self, pb: bytearray):
        self.tak_message = parse_proto(pb)

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
        output += "Detail: " + self.getDetail() + ", "
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

            detail = ET.SubElement(event, "detail")
            detail.text = self.getDetail()

            xml = ET.tostring(event)
        except Exception as e:
            self._logger.debug(f"{e}")

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

class Remarks:
    _logger = logging.getLogger(__name__)

    def __init__(self, remarks: str=None):
        self.remarks = remarks
    
    def __str__(self):
        return self.toString()
    
    def toString(self):
        output = str()
        output += "Source: " + self.getSource() + ", "
        output += "SourceID: " + self.getSourceID() + ", "
        output += "Time: " + str(self.fromMicroseconds(self.getTime())) + ", "
        output += "Time: " + str(self.getTime()) + ", "
        output += "To: " + self.getTo() + ", "
        output += "Remarks: " + self.getRemarks()

        return output
    
    # Generate an ElementTree ELement from the Remarks object.
    def toElement(self):
        remarks = None

        try:
            remarks = ET.Element("remarks")
            remarks.set("source", self.getType())
            remarks.set("sourceID", self.getUid())
            remarks.set("time", self.getHow())
            remarks.set("to", str(self.fromMicroseconds(self.getTime())))

            remarks.text = self.getRemarks()
            
        except Exception as e:
            self._logger.debug(f"{e}")

        return remarks

    def getSource(self):
        return self.source

    def setSource(self, source: str):
        self.source = source
    
    def getSourceID(self):
        return self.sourceID
    
    def setSourceID(self, sourceID: str):
        self.sourceID = sourceID
    
    def getTime(self):
        return self.time

    def setTime(self, time: str):
        self.time = time
    
    def getTo(self):
        return self.to
    
    def setTo(self, to: str):
        self.to = to
    
    def getRemarks(self):
        return self.remarks
    
    def setRemarks(self, remarks: str):
        self.to = remarks
    
    
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