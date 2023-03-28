import socket
from dataclasses import dataclass
from enum import Enum


class PacketType(Enum):
    SEND = 1
    RECEIVE = 0


@dataclass
class Packet:
    type: PacketType
    header: str
    content: str

    @classmethod
    def from_string(cls, packet: str):
        parts = packet.strip().split(' ', 2)
        if len(parts) < 3:
            return None
        return cls(PacketType(int(parts[0])), *parts[1:])


class PacketIterator:
    def __init__(self, packet_logger: 'PacketLogger'):
        self.__packet_logger = packet_logger
        self.__buffer = ''

    def __read_data(self):
        try:
            return self.__packet_logger.read()
        except OSError:
            return None

    def __check_none(self, value, exception):
        if value is None:
            raise exception

    def __next__(self):
        buffer = self.__buffer or self.__read_data()
        self.__check_none(buffer, StopIteration)

        if not self.__packet_logger.DELIM in buffer:
            more = self.__read_data()
            self.__check_none(more, StopIteration)
            self.__buffer += more

        while self.__packet_logger.DELIM not in buffer:
            buffer += self.__packet_logger.read()

        line, buffer = buffer.split(self.__packet_logger.DELIM, 1)
        self.__buffer = buffer
        return line


class PacketLogger:
    BUFFER_SIZE = 1024 * 8
    ENCODING = 'windows-1252'
    DELIM = '\r'

    __instances = {}  # thread_id: PacketLogger

    def __init__(self, port: int):
        self.__port = port
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.connect(('localhost', port))

    @property
    def socket(self):
        return self.__socket

    def read(self):
        return self.socket.recv(self.BUFFER_SIZE).decode(self.ENCODING)

    # Sends packet to server
    def send(self, packet: str):
        self.__socket.send(('1 ' + packet + '\r').encode(self.ENCODING))

    # Sends packet to client
    def receive(self, packet: str):
        self.__socket.send(('0 ' + packet + '\r').encode(self.ENCODING))

    def set_global(self):
        from threading import get_ident
        self.__instances[get_ident()] = self

    def unset_global(self):
        from threading import get_ident
        self.__instances.pop(get_ident())

    def __iter__(self):
        return PacketIterator(self)

    def __enter__(self):
        self.set_global()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unset_global()

    @classmethod
    def get_global_instance(cls) -> 'PacketLogger':
        from threading import get_ident
        return cls.__instances.get(get_ident(), None)


def send(packet: str):
    PacketLogger.get_global_instance().send(packet)


def receive(packet: str):
    PacketLogger.get_global_instance().receive(packet)


PORT = 63247


# This example shows how to create packet logger instance and
# then print each packet on standard output
def example1():
    pl = PacketLogger(PORT)

    # You can just iterate over packet logger
    for packet in pl:
        # handle packet somehow
        print(packet)


# This example prints pairs of packet_type: packet_header
# Output:
#   RECEIVE cond
#   RECEIVE mv
#   SEND walk
def example2():
    pl = PacketLogger(PORT)

    # Again iterate over packet logger
    for packet in pl:
        # Parse packet using Packet class (Just basic implementation)
        packet = Packet.from_string(packet)
        if packet is not None:
            print(packet.type.name, packet.header)


# This example shows how to send packets to packet logger
def example3():
    pl = PacketLogger(PORT)
    pl.send('say hello')  # send message to chat (you probably won't see the message in chat)
    pl.receive('say 1 312 5 user message')  # receives message in chat (client-side only)


# This example shows how to use `with` syntax, it does the same thing as example3
def example4():
    pl = PacketLogger(PORT)
    with pl:
        send('say hello')
        receive('say 1 312 5 user message')


# You can also combine them together using threads!
def example5():
    from threading import Thread

    pl = PacketLogger(PORT)

    def receiving_loop():
        for packet in pl:
            print(packet)

    # Create thread that will take care of incoming packets
    thread = Thread(target=receiving_loop)
    thread.start()

    # Send some packets from previous examples
    pl.send('say hello')
    pl.receive('say 1 312 5 user message')

    # Wait till thread ends
    thread.join()

if __name__ == '__main__':
    example2()
