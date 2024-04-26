import threading
import pytest
import can

from src.caroa04.caroa04 import CaroA04, MSGID_DO_READ, MSGID_DO_WRITE, MSGID_DI_READ
from src.caroa04.canmessage import CanMessage, CanSignal, BOOL


class VirtualDevice:
    """
    This class aims to simulate the device.
    It will respond to the messages sent by the library, and keep track of the signal's value to answer properly.
    """
    def __init__(self):
        self.bus = None
        self.notifier = None
        self.message_do_set = CanMessage(MSGID_DO_WRITE)
        self.message_do_get = CanMessage(MSGID_DO_READ)
        self.message_di = CanMessage(MSGID_DI_READ)
        self.do1 = CanSignal(startbit=0, length=1, type=BOOL)
        self.do2 = CanSignal(startbit=1, length=1, type=BOOL)
        self.do3 = CanSignal(startbit=2, length=1, type=BOOL)
        self.do4 = CanSignal(startbit=3, length=1, type=BOOL)
        self.do1_tx = CanSignal(startbit=0, length=1, type=BOOL)
        self.do2_tx = CanSignal(startbit=1, length=1, type=BOOL)
        self.do3_tx = CanSignal(startbit=2, length=1, type=BOOL)
        self.do4_tx = CanSignal(startbit=3, length=1, type=BOOL)
        self.di1 = CanSignal(startbit=0, length=1, type=BOOL)
        self.di2 = CanSignal(startbit=1, length=1, type=BOOL)
        self.di3 = CanSignal(startbit=2, length=1, type=BOOL)
        self.di4 = CanSignal(startbit=3, length=1, type=BOOL)

        self.message_do_get.add(
            self.do1,
            self.do2,
            self.do3,
            self.do4
        )

        self.message_do_set.add(
            self.do1_tx,
            self.do2_tx,
            self.do3_tx,
            self.do4_tx
        )

        self.message_di.add(
            self.di1,
            self.di2,
            self.di3,
            self.di4
        )

    def start(self, node_id):
        self.message_do_set.arbitration_id = (self.message_do_set.arbitration_id & 0x700) | node_id
        self.message_do_get.arbitration_id = (self.message_do_get.arbitration_id & 0x700) | node_id
        self.message_di.arbitration_id = (self.message_di.arbitration_id & 0x700) | node_id

        if self.bus is None:
            self.bus = can.interface.Bus(interface='virtual')
            self.notifier = can.Notifier(self.bus, [self.listener])

    def listener(self, msg):
        if msg.arbitration_id == self.message_do_get.arbitration_id:
            # read request received, respond with the last values set with message_do_set
            self.bus.send(can.Message(arbitration_id=self.message_do_get.arbitration_id,
                                      data=self.message_do_set.payload,
                                      is_extended_id=False))
        elif msg.arbitration_id == self.message_do_set.arbitration_id:
            # write request received, respond with empty message
            self.message_do_get.update_payload(msg.data)
            self.bus.send(can.Message(arbitration_id=self.message_do_set.arbitration_id,
                                      data=msg.data,
                                      is_extended_id=False))
        elif msg.arbitration_id == self.message_di.arbitration_id:
            # read DI request received, respond with the DI message
            self.bus.send(can.Message(arbitration_id=self.message_di.arbitration_id,
                                      data=self.message_di.payload,
                                      is_extended_id=False))

    def stop(self):
        pass

    def shutdown(self):
        if self.bus is not None:
            self.bus.shutdown()
            self.bus = None


class TestVirtualCanIoExp1:
    @pytest.fixture(scope="class")
    def caro(self):
        return CaroA04()

    @pytest.fixture(scope="class")
    def virtualdevice(self):
        return VirtualDevice()

    @pytest.fixture(autouse=True, scope="class")
    def setup_teardown_class(self, caro, virtualdevice):
        """Fixture to execute asserts before and after a sccenario is run"""
        caro.start(0xE0, 'virtual')
        virtualdevice.bus = caro.bus
        caro.notifier.add_listener(virtualdevice.listener)

        virtualdevice.start(0xE0)

        yield

        caro.stop()
        caro.shutdown()
        virtualdevice.stop()
        virtualdevice.shutdown()

    def test_do1(self, caro, virtualdevice):
        assert caro.do1.phys is False, "Initial value of DO1 is wrong"
        caro.do1.phys = True
        assert virtualdevice.do1.phys is True, "DO1 write message not sent"
        caro.do1.phys = False
        assert virtualdevice.do1.phys is False, "Value of DO1 is wrong"

    def test_do2(self, caro, virtualdevice):
        assert caro.do2.phys is False, "Initial value of DO2 is wrong"
        caro.do2.phys = True
        assert virtualdevice.do2.phys is True, "DO2 write message not sent"
        caro.do2.phys = False
        assert virtualdevice.do2.phys is False, "Value of DO2 is wrong"

    def test_do3(self, caro, virtualdevice):
        assert caro.do3.phys is False, "Initial value of DO3 is wrong"
        caro.do3.phys = True
        assert virtualdevice.do3.phys is True, "DO3 write message not sent"
        caro.do3.phys = False
        assert virtualdevice.do3.phys is False, "Value of DO3 is wrong"

    def test_do4(self, caro, virtualdevice):
        assert caro.do4.phys is False, "Initial value of DO4 is wrong"
        caro.do4.phys = True
        assert virtualdevice.do4.phys is True, "DO4 write message not sent"
        caro.do4.phys = False
        assert virtualdevice.do4.phys is False, "Value of DO4 is wrong"

    def test_di1(self, caro, virtualdevice):
        assert caro.di1.phys is False, "Initial value of DI1 is wrong"
        virtualdevice.di1.phys = True
        assert caro.di1.phys is True, "Read value is not correct"
        virtualdevice.di1.phys = False
        assert caro.di1.phys is False, "Read value is not correct"

    def test_di2(self, caro, virtualdevice):
        assert caro.di2.phys is False, "Initial value of DI2 is wrong"
        virtualdevice.di2.phys = True
        assert caro.di2.phys is True, "Read value is not correct"
        virtualdevice.di2.phys = False
        assert caro.di2.phys is False, "Read value is not correct"

    def test_di3(self, caro, virtualdevice):
        assert caro.di3.phys is False, "Initial value of DI3 is wrong"
        virtualdevice.di3.phys = True
        assert caro.di3.phys is True, "Read value is not correct"
        virtualdevice.di3.phys = False
        assert caro.di3.phys is False, "Read value is not correct"

    def test_di4(self, caro, virtualdevice):
        assert caro.di4.phys is False, "Initial value of DI4 is wrong"
        virtualdevice.di4.phys = True
        assert caro.di4.phys is True, "Read value is not correct"
        virtualdevice.di4.phys = False
        assert caro.di4.phys is False, "Read value is not correct"
