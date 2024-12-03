from pywebtransport.server import WebTransportServer, WebTransportProtocol
import asyncio, logging

logging.basicConfig(level=logging.DEBUG)

class MyProtocol(WebTransportProtocol):
    # No need to override the init method, but you can if you want

    def handle_stream_data_received(self, stream_id, data): # Override this
        print(f"Received data on stream {stream_id}: {data.decode()}")
        self.send_stream_data(stream_id, data) # Echo back the received data
    
    def handle_datagram_received(self, stream_id, data): # Override this
        print(f"Received datagram: {data.decode()}")
        self.send_datagram(stream_id, data) # Echo back the received datagram
    
    def handle_connection_made(self, headers):
        print(f"Connection made with headers: {headers}")

    # Don't override anything else

server = WebTransportServer("127.0.0.1", 4433, "cert.pem", "key.pem", MyProtocol)
asyncio.run(server.run())