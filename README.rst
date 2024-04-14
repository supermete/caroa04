=======
caroa04
=======


.. image:: https://img.shields.io/pypi/v/caroa04.svg
        :target: https://pypi.python.org/pypi/caroa04

.. image:: https://img.shields.io/travis/supermete/caroa04.svg
        :target: https://travis-ci.com/supermete/caroa04

.. image:: https://readthedocs.org/projects/caroa04/badge/?version=latest
        :target: https://caroa04.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status




Library to control the CAROA04 CAN-IO expander device from eletechsup.


* Free software: MIT license
* Documentation: https://caroa04.readthedocs.io.


Installation
------------

You can install "caroa04" via `pip`_ from `PyPI`_::

    $ pip install caroao4

Usage
-----

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

Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
