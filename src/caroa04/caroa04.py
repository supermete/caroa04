import can
import logging
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent))

from canmessage import CanMessageRW, XCanSignal, BOOL, ENUM

logger = logging.getLogger(__name__)
logger.propagate = True

__author__ = "R. Soyding"
__version__ = "1.0.3"

MSGID_DO_WRITE = 0x100
MSGID_DO_READ = 0x200
MSGID_DI_READ = 0x300
MSGID_PARAM = 0x700
DEFAULT_NODEID = 0xE0

GET_ADDR_CODE_CMD = 0xA1
SET_ADDR_CODE_CMD = 0xB1
GET_BAUDRATE_CMD = 0xA2
SET_BAUDRATE_CMD = 0xB2

BitrateEnum = {
    0: 5000,
    1: 10000,
    2: 20000,
    3: 50000,
    4: 100000,
    5: 120000,
    6: 200000,
    7: 250000,
    8: 400000,
    9: 500000,
    10: 800000,
    11: 1000000,
}


class CaroA04:
    """
    API to control the CaroA04 device from eletechsup.
    It will basically create CanSignal instances for the user to read/write the signals supported by the device.
    Reading/writing a signal triggers a CAN message sent to the device.
    The response is processed by the library and the CanSignal instances are updated with the received data.

    The node ID (or address code) shall be indicated when starting the communication (see start method).
    It is, together with the bitrate, also a signal that can be set by the user. However, changing the bitrate or
    address code will only take effect after power cyclcing the device. Then the communication needs to be stopped and
    restarted with the new address code/bitrate.
    """
    def __init__(self):
        self._node_id = DEFAULT_NODEID
        self._bus = None
        self._notifier = None

        self.message_do = CanMessageRW(self._node_id, MSGID_DO_READ, MSGID_DO_WRITE, dlc=8)
        self.message_di = CanMessageRW(self._node_id, MSGID_DI_READ, MSGID_DI_READ, dlc=8)
        self.message_bitrate = CanMessageRW(self._node_id,
                                            MSGID_PARAM,
                                            MSGID_PARAM,
                                            rx_cmd_byte=GET_BAUDRATE_CMD,
                                            tx_cmd_byte=SET_BAUDRATE_CMD,
                                            dlc=8)
        self.message_nodeid = CanMessageRW(self._node_id,
                                           MSGID_PARAM,
                                           MSGID_PARAM,
                                           rx_cmd_byte=GET_ADDR_CODE_CMD,
                                           tx_cmd_byte=SET_ADDR_CODE_CMD,
                                           dlc=8)

        self.do1 = XCanSignal(startbit=0, length=1, type=BOOL)
        self.do2 = XCanSignal(startbit=1, length=1, type=BOOL)
        self.do3 = XCanSignal(startbit=2, length=1, type=BOOL)
        self.do4 = XCanSignal(startbit=3, length=1, type=BOOL)

        self.di1 = XCanSignal(startbit=0, length=1, type=BOOL)
        self.di2 = XCanSignal(startbit=1, length=1, type=BOOL)
        self.di3 = XCanSignal(startbit=2, length=1, type=BOOL)
        self.di4 = XCanSignal(startbit=3, length=1, type=BOOL)

        self.bitrate = XCanSignal(startbit=8, length=8, type=ENUM, enum=BitrateEnum)
        self.node_id = XCanSignal(startbit=8, length=8)

        self.message_do.add(
            self.do1,
            self.do2,
            self.do3,
            self.do4
        )
        self.message_di.add(
            self.di1,
            self.di2,
            self.di3,
            self.di4
        )

        self.message_bitrate.add(
            self.bitrate
        )

        self.message_nodeid.add(
            self.node_id
        )

    def start(self, node_id, interface=None, bitrate=None, channel=None):
        """
        Start the communication.
        :param node_id: node ID (or address code) of the device
        :param interface: CAN interface to be used for the communication
        :param bitrate: CAN speed
        :param channel: channel used for the communication
        :return: None
        """
        self._node_id = node_id

        self.message_di.node_id = node_id
        self.message_do.node_id = node_id
        self.message_bitrate.node_id = node_id
        self.message_nodeid.node_id = node_id

        if self._bus is None:
            self._bus = can.ThreadSafeBus(interface=interface, channel=channel, bitrate=bitrate)
            self._notifier = can.Notifier(self._bus, [self._listener], timeout=2.0)
        else:
            if self._listener not in self._notifier.listeners:
                self._notifier.add_listener(self._listener)

        self.message_do.bus = self._bus
        self.message_di.bus = self._bus
        self.message_nodeid.bus = self._bus
        self.message_bitrate.bus = self._bus

        self._init_outputs()

    def _init_outputs(self):
        """
        To avoid overwriting the state of already set outputs, initialize by reading the current
        state of the outputs first.
        :return: None
        """
        self.message_do.read()

    def _listener(self, msg):
        if msg.arbitration_id in (self.message_do.read_id, self.message_do.write_id):
            logger.debug(msg)
            self.message_do.update_payload(msg.data)
        elif msg.arbitration_id in (self.message_di.read_id, self.message_di.write_id):
            logger.debug(msg)
            self.message_di.update_payload(msg.data)
        elif msg.arbitration_id in (self.message_bitrate.read_id, self.message_bitrate.write_id):
            logger.debug(msg)
            self.message_bitrate.update_payload(msg.data)
        elif msg.arbitration_id in (self.message_nodeid.read_id, self.message_nodeid.write_id):
            logger.debug(msg)
            self.message_nodeid.update_payload(msg.data)

    def stop(self):
        """Stops any ongoing thread"""
        if self._notifier is not None:
            self._notifier.stop()
        if self._bus is not None:
            self._bus.shutdown()  # free the port
            self._bus = None
        self.message_do.bus = None
        self.message_di.bus = None
        self.message_nodeid.bus = None
        self.message_bitrate.bus = None


if __name__ == "__main__":
    caro = CaroA04()
    caro.start(0xE0, 'pcan', 250000, 'PCAN_USBBUS2')
    caro.do1.phys = True
    print(caro.do1.phys)
    caro.do1.phys = False
    caro.stop()
