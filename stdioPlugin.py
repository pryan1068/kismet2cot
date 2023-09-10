#!/usr/bin/env python3
import asyncio
import pytak
import sys

class StdioPlugin:
    # Copy data from the cotqueue
    class MySender(pytak.QueueWorker):
        async def handle_data(self, data):
            # Output the cot data to stdout
            self._logger.info("stdout:%s", data)
            await asyncio.sleep(.1)

        async def run(self, number_of_iterations=-1):
            while True:
                # Get the cot data from the cotqueue
                data = await self.config.cotqueue.get()
                await self.handle_data(data)

    # Copy data to the cotqueue
    class MyReceiver(pytak.QueueWorker):
        async def handle_data(self, data):
            self._logger.info("stdin:%s", data)

            # Input the cot data onto the cotqueue
            await self.config.cotqueue.put(data)

        async def run(self):
            while True:
                # Get the input data from stdin
                for data in sys.stdin:
                    await self.handle_data(data)
                    await asyncio.sleep(.1)
