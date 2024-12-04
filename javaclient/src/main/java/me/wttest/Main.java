package me.wttest;

import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;

import net.luminis.quic.QuicClientConnection;
import net.luminis.quic.QuicStream;

public class Main {
    public static void main(String[] args) throws IOException{
        System.out.println("Hello world!");
        QuicClientConnection.Builder builder = QuicClientConnection.newBuilder();
        builder.noServerCertificateCheck();
        QuicClientConnection connection = builder
                .uri(URI.create("https://127.0.0.1:4433"))
                .applicationProtocol("h3")
                .build();
        connection.connect();
        QuicStream quicStream = connection.createStream(true);
        byte[] requestData = "java-: hello test".getBytes(StandardCharsets.US_ASCII);
        quicStream.getOutputStream().write(requestData);
        quicStream.getOutputStream().close();

        System.out.print("Response from server: ");
        quicStream.getInputStream().transferTo(System.out);
        System.out.println();
        System.out.println("Closing connection...");
        connection.closeAndWait();

    }
}
