#!/usr/bin/env python3
import asyncio
import pytak
import sys
from configparser import ConfigParser

# Copy data from the cotqueue
class StdioSender(pytak.QueueWorker):
    async def handle_data(self, data):
        # Output the cot data to stdout
        self._logger.info("stdout:%s", data)
        await asyncio.sleep(.1)

    async def run(self, number_of_iterations=-1):
        while True:
            # Get the cot data from the cotqueue
            data = await self.config.cotqueue.get()
            await self.handle_data(data)

    async def setup(self):
        asyncio.create_task(self.run())

# Copy data to the cotqueue
class StdioReceiver(pytak.QueueWorker):
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
    
    async def setup(self):
        asyncio.create_task(self.run())

async def main():
    parser = ConfigParser()
    parser.read("config.ini")
    config = parser["mycottool"]

    # create a cotqueue in config for all the plugins to use
    config.cotqueue = asyncio.Queue()

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await clitool.setup()

    stdioReceiver = StdioReceiver(clitool.rx_queue, config)
    stdioSender = StdioSender(clitool.tx_queue, config)

    await stdioReceiver.setup()
    await stdioSender.setup()
                
if __name__ == "__main__":
    asyncio.run(main())
