from .utils import validate_certfile, get_quic_configuration
import logging

from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection
from aioquic.h3.events import (
    HeadersReceived,
    WebTransportStreamDataReceived,
    DatagramReceived
)
from aioquic.quic.connection import stream_is_unidirectional
from typing import Optional
from aioquic.quic.events import QuicEvent, ProtocolNegotiated
import asyncio

logger = logging.getLogger(__name__)

logger.info("WebTransport server initialized")

class WebTransportProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http: Optional[H3Connection] = None
    
    def get_next_available_stream_id(self):
        """
        Get the next available stream ID for creating WebTransport streams.

        :return: The next available stream ID
        """
        return self._quic.get_next_available_stream_id()

    def create_webtransport_stream(self, is_unidirectional=False):
        """
        Creates a WebTransport stream from the server side

        :param is_unidirectional: Boolean indicating if the stream is unidirectional
        :return: The created WebTransport stream id
        """
        return self._http.create_webtransport_stream(is_unidirectional)

    def quic_event_received(self, event: QuicEvent):

        if isinstance(event, ProtocolNegotiated):
            logger.debug("Protocol negotiated: " + event.alpn_protocol)
            self._http = H3Connection(self._quic, enable_webtransport=True)
        
        logger.debug("Received QUIC event: " + str(event))
        if self._http:
            for http_event in self._http.handle_event(event):
                logger.debug("Received HTTP/3 event: " + str(http_event))
                self.http_event_received(http_event)
    
    def stream_is_unidirectional(self, stream_id):
        """
        Check if a WebTransport stream is unidirectional.

        :param stream_id: Stream ID to check
        :return: Boolean indicating if the stream is unidirectional
        """
        return stream_is_unidirectional(stream_id)
    
    def send_stream_data(self, stream_id, data, end_stream=False):
        """
        Send data over a WebTransport stream.

        :param stream_id: Stream ID to send data on
        :param data: Data to send
        :param end_stream: Boolean indicating if the stream should be closed
        """
        self._http._quic.send_stream_data(stream_id, data, end_stream=end_stream)
    
    def send_datagram(self, stream_id, data):
        """
        Send a datagram message over the WebTransport connection.

        :param stream_id: Stream ID to send data on
        :param data: Data to send
        """
        self._http.send_datagram(stream_id, data)

    def handle_stream_data_received(self, stream_id, data):
        """
        Default handler for data received on a WebTransport stream.
        Override this method to handle stream data.

        :param stream_id: Stream ID where data was received
        :param data: Data payload received
        """
    
    def handle_datagram_received(self, stream_id, data):
        """
        Default handler for datagrams received over the WebTransport connection.
        Override this method to handle datagrams.

        :param data: Datagram payload received
        """

    def handle_connection_made(self, headers):
        """
        Default handler for when the connection is made.
        Override this method to handle connection events.

        :param headers: Headers of the connection
        """

    def http_event_received(self, event):
        if isinstance(event, HeadersReceived):
            # Accept the WebTransport session
            logger.debug("Accepting WebTransport session")
            self._http.send_headers(
                event.stream_id,
                [
                    (b":status", b"200"),
                    (b"sec-webtransport-http3-draft", b"draft02"),
                ],
            )
            self.handle_connection_made(event.headers)

        elif isinstance(event, WebTransportStreamDataReceived):
            self.handle_stream_data_received(event.stream_id, event.data)
        elif isinstance(event, DatagramReceived):
            self.handle_datagram_received(event.stream_id, event.data)

class WebTransportServer:
    def __init__(self, host, port, certfile, keyfile, protocol: WebTransportProtocol):
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.protocol = protocol

        validate_certfile(self.certfile)
        validate_certfile(self.keyfile)
    
    async def run(self):
        configuration = get_quic_configuration(is_client=False, certfile=self.certfile, private_key=self.keyfile)
        await serve(
            self.host,
            self.port,
            configuration=configuration,
            create_protocol=self.protocol
        )
        logger.info("WebTransport server running on %s:%s", self.host, self.port)
        await asyncio.Future()