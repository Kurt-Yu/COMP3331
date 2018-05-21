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
        self._request_port = 0
        
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @property
    def identity(self):
        return self._identity

    @property
    def first(self):
        return self._first

    @property
    def second(self):
        return self._second

    def UDPclient(self):
        while True:
            self.ping("first")
            time.sleep(1)       # sleep for 1 second and then ping the second one 
            self.ping("second")
            time.sleep(20)      # send ping request every 15 seconds
    
    def ping(self, string):
        if string == "first":
            message = "A ping request message was received from peer {0} first".format(self._identity)
            self._sock.sendto(message.encode(), ('localhost', self._first + 50000))
        else:
            message = "A ping request message was received from peer {0} second".format(self._identity)
            self._sock.sendto(message.encode(), ('localhost', self._second + 50000))
        try:
            self._sock.settimeout(2.0)     # Set time out to be 2 seconds
            data, addr = self._sock.recvfrom(1024)
            self._sock.settimeout(None)
        except socket.timeout:
            if string == "first":
                self._first_successor_lost += 1
                if self._first_successor_lost > 2:   # if the ping message sent to first successor get lost 3 time or more
                    print("Peer {0} is no longer alive.".format(self._first))
                    self._first = self._second  # make the second successor to be the new first successor
                    print("My first successor is now peer {0}".format(self._first))
                    temp = self.TCPclient(self._second + 50000, "What's your next successor")    # TCP socket connect to the second successor
                    self._second = int(temp)   # set the new second successor
                    print("My second successor is now peer {0}".format(self._second))

                    # After updating new successors, start pinging them
                    self.ping("first")
                    time.sleep(1)     
                    self.ping("second")
            if string == "second":
                self._second_successor_lost += 1
                if self._second_successor_lost > 2:
                    print("Peer {0} is no longer alive.".format(self._second))
                    print("My first successor is now peer {0}".format(self._first))
                    temp = self.TCPclient(self._first + 50000, "What's your next successor")
                    self._second = int(temp)
                    print("My second successor is now peer {0}".format(self._second))

                    # After updating new successors, start pinging them
                    self.ping("first")
                    time.sleep(1)     
                    self.ping("second")
        else:
            print(data.decode())

    def UDPserver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('localhost', self._identity + 50000))
        while True:
            data, addr = sock.recvfrom(1024)
            data = data.decode().split()
            if data[-1] == "first":
                self._first_predecessor = int(data[-2])
            else:
                self._second_predecessor = int(data[-2])
            print(' '.join(data[:-1]))
            
            response = "A ping response message was received from Peer {0}".format(self._identity)
            sock.sendto(response.encode(), addr)

    def TCPclient(self, port, message = None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', port))
        sock.sendall(message.encode())
        if "File request message for" in message:
            sock.close()
            return None
        if ("is not stored here" in message) or ("Received a response message from peer" in message) or ("will depart from the network" in message):
            sock.close()
            return None
        data = sock.recv(1024).decode()
        sock.close()
        return data

    def TCPserver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', self._identity + 50000))
        sock.listen(5)

        while True:
            conn, addr = sock.accept()
            data = conn.recv(1024).decode()
            if "What's your next successor" in data:
                message = str(self._first)
                conn.sendall(message.encode())
            if ("File request message for" in data) or ("is not stored here" in data):
                messages = data.split()
                if "File request message for" in data:
                    file = int(messages[4])
                if "is not stored here" in data:
                    file = int(messages[1])
                port = int(messages[-1])
                request_port = int(messages[-2])
                stored = file % 256
                if (port < stored and stored <= self._identity) or (self._identity < port and stored > port) or (self._identity < port and stored <= self._identity):
                    message = "Received a response message from peer {0}, which has the file {1}".format(self._identity, file)
                    print("File {0} is here.".format(file))
                    print("A response message, destined for peer {0}, has been sent.".format(request_port))
                    self.TCPclient(request_port + 50000, message)
                else:
                    message = "File {0} is not stored here.\nFile request message has been forwarded to my successor. {1} {2}".format(file, request_port, self._identity)
                    print(message[:-4])
                    self.TCPclient(self._first + 50000, message)
            if "Received a response message from peer" in data:
                print(data)
            if "will depart from the network" in data:
                parts = data.split()
                print(" ".join(parts[:-2]))

                if self._first == int(parts[1]):
                    self._first = int(parts[-2])
                    self._second = int(parts[-1])
                else:
                    self._second = int(parts[-2])
                print("My first successor is now peer {0}".format(self._first))
                print("My second successor is now peer {0}".format(self._second))

                # After updating the new successors, start pinging them
                self.ping("first")
                time.sleep(1)     
                self.ping("second")
        
    def get_input(self):
        while True:
            string = input()
            if "request" in string:   # Dealing with the request file part
                message = "File request message for {0} has been sent to my successor. {1} {2}".format(string.split()[1], self._identity, self._identity)
                print(message[:-4])
                self.TCPclient(self._first + 50000, message)

            if "quit" in string:      # Dealing with the peer leaving part
                message = "Peer {0} will depart from the network. {1} {2}".format(self._identity, self._first, self._second) 
                print("My first predecessor is {}".format(self._first_predecessor))  
                print("My second predecessor is {}".format(self._second_predecessor))             
                self.TCPclient(self._first_predecessor + 50000, message)
                time.sleep(1)
                self.TCPclient(self._second_predecessor + 50000, message)
                print("something")
                sys.exit()
                break

def main():
    # Read in command line arguments, and create a Peer object
    identity = int(sys.argv[1])
    first = int(sys.argv[2])
    second = int(sys.argv[3])
    peer = Peer(identity, first, second)

    # Initialize the client and server thread of each peer
    # Sending ping request to its successors and catch for response
    UDPclient = threading.Thread(target = peer.UDPclient, args = ())
    UDPserver = threading.Thread(target = peer.UDPserver, args = ())
    TCPserver = threading.Thread(target = peer.TCPserver, args = ())

    user_input = threading.Thread(target = peer.get_input)

    UDPclient.start()
    UDPserver.start()
    TCPserver.start()
    user_input.start()

if __name__ == "__main__":main()