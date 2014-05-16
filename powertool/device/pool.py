# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import subprocess
import time

from .. import ammeter

def _run_adb(args):
    args.insert(0, 'adb')
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    retcode = proc.wait()
    if retcode:
        raise Exception('adb terminated with exit code %d: %s'
                        % (retcode, proc.stdout.read()))
    return proc.stdout.read()


class Pool(object):
    serial_map = {}

    def __init__(self, device_class):
        self.device_class = device_class
        self.build_serial_map()

    def __getitem__(self, serial):
        return self.serial_map[serial]

    def _get_serials(self):
        output = _run_adb(['devices'])
        devices = [line.split()[0] for line in output.splitlines() if line.endswith('device')]
        return set(devices)

    def build_serial_map(self):
        self.serial_map = {}
        serials = self._get_serials()
        am_type = self.device_class.ammeter_type
        am_paths = ammeter.get_paths[am_type]()

        for s in serials:
            _run_adb(['-s', s, 'shell', 'echo', '0', '>>',
                      '/sys/class/power_supply/battery/charging_enabled'])

        for path in am_paths:
            am = ammeter.get_class[am_type](path)
            am.hard_power_off()

            now = datetime.datetime.now()
            missing_serial = serials - self._get_serials()
            while missing_serial == set([]):
                time.sleep(1)
                if datetime.datetime.now() - now > datetime.timedelta(seconds=60):
                    raise Exception('timed out waiting for device to power off')
                missing_serial = serials - self._get_serials()

            assert len(missing_serial) == 1
            serial = list(missing_serial)[0]
            am.hard_power_on()

            now = datetime.datetime.now()
            while serials - self._get_serials() != set([]):
                time.sleep(1)
                if datetime.datetime.now() - now > datetime.timedelta(seconds=60):
                    raise Exception('timed out waiting for device to power on')

            self.serial_map[serial] = self.device_class(serial, am)
