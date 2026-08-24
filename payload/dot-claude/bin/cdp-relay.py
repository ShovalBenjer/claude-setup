"""TCP relay so WSL can reach Chrome's DevTools port on Windows.

Chrome binds --remote-debugging-port to 127.0.0.1 only, and refuses to bind
anywhere else. Under WSL2's default NAT networking, WSL's 127.0.0.1 is its own
loopback, not Windows'. So the port is simultaneously up and unreachable, which
is why a probe from WSL returns "connection refused" for a server that is
demonstrably answering on the Windows side.

Measured 2026-08-06 on this machine: a listener bound to 0.0.0.0 on Windows IS
reachable from WSL at the default-route address, with no admin rights and no
firewall prompt. So the whole gap is Chrome's loopback-only bind, and a
userspace relay closes it without .wslconfig, without mirrored networking, and
without `wsl --shutdown` killing every running session.

Runs on the WINDOWS python. Bidirectional raw byte pump, so the WebSocket
upgrade and everything after it passes through untouched.
"""
import socket
import sys
import threading

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9324
TARGET_HOST = "127.0.0.1"
TARGET_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9224


def pump(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        # Half-close rather than close: the other direction may still be
        # streaming. A CDP screenshot response outlives the request that asked
        # for it, and closing both ways here truncates it.
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle(client):
    try:
        upstream = socket.create_connection((TARGET_HOST, TARGET_PORT), timeout=10)
    except OSError:
        client.close()
        return
    upstream.settimeout(None)
    client.settimeout(None)
    threading.Thread(target=pump, args=(client, upstream), daemon=True).start()
    pump(upstream, client)
    for s in (client, upstream):
        try:
            s.close()
        except OSError:
            pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LISTEN_HOST, LISTEN_PORT))
    srv.listen(64)
    print(f"relay {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}", flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
