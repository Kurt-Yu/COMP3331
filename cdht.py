import socket
import sys
import random
import threading
import time

class Peer:
    def __init__(self, identity, first, second):
        self._identity = identity
        self._first = first
        self._second = second
        self._first_predecessor = None
        self._second_predecessor = None

        self._host = socket.gethostname()
        self._port = int(identity) + 50000
        # Create a UDP socket
        self._UDPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._UDPsocket.bind((self._host, self._port))
        # Create a TCP socket
        self._TCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._TCPsocket.bind((self._host, self._port))

    @property
    def identity(self):
        return self._identity

    @property
    def first(self):
        return self._first

    @property
    def second(self):
        return self._second

    @property
    def UDPsocket(self):
        return self._UDPsocket

    @first.setter
    def first(self, new_first):
        self._first = new_first
    
    @second.setter
    def second(self, new_second):
        self._second = new_second  

    def send_ping_request(self):
        lost_packets = 0
        while True:
            message = "Sending Ping Request"
            self._UDPsocket.sendto(message.encode(), (socket.gethostname(), self._first + 50000))
            try:
                self._UDPsocket.settimeout(1.0)     # Set time out to be 1 seconds
                data, addr = self._UDPsocket.recvfrom(1024)
                self._UDPsocket.settimeout(None)
                print(data.decode())
            except socket.timeout:
                lost_packets = lost_packets + 1
                if lost_packets > 2:          # if the number of lost packets is greater than 2, then we can assume it's leaving
                    print("Peer {0} is no longer alive.".format(self._first))
                    self._first = self._second  # make the second successor to be the new first successor
                    self._TCPsocket.connect((socket.gethostname(), self._first + 50000))    # TCP socket connect to the second successor
                    self._TCPsocket.send("What's your next successor")
                    self._TCPsocket.recv()
                    conn, addr = self._TCPsocket.accept()
                    data = conn.recv(1024)
                    self._second = int(data)   # set the new second successor
                    lost_packets = 0           # set the number of lost packets to zero again



            time.sleep(1)    # Sleep for 1 second after ping the first successor
            self._UDPsocket.sendto(message.encode(), (socket.gethostname(), self.second + 50000))
            time.sleep(20)   # send ping requests to successors every 20 seconds

    def catch_ping_response(self):
        lost_packets = 0     
        i = 0

        while True:
            # FIRST PART: Deal with UDP ping message 
            if lost_packets > 2:    # If i is greater than 2, then we can assume the peer left
                print("Peer {0} is no longer alive.".format())
                
                lost_packets = 0
            try:
                self._UDPsocket.settimeout(1.0)     # Set time out to be 1 seconds
                data, addr = self._UDPsocket.recvfrom(1024)
                self._UDPsocket.settimeout(None)
            except socket.timeout:
                lost_packets = lost_packets + 1
                continue
        
            identity = int(addr[1]) - 50000
            if "Sending Ping Request" in data.decode():
                i = i + 1
                if i % 2 == 1:
                    self._first_predecessor = identity
                else:
                    self._second_predecessor = identity
                response = "A ping request message was received from Peer {0}".format(identity)
                self._UDPsocket.sendto(response.encode(), addr)
                print(response)
            if "A ping request message was received" in data.decode():
                time.sleep(2) # sleep for 2 seconds to print the response message
                print("A ping response message was received from Peer {0}".format(identity))

            # SECOND PART: Deal with TCP File request message
            conn, addr = self._TCPsocket.accept()
            if conn:
                data = conn.recv(1024)
                if ("File request message for" in data) or ("is not stored here" in data):
                    messages = data.split()
                    if "File request message for" in data:
                        request_port = int(addr[1]) - 50000
                        file = int(messages[4])
                    if "is not stored here" in data:
                        file = int(messages[1])
                    stored = file % 256
                    port = int(addr[1]) - 50000
                    if (port < stored and stored < self._identity) or (port > self._identity and port < stored):
                        message = "Received a response message for peer {0}, which has the file {1}".format(self._identity, file)
                        self._TCPsocket.connect((socket.gethostname(), request_port))
                        self._TCPsocket.send(message)
                        print("File {0} is here.".format(file))
                        print("A response message, destined for peer {0}, has been sent.".format(request_port))
                    else:
                        message = "File {0} is not stored here.\nFile request message has been forwarded to my successor.".format(file)
                        self._TCPsocket.connect(socket.gethostname(), self._first + 50000)
                        self._TCPsocket.send(message)
                if "Received a response message from peer" in data:
                    print(data)
                if "will depart from the network" in data:
                    parts = data.split()
                    print(" ".join(parts[:-2]))

                    if self._first == int(addr[1]) - 50000:
                        self._first = parts[-2]
                        self._second = parts[-1]
                    else:
                        self._first = self._second
                        self._second = parts[-2]
                    print("My first successor is now peer {0}".format(self._first))
                    print("My second successor is now peer {0}".format(self._second))
            
                    
    def sort(self, first, second):
        if (self._identity < first and self._identity > second) or (self._identity > first and self._identity < second):
            if first > second:
                return second, first
        else:
            if first < second:
                return second, first
        
    def get_input(self):
        while True:
            string = input()
            if "request" in string:   # Dealing with the request file part
                self._TCPsocket.connect((socket.gethostname(), self._first + 50000))
                message = "File request message for {0} has been sent to my successor.".format(string.split()[1])
                self._TCPsocket.send(message)
                print(message)

            if "quit" in string:      # Dealing with the peer leaving part
                self._first_predecessor, self._second_predecessor = sort(self._first_predecessor, self._second_predecessor)
                message = "Peer {0} will depart from the network. {1} {2}".format(self._identity, self._first, self._second)                
        
                self._TCPsocket.connect((socket.gethostname(), self._first_predecessor + 50000))
                self._TCPsocket.send(message)

                self._TCPsocket.connect((socket.gethostname(), self._first_predecessor + 50000))
                self._TCPsocket.send(message)
                break


def main():
    # Read in command line arguments, and create a Peer object
    identity = int(sys.argv[1])
    first = int(sys.argv[2])
    second = int(sys.argv[3])
    peer = Peer(identity, first, second)

    # Initialize the client and server thread of each peer
    # Sending ping request to its successors and catch for response
    client = threading.Thread(target = peer.send_ping_request, args = ())
    server = threading.Thread(target = peer.catch_ping_response, args = ())
    client.start()
    server.start()


# def main():
#     p1 = Peer(1, 2, 3)
#     p2 = Peer(2, 3, 1)
#     p3 = Peer(3, 1, 2)

#     t1 = threading.Thread(target = p1.send_ping_request, args = ())
#     t2 = threading.Thread(target = p1.catch_ping_response, args = ())

#     t3 = threading.Thread(target = p2.send_ping_request, args = ())
#     t4 = threading.Thread(target = p2.catch_ping_response, args = ())

#     t5 = threading.Thread(target = p3.send_ping_request, args = ())
#     t6 = threading.Thread(target = p3.catch_ping_response, args = ())

#     t1.start()
#     t2.start()
#     t3.start()
#     t4.start()
#     t5.start()
#     t6.start()

# class ClientThread(threading.Thread):
#     def __init__(self, peer):
#         super(ClientThread, self).__init__()
#         self._peer = peer
#         self._sock = peer.sock
    
#     def send_ping_request(self):
#         message = "Sending Ping Request"
#         self._sock.sendto(message.encode(), (socket.gethostname(), self._peer.first + 50000))
#         # self._sock.sendto(message.encode(), (socket.gethostname(), self._sock.second + 50000))

# class ServerThread(threading.Thread):
#     def __init__(self, peer):
#         super(ServerThread, self).__init__()
#         self._peer = peer
#         self._sock = peer.sock

#     def receive_and_respond(self):
#         while True:
#             data, addr = self._sock.recvfrom(1024) # buffer size 1024
#             if data:
#                 identity = int(addr[1]) - 50000
#                 response = "I'm Peer {0}, A ping request message was received from Peer ".format(self._peer.identity) + str(identity)
#                 self._sock.sendto(response.encode(), addr)
#                 print(identity)
#                 print(response)
#             else:
#                 continue

# p1 = Peer(1, 2, 3)
# p2 = Peer(2, 3, 4)
# client1 = ClientThread(p1)
# server1 = ServerThread(p1)

# client2 = ClientThread(p2)
# server2 = ServerThread(p2)

# client1.start()
# server1.start()
# client2.start()
# server2.start()

# client1.send_ping_request()
# server2.receive_and_respond()
# client1.send_ping_request()
# server1.receive_and_respond()

# client1.join()
# server1.join()
# client2.join()
# server2.join()


# def main():
    # identity = int(sys.argv[1])
    # first = int(sys.argv[2])
    # second = int(sys.argv[3])
    # host = socket.gethostname()
    # peer = Peer(identity, first, second, host, 50000 + identity)

    # first_port = peer.first + 50000
    # second_port = peer.second + 50000

    # # Send messge to its two successors 
    # sock.sendto("A ping request message was received from Peer " + peer.identity + ".", (local_ip, first_port))
    # sock.sendto("A ping request message was received from Peer " + peer.identity + ".", (local_ip, second_port))
    
    


if __name__ == "__main__":main()