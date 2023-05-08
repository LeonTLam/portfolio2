import socket
import argparse
import sys
import signal
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

def handle_method(server_socket, client_socket, client_address, args):
    if args.server:
        method = args.reliable_method
        print(f'Reliable method: {method}')
        
        msg = server_socket.recv(1024).decode()
        print(f'{client_address} +[method]')
        if msg == method:
            print('Both methods are valid, continuing...')
            
            flags = 0
            msg = packet_create(0, 1, flags, 0, b'')
            client_socket.send(msg)
            print(f'{client_address} <-[ACK]')
            
            server_handle_client(server_socket,client_address,client_address,args)
        else:
            print(f"Client's method {msg} is different from server's method {method}\nRestarting...")
            client_socket.close()
            server_socket.close()
            server_start(args)
    
    elif args.client:
        method = args.reliable_method
        print(f'Reliable method: {method}')
        
        client_socket.send(method.encode())
        print(f'{args.server} <-[method]')
        
        msg = client_socket.recv(1024).decode()
        seq, ack, flags, win = header_parse(msg)
        if ack == 1:
            print(f'{client_address} +[ACK]\nBoth methods are valid, continuing...')
            client_send(client_socket, args)
        else:
            print(f"Your method {method} is different from server's method, make sure you are running the same method as server.\nClosing...")
            client_socket.close()
            sys.exit(1)            
            

# Section to implement and develope the use of headers etc.

header_format = '!IIHH'
packet_size = 1472
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

def flags_parse(flags):

    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    res = flags & (1 << 0)

    return syn, ack, fin, res

def three_way_handshake(server_socket, client_socket, client_address, args):
    
    if args.server:
        server_socket.settimeout(0.5)
        try:
            # Server receives SYN handshake
            msg = server_socket.recv(packet_size).decode()
            seq, ack, flags, win = header_parse(msg)
            flags = flags_parse(flags)
            
            if seq == 1 and flags[0] == 8:
                print(f'{client_address} +[SYN]')
                # Server sends SYN-ACK handshake
                
                flags = 12 # 1 1 0 0 (SYN, ACK)
                msg = packet_create(0, 0, flags, 0, b'')
                client_socket.send(msg)
                print(f'{client_address} <-[SYN-ACK]')
                
                # Server receives ACK handshake
                msg = server_socket.recv(packet_size).decode()
                seq, ack, flags, win = header_parse(msg)
                if ack == 1:
                    print(f'{client_address} +[ACK]\nClient has connected.')
                    handle_method(server_socket, client_socket, client_address, args)

        except socket.timeout:
            print('Error communicating with client, try again.')
            client_socket.close()
            server_socket.close()
            server_start(args)
            
    elif args.client:
        client_socket.settimeout(0.5)
        try:
            # Client sends SYN handshake
            flags = 8 # 1 0 0 0 (SYN)
            msg = packet_create(1, 0, flags, 0, b'') # Sender sends SYN with sequence 1
            client_socket.send(msg)
            print(f'{args.bind} <-[SYN]')
            # Client receives SYN-ACK handshake
            msg = client_socket.recv(packet_size).decode()
            seq, ack, flags, win = header_parse(msg)
            flags = flags_parse(flags)

            if flags[0] == 8 and flags[1] == 4:
                print(f'{args.bind} +[SYN-ACK]')
                
                # Client sends ACK
                flags = 0
                msg = packet_create(0, 1, flags, 0, b'')
                client_socket.send(msg)
                print(f'{args.bind} <-[ACK]')
                
                handle_method(None, client_socket, None, args)

        except socket.timeout:
            print('Error communication with server, try again')
            client_socket.close()
            sys.exit(1)

def two_way_byeshake(server_socket, client_socket, client_address, args):

    if args.server:
        server_socket.settimeout(0.5)
        try:
            msg = server_socket.recv(packet_size).decode()
            seq, ack, flags, win = header_parse(msg)
            flags = flags_parse(flags)

            if flags[2] == 2:
                print(f'{client_address} +[FIN]')

                flags = 0
                msg = packet_create(0, 1, flags, 0, 0)
                client_socket.send(msg)
                print(f'{client_address} <-[ACK]')
                
                print(f'Client {client_address} has disconnected')
                client_socket.close()
        except socket.timeout:
            two_way_byeshake(server_socket,client_socket,client_address,args)
        
    elif args.client:
        client_socket.settimeout(0.5)
        try:
            flags = 2
            msg = packet_create(0, 0, flags, 0, b'')
            client_socket.send(msg)
            print(f'{args.bind} <-[FIN]')
            
            msg = client_socket.recv(packet_size).decode()
            seq, ack, flags, win = header_parse(msg)
            
            if ack == 1:
                print(f'{args.bind} +[ACK]\nClosing...')
                client_socket.close()
                sys.exit(1)
        except socket.timeout:
            two_way_byeshake(None,client_socket,None,args)
# Section for starting server and client

def server_start(args: argparse.Namespace):
    
    server_host = args.ip
    server_port = args.port
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        
        server_socket.bind((server_host,server_port))
        server_socket.listen(1)
        
        try:
            while True:
                print('---------------------------------------')
                print(f'Server is listening on port {server_port}')
                print('---------------------------------------')
                client_socket, client_address = server_socket.accept()
                three_way_handshake(server_socket, client_socket, client_address, args)
                
        
        except KeyboardInterrupt:
            print('Closing server')
            server_socket.close()
            sys.exit(1)
            
def server_handle_client(server_socket, client_socket, client_address, args):
    server_socket.settimeout(0.5)
    
    dataArray = []
    def send_and_wait(seq_num):
        while True:
            try:
                msg = server_socket.recv(packet_size).decode()
                seq, ack, flags, win= header_parse(msg)
                flags = flags_parse(flags)
                
                if seq == seq_num:
                    print(f'{client_address} +[PACKET #{seq}]')
                    data_msg = msg[12:]
                    dataArray.append(data_msg)
                    
                    msg = packet_create(0, 1, 0, 0, b'')
                    client_socket.send(msg)
                    print(f'{client_address} +[ACK #{seq_num}]')
                    seq_num += 1
                
                elif seq != seq_num:
                    msg = packet_create(seq_num-1, 1, 0, 0, b'')
                    client_socket.send(msg)
                    print(f'{client_address} +[DUPACK #{seq_num - 1}]')
                
                elif flags[2] == 2:
                    print(f'{client_address} +[FIN]')

                    msg = packet_create(0, 1, 0, 0, 0)
                    client_socket.send(msg)
                    print(f'{client_address} <-[ACK]')
                    
                    print(f'Client {client_address} has disconnected')
                    client_socket.close()
                    break
            except socket.timeout:
                send_and_wait(seq_num)            
        return dataArray
    
    with open(args.file, 'wb') as file:
        for data in dataArray:
            file.write(data)

def client_connect(args: argparse.Namespace):

    server_host = args.ip
    server_port = args.port

    print('----------------------------------------------------')
    print(f'Connecting to server {server_host}:{server_port}')
    print('----------------------------------------------------')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host,server_port))
        three_way_handshake(None, client_socket, None, args)
        
def client_send(client_socket, args: argparse.Namespace):
    client_socket.settimeout(0.5)
    
    dataArray = []
    
    with open(args.file, 'rb') as file:
        while True:
            try:
                data = file.read(1460)
                dataArray.append(data)
                if not data:
                    break
            except IOError as e:
                print(f'An IOerror occured: {e}')
                client_socket.close()
                sys.exit(1)
    
    def send_and_wait(seq_num):
        for seq_num in range(len(dataArray)):
            try:
                msg = packet_create(seq_num, 0, 0, 1, dataArray[seq_num])
                client_socket.send(msg)
            except:
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
    