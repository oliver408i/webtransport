import argparse
import asyncio
import logging
from typing import Optional

from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h0.connection import H0_ALPN
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import (
    HeadersReceived,
    WebTransportStreamDataReceived,
)
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, ProtocolNegotiated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebTransportProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http: Optional[H3Connection] = None

    def quic_event_received(self, event: QuicEvent):

        if isinstance(event, ProtocolNegotiated):
            print("Protocol negotiated:", event.alpn_protocol)
            self._http = H3Connection(self._quic, enable_webtransport=True)
        
        print("Received QUIC event:", event)
        if self._http:
            for http_event in self._http.handle_event(event):
                print("Received HTTP/3 event:", http_event)
                self.http_event_received(http_event)

    def http_event_received(self, event):
        if isinstance(event, HeadersReceived):
            # Accept the WebTransport session
            print("Accepting WebTransport session")
            self._http.send_headers(
                event.stream_id,
                [
                    (b":status", b"200"),
                    (b"sec-webtransport-http3-draft", b"draft02"),
                ],
            )
        elif isinstance(event, WebTransportStreamDataReceived):
            # Echo back the received data
            print("Echoing data:", event.data)
            self._http._quic.send_stream_data(event.stream_id, event.data, end_stream=False)
            if event.stream_ended:
                self._http._quic.send_stream_data(event.stream_id, b"", end_stream=True)

async def main():
    parser = argparse.ArgumentParser(description="WebTransport Echo Server")
    parser.add_argument(
        "--certificate", type=str, required=True, help="Path to the certificate file"
    )
    parser.add_argument(
        "--private-key", type=str, required=True, help="Path to the private key file"
    )
    parser.add_argument(
        "--port", type=int, default=4433, help="Port to listen on (default: 4433)"
    )
    args = parser.parse_args()

    configuration = QuicConfiguration(
        is_client=False,
        alpn_protocols=H0_ALPN + H3_ALPN,
        max_datagram_frame_size=65536
    )
    configuration.load_cert_chain(args.certificate, args.private_key)

    await serve(
        "0.0.0.0",
        args.port,
        configuration=configuration,
        create_protocol=WebTransportProtocol,
        retry=True,
        
    )
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass