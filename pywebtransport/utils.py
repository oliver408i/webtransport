import os, asyncio
from aioquic.h3.connection import H3Connection
from aioquic.h3.events import HeadersReceived, DatagramReceived, WebTransportStreamDataReceived
from aioquic.quic.events import StreamDataReceived
from aioquic.quic.configuration import QuicConfiguration

class WebTransportError(Exception):
    """Custom exception for WebTransport-related errors."""
    pass


def validate_certfile(certfile):
    """
    Validate the certificate file path if provided.

    :param certfile: Path to the certificate file
    :raises WebTransportError: If the certificate file is invalid or not accessible
    """
    if certfile and not os.path.isfile(certfile):
        raise WebTransportError(f"Invalid certificate file: {certfile}")


def get_quic_configuration(is_client, certfile=None, private_key=None):
    """
    Create and return a QUIC configuration object.

    :param is_client: Boolean indicating if the configuration is for a client
    :param certfile: Optional path to a certificate file for secure connections
    :return: A configured QuicConfiguration instance
    """
    configuration = QuicConfiguration(is_client=is_client, alpn_protocols=["h3"], max_datagram_frame_size=65536)
    if certfile and is_client:
        configuration.load_verify_locations(certfile)
    elif certfile and not is_client:
        if not private_key:
            raise ValueError("Private key is required for server-side QUIC connections")
        configuration.load_cert_chain(certfile, private_key)
    return configuration