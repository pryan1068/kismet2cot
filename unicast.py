import asyncio
import socket
import time
from async_timer import async_timed

ADDRESS="127.0.0.1"
PORT=4242

@async_timed()
# squirts a CoT message to the specified address and port with asyncio
async def squirt(message: bytearray, addr=ADDRESS, port=PORT):
    reader, writer = await asyncio.open_connection(addr, port)
    writer.write(message)
    await writer.drain()
    writer.close()
    await writer.wait_closed()

# squirts a CoT message to the specified address and port without asyncio
def squirt2(message: bytearray, addr=ADDRESS, port=PORT):
    start = time.time()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message, (addr, port))
    sock.close()
    end = time.time()
    # print(f"squirt2(): Sent CoT message in {0:.40f} seconds".format(end-start))
    print(f"finished squirt2 in {end-start:.25f} second(s))")
    # print(f'finished {func} in {total:.25f} second(s)'.format(total))


async def main():
    cot = CoT(uid="GOOBER", how="m-g", type="a-f-G-U-C", lat=40.0, lon=-84.0)
    task1 =asyncio.create_task(squirt(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242))
    task2 =asyncio.create_task(squirt(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242))
    task3 =asyncio.create_task(squirt(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242))
    task4 =asyncio.create_task(squirt(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242))
    task5 =asyncio.create_task(squirt(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242))
    await task1
    await task2
    await task3
    await task4
    await task5

if __name__ == "__main__":
    from cot import CoT
    from takproto.constants import TAKProtoVer

    # sync version
    cot = CoT(uid="GOOBER", how="m-g", type="a-f-G-U-C", lat=40.0, lon=-84.0)
    squirt2(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242)
    squirt2(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242)
    squirt2(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242)
    squirt2(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242)
    squirt2(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242)

    # async version
    asyncio.run(main()) 


