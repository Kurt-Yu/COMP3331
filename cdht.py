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

    def client_thread(self):
        first_lost_packets = 0
        second_lost_packets = 0
        while True:
            message = "A ping request message was received from peer {0}".format(self._identity)
            self._UDPsocket.sendto(message.encode(), (socket.gethostname(), self._first + 50000))
            try:
                self._UDPsocket.settimeout(2.0)     # Set time out to be 2 seconds
                data, addr = self._UDPsocket.recvfrom(1024)
                self._UDPsocket.settimeout(None)
                print(data.decode())
            except socket.timeout:
                first_lost_packets = first_lost_packets + 1
                if first_lost_packets > 2:          # if the number of lost packets is greater than 2, then we can assume it's leaving
                    print("Peer {0} is no longer alive.".format(self._first))
                    self._first = self._second  # make the second successor to be the new first successor
                    print("My first successor is now peer {0}".format(self._first))
                    self._TCPsocket.connect((socket.gethostname(), self._first + 50000))    # TCP socket connect to the second successor
                    self._TCPsocket.send("What's your next successor")
                    conn, addr = self._TCPsocket.accept()
                    data = conn.recv(1024)
                    self._second = int(data)   # set the new second successor
                    print("My second successor is now peer {0}".format(self._second))

                    # Start ping the new first and second successor
                    self._UDPsocket.sendto(message.encode(), (socket.gethostname(), self._first + 50000))
                    data, addr = self._UDPsocket.recvfrom(1024)
                    print(data.decode())
                    time.sleep(1)

                    self._UDPsocket.sendto(message.encode(), (socket.gethostname(), self._second + 50000))
                    data, addr = self._UDPsocket.recvfrom(1024)
                    print(data.decode())

                    first_lost_packets = 0           # set the number of lost packets to zero again

            time.sleep(1)      # sleep for 2 second and then start pinging to the second successor

            self._UDPsocket.sendto(message.encode(), (socket.gethostname(), self._second + 50000))
            try:
                self._UDPsocket.settimeout(2.0)     # Set time out to be 2 seconds
                data, addr = self._UDPsocket.recvfrom(1024)
                self._UDPsocket.settimeout(None)
                print(data.decode())
            except socket.timeout:
                second_lost_packets = second_lost_packets + 1
                if second_lost_packets > 2:          # if the number of lost packets is greater than 2, then we can assume it's leaving
                    print("Peer {0} is no longer alive.".format(self._second))
                    print("My first successor is now peer {0}".format(self._first))
                    self._TCPsocket.connect((socket.gethostname(), self._second + 50000))    # TCP socket connect to the second successor
                    self._TCPsocket.send("What's your next successor")
                    conn, addr = self._TCPsocket.accept()
                    data = conn.recv(1024)
                    self._second = int(data)   # set the new second successor
                    print("My second successor is now peer {0}".format(self._second))

                    # Start ping the new first and second successor
                    self._UDPsocket.sendto(message.encode(), (socket.gethostname(), self._first + 50000))
                    data, addr = self._UDPsocket.recvfrom(1024)
                    print(data.decode())
                    time.sleep(1)

                    self._UDPsocket.sendto(message.encode(), (socket.gethostname(), self._second + 50000))
                    data, addr = self._UDPsocket.recvfrom(1024)
                    print(data.decode())
                
                    second_lost_packets = 0           # set the number of lost packets to zero again

            time.sleep(20)     # send ping messages every 20 seconds

    def server_thread(self):   
        i = 0
        while True:
            # FIRST PART: Deal with UDP ping message 
            data, addr = self._UDPsocket.recvfrom(1024)
            if data:
                identity = int(addr[1]) - 50000
               
                i = i + 1
                if i % 2 == 1:
                    self._first_predecessor = identity
                if i % 2 == 0 and identity != self._first_predecessor:
                    self._second_predecessor = identity
                print(data.decode())
                response = "A ping response message was received from Peer {0}".format(self._identity)
                self._UDPsocket.sendto(response.encode(), addr)

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
                if "What's your next successor" in data:
                    self._TCPsocket.connect(addr)
                    self._TCPsocket.send("{0}".format(self._first))
                              
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
                self._first_predecessor, self._second_predecessor = self.sort(self._first_predecessor, self._second_predecessor)
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
    client = threading.Thread(target = peer.client_thread, args = ())
    server = threading.Thread(target = peer.server_thread, args = ())
    user_input = threading.Thread(target = peer.get_input)

    client.start()
    server.start()
    user_input.start()

if __name__ == "__main__":main()