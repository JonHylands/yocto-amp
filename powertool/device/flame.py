# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mozdevice import DeviceManagerADB
from ..ammeter import get_class

class Flame(object):
    ammeter_type = 'mozilla'

    def __init__(self, serial=None, ammeter=None):
        self.serial = serial
        self.ammeter = ammeter or get_class[self.ammeter_type](None)
        self._dm = None

    @property
    def dm(self):
        if not self._dm:
            self._dm = DeviceManagerADB(deviceSerial=self.serial)
        return self._dm

    def disable_usb_charging(self):
        self.dm.shellCheckOutput([
            'echo', '0', '>>', '/sys/class/power_supply/battery/charging_enabled'
        ])

    def enable_usb_charging(self):
        self.dm.shellCheckOutput([
            'echo', '1', '>>', '/sys/class/power_supply/battery/charging_enabled'
        ])

    def power_on(self):
        self.ammeter.hard_power_on()

    def power_off(self):
        self.disable_usb_charging()
        self.ammeter.hard_power_off()
