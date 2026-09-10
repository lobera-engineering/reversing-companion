#!/usr/bin/env python3
"""Behavior checks run inside a network-disabled course container."""
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import threading
import time


def connect(port, process):
    until = time.monotonic() + 5
    while time.monotonic() < until:
        try:
            return socket.create_connection(('127.0.0.1', port), timeout=3)
        except ConnectionRefusedError:
            if process.poll() is not None:
                raise RuntimeError('Server exited: ' + process.communicate()[1].decode(errors='replace'))
            time.sleep(.05)
    raise RuntimeError('Server did not listen in time.')


def server(mode, binary):
    port = 5001 if mode == 'tcp-server' else 4443 if mode == 'tls-server' else 5017
    args = [binary, str(port)] if mode == 'smart-server' else [binary]
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        sock = connect(port, process)
        if mode == 'tls-server':
            sock = ssl._create_unverified_context().wrap_socket(sock, server_hostname='course.local')
        with sock:
            sock.settimeout(4)
            if mode == 'tcp-server':
                sock.sendall(b'COURSE_TCP_MESSAGE\n')
                response = sock.recv(1024)
                assert response == b'I got your message', response
            elif mode == 'tls-server':
                greeting = sock.recv(1024)
                assert b'hello hacker' in greeting, greeting
                sock.sendall(b'printf COURSE_TLS_OK\r\n')
                response = sock.recv(1024)
                assert b'COURSE_TLS_OK' in response, response
            else:
                greeting = sock.recv(1024)
                assert b'Please enter the secret text' in greeting, greeting
                sock.sendall(b'incorrect\n')
                rejected = sock.recv(1024)
                assert b'secret was wrong' in rejected, rejected
                sock.sendall(b"You don't know the power of the dark side\n")
                response = sock.recv(8192)
                assert len(response) > 100 and b'::' in response, response
        return {'mode': mode, 'response': response.decode(errors='replace'), 'network': 'loopback only inside --network none'}
    finally:
        process.terminate()
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()


def client(mode, binary):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 80 if mode == 'http-code' else 0))
        listener.listen(1)
        listener.settimeout(5)
        port = listener.getsockname()[1]
        received = []
        errors = []
        def serve():
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(4)
                    received.append(conn.recv(4096))
                    # A single ret instruction provides a bounded test payload.
                    conn.sendall(b'\xc3' if mode == 'http-code' else b'COURSE_TCP_REPLY')
            except Exception as exc:
                errors.append(str(exc))
        thread = threading.Thread(target=serve)
        thread.start()
        try:
            args = [binary, '127.0.0.1', str(port)] if mode == 'tcp-client' else [binary]
            result = subprocess.run(args, input=b'COURSE_TCP_INPUT\n', capture_output=True, timeout=8)
        finally:
            thread.join(timeout=6)
        assert not errors, errors
        assert received, 'Client did not send a request.'
        if mode == 'tcp-client':
            assert b'COURSE_TCP_INPUT' in received[0], received
            assert b'COURSE_TCP_REPLY' in result.stdout, result.stdout
            assert result.returncode == 0, result.stderr
        else:
            assert b'GET /sh HTTP/1.1' in received[0], received
            # Default build has an NX stack. Fetch succeeds, execution must fault.
            assert result.returncode == -11, result.returncode
        return {'mode': mode, 'request': received[0].decode(errors='replace'),
                'stdout': result.stdout.decode(errors='replace'), 'exit_code': result.returncode}


if __name__ == '__main__':
    mode, binary = sys.argv[1:]
    result = client(mode, binary) if mode in ('tcp-client', 'http-code') else server(mode, binary)
    print(json.dumps(result))
