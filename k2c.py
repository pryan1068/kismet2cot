#!/usr/bin/env python

import asyncio
import pytak
from configparser import ConfigParser

from stdioPlugin import StdioSender
from kismetPlugin import KismetReceiver
import logging

# ======================================================================================
# Kismet to CoT
#
# Subscribe to Kismet device detections, convert them to CoT.
#
# The kismet login/password and CoT output (TAKServer or EUD) settings are in config.ini
#
# ======================================================================================
async def main():
    # Enable this to see websockets debug output
    logger = logging.getLogger('pytak.classes')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    # config.ini contains configuration settings
    parser = ConfigParser()
    parser.read("config.ini")
    config = parser["kismet"]

    # create a cotqueue in config for all the plugins to use
    config.cotqueue = asyncio.Queue()

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await clitool.setup()

    # Capture Kismet data and send it out as CoT
    clitool.add_task(KismetReceiver(clitool.tx_queue, config))
    
    await clitool.run()

if __name__ == "__main__":
    asyncio.run(main())
