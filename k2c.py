#!/usr/bin/env python

import asyncio
import pytak
from configparser import ConfigParser

from multicast import Multicast
from multicastPlugin import MulticastSender, MulticastReceiver
from stdioPlugin import StdioSender
from kismetPlugin import KismetReceiver
# import logging

async def main():
    # Enable this to see websockets debug output
    # logger = logging.getLogger('pytak')
    # logger.setLevel(logging.DEBUG)
    # logger.addHandler(logging.StreamHandler())

    # config.ini contains configuration settings
    parser = ConfigParser()
    parser.read("config.ini")
    config = parser["mycottool"]

    # create a cotqueue in config for all the plugins to use
    config.cotqueue = asyncio.Queue()

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await clitool.setup()

    clitool.add_tasks(
        set([
            # NOTE: ONLY ENABLE 1 SENDER and 1 RECEIVER

            # RECEIVERS:
            # PyTAK.MyReceiver(clitool.rx_queue, config),
            # StdioPlugin.MyReceiver(clitool.rx_queue, config),
            KismetReceiver(clitool.rx_queue, config),
            
            # SENDERS:
            # PyTAK.MySender(clitool.tx_queue, config),
            StdioSender(clitool.tx_queue, config),
            # MulticastSender(clitool.tx_queue, config)
            ])
    )
    

    await clitool.run()

if __name__ == "__main__":
    asyncio.run(main())
