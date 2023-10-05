#!/usr/bin/env python3
import asyncio
import pytak
import sys

from multicast import Multicast
from takproto.constants import (
    ISO_8601_UTC,
    DEFAULT_MESH_HEADER,
    DEFAULT_PROTO_HEADER,
    TAKProtoVer,
)
from cot import CoT

# Copy data from the cotqueue
class MulticastSender(pytak.QueueWorker):
    async def handle_data(self, data):
        # Output the cot data to multicast
        self._logger.info("multicast:%s", data)

        # protover = TAKProtoVer.MESH
        # pb = self.cot.toProtobuf(data.tak_message, protover)     
        self.cot.fromTakMessage(data.tak_message)
        pb = self.cot.getPayload()               
        self.mc.send(data)
        await asyncio.sleep(.1)

    async def run(self, number_of_iterations=-1):
        self.mc = Multicast(asyncio.Queue())
        self.cot = CoT()

        while True:
            # Get the cot data from the cotqueue
            data = await self.config.cotqueue.get()
            await self.handle_data(data)

# Copy data to the cotqueue
class MulticastReceiver(pytak.QueueWorker):
    async def handle_data(self, data):
        self._logger.info("multicast:%s", data)

        # Input the cot data onto the cotqueue
        await self.config.cotqueue.put(data)

    async def run(self):
        self.mc = Multicast(self.config.cotqueue)
        self.mc.startListening()
        while True:
            # Get the cot data from the cotqueue
            data = await self.mc.get()
            await self.handle_data(data)
