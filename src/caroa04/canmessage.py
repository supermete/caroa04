import numpy
import logging
import can
logger = logging.getLogger(__name__)
logger.propagate = True

__author__ = "R. Soyding"

BOOL = 1
ENUM = 99
LITTLE_ENDIAN = 0
BIG_ENDIAN = 1
ID_EXTENDED_MAX_BITLENGTH = 29
ID_STANDARD_MAX_BITLENGTH = 11


class CanMessage:
    def __init__(self, can_id, cycle_ms=10, dlc=8, is_extended=False):
        assert isinstance(can_id, int), "CAN indentifier should be an integer"
        self.dlc = dlc
        self._payload = [0] * dlc  # Although for now messages with dlc > 8 won't work
        self.signals = list()
        self._identifier = can_id
        self.cycle_ms = cycle_ms
        self.is_extended = is_extended

    def add(self, *signals):
        # Todo: check that added signals don't overlap each other
        for signal in signals:
            assert isinstance(signal, CanSignal), "signal must be a CanSignal instance"
            assert signal.startbit + signal.length <= self.dlc * 8, "Signal out of message payload length"
            signal.set_parent(self)
            self.signals.append(signal)
            self._update_signal_in_payload(signal)

    def clear(self):
        for signal in reversed(self.signals):
            signal.clear()
            self.signals.remove(signal)
        self._payload = [0] * self.dlc

    def get_cycle_ms(self):
        return self.cycle_ms

    def get_dlc(self):
        return self.dlc

    @property
    def arbitration_id(self):
        return self._identifier

    @arbitration_id.setter
    def arbitration_id(self, can_id):
        assert isinstance(can_id, int)
        assert can_id.bit_length() <= ID_EXTENDED_MAX_BITLENGTH
        self._identifier = can_id

    @property
    def payload(self):
        self.update()
        return self._payload

    @payload.setter
    def payload(self, data):
        assert len(data) == self.dlc, "Payload length does not match message DLC"
        self._payload = data
        self._update_from_payload()

    def get_payload_byte(self, index):
        assert isinstance(index, int)
        assert index < self.dlc
        return self._payload[index]

    def set_cycle_ms(self, cycle_ms):
        assert isinstance(cycle_ms, int)
        assert cycle_ms > 0
        self.cycle_ms = cycle_ms

    def set_payload_byte(self, index, value):
        assert isinstance(index, int)
        assert index < self.dlc
        assert isinstance(value, int)
        self._payload[index] = value

    def update_payload(self, payload):
        assert len(payload) == self.dlc, "Payload length does not match message DLC"
        self._payload = payload
        self._update_from_payload()

    def _update_from_payload(self):
        """Update signals value from payload raw hex values"""
        for signal in self.signals:
            byte_index = 0
            measured = 0

            tmp_length = signal.length
            tmp_startbit = signal.startbit
            # Get the index of the first byte to be modified
            if tmp_startbit % 8 == 0:
                while tmp_length > 0:
                    if tmp_length < 8:
                        mask = eval("0b" + "1" * tmp_length)  # only the first "length" bits are to be considered
                    else:
                        mask = 0xff
                    measured += (self._payload[tmp_startbit // 8] & mask) << (8 * byte_index)
                    tmp_startbit += 8
                    tmp_length -= 8
                    byte_index += 1
            else:
                # Build the mask in binary first
                tmpmask = [0 for _ in range(tmp_startbit % 8)]
                tmpmask += [1 for _ in range(tmp_startbit % 8, tmp_startbit % 8 + tmp_length)]
                tmpmask += [0 for _ in range(tmp_startbit % 8 + tmp_length, 8)]
                mask = eval("0b" + "".join(
                    [str(i) for i in reversed(tmpmask)]))  # convert the binary string into an hex then an int
                measured += (self._payload[tmp_startbit // 8] & mask) >> (tmp_startbit % 8)

            signal.value = int(measured + signal.offset) & int(f"0b{'1' * signal.length}", 2)

    def update(self):
        for signal in self.signals:
            self._update_signal_in_payload(signal)

    def _update_signal_in_payload(self, signal):
        """Update the message payload with the signal's value"""
        byte_index = 0

        val = signal.value
        startbit = signal.startbit
        # Get the index of the first byte to be modified
        while startbit // 8 > 0:
            byte_index += 1
            startbit -= 8

        # calculate the mask for the first byte to modify
        if signal.length <= 8 - startbit :
            mask = int(f"0b{'1' * signal.length}", 2)
        else:
            mask = int(f"0b{'1' * (8 - startbit)}", 2)
        mask = (0xFF ^ (mask << startbit))

        # The remaining of startbit can be used to shift the value now
        if startbit > 0:
            val <<= numpy.uint32(startbit)

        # if big endian, we start by the msb and we shift to the lsb
        if signal.endianness == BIG_ENDIAN:
            shift = (signal.length // 8)
            if signal.length % 8 == 0:
                shift -= 1
        else:
            shift = 0
        # Cut val in 8 bits chunks and put it at the right index in payload
        bitlength = signal.length
        while bitlength // 8 > 0:
            try:
                self._payload[byte_index] &= numpy.uint8(mask)
                self._payload[byte_index] |= (val >> (shift * 8)) & 0xff
            except Exception as e:
                raise Exception(f"Signal do not fit in the message. DLC might be too small.\n{e}")
            bitlength -= 8
            byte_index += 1
            if signal.endianness == BIG_ENDIAN:
                shift -= 1
            else:
                shift += 1

            if bitlength >= 8:
                mask = 0
            elif bitlength > 0:
                mask = int(f"0b{'1' * (8 - bitlength)}{'0' * bitlength}", 2)

        # if bitlength is not 0 put the last chunk in payload too as there are some bits of data left in val
        if bitlength > 0 and byte_index < 8:
            self._payload[byte_index] &= (mask & 0xFF)
            self._payload[byte_index] |= ((val >> (shift * 8)) & 0xFF)


class CanSignal:
    def __init__(self, startbit=0, length=1, factor=1, offset=0, endianness=BIG_ENDIAN, signed=False, type=0, enum=None):
        self.startbit = startbit
        self.length = length
        self.factor = factor
        self.value = 0
        self.parent = None
        self.signed = signed
        self.offset = offset
        self.endianness = endianness
        self.type = type
        self.enum = enum

    def clear(self):
        self.parent = None

    @property
    def raw(self):
        return self.value

    @property
    def phys(self):
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
        self.value = int(value + self.offset) & int(f"0b{'1'*self.length}", 2)

    @phys.setter
    def phys(self, value):
        if self.type == ENUM:
            if value in self.enum.values():
                for key in self.enum:
                    if self.enum[key] == value:
                        self.value = key
                        break
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

    def set_parent(self, message):
        self.parent = message


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
            logger.debug(f"Sending message {self.write_id:#x}")

            if self.cmd_byte is not None:
                self.cmd_byte.raw = self.tx_cmd_byte

            message = can.Message(arbitration_id=self.write_id,
                                  data=self.payload,
                                  is_extended_id=self.is_extended)
            logger.debug(message)
            self.bus.send(message)
            self.bus.recv(1)

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
            logger.debug(message)
            self.bus.send(message)
            self.bus.recv(1)


if __name__ == "__main__":
    msg_3c2 = CanMessage(0x3c2)
    csm_fail = CanSignal(startbit=8, length=1)
    sig1 = CanSignal(startbit=0, length=8)
    msg_3c2.add(csm_fail)
    msg_3c2.add(sig1)

    csm_fail.raw = 1
    sig1.raw = 0xff

    print(csm_fail.raw)
    print(msg_3c2.payload)