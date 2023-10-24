#!/usr/bin/env python3
import asyncio
import pytak
import sys
from configparser import ConfigParser

# Data flows from stdin to PyTAK
class StdioSender(pytak.QueueWorker):
    async def __init__(self, rx_queue, config):
        super().__init__(rx_queue, config)
        self._logger = pytak.getLogger("StdioSender")

        loop = asyncio.get_event_loop()
        self.reader = asyncio.StreamReader()
        self.protocol = asyncio.StreamReaderProtocol(self.reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    async def handle_data(self, data):
        self._logger.info("stdout:%s", data)
        await asyncio.sleep(.1)

    async def run(self, number_of_iterations=-1):
        while True:
            # Get data from stdin
            data =
            await self.handle_data(data)

    async def setup(self):
        asyncio.create_task(self.run())

# Data flows from PyTAK to stdout
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

async def connect_stdin_stdout():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer


async def main():
    reader, writer = await connect_stdin_stdout()
    while True:
        res = await reader.read(100)
        if not res:
            break
        writer.write(res)
        await writer.drain()


if __name__ == "__main__":
    asyncio.run(main())