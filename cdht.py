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
        self._first_successor_lost = 0    # This is the value that used to track how many packets are lost
        self._second_successor_lost = 0   # during the ping request and response

        self._host = socket.gethostname()
        self._port = int(identity) + 50000

        # Create a UDP socket
        try:
            self._UDPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error:
            print("Failed to create UDP socket.")
            sys.exit()
        self._UDPsocket.bind((self._host, self._port))

        # Create a TCP socket
        try:
            self._TCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            print("Failed to create TCP socket.")
            sys.exit()

    @property
    def identity(self):
        return self._identity

    @property
    def first(self):
        return self._first

    @property
    def second(self):
        return self._second

    def send_ping(self, port, lost_packets):    # port is the value of successor's identity + 50000
        message = "A ping request message was received from peer {0}".format(self._identity)
        self._UDPsocket.sendto(message.encode(), (socket.gethostname(), port))
        try:
            self._UDPsocket.settimeout(2.0)     # Set time out to be 2 seconds
            data, addr = self._UDPsocket.recvfrom(1024)
            self._UDPsocket.settimeout(None)
            print(data.decode())
        except socket.timeout:
            lost_packets = lost_packets + 1
            if lost_packets > 2:     # if the number of lost packets is greater than 2, then we can assume it's leaving
                if self._first == port - 50000:
                    print("Peer {0} is no longer alive.".format(self._first))
                    self._first = self._second  # make the second successor to be the new first successor
                else:
                    print("Peer {0} is no longer alive.".format(self._second))
                
                print("My first successor is now peer {0}".format(self._first))
                self._TCPsocket.connect((socket.gethostname(), self._first + 50000))    # TCP socket connect to the second successor
                self._TCPsocket.send(str.encode("What's your next successor"))       # send the whole string
                data = self._TCPsocket.recv(1024)
                self._second = int(data)   # set the new second successor
                print("My second successor is now peer {0}".format(self._second))
                
                # start ping the new first and second successors
                self._first_successor_lost = 0
                self._second_successor_lost = 0
                self._first_successor_lost = self.send_ping(self._first + 50000, 0)
                self._second_successor_lost = self.send_ping(self._second + 50000, 0)
            else:
                if self._first == port - 50000:
                    self._first_successor_lost = lost_packets
                else:
                    self._second_successor_lost = lost_packets
        return
        

    def client_thread(self):
        while True:
            self.send_ping(self._first + 50000, self._first_successor_lost)
            time.sleep(1)   # sleep for 1 second before sending ping to the second successor
            self.send_ping(self._second + 50000, self._second_successor_lost)
            time.sleep(20)  # send ping request to successors every 20 seconds

    def server_thread(self):   
        temp = 0
        while True:
            # FIRST PART: Deal with UDP ping message
            try:
                self._UDPsocket.settimeout(2.0)     # Set time out to be 2 seconds
                data, addr = self._UDPsocket.recvfrom(1024)
                self._UDPsocket.settimeout(None)

                identity = int(addr[1]) - 50000
                temp = temp + 1
                if temp % 2 == 1:
                    self._first_predecessor = identity
                if temp % 2 == 0 and identity != self._first_predecessor:
                    self._second_predecessor = identity
                print(data.decode())
                response = "A ping response message was received from Peer {0}".format(self._identity)
                self._UDPsocket.sendto(response.encode(), addr)
            except socket.timeout:
                continue

            # SECOND PART: Deal with TCP File request message
            try:
                self._TCPsocket.bind((self._host, self._port))
            except socket.error:
                print("Bind failed.")
            self._TCPsocket.listen(5)
            (conn, addr) = self._TCPsocket.accept()
            if conn:
                data = conn.recv(1024)
                data = data.decode()
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
                        self._TCPsocket.send(message.encode())
                        print("File {0} is here.".format(file))
                        print("A response message, destined for peer {0}, has been sent.".format(request_port))
                    else:
                        message = "File {0} is not stored here.\nFile request message has been forwarded to my successor.".format(file)
                        self._TCPsocket.connect(socket.gethostname(), self._first + 50000)
                        self._TCPsocket.send(message.encode())
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
                    message = str(self._first)
                    self._TCPsocket.send(message.encode())
                              
    def sort(self, first, second):
        if (self._identity < first and self._identity > second) or (self._identity > first and self._identity < second):
            if first > second:
                return second, first
        if first < second:
            return second, first
        
    def get_input(self):
        while True:
            string = input()
            if "request" in string:   # Dealing with the request file part
                self._TCPsocket.connect((socket.gethostname(), self._first + 50000))
                message = "File request message for {0} has been sent to my successor.".format(string.split()[1])
                self._TCPsocket.send(message.encode())
                print(message)

            if "quit" in string:      # Dealing with the peer leaving part
                self._first_predecessor, self._second_predecessor = self.sort(self._first_predecessor, self._second_predecessor)
                message = "Peer {0} will depart from the network. {1} {2}".format(self._identity, self._first, self._second)                
        
                self._TCPsocket.connect((socket.gethostname(), self._first_predecessor + 50000))
                self._TCPsocket.send(message.encode())

                self._TCPsocket.connect((socket.gethostname(), self._first_predecessor + 50000))
                self._TCPsocket.send(message.encode())
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