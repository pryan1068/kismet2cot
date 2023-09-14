# kismet2cot
A Python script that subscribes to kismet emitter detections and outputs them in cot format.

# Install
kismet2cot.py expects a Python 3.11+ environment. Dependant libraries are captured in requirements.txt and can be installed by running:

pip install -r requirements.txt

# Configuration
Modify the USER and PW variables in the kismetPlugin.py file. They should match whatever user and password you created the first time you ran kismet. They are also stored in 

Modify kismet to automatically begin capturing at startup by modifying the source= value in /etc/kismet_site.conf to point to your wi-fi radio (See https://www.kismetwireless.net/docs/readme/configuring/configfiles/#customizing-configs-with-kismet_siteconf).

# Usage
Simply run the main script:

python k2c.py

You can run kismet first or k2c.py first.

# Design
A kismet plugin was considered. A c++ version would require binaries to be generated for every possible platform (intel, arm, etc.). A script solution would be more portable. kismet also allows Javascript plugins. But Javascript does not allow TCP connections to be made, which prevents sending out cot on unicast or multicast.

A Python script was determined to be the best solution since it is portable, simple, field extensible and can work transparently behind the scenes once installed.

The PyTAK library (See https://github.com/snstac/pytak) has the CoT side solved, so it was used for sending out CoT. PyTAK leverages Python's ayncio feature to ensure network data inputs don't get dropped. kismet2cot followed their same architecture to keep things simple and consistent.

kismet has a python-kismet-rest library (See https://github.com/kismetwireless/python-kismet-rest) which handles all the REST API communication, however it does not appear to handle realtime updates.

Additional Receiver and Sender plugins were provided for stdio to allow piping inputs and outputs if so desired. Out of the box kismet2cot will subscribe to kismet (WiFi and Bluetooth) devices, and output them to multicast CoT.

k2c.py defines which Receiver (kismet, pytak or stdin) and which Sender (PyTAK or stdout) to use.

config.ini is a PyTAK config file that defines where CoT goes (unicast to TAKServer or multicast to all local End User Devices).


# 

