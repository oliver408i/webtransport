import warnings
from cryptography.utils import CryptographyDeprecationWarning

# Suppress CryptographyDeprecationWarning to avoid the spam
warnings.filterwarnings(
    "ignore",
    category=CryptographyDeprecationWarning,
    message=".*naïve datetime object have been deprecated.*",
)

import asyncio, logging
import os
from aioquic.asyncio import connect
from aioquic.h3.connection import H3Connection
from aioquic.h3.events import HeadersReceived, DataReceived, DatagramReceived, WebTransportStreamDataReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived
from .utils import WebTransportError, validate_certfile, get_quic_configuration

# Patch asyncio.StreamWriter.__del__ to avoid the NotImplementedError spam
def safe_del(self):
    try:
        if self._transport and not self._transport.is_closing():
            pass
    except NotImplementedError:
        pass
    except Exception:
        pass
asyncio.StreamWriter.__del__ = safe_del

logger = logging.getLogger(__name__)
logger.info("WebTransport client initialized")

class WebTransportClient:
    """
    A WebTransport client for connecting to a WebTransport server and handling
    WebTransport-specific communication using QUIC and HTTP/3.
    """
    def __init__(self, host, port, certfile=None):
        """
        Initialize the WebTransport client.

        :param host: Hostname or IP address of the WebTransport server
        :param port: Port of the WebTransport server
        :param certfile: Optional path to the certificate file for secure connections
        """
        super().__init__()
        self.host = host
        self.port = port
        self.certfile = certfile
        self.connection = None
        self.http = None
        self.streamOpen = False
        self._context_manager = None
        self.ping_task = None
        self.session_id = None
        self._datagram_handler = None
        self._stream_data_handler = None
        self._wt_stream_ids = []

        validate_certfile(self.certfile)

    async def connect(self):
        """
        Establish a WebTransport connection and perform the handshake.

        :raises WebTransportError: If the WebTransport handshake fails
        """
        configuration = get_quic_configuration(is_client=True, certfile=self.certfile)
        if self.certfile:
            configuration.load_verify_locations(self.certfile)

        self._context_manager = connect(self.host, self.port, configuration=configuration)
        self.connection = await self._context_manager.__aenter__()
        self.http = H3Connection(self.connection._quic, enable_webtransport=True)
        self.connection.quic_event_received = self._quic_event_received

        await self._send_webtransport_request()

        logger.debug("WebTransport handshake completed")

    def _quic_event_received(self, event):
        """
        Handle QUIC events and route HTTP/3 events.

        :param event: A QUIC event received from the connection
        """
        logger.debug("Received QUIC event: %s", event)
        if isinstance(event, StreamDataReceived):
            if event.stream_id in self._wt_stream_ids:
                self._handle_stream_data_received(event.stream_id, event.data)
        if self.http:
            for http_event in self.http.handle_event(event):
                if isinstance(http_event, HeadersReceived):
                    self._handle_headers_received(http_event)
                elif isinstance(http_event, WebTransportStreamDataReceived):
                    self._handle_stream_data_received(http_event.stream_id, http_event.data)
                elif isinstance(http_event, DatagramReceived):
                    self._handle_datagram_received(http_event.data)
    
    def get_next_available_stream_id(self):
        """
        Get the next available stream ID for creating WebTransport streams.

        :return: The next available stream ID
        """
        return self.http._quic.get_next_available_stream_id()
    
    def create_webtransport_stream(self, is_unidirectional=False):
        """
        Create a WebTransport stream.

        :param stream_id: Stream ID to create
        :raises WebTransportError: If the WebTransport session is not established
        :return: The created WebTransport stream id
        """
        if self.session_id is None:
            raise WebTransportError("WebTransport session not established")
        s = self.http.create_webtransport_stream(self.session_id, is_unidirectional)
        self.connection.transmit()
        self._wt_stream_ids.append(s)
        return s

    def _handle_headers_received(self, event):
        """
        Handle HTTP/3 headers received during the WebTransport handshake.

        :param event: HeadersReceived event
        """
        logger.debug("Received HTTP/3 headers: %s", event)
        headers = dict(event.headers)
        if headers.get(b":status") == b"200":
            self.streamOpen = True

    def _handle_stream_data_received(self, stream_id, data):
        """
        Default handler for data received on a WebTransport stream.

        :param stream_id: Stream ID where data was received
        :param data: Data payload received
        """
        if self._stream_data_handler:
            asyncio.create_task(self._stream_data_handler(stream_id, data))

    def _handle_datagram_received(self, data):
        """
        Default handler for datagrams received over the WebTransport connection.

        :param data: Datagram payload received
        """
        if self._datagram_handler:
            asyncio.create_task(self._datagram_handler(data))

    def set_stream_data_handler(self, handler):
        """
        Set a custom handler for stream data received.

        :param handler: A coroutine function to handle stream data
        :raises ValueError: If the handler is not a coroutine function
        """
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError("Stream data handler must be an async function")
        self._stream_data_handler = handler

    def set_datagram_handler(self, handler):
        """
        Set a custom handler for datagrams received.

        :param handler: A coroutine function to handle datagrams
        :raises ValueError: If the handler is not a coroutine function
        """
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError("Datagram handler must be an async function")
        self._datagram_handler = handler

    def send_datagram(self, stream_id,data):
        """
        Send a datagram message over the WebTransport connection.

        :param data: Data to send
        :raises WebTransportError: If the WebTransport session is not established
        """
        if self.session_id is None:
            raise WebTransportError("WebTransport session not established")
        self.http.send_datagram(stream_id, data)

    def send_stream_data(self, stream_id, data, end_stream=False):
        """
        Send data over a WebTransport stream.

        :param data: Data to send
        :raises WebTransportError: If the WebTransport session is not established
        :param end_stream: Boolean indicating if the stream should be closed
        """
        if self.session_id is None:
            raise WebTransportError("WebTransport stream not established")
        self.http._quic.send_stream_data(stream_id, data, end_stream=end_stream)

    async def _send_webtransport_request(self):
        """
        Send the initial WebTransport CONNECT request and complete the handshake.

        :raises WebTransportError: If the handshake does not complete successfully
        """
        self.session_id = self.http._quic.get_next_available_stream_id()
        self.http.send_headers(
            stream_id=self.session_id,
            headers=[
                (b":method", b"CONNECT"),
                (b":protocol", b"webtransport"),
                (b":path", b"/"),  # Adjust to your server's WebTransport path
                (b":authority", f"{self.host}:{self.port}".encode()),
                (b"sec-webtransport-http3-draft", b"draft02"),
            ]
        )
        self.connection.transmit()

        self.ping_task = asyncio.create_task(self._ping())

        while not self.streamOpen:
            await asyncio.sleep(0.1)

    async def _ping(self):
        """
        Continuously transmit data to keep the connection alive.
        """
        try:
            while True:
                self.connection.transmit()
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass

    async def close(self):
        """
        Close the WebTransport connection and clean up resources.
        """
        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass

        if self.connection:
            self.connection.close()

        if self._context_manager:
            await self._context_manager.__aexit__(None, None, None)
            self._context_manager = None