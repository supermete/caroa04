import time
import can
import logging

try:
    from autotest.framework.canmessage import *
except:
    from canmessage import *

logging.basicConfig(level=logging.INFO)

__author__ = "R. Soyding"

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


class XCanSignal(CanSignal):
    """
    Overrides CanSignal class to send a message on the CAN when signal is being read or written.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def raw(self):
        """
        Get raw value of the signal
        :return: raw value of the signal
        """
        if self.parent is not None:
            self.parent.read()

        return self.value

    @property
    def phys(self):
        """
        Get physical value of the signal
        :return: physical value of the signal
        """
        if self.parent is not None:
            self.parent.read()

        value = self.value

        if self.type == BOOL:
            return bool(value)
        elif self.type == ENUM:
            if self.value in self.enum:
                return self.enum[self.value]
            else:
                return self.value
        else:
            if self.signed:
                value *= float(self.factor)
                value += self.offset
                value &= int(f"0b{'1' * self.length}", 2)

            return value

    @raw.setter
    def raw(self, value):
        """
        Set the raw value of the signal
        :param value: raw value to be set
        :return: None
        """
        self.value = int(value + self.offset) & int(f"0b{'1'*self.length}", 2)

        if self.parent is not None:
            self.parent.write()

    @phys.setter
    def phys(self, value):
        """
        Set the physical value of the signal (applies factor or enum depending on signal's type)
        :param value: physical value to be set
        :return: None
        """
        if self.type == ENUM:
            if value in self.enum.values():
                for key in self.enum:
                    if self.enum[key] == value:
                        self.value = key
                        break
                else:
                    return  # don't send anything if value is not valid
        else:
            if self.signed:
                if self.length <= 8:
                    value = numpy.uint8(round(value / float(self.factor)))
                elif self.length <= 16:
                    value = numpy.uint16(round(value / float(self.factor)))
                elif self.length <= 32:
                    value = numpy.uint32(round(value / float(self.factor)))
                elif self.length <= 64:
                    value = numpy.uint64(round(value / float(self.factor)))
                self.value = ((value + self.offset) & int(f"0b{'1' * self.length}", 2))
            else:
                self.value = round((int(value / float(self.factor)) + self.offset) & int(f"0b{'1' * self.length}", 2))

        if self.parent is not None:
            self.parent.write()


class CanMessageRW(CanMessage):
    """
    Overrides CanMessage class to use a different arbitration ID for reading and writing and actually handling
    read and writes using the provided bus instance.
    Includes a command byte support, where the first byte of the payload can be set to a specific value everytime a
    signal read or write operation is requested.
    """
    def __init__(self, node_id, read_id, write_id, **kwargs):
        self.bus = kwargs.pop('bus', None)
        self.rx_cmd_byte = kwargs.pop('rx_cmd_byte', None)
        self.tx_cmd_byte = kwargs.pop('tx_cmd_byte', None)
        self.cmd_byte = None
        self.read_id = read_id | node_id
        self.write_id = write_id | node_id
        self._node_id = node_id
        super().__init__(0, **kwargs)

        if self.rx_cmd_byte is not None and self.tx_cmd_byte is not None:
            self.cmd_byte = CanSignal(startbit=0, length=8)
            self.add(self.cmd_byte)

    @property
    def node_id(self):
        return self._node_id

    @node_id.setter
    def node_id(self, value):
        self.read_id = (self.read_id & 0x700) | value
        self.write_id = (self.write_id & 0x700) | value
        self._node_id = value

    def write(self):
        """
        Sends message with the write identifier.
        :return: None
        """
        if self.bus is not None:
            logging.debug(f"Sending message {self.write_id:#x}")

            if self.cmd_byte is not None:
                self.cmd_byte.raw = self.tx_cmd_byte

            message = can.Message(arbitration_id=self.write_id,
                                  data=self.payload,
                                  is_extended_id=self.is_extended)
            logging.debug(message)
            self.bus.send(message)

            self.bus.set_filters([{"can_id": self.write_id, "can_mask": 0x7ff, "extended": False}])
            sts = self.bus.recv(5)
            if sts is not None and sts.arbitration_id == self.write_id and sts.dlc > 0:
                self.update_payload(sts.data)
            else:
                logging.warning('Could not get a response from the device')
            self.bus.set_filters()

    def read(self):
        """
        Sends message with the read identifier and updates the signals with the received response.
        :return: None
        """
        if self.bus is not None:
            if self.cmd_byte is not None:
                self.cmd_byte.raw = self.rx_cmd_byte

            message = can.Message(arbitration_id=self.read_id,
                                  data=self.payload,
                                  is_extended_id=self.is_extended)
            logging.debug(message)
            self.bus.send(message)

            self.bus.set_filters([{"can_id": self.read_id, "can_mask": 0x7ff, "extended": False}])
            sts = self.bus.recv(5)
            if sts is not None and sts.arbitration_id == self.read_id and sts.dlc > 0:
                logging.debug(sts)
                self.update_payload(sts.data)
            else:
                logging.warning('Could not get a response from the device')
            self.bus.set_filters()


class CanIoExp1:
    def __init__(self):
        self._node_id = DEFAULT_NODEID
        self.bus = None

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

    def start(self, node_id, interface, bitrate=None, channel=None):
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

        if self.bus is None:
            self.bus = can.Bus(interface=interface, channel=channel, bitrate=bitrate)
            self.message_do.bus = self.bus
            self.message_di.bus = self.bus
            self.message_nodeid.bus = self.bus
            self.message_bitrate.bus = self.bus

    def stop(self):
        """Stops any ongoing thread - unused"""
        pass

    def shutdown(self):
        if self.bus is not None:
            self.bus.shutdown()  # free the port
            self.bus = None
            self.message_do.bus = None
            self.message_di.bus = None
            self.message_nodeid.bus = None
            self.message_bitrate.bus = None


if __name__ == "__main__":
    caro = CanIoExp1()
    caro.start(0xE0, 'pcan', 250000, 'PCAN_USBBUS2')
    print(caro.do1.phys)
    caro.do1.phys = True
    print(caro.do1.phys)
    time.sleep(0.5)
    caro.do1.phys = False
    print(caro.do1.phys)
    caro.shutdown()
