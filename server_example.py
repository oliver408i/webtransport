from pywebtransport.server import WebTransportServer, WebTransportProtocol
import asyncio, logging

logging.basicConfig(level=logging.DEBUG)

class MyProtocol(WebTransportProtocol):
    # No need to override the init method, but you can if you want

    def handle_stream_data_received(self, stream_id, data): # Override this
        self.send_stream_data(stream_id, data) # Echo back the received data
    
    def handle_datagram_received(self, stream_id, data): # Override this
        print(f"Received datagram: {data.decode()}")
        self.send_datagram(stream_id, data) # Echo back the received datagram
    
    def handle_connection_made(self, headers):
        print(f"Connection made with headers: {headers}")
    
    def handle_quic_stream_data_received(self, stream_id, data): # This is for lower-level QUIC stream data
        # Use this if you need to handle non-WebTransport stream data
        try:
            if data.decode("utf-8").startswith("java"): # This is custom handling for javaclient since it doesn't send over WebTransport
                self.send_stream_data(stream_id, data) # Echo back
                self.send_stream_data(stream_id, b"", True) # Close the stream
                return 1 # Do not process further (i.e. propagate data to HTTP/3)
            else:
                return # Propagate data to HTTP/3
        except UnicodeDecodeError:
            pass # Ignore non-UTF-8 data (usually connection and system data)

    # Don't override anything else

server = WebTransportServer("127.0.0.1", 4433, "cert.pem", "key.pem", MyProtocol)
asyncio.run(server.run())