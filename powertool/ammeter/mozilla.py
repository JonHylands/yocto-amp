# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import collections
import Queue
import serial
import sys
import threading
import time

from ..sample_source import SampleSource, SampleSourceNoDeviceError
from ..device_manager import DeviceManager
from ..sample import Sample
from ..time_utils import now_in_millis
from serial.tools import list_ports

# the name of the SampleSource class to use
SampleSourceClass = 'MozillaAmmeter'

SAMPLE_RATE = 100
SAMPLE_TIME = 1000 / SAMPLE_RATE

class MozillaDevice(threading.Thread):

    BAUD = 1000000
    TIMEOUT = 1
    ASYNC_RESPONSE_SIZE = 86
    SYNC_RESPONSE_SIZE = 14

    # commands
    SET_ID = bytearray.fromhex("ff ff 01 02 01 FB")
    START_ASYNC = bytearray.fromhex("ff ff 01 02 02 FA")
    STOP_ASYNC = bytearray.fromhex("ff ff 01 02 03 F9")
    TURN_OFF_BATTERY = bytearray.fromhex("ff ff 01 02 05 F7")
    TURN_ON_BATTERY = bytearray.fromhex("ff ff 01 02 06 F6")
    GET_SAMPLE = bytearray.fromhex("ff ff 01 02 07 F5")
    GET_RAW_SAMPLE = bytearray.fromhex("ff ff 01 02 0A F2")
    GET_VERSION = bytearray.fromhex("ff ff 01 02 0B F1")
    GET_SERIAL = bytearray.fromhex("ff ff 01 02 0E EE")

    #SET_SERIAL = bytearray.fromhex("ff ff 01 04 0D")
    #SET_SERIAL also includes 2 bytes (little endian) of the serial#, plus the CRC

    #SET_CALIBRATION = bytearray.fromhex("ff ff 01 0A 09")
    #SET_CALIBRATION also includes two 4-byte floats (floor and scale), plus the CRC

    def __init__(self, path, async=True):
        super(MozillaDevice, self).__init__()
        self._path = path
        if path == None:
            self._path = self.get_device_paths()[0]
            print "Found Mozilla Ammeter attached to: %s" % self._path
        else:
            self._path = path
        self._cmds = Queue.Queue()
        self._quit = threading.Event()
        self._packets = collections.deque(maxlen=10)
        self._module = serial.Serial(port=self._path, baudrate=self.BAUD, timeout=self.TIMEOUT)
        self._async = async

        if self._async:
            self._response_size = self.ASYNC_RESPONSE_SIZE
            # start the thread
            super(MozillaDevice, self).start()
        else:
            self._response_size = self.SYNC_RESPONSE_SIZE

    @classmethod
    def get_device_paths(cls):
        # get the list of os-specific serial port names that have a Mozilla ammeter connected to them
        ports = [p[0] for p in serial.tools.list_ports.comports() if p[2].lower().startswith('usb vid:pid=03eb:204b')]
        if len(ports) > 0:
            return ports
        raise SampleSourceNoDeviceError('mozilla')

    def send_command(self, cmd):
        """ adds a command to the command queue """
        self._cmds.put_nowait(cmd)

    def get_packet(self):
        # We use this when we're running in sync mode
        self._module.write(self.GET_SAMPLE)
        self._module.flush()
        return self._module.read(self._response_size)

    @property
    def packet(self):
        try:
            if not self._async:
                self._packets.append( self._module.read(self._response_size) )
            # this is atomic
            return self._packets.popleft()
        except:
            return None

    # make packet a read-only property
    @packet.setter
    def packet(self, data):
        pass

    def quit(self):
        if self._async:
            # send STOP_ASYNC command to wake up the worker thread, if needed
            self.send_command(self.STOP_ASYNC)

        # set the quit flag, all remaining commands will be processed before
        # the thread function exits
        self._quit.set()

        if self._async:
            # join the thread and wait for the thread function to exit
            super(MozillaDevice, self).join()

        # when we get here, the thread has stopped so close the serial port
        self._module.close()

    def run(self):
        """ This is run in a separate thread """

        # start off by putting the START_ASYNC command in the command queue
        self.send_command(MozillaDevice.START_ASYNC)

        while True:
            if not self._cmds.empty():
                try:
                    # block waiting for a command at most 100ms
                    cmd = self._cmds.get( True, 0.1)

                    # send the command to the device
                    self._module.write(cmd)
                    self._module.flush()

                    # mark the command as processed
                    self._cmds.task_done()

                except Queue.Empty:
                    # if we get here, the get() timed out or the queue was empty
                    pass

            elif self._quit.is_set():
                # time to quit
                return

            # read a packet from the device and queue it up
            self._packets.append( self._module.read(self._response_size) )


class MozillaPacketHandler(threading.Thread):

    ASYNC_PACKET_SIZE = 86
    SYNC_PACKET_SIZE = 14

    def __init__(self, device, async=True):
        super(MozillaPacketHandler, self).__init__()
        self._quit = threading.Event()
        self._samples = collections.deque(maxlen=20)
        self._device = device
        self._async = async

        if self._async:
            self._packet_size = self.ASYNC_PACKET_SIZE
            # start the thread
            super(MozillaPacketHandler, self).start()
        else:
            self._packet_size = self.SYNC_PACKET_SIZE

    @property
    def sample(self):
        try:
            if not self._async:
                self.process_packet(self._device.get_packet())
            # this is atomic
            return self._samples.popleft()
        except:
            return {}

    # make packet a read-only property
    @sample.setter
    def sample(self, data):
        pass

    def quit(self):
        self._quit.set()
        if self._async:
            super(MozillaPacketHandler, self).join()

    def process_packet(self, data):
        # sanity check
        packet_length = len(data)
        if packet_length != self._packet_size:
            print >> sys.stderr, "Packet is not %d bytes long - %d bytes" % (self._packet_size, packet_length)
            return

        # unpack the first sample from the packet
        data_portion = data[5:packet_length-1]
        packet_count = (packet_length - 6) / 8
        for index in range(0, packet_count):
            start_index = index * 8
            end_index = start_index + 8
            sample_bytes = data_portion[start_index:end_index]

            # get the current in mA
            current = int((ord(sample_bytes[0]) + (ord(sample_bytes[1]) * 256)) / 10)
            if (current > 32767):
                current = (65536 - current) * -1;

            # get the voltage in mV
            voltage = ord(sample_bytes[2]) + (ord(sample_bytes[3]) * 256)
            time = ord(sample_bytes[4]) + (ord(sample_bytes[5]) * 256) + (ord(sample_bytes[6]) * 65536) + (ord(sample_bytes[7]) * 16777216)

            self._samples.append({'current':current, 'voltage':voltage, 'time':time})


    def run(self):

        while True:
            if self._quit.is_set():
                return

            # get a packet from the device thread
            data = self._device.packet

            # if we didn't get a packet, sleep a little and try again
            if data == None:
                time.sleep(0.1)
                continue

            self.process_packet(data)


class MozillaAmmeter(SampleSource, DeviceManager):
    """ This is a concrete class that interfaces with the Mozilla USB Ammeter
    and implements the SampleSource interface.  It provides sources called
    'current', 'voltage', and 'time'. """

    UNITS = { 'current': 'mA', 'voltage': 'mV', 'time': 'ms' }

    def __init__(self, path, async=True):
        super(MozillaAmmeter, self).__init__()

        # create the threaded device object and get the thread going
        self._async = async
        self._device = MozillaDevice(path, self._async)
        self._handler = MozillaPacketHandler(self._device, self._async)

    @property
    def names(self):
        return ('current','voltage', 'time')

    def get_sample(self, names):
        # get a sample
        sample = self._handler.sample

        if sample:
            # pull the requested samples out
            return { name: Sample(int(sample[name]), self.UNITS[name]) for name in names }
        else:
            return None

    def close(self):
        # stop the packet handler thread and wait for it to finish
        self._handler.quit()
        # stop the device handler thread and wait for it to finish
        self._device.quit()

    # FIXME: refactor this to use an ADBDeviceManager mixin eventually
    def start_charging(self, charge_complete):
        pass

    def stop_charging(self):
        pass

    def disconnect_usb(self):
        pass

    def connect_usb(self):
        pass

    def hard_power_off(self):
        self._device.send_command(MozillaDevice.TURN_OFF_BATTERY)

    def hard_power_on(self):
        self._device.send_command(MozillaDevice.TURN_ON_BATTERY)
