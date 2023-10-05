import asyncio
import socket

MULTICAST_PORT = 6969
MULTICAST_ADDR = "239.2.3.1"
HOST = "0.0.0.0"

class Multicast:
    def __init__(self, queue):
        self.cotqueue = queue
        self.loop = asyncio.get_event_loop()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(MULTICAST_ADDR) + socket.inet_aton(HOST))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, MULTICAST_PORT))

    def startListening(self, addr, port):
        print('listening(', addr, ", ", port, ")")
        self.listen = self.loop.create_datagram_endpoint(lambda: self, sock=self.sock)
        asyncio.ensure_future(self.listen)

    def send(self, data):
        print('sending:', data)
        self.sock.sendto(data, (MULTICAST_ADDR, MULTICAST_PORT))

    def connection_made(self, transport):
        print("Connection made")
        self.transport = transport

    def datagram_received(self, data, addr):
        print('datagram_received {!r} from {!r}'.format(data, addr))
        self.cotqueue.put_nowait(data)

    def error_received(self, exc):
        print('error_received:', exc)

    def connection_lost(self, exc):
        print("connection_lost")

    async def mainLoop(self):
        try:
            self.loop.run_forever()
        except:
            pass
            # self.loop.close()
    
        print("multicast is done.")


def squirt(data: bytearray, addr=MULTICAST_ADDR, port=MULTICAST_PORT, host=HOST):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(addr) + socket.inet_aton(host))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    print("sending ", data, " to ", addr, ":", port)
    sock.sendto(data, (addr, port))

# This main() is for testing purposes only
if __name__ == "__main__":
    from cot import CoT
    from takproto.constants import TAKProtoVer

    # Create a CoT message
    cot = CoT(uid="Pete Mitchell", callsign="Maverick", type="a-f-G-E-W-R-R", lat=40.0, lon=-84.0)

    # Open-Squirt-Close the cot message to the multicast address in Version 0 (XML)
    squirt(cot.getPayload(TAKProtoVer.XML))

    # Open-Squirt-Close the cot message to the multicast address in Version 1 (Protobuf Mesh)
    squirt(cot.getPayload(TAKProtoVer.MESH))

    # Open-Squirt-Close the cot message to the multicast address in Version 1 (Protobuf Stream)
    squirt(cot.getPayload(TAKProtoVer.STREAM))

    # Listen for multicast messages
    # inputQueue = asyncio.Queue()
    # cotMulticast = Multicast(inputQueue)
    # asyncio.run(cotMulticast.mainLoop())




