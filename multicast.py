import asyncio
import socket
# from cot import CoT

MULTICAST_PORT = 6969
MULTICAST_ADDR = "239.2.3.1"
HOST = "0.0.0.0"

class CoTMulticast:
    def __init__(self, queue):
        self.queue = queue
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
        self.queue.put_nowait(data)

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
                
if __name__ == "__main__":
    inputQueue = asyncio.Queue()
    cotMulticast = CoTMulticast(inputQueue)
    asyncio.run(cotMulticast.mainLoop())




