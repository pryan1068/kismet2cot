import asyncio

ADDRESS="127.0.0.1"
PORT=4242

async def squirt(message: bytearray, addr=ADDRESS, port=PORT):
    reader, writer = await asyncio.open_connection(addr, port)

    writer.write(message)
    await writer.drain()
    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    from cot import CoT
    from takproto.constants import TAKProtoVer
    
    cot = CoT(uid="GOOBER", how="m-g", type="a-f-G-U-C", lat=40.0, lon=-84.0)
    
    asyncio.run(squirt(cot.getPayload(version=TAKProtoVer.XML), addr="192.168.0.46", port=4242))