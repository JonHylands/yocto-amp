FxOS Powertool!
===============

The FxOS Powertool! is intended for FxOS developers to use when optimizing software for power consumption.  It is also handy for verifying and fixing power consumption bugs.

Prerequisites
-------------

This tool requires that you have a USB ammeter device like the [Yoctopuce USB ammeter](http://www.yoctopuce.com/EN/products/usb-sensors/yocto-amp) or build your own using the [Mozilla ammeter design](http://wiki.mozilla.org).

You will also need a battery harness for your FxOS device.  The battery harnesses are open source hardware that consist of a 3D printed piece, and a small circuit board.  You can find all of the data files for the currently supported FxOS devices below:

* [Alcatel OneTouch Battery Harness](http://missing.link)
* [Samsung Nexus S Battery Harness](http://missing.link)
* [LG Nexus 4 Battery Harnes](http://missing.link)

Quick Start
-----------

The first step is to clone this repo:

```sh
$ git clone git://github.com/JonHylands/fxos-powertool
```

Then isntall the application and dependencies:

```sh
$ cd fxos-powertool
$ sudo python ./setup.py install
```

Write your test suite description file.  There is an example in the examples folder.  It is a JSON file that looks like this:

```json
{
    "title": "My Tests",
    "tests": [
        "My first test",
        "My second test",
        "My third test"
    ]
}
```

Plug in your ammeter device, and hook it up to the battery harness for your device.  Then launch the powertool to begin testing.

Using Programmatically
----------------------

To use powertool as a script, you typically instantiate a device or pool object. For now only Flame devices are supported.

If only a single device is attached to your computer, the device serial and attached ammeter are detected automatically:
```py
from powertool.device import Flame
device = Flame()
device.power_on()
device.power_off()
```

If multiple devices are attached, we need to figure out which ammeters are attached to which devices. To do this you can
instantiate a Pool object. Pool objects will power off all attached devices one by one and monitor which serial goes
offline via adb. It maps serials to ammeters which gives the pool the ability to power on or off devices using the serial
number. For example:

```py
from powertool.device import Flame, Pool
pool = Pool(device_class=Flame)
# replace <serial> with the serial of the device you wish to operate on
pool['<serial>'].power_on()
pool['<serial>'].power_off()
