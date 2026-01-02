.. rst-class:: hide-header

TTGWLib
=======

Library to control a Bluetooth Mesh net using a Nordic nRF52 microcontroller
connected through serial interface.

This library is written for Python 3, and it will not work with Python 2. This
documentation assumes that python executes Python 3. This can be check through
the commands python --version or pip --version. If those execute Python 2, the
commands python3 and pip3 should be used instead, as happen, for example, with
most RaspberryPi OS.

The firmware that should be used in the microcontroller can be found
`here <https://bitbucket.org/tychetools/gw-firmware>`_. This
library is not meant to be used by itself. There is a
`CLI app <https://bitbucket.org/tychetools/gw-app>`_ that implements
this library.

Documentation
-------------

.. toctree::
    :maxdepth: 2

    quickstart
    example

API Reference
-------------

Información sobre funciones y clases.

.. toctree::
    :maxdepth: 2

    api
