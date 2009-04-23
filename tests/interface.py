import termios
import struct
import fcntl

from tests.mocker import MockerTestCase

from smart.interface import getScreenWidth
import smart



class InterfaceTest(MockerTestCase):

    def test_getScreenWidth(self):
        input_data = struct.pack("HHHH", 0, 0, 0, 0)
        output_data = struct.pack("HHHH", 0, 100, 0, 0)

        ioctl_mock = self.mocker.replace(fcntl.ioctl)
        ioctl_mock(1, termios.TIOCGWINSZ, input_data)
        self.mocker.result(output_data)

        self.mocker.replay()

        self.assertEquals(getScreenWidth(), 100)

    def test_getScreenWidth_with_zero_width_falls_back_to_80(self):
        input_data = struct.pack("HHHH", 0, 0, 0, 0)
        output_data = struct.pack("HHHH", 0, 0, 0, 0)

        ioctl_mock = self.mocker.replace(fcntl.ioctl)
        ioctl_mock(1, termios.TIOCGWINSZ, input_data)
        self.mocker.result(output_data)

        self.mocker.replay()

        self.assertEquals(getScreenWidth(), 80)

    def test_getScreenWidth_falls_back_to_80_if_raising_IOError(self):
        input_data = struct.pack("HHHH", 0, 0, 0, 0)

        ioctl_mock = self.mocker.replace(fcntl.ioctl)
        ioctl_mock(1, termios.TIOCGWINSZ, input_data)
        self.mocker.throw(IOError)

        self.mocker.replay()

        self.assertEquals(getScreenWidth(), 80)

