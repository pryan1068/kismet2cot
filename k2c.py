#!/usr/bin/env python

import asyncio
import pytak
import os
import os.path
import logging.config
import argparse
import logging
from configparser import ConfigParser
from kismetPlugin import KismetReceiver

LOGGING_CONFIG="./logging.ini"

# ======================================================================================
# Kismet to CoT
#
# Subscribe to Kismet device detections, convert them to CoT.
#
# The kismet login/password and CoT output (TAKServer or EUD) settings are in config.ini
#
# ======================================================================================
async def main():
    # If there's a logging.ini file, use it to configure logging.
    if os.path.isfile(LOGGING_CONFIG):
        logging.config.fileConfig(LOGGING_CONFIG, disable_existing_loggers=True)

    # TODO: --log arg not working yet
    # Look for a --log argument and set the logging level.
    # argparser = argparse.ArgumentParser()
    # argparser.add_argument( '-log',
    #                  '--loglevel',
    #                  default='warning',
    #                  help='Provide logging level. Example --loglevel debug, default=warning' )
    # args = argparser.parse_args()
    # numeric_level = getattr(logging, args.loglevel.upper(), None)
    # if not isinstance(numeric_level, int):
    #     raise ValueError('Invalid log level: %s' % args.loglevel)
    # _logger.setLevel(numeric_level)

    # config.ini contains configuration settings
    parser = ConfigParser()
    parser.read("config.ini")
    config = parser["kismet"]

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await clitool.setup()

    # Capture Kismet data and send it out as CoT
    clitool.add_task(KismetReceiver(clitool.tx_queue, config))
    
    # Start processing data from kismet to CoT
    await clitool.run()

if __name__ == "__main__":
    asyncio.run(main())
