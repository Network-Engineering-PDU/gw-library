

Installation
------------

To install the library::

    pip install --user .

This will also install the required dependencies.

Threads
-------

The library creates 4 sub-threads, which are:

- Reader: Reads bytes from the serial port.
- Writer: Writes bytes to the serial port.
- EventParser: Forms seral messages from received bytes.
- EventHandler: Handles events.


Logging
-------

This library implements the Python 3
`logging module <https://docs.python.org/3/library/logging.html>`_ for
logging internal events.

The library uses the default logging levels (ERROR, WARNING, INFO, DEBUG), but
also implements an even higher level than DEBUG. This log level, with value 9,
logs all UART raw packets.

Each thread has its own name, so it can be used in the logger as well.
