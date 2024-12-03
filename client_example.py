from pywebtransport.client import WebTransportClient, WebTransportError
import asyncio
# Example usage function for integration
async def main():
    host = "127.0.0.1"
    port = 4433
    certfile = "cert.pem"

    client = WebTransportClient(host, port, certfile)

    async def handle_datagram(data):
        print(f"Datagram received: {data.decode()}")

    async def handle_stream_data(stream_id, data):
        print(f"Stream {stream_id} received data: {data.decode()}")

    client.set_datagram_handler(handle_datagram)
    client.set_stream_data_handler(handle_stream_data)

    try:
        await client.connect()
        streamid = client.create_webtransport_stream()
        client.send_datagram(streamid, b"Hello from Datagram!")
        client.send_stream_data(streamid, b"Hello from Stream!")
        await asyncio.sleep(5)
        await client.close()
    except WebTransportError as e:
        print(f"Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())