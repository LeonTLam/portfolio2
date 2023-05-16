import socket
import argparse
import sys
import time
import os
from struct import *

# Description:
# Custom action to check if port is within valid range ∊ [1024, 65535]
# Arguments:
# args.port or port: holds the port retrieved from command-line option
# __call__: Method to be called when corresponding command-line argument is encountered
# namespace: When action is triggered, value port is set to namespace object (args.port)
# Returns ArgumentError if out of range; Returns port if valid
class PortInRangeAction(argparse.Action):
    def __call__(self, parser, namespace, port, option_string=None):
        if port < 1024 or port > 65535:
            raise argparse.ArgumentError(self, f"{port} is not in range of [1024, 65535]")
        setattr(namespace, self.dest, port)

# Description
# Custom action to check if args.reliable_method is valid
# Arguments:
# method: holds string args.reliable_method without whitespace and in lower capitalization
# methods: dictionary with valid string to be entered
# Returns ArgumentError if method is invalid; Returns method in uppercase and shortened if valid
class ValidMethodAction(argparse.Action):
    def __call__(self, parser, namespace, method, option_string=None):
        method = method.strip().lower()
        methods = {'saw':'SAW','stop_and_wait':'SAW', 'gbn':'GBN', 'gbn-sr':'GBN-SR'}
        if method not in methods:
            raise argparse.ArgumentError(self, f'{method} is an invalid method')
        setattr(namespace, self.dest, methods[method])

# Description:
# Function to handle if both server and client are invoked with same reliable method
# Arguments:
# server_socket: holds the binded server connection
# client_socket: holds the connected client
# client_address: holds the connected client's address and port
# args: holds the server arguments with the same object-names
def handle_method(server_socket, client_socket, client_address, args):
    
    # If invoked as server
    if args.server:
        # Store reliable method
        method = args.reliable_method
        print(f'Reliable method: {method}')
        
        # Receive client's reliable method
        msg = client_socket.recv(packet_size).decode()
        print(f'{client_address} +[method]')
        
        # If both methods match, send ACK, then call function server_handle_client()
        if msg == method:
            send_ack(client_socket, client_address, args)
            print('Both methods are valid, continuing...')
            server_handle_client(server_socket,client_socket,client_address,args)
        else:
        # If methods do not match, exit
            print(f"Client's method {msg} is different from server's method {method}\nRestarting...")
            client_socket.close()
            server_socket.close()
            server_start(args)
    
    # If invoked as client
    elif args.client:
        # Store reliable method
        method = args.reliable_method
        print(f'Reliable method: {method}')
        
        # Send reliable method
        client_socket.send(method.encode())
        print(f'{args.ip} <-[method]')
        
        # Receive msg
        msg = client_socket.recv(packet_size)
        seq, ack, flags, win = header_parse(msg)
        # Receive ACK, call function client_send()
        if ack == 1:
            print(f'{args.ip} +[ACK]\nBoth methods are valid, continuing...')
            client_send(client_socket, args)
        else:
        # If not ACK, exit
            print(f"Your method {method} is different from server's method, make sure you are running the same method as server.\nClosing...")
            client_socket.close()
            sys.exit(1)            
            


# Description:
# Structure for header (12 bytes)
# Arguments:
# '!' Byte order, network (= big-endian)
# 'I' Unsigned int, 4 bytes
# 'H' Unsigned short int, 2 bytes
header_format = '!IIHH'

# Packet_size = size_of_data + header_format = 1460 + 12
packet_size = 1472

# Description:
# Convert values into packed binary format
# Arguments:
# Seq: sequence numer
# Ack: acknowledgment number
# Flags: conditions of packet
# Win: window size
# Data: file data
# Returns a bytes object packed according to header_format
def packet_create(seq, ack, flags, win, data):
    
    header = pack(header_format, seq, ack, flags, win)
    
    packet = header + data
    
    return packet

# Description:
# Takes header of 12 bytes and unpacks values
# Arguments:
# Header: packet containing a header
# Returns values in a tuple
def header_parse(header):
    
    msg_header = unpack(header_format, header[:12])
    
    return msg_header

# Description:
# Applies certain conditions based on binary
# Returns values for different indexes, depending on condition applied
def flags_parse(flags):

    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    res = flags & (1 << 0)

    return syn, ack, fin, res

# Description:
# Function to establish a reliable connection between server and client
# If successfully established, call function handle_method()
def three_way_handshake(server_socket, client_socket, client_address, args):
    
    if args.server:
        server_socket.settimeout(0.5)
        try:
            # Server receives SYN handshake
            msg = client_socket.recv(packet_size)
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
                msg = client_socket.recv(packet_size)
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
        
        # Client sends SYN handshake
        flags = 8 # 1 0 0 0 (SYN)
        msg = packet_create(1, 0, flags, 0, b'') # Sender sends SYN with sequence 1
        client_socket.send(msg)
        print(f'{args.ip} <-[SYN]')
           
        # Client receives SYN-ACK handshake
        msg = client_socket.recv(packet_size)
        seq, ack, flags, win = header_parse(msg)
        flags = flags_parse(flags)

        if flags[0] == 8 and flags[1] == 4:
            print(f'{args.ip} +[SYN-ACK]')
            
            send_ack(client_socket, None, args)
            
            handle_method(None, client_socket, None, args)

    
        print('Error communication with server, try again')
        client_socket.close()
        sys.exit(1)

# Description:
# Function to establish termination of connection between server and client
# If successfully established, close corresponding sockets.
def two_way_byeshake(server_socket, client_socket, client_address, args):

    if args.server:
        server_socket.settimeout(0.5)
        try:
            send_ack(client_socket, client_address,args)
            print(f'Client {client_address} has disconnected')
            server_socket.close()
            client_socket.close()
        except socket.timeout:
            two_way_byeshake(server_socket,client_socket,client_address,args)
        
    elif args.client:
        client_socket.settimeout(0.5)
        try:
            flags = 2
            msg = packet_create(0, 0, flags, 0, b'')
            client_socket.send(msg)
            print(f'{args.ip} <-[FIN]')
            
            msg = client_socket.recv(packet_size)
            seq, ack, flags, win = header_parse(msg)
            
            if ack == 1:
                print(f'{args.ip} +[ACK]\nClosing...')
                client_socket.close()
                sys.exit(1)
        except socket.timeout:
            two_way_byeshake(None,client_socket,None,args)


# Function to send ACK-header without application data
def send_ack(client_socket, client_address, args):
    if args.server:
        msg = packet_create(0, 1, 0, 0, b'')
        client_socket.send(msg)
        print(f'{client_address} <-[ACK]')
    elif args.client:
        msg = packet_create(0, 1, 0, 0, b'')
        client_socket.send(msg)
        print(f'{args.ip} <-[ACK]')

# Description:
# Function to send DUPACK-header without application data
# Arguments:
# seq_num: Usually missing packet
def send_dupack(client_socket, client_address, seq_num):
    msg = packet_create(seq_num, 1, 0, 0, b'')
    client_socket.send(msg)
    print(f'{client_address} <-[DUPACK #{seq_num}]')

# Function to start server and listen for 1 client
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
                # Establish connection
                three_way_handshake(server_socket, client_socket, client_address, args)
                break
        
        except KeyboardInterrupt:
            print('Closing server')
            server_socket.close()
            client_socket.close()
            sys.exit(1)
        
    server_socket.close()
# Function for server to handle incoming data with requested reliable method
# Returns file sent by client
def server_handle_client(server_socket, client_socket, client_address, args):
    dataArray = []
    server_socket.setblocking(False)
    # Read more under project report
    def send_and_wait(seq_num):
        
        # Initialize measuring variables
        throughput_start = time.time()
        packets_recv= 0
        start_time = 0
        
        while True:
            try:
                # Set the time equal to RTT of a packet, multiplied by 4
                if start_time != 0:
                    server_socket.settimeout(4 * (time.monotonic() - start_time))
                    
                msg = client_socket.recv(packet_size)
                packets_recv += 1
                seq, ack, flags, win= header_parse(msg)
                flags = flags_parse(flags)
            
            except socket.timeout:
                if seq_num == 1:
                    # Will force timeout for both server and client to resend first packet
                    time.sleep(0.3) 
                else:
                    send_dupack(client_socket, client_address, seq_num)    
            
            if seq_num == seq:
                print(f'{client_address} +[PACKET #{seq}]')
                data_msg = msg[12:]
                dataArray.append(data_msg)
                start_time = time.monotonic()
                send_ack(client_socket, client_address, args)
                seq_num += 1
            
            elif seq != seq_num and flags[2] != 2:
                send_dupack(client_socket, client_address, seq_num)
                
            elif seq == 0 and ack == 0 and flags[2] == 2:
                print(f'{client_address} +[FIN]')
                throughput = packets_recv / (time.time() - throughput_start)
                print(f"Receiver throughput (Send and wait): {throughput} packets/s")    
                two_way_byeshake(server_socket,client_socket,client_address,args)
                break
    # Read more under project report        
    def go_back_n(seq_num):
        throughput_start = time.time()
        packets_recv = 0
        start_time = 0
        while True:
            try:
                if start_time != 0:
                    server_socket.settimeout(4 * (time.time() - start_time))
                msg = client_socket.recv(packet_size)
                packets_recv += 1
                seq, ack, flags, win= header_parse(msg)
                flags = flags_parse(flags)
            
            except socket.timeout:
                send_dupack(client_socket, client_address, seq_num)
                    
            if seq == seq_num:
                print(f'{client_address} +[PACKET #{seq}]')
                data_msg = msg[12:]
                dataArray.append(data_msg)
                start_time = time.time()
                send_ack(client_socket, client_address, args)
                seq_num += 1

            elif seq != seq_num and flags[2] != 2:
                send_dupack(client_socket, client_address, seq_num)
                
            
            elif seq == 0 and ack == 0 and flags[2] == 2:
                throughput = packets_recv / (time.time() - throughput_start)
                print(f"Receiver throughput (Go back N): {throughput} packets/s")  
                print(f'{client_address} +[FIN]')
                two_way_byeshake(server_socket,client_socket,client_address,args)
                break
    # Read more under project report    
    def go_back_n_sr(seq_num):
        
        throughput_start = time.time()
        packets_recv = 0
        
        seq_first = 1
        seq_end = 0
        
        tempDataArray = {} # Dictionary of seq-num and data, to be sorted
        
        while True:
            msg = client_socket.recv(packet_size)
            seq, ack, flags, win = header_parse(msg)
            flags = flags_parse(flags)
            packets_recv += 1
            if seq_end == 0:
                seq_end = win
            
            if seq == seq_num:
                if seq_num not in tempDataArray:
                    data_msg = msg[12:]
                    tempDataArray.update({seq:data_msg})
                    print(f'{client_address} +[PACKET #{seq}]')
                    send_ack(client_socket, client_address, args)
                    seq_first += 1
                    seq_end += 1
                    seq_num += 1
                else:
                    send_ack(client_socket, client_address, args)
                    seq_first += 1
                    seq_end += 1
                    seq_num += 1
            
            elif flags[2] == 2:
                two_way_byeshake(server_socket,client_socket,client_address,args)
                break
            
            elif seq_first <= seq <= seq_end:
                if seq not in tempDataArray:
                    print(f'{client_address} +[PACKET #{seq}]')
                    data_msg = msg[12:]
                    tempDataArray.update({seq:data_msg})
                    send_dupack(client_socket, client_address, seq_num)
        
        # Sorting by key (seq-number)
        dataArray_sorted = dict(sorted(tempDataArray.items(), key=lambda x: int(x[0])))
            
        for value in dataArray_sorted.values():
            dataArray.append(value)    
            
        throughput = packets_recv / (time.time() - throughput_start)
        print(f"Receiver throughput (Go back N): {throughput} packets/s")  
        print(f'{client_address} +[FIN]')        
                
    if args.reliable_method == 'SAW':
        send_and_wait(1)
    elif args.reliable_method == 'GBN':
        go_back_n(1)
    elif args.reliable_method == 'GBN-SR':
        go_back_n_sr(1)
            
    # Write file in same directory with requested name
    with open(os.path.join(os.getcwd(), args.file), 'wb') as file:
        for data in dataArray:
            file.write(data)

# Function to connect the client to server    
def client_connect(args: argparse.Namespace):

    server_host = args.ip
    server_port = args.port

    print('----------------------------------------------------')
    print(f'Connecting to server {server_host}:{server_port}')
    print('----------------------------------------------------')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host,server_port))
        three_way_handshake(None, client_socket, None, args)

# Function for client to handle data to be sent with requested reliable method    
def client_send(client_socket, args: argparse.Namespace):
    dataArray = []
    
    # Reads data onto a list in increments of 1460 bytes
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
    
    # Read more under project report
    def send_and_wait(seq_num):
        throughput_start = time.time()
        packets_sent = 0
        while seq_num <= len(dataArray):
            msg = packet_create(seq_num, 0, 0, 1, dataArray[seq_num-1])
            client_socket.send(msg)
            start_time = time.monotonic()
            packets_sent += 1
            print(f'{args.ip} <-[PACKET #{seq_num}]')
            try:
                msg = client_socket.recv(packet_size)
                seq, ack, flags, win= header_parse(msg)
                client_socket.settimeout(4 * (time.monotonic() - start_time)) 
                if seq == 0 and ack == 1:
                    print(f'{args.ip} +[ACK]')
                    seq_num += 1
                
                elif seq > 0 and ack == 1:
                    print(f'{args.ip} +[DUPACK #{seq}]')
                    seq_num = seq
                    
            except socket.timeout:
                print('Timeout, retransmitting packets from current window')
                pass    
        # Measure throughput by recording how many packets were sent between the time program began and finished    
        throughput = packets_sent / (time.time() - throughput_start)
        print(f"Sender throughput (Send and wait): {throughput} packets/s")        
        two_way_byeshake(None,client_socket,None,args)
    
    # Read more under project report           
    def go_back_n(seq_num):
        throughput_start = time.time()
        packets_sent = 0
        
        seq_win = args.window
        seq_first = seq_num
        seq_end = seq_first + seq_win
        while seq_first <= len(dataArray):
            while seq_first <= seq_end:
                if seq_first > len(dataArray):
                    break
                msg = packet_create(seq_first, 0, 0, seq_win, dataArray[seq_first-1])
                client_socket.send(msg)
                start_time = time.time()
                packets_sent += 1
                print(f'{args.ip} <-[PACKET #{seq_first}]')
                seq_first += 1
                    
            while True:
                try:
                    msg = client_socket.recv(packet_size)
                    seq, ack, flags, win = header_parse(msg)
                    client_socket.settimeout(4 * (time.time() - start_time) ) 
                    if seq == 0 and ack == 1:
                        print(f'{args.ip} +[ACK]')
                        seq_num += 1
                        seq_end += 1
                        break
                        
                    elif seq > 0 and ack == 1:
                        print(f'{args.ip} +[DUPACK #{seq}]')
                        seq_num = seq
                        seq_end = seq_num + seq_win
                        break
                    
                except socket.timeout:
                    seq_first = seq_num
                    seq_end = seq_first + seq_win
                    print('Timeout, retransmitting packets from current window')
                    break
                    
        throughput = packets_sent / (time.time() - throughput_start)
        print(f"Sender throughput (Go back N): {throughput} packets/s")     
        two_way_byeshake(None,client_socket,None,args)
    
    
    # Read more under project report    
    def go_back_n_sr(seq_num):
        throughput_start = time.time()
        packets_sent = 0
        
        seq_win = args.window
        seq_first = seq_num
        seq_end = seq_first + seq_win
        missing_packets = []
        
        while seq_num <= len(dataArray):
            while missing_packets:
                for seq_missing in missing_packets:
                    msg = packet_create(seq_missing, 0, 0, seq_win, dataArray[seq_missing-1])
                    client_socket.send(msg)
                    start_time = time.time()
                    packets_sent += 1
                    print(f'{args.ip} <-[PACKET #{seq_missing}]')
                    
                    msg = client_socket.recv(packet_size)
                    seq, ack, flags, win = header_parse(msg)
                    client_socket.settimeout(4 * (time.time() - start_time) ) 
                    
                    if seq == 0 and ack == 1:
                        missing_packets.remove(seq_missing)
                        seq_num += 1
                        seq_end += 1
                
            while seq_first < seq_end:
                msg = packet_create(seq_first, 0, 0, seq_win, dataArray[seq_first-1])
                client_socket.send(msg)
                start_time = time.time()
                packets_sent += 1
                print(f'{args.ip} <-[PACKET #{seq_first}]')
                seq_first += 1
            
                try:
                    msg = client_socket.recv(packet_size)
                    seq, ack, flags, win = header_parse(msg)
                    client_socket.settimeout(4 * (time.time() - start_time) ) 
                    if seq == 0 and ack == 1:
                        print(f'{args.ip} +[ACK]')
                        seq_num += 1
                        seq_end += 1
                        break
                    elif seq > 0 and ack == 1:
                        if seq not in missing_packets:
                            missing_packets.append(seq)
                            break
                
                except socket.timeout:
                    seq_first = seq_num
                    seq_end = seq_first + seq_win
                    
        throughput = packets_sent / (time.time() - throughput_start)
        print(f"Sender throughput (Go back N with Selective Repeat): {throughput} packets/s")             
        two_way_byeshake(None,client_socket,None,args)            
                    
    if args.reliable_method == 'SAW':
        send_and_wait(1)
    elif args.reliable_method == 'GBN':
        go_back_n(1)
    elif args.reliable_method == 'GBN-SR':
        go_back_n_sr(1)

def main():
    
    # Create an argument parser
    parser = argparse.ArgumentParser(description="File transferring application over 'DRTP'.")
    
    # Add all options common for server and client
    parser.add_argument(
        '-i', '--ip', type=str, default='10.0.0.1', help="Enter server ip (default = 10.0.0.1)")
    parser.add_argument(
        '-p', '--port', type=int, default=24, action=PortInRangeAction, help="Enter server port (default = 24)")
    parser.add_argument(
        '-r', '--reliable_method', type=str, default='stop_and_wait', action=ValidMethodAction, help="Enter one of three reliability functions (stop_and_wait, GBN, GBN-SR)")
    
    # Create a group for server-arguments
    server_parser = parser.add_argument_group('Server')
    # Add all available options to invoke the server 
    server_parser.add_argument(
        '-s', '--server', action='store_true', help='Invoke as server (receiver)')
    
    # Create a group for client-arguments
    client_parser = parser.add_argument_group('Client')
    # Add all available options to invoke the client
    client_parser.add_argument(
        '-c', '--client', action='store_true', help='Invoke as client (sender)')
    client_parser.add_argument(
        '-f', '--file', type=str, default='file_to_transfer.jpg', help="Enter file from client to be transfered")
    client_parser.add_argument(
        '-w', '--window', type=int, default='5', help="Enter window size of datapackets (default = 3 for GBN and GBN-SR)")
    
    # Parse the commands line arguments
    args = parser.parse_args()
    
    # If program is invoked as server
    if args.server:
        server_start(args)
    # If program is invoked as client
    elif args.client:
        client_connect(args)
    # If program is invoked as both  
    else:
        print("Error: you must run either in server or client mode")
        parser.print_help()
        sys.exit()
        
if __name__ == "__main__":
    main()