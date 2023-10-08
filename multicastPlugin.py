#!/usr/bin/env python3
import asyncio
import pytak

from multicast import Multicast
# from takproto.constants import (
#     ISO_8601_UTC,
#     DEFAULT_MESH_HEADER,
#     DEFAULT_PROTO_HEADER,
#     TAKProtoVer,
# )
from cot import CoT

# Copy data from the cotqueue
class MulticastSender():
    async def handle_data(self, data):
        # Output the cot data to multicast
        self._logger.info("multicast:%s", data)
        cot = CoT()
        cot.fromTakMessage(data.tak_message)
        pb = cot.getPayload()               
        self.mc.send(data)
        await asyncio.sleep(.1)

    async def run(self, number_of_iterations=-1):
        self.mc = Multicast(asyncio.Queue())

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
            pass

async def main():
    pass

if __name__ == "__main__":
    asyncio.run(main())