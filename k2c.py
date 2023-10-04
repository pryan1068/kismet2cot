#!/usr/bin/env python

import asyncio
import pytak
from configparser import ConfigParser

from multicast import CoTMulticast
from stdioPlugin import StdioPlugin
from kismetPlugin import KismetPlugin
from pytakPlugin import PyTAK
import logging

# Create a shared queue to pass data between them
cotqueue = asyncio.Queue()

async def main():
    # Enable this to see websockets debug output
    # logger = logging.getLogger('pytak')
    # logger.setLevel(logging.DEBUG)
    # logger.addHandler(logging.StreamHandler())

    # config.ini contains configuration settings
    parser = ConfigParser()
    parser.read("config.ini")
    config = parser["mycottool"]

    # store cotqueue in config for all the plugins to use
    config.cotqueue = cotqueue

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await clitool.setup()

    cotMulticast = CoTMulticast(clitool.tx_queue)
 
    clitool.add_tasks(
        set([
            # NOTE: ONLY ENABLE 1 SENDER and 1 RECEIVER

            # RECEIVERS:
            # PyTAK.MyReceiver(clitool.rx_queue, config),
            # StdioPlugin.MyReceiver(clitool.rx_queue, config),
            KismetPlugin.MyReceiver(clitool.rx_queue, config),
            
            # SENDERS:
            # PyTAK.MySender(clitool.tx_queue, config),
            StdioPlugin.MySender(clitool.tx_queue, config),
            # asyncio.create_task(cotMulticast.mainLoop())
            ])
    )
    

    await clitool.run()

if __name__ == "__main__":
    asyncio.run(main())
