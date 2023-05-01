import socket
import argparse
import sys
from struct import *

class PortInRangeAction(argparse.Action):
    def __call__(self, parser, namespace, port, option_string=None):
        if port < 1024 or port > 65535:
            raise argparse.ArgumentError(self, f"{port} is not in range of [1024, 65535]")
        setattr(namespace, self.dest, port)
        
class TestInRangeAction(argparse.Action):
    def __call__(self, parser, namespace, test, option_string=None):
        if test < 1 or test > 3:
            raise argparse.ArgumentError(self, f"{test} is not in range of [1, 3]")
        setattr(namespace, self.dest, test)
        
class ValidMethodAction(argparse.Action):
    def __call__(self, parser, namespace, method, option_string=None):
        method = method.strip().lower()
        methods = {'stop_and_wait':'SAW', 'gbn':'GBN', 'gbn-sr':'GBN-SR'}
        if method not in methods:
            raise argparse.ArgumentError(self, f'{method} is an invalid method')
        setattr(namespace, self.dest, methods[method])



def main():
    
    parser = argparse.ArgumentParser(description="File transferring application over 'DRTP'.")
    
    parser.add_argument(
        '-i', '--ip', type=str, default='127.0.0.1', help="Enter server ip (default = 127.0.0.1)")
    parser.add_argument(
        '-p', '--port', type=int, default=8088, action=PortInRangeAction, help="Enter server port (default = 8088)")
    parser.add_argument(
        '-t', '--test_case', type=int, default=1, action=TestInRangeAction, help="Enter testcase scenario")
    parser.add_argument(
        '-r', '--reliable_method', type=str, default='stop_and_wait', action=ValidMethodAction, help="Enter one of three reliability functions (stop_and_wait, GBN, GBN-SR)")
    
    server_parser = parser.add_argument_group('Server')
    
    server_parser.add_argument(
        '-s', '--server', action='store_true', help='Invoke as server')
    
    client_parser = parser.add_argument_group('Client')
    
    client_parser.add_argument(
        '-f', '--file', type=str, default='file_to_transfer.jpg', help="Enter file from client to be transfered")
    
    args = parser.parse_args()
    
# Section to implement and develope the use of headers etc.

header_format = '!IIHH'
#creates a packet with header information and application data
    #the input arguments are sequence number, acknowledgment number
    #flags (we only use 4 bits),  receiver window and application data 
    #struct.pack returns a bytes object containing the header values
    #packed according to the header_format !IIHH

def packet_create(seq, ack, flags, win, data):
    
    header = pack(header_format, seq, ack, flags, win)
    
    packet = header + data
    
    return packet.encode()

def header_parse(header):
    
    msg_header = unpack(header_format, header[:12])
    
    return msg_header
    

def connection_handshake(server_socket, client_socket):
    
    if server_socket:
        try:
            msg = server_socket.recv(1472).decode()
            
            seq, ack, flags, win = header_parse(msg)
            flags = flags_parse(flags)
            
            if seq == 1 and flags[0] == 1:
                flags = 12 # 1 1 0 0 (syn, ack)
                msg = packet_create(0, 0, flags, 0, b'')
                
                client_socket.send(msg)
                
                msg = server_socket.recv(1472).decode()
                
                
        except:
            
    elif client_socket:
        flags = 8 # 1 0 0 0 (syn)
        packet_create(1, 0, flag, 0, b'') # Sender sends SYN with sequence 1
# Section for starting server and client

def server_start(args: argparse.Namespace):
    
    server_host = args.ip
    server_port = args.port
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        
        server_socket.bind((server_host,server_port))
        server_socket.listen(1)
        
        print('------------------------------------------------')
        print(f'A simpleperf server is listening on port {server_port}')
        print('------------------------------------------------')
    
        try:
            while True:
                
                client_socket, client_address = server_socket.accept()
                connection_handshake(server_socket, client_socket)
                
def server_handle_client(conn, addr, args: argparse.Namespace):
    
def client_connect(args: argparse.Namespace):
    
def client_send(client_socket, args: argparse.Namespace):