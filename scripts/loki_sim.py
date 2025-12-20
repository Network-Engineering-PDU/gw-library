import sys
import ssl
import time
import socket
import threading
import argparse

import ttgwlib.commands as commands
from ttgwlib.uart import Uart
from ttgwlib import GatewayError


class LokiSim:
    START = bytearray.fromhex("04810200ff")
    
    def __init__(self, host="localhost", port=31888, dev=None):
        self.host = host
        self.port = port
        self.dev = dev
        self.uart = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5)
        self.ssl_context = None
        self.rx_thd = threading.Thread(target=self.relay_rx)
        self.tx_thd = threading.Thread(target=self.relay_tx)
        self.running = False

    def create_default_ssl_context(self):
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.ssl_context.options |= ssl.OP_NO_SSLv2
        self.ssl_context.options |= ssl.OP_NO_SSLv3
        self.ssl_context.options |= ssl.OP_NO_TLSv1
        self.ssl_context.options |= ssl.OP_NO_TLSv1_1
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def set_ca_cert(self, ca_cert):
        if self.ssl_context is None:
            self.create_default_ssl_context()
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        self.ssl_context.load_verify_locations(ca_cert)

    def set_client_auth(self, client_cert, client_key):
        if self.ssl_context is None:
            self.create_default_ssl_context()
        self.ssl_context.load_cert_chain(client_cert, client_key)


    def relay_rx(self):
        while self.running:
            msg = bytearray()
            while len(msg) < 255:
                b = self.uart.get_byte(1)
                if b:
                    msg += b
                else:
                    break
            if msg:
                self.socket.sendall(msg)

    def relay_tx(self):
        msg = commands.Reset()
        self.uart.send_msg(msg.serialize())
        while self.running:
            try:
                msg = self.socket.recv(4096)
                self.uart.send_msg(msg)
            except socket.timeout:
                continue

    def close(self):
        print("Exiting...")
        self.running = False
        if self.rx_thd.is_alive():
            self.rx_thd.join()
        if self.tx_thd.is_alive():
            self.tx_thd.join()
        self.socket.close()
        if self.uart:
            self.uart.stop()

    def run(self):
        try:
            self.uart = Uart(self.dev)
            print(f"Connecting to {self.host}:{self.port}")
            if self.ssl_context:
                self.socket = self.ssl_context.wrap_socket(self.socket)
            self.socket.connect((self.host, self.port))
            print("Connected")
            print("Press CTRL+C to exit")
            self.running = True
            self.rx_thd.start()
            self.tx_thd.start()
            while True:
                time.sleep(1)

        except GatewayError:
            print("Gateway error")
        except ConnectionRefusedError:
            print("Unable to connect")
        except KeyboardInterrupt:
            pass
        finally:
            self.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Loki simulator.')
    parser.add_argument("-d", "--device", type=str, default=None,
        help='Device port')
    parser.add_argument("-a", "--address", type=str, default="localhost",
        help='Remote server ip address')
    parser.add_argument("-p", "--port", type=int, default=31888,
        help='Remote server tcp port')
    parser.add_argument("--ca-cert", dest="ca_cert", type=str,
        help='CA certificate path (enables server authentication)')
    parser.add_argument("--client-cert", dest="client_cert", type=str,
        help='Client certificate path (enables client authentication)')
    parser.add_argument("--client-key", dest="client_key", type=str,
        help='Client private key path (enables client authentication)')
    args = parser.parse_args()

    if ((args.client_key and not args.client_cert)
            or (not args.client_key and args.client_cert)):
        print("Client certificate requires client key")
        sys.exit(1)

    loki_sim = LokiSim(args.address, args.port, args.device)
    if args.ca_cert:
        loki_sim.set_ca_cert(args.ca_cert)
    if args.client_cert:
        loki_sim.set_client_auth(args.client_cert, args.client_key)
    loki_sim.run()
