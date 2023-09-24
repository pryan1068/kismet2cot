#!/usr/bin/env python

import asyncio
import pytak
from configparser import ConfigParser

from stdioPlugin import StdioPlugin
from kismetPlugin import KismetPlugin
from pytakPlugin import PyTAK
import logging

# Create a shared queue to pass data between them
cotqueue = asyncio.Queue()

async def main():
    # Enable this to see websockets debug output
    # logger = logging.getLogger('websockets')
    # logger.setLevel(logging.DEBUG)
    # logger.addHandler(logging.StreamHandler())

    parser = ConfigParser()
    parser.read("config.ini")

    # print("sections=", parser.sections())
    # for i in parser.sections():
    #     print("section=", i)
    # for i in parser.keys():
    #     print("key=", i)
    # for i in parser.values():
    #     print("value=", i)

    # print("mycottool=", parser["mycottool"]["COT_URL"])

    # config["mycottool"] = {"COT_URL": "tcp://192.168.0.20:4242"}
    # parser["mycottool"] = {"COT_URL": "udp://239.2.3.1:6969"}
    config = parser["mycottool"]
    print("config=", config)

    # store cotqueue in config for all the plugins to use
    config.cotqueue = cotqueue

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await clitool.setup()

    clitool.add_tasks(
        set([
            # NOTE: ONLY ENABLE 1 SENDER and 1 RECEIVER

            # RECEIVERS:
            # PyTAK.MyReceiver(clitool.rx_queue, config),
            # StdioPlugin.MyReceiver(clitool.rx_queue, config),
            KismetPlugin.MyReceiver(clitool.rx_queue, config),
            
            # SENDERS:
            PyTAK.MySender(clitool.tx_queue, config),
            # StdioPlugin.MySender(clitool.tx_queue, config),
            ])
    )
    

    await clitool.run()

if __name__ == "__main__":
    asyncio.run(main())
