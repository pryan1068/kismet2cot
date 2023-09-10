# kismet2cot
A Python script that subscribes to kismet emitter detections and outputs them in cot format.

# Usage
Simply run the main script:

k2c.py

This c

# Design
PyTAK has the CoT side solved, so it was used for sending out CoT. PyTAK leverages Python's ayncio feature to ensure network data inputs don't get dropped. kismet2cot followed their same architecture to keep things simple and consistent.

Additional Receiver and Sender plugins were provided for stdio to allow piping inputs and outputs if so desired. Out of the box kismet2cot will subscribe to kismet (WiFi and Bluetooth) devices, and output them to multicast CoT.

k2c.py defines which Receiver (kismet, pytak or stdin) and which Sender (PyTAK or stdout) to use.

config.ini is a PyTAK config file that defines where CoT goes (unicast to TAKServer or multicast to all local End User Devices).

# Install
kismet2cot.py expects a Python 3.11+ environment. Dependant libraries are captured in requirements.txt and can be installed by running:

pip install -r requirements.txt


