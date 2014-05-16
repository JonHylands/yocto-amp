# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mozilla import MozillaAmmeter, MozillaDevice
from yocto import YoctoAmmeter

get_class = {
    'mozilla': MozillaAmmeter,
    'yocto': YoctoAmmeter,
}

get_paths = {
    'mozilla': MozillaDevice.get_device_paths,
    'yocto': lambda: [], # not implemented
}
