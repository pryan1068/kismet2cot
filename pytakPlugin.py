#!/usr/bin/env python3
import asyncio
import pytak
import xml.etree.ElementTree as ET

from configparser import ConfigParser

class PyTAK:
    # Copy data from the cotqueue
    class MySender(pytak.QueueWorker):
        async def handle_data(self, data):
            # Output the cot data in PyTAK's queue
            self._logger.debug("pytak-out:%s", data)
            await self.put_queue(data)

        async def run(self, number_of_iterations=-1):
            while 1:
                # Get the cot data from the cotqueue
                data = await self.config.cotqueue.get()
                await self.handle_data(data)

    # Copy data to the cotqueue
    class MyReceiver(pytak.QueueWorker):
        async def handle_data(self, data):
            self._logger.debug("pytak-in:%s")

            # Input the cot data onto the cotqueue
            await self.config.cotqueue.put(data)

        async def run(self):
            while 1:
                # Get the input data from PyTAK's queue
                data = await self.queue.get()
                await self.handle_data(data)

def gen_cot():
    """Generate CoT Event."""
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("type", "a-h-A-M-A")  # insert your type of marker
    root.set("uid", "name_your_marker")
    root.set("how", "m-g")
    root.set("time", pytak.cot_time())
    root.set("start", pytak.cot_time())
    root.set(
        "stale", pytak.cot_time(60)
    )  # time difference in seconds from 'start' when stale initiates

    pt_attr = {
        "lat": "40.781789",  # set your lat (this loc points to Central Park NY)
        "lon": "-73.968698",  # set your long (this loc points to Central Park NY)
        "hae": "0",
        "ce": "10",
        "le": "10",
    }

    ET.SubElement(root, "point", attrib=pt_attr)

    return ET.tostring(root)

