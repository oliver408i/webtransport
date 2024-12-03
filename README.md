# Py WebTransport
A simplified toolchain for working with WebTransport in Python. This uses the lower-level `aioquic` module to implement a WebTransport server and client. The purpose of this repo is to simplify the usage of `aioquic` for WebTransport. Many other languages, esp `Node.js` have pre-made modules implementing WebTransport servers and clients, but not Python, so I aim to do that here.

## Making Certs
HTTP/3 (which WebTransport runs on) requires TLS (https) and so you need certificates. For local development, we can make our own certs.  
`openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem -config openssl.cnf` will use the example cnf file to make minimal QUIC-compatable certificate. Import it into your system's certificate manager and trust it.  
There are a few additional steps if you wish to use this in a browser. Always use the most update to date version to ensure you have http3 compat.
- Chrome, Chromium, Edge, and forks: Launch with `--origin-to-force-quic-on=127.0.0.1:4433`
- Firefox: Go to `about:config` and set `network.http.http3.disable_when_third_party_roots_found` to false
- Safari, Webkit: Doesn't support WebTransport yet!

## Client
See `client_example.py` for an example on how to use the module. It's pretty simple & straightforward, not much harder than using WebSockets.  
`web.html` is a very basic implementation for web. JS already have a full API for WebTransport, see [Mozilla's docs](https://developer.mozilla.org/en-US/docs/Web/API/WebTransport)

## Server
See `server_example.py` for an example on how to use the module for making a server. It works with both browsers (as long as you have valid certs) and the python client.

## Features
 - [x] Client custom stream & datagram handler (receiver)
 - [x] Client open stream & send stream data or datagram
 - [x] Server custom stream & datagram handler (receiver)
 - [x] Server open stream & send stream data or datagram
 - [x] Server supports web (JS api client)
 - [x] Server custom handler for new incomming requests
 - [x] Basic support for Unidirectional streams and checking for Unidirectional streams
 - [ ] Proper support for ending stream (end_stream)
 - [ ] Complete support for Unidirectional streams and properly handing then
 - [ ] Server & Client custom header receiving and sending
 - [ ] Server & Client custom (non-WebTransport) stream sending and receiving