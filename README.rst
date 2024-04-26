=======
caroa04
=======


.. image:: https://img.shields.io/pypi/v/caroa04.svg
        :target: https://pypi.python.org/pypi/caroa04

.. image:: https://img.shields.io/pypi/pyversions/caroa04.svg
        :target: https://pypi.org/project/caroa04
        :alt: Python versions

.. image:: https://github.com/supermete/caroa04/actions/workflows/python-app.yml/badge.svg
        :target: https://github.com/supermete/caroa04/actions/workflows/python-app.yml
        :alt: See Build Status on GitHub Actions

.. image:: https://readthedocs.org/projects/caroa04/badge/?version=latest
        :target: https://caroa04.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status




Library to control the CAROA04 CAN-IO expander device from eletechsup.


* Free software: MIT license
* Documentation: https://caroa04.readthedocs.io.


Installation
------------

You can install "caroa04" via pip from PyPI:

    $ pip install caroao4


Usage
-----

You can instantiate a CaroA04 object and start it to communicate with the device as follows.

.. code-block:: python

    from caroa04 import CaroA04

    caro = CaroA04()
    caro.start(0xE0, 'pcan', 250000, 'PCAN_USBBUS1')  # start communication

    caro.do1.phys = True  # set do1 state to True
    print(caro.do1.phys)  # read do1 state
    print(caro.di1.phys)  # read di1 state

    print(caro.bitrate.phys)  # read current bitrate
    caro.bitrate.phys = 500000  # set different baudrate (will require device power cycle)

    print(caro.node_id.phys)  # read current address code
    caro.node_id.phys = 0xE1  # set address code (will require device power cycle)

    caro.shutdown()  # free the bus

..

In order to share the bus with other participants, you can assign the bus attribute of the CaroA04 object before starting it.
You should simply then add CaroA04's listener to the existing bus' notifier.

.. code-block:: python

    import canopen
    from caroa04 import CaroA04

    nw = canopen.Network()
    nw.connect(interface='pcan', bitrate=250000, channel='PCAN_USBBUS1')


    caro = CaroA04()
    caro.bus = nw.bus  # use the bus already started by canopen
    nw.notifier.add_listener(caro.listener)  # add listener so that we can receive messages

    caro.start(0xE0, 'pcan')  # start communication
    caro.shutdown()  # free the bus

..

Features
--------

* This library uses the python-can library to communicate with the device. Please refer to its documentation to know about all the CAN interfaces that can be used with this library (https://python-can.readthedocs.io/en/stable/)
* The device has 4 digital outputs and 4 digital inputs. Hence the signals can be read/written by using the attributes of the CaroA04 class:
    * do1, do2, do3, do4 : digital output 1 to digital output 4
    * di1, di2, di3, di4 : digital input 1 to digital input 4
    * bitrate, node_id : bitrate and address code of the device
* Each signal has a raw value and a physical value. For example, the device does not understand a bitrate in bps. It expects an enumeration that it will interpret. So it can either be set by writing its physical value (bitrate.phys = 250000) or by writing its raw value (bitrate.raw) as follows:
    * 0: 5 kbps
    * 1: 10 kbps
    * 2: 20 kbps
    * 3: 50 kbps
    * 4: 100 kbps
    * 5: 120 kbps
    * 6: 200 kbps
    * 7: 250 kbps
    * 8: 400 kbps
    * 9: 500 kbps
    * 10: 800 kbps
    * 11: 1000 kbps

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
