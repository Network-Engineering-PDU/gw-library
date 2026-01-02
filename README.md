# TTGWLib

Library to control a Bluetooth Mesh net using a Nordic nRF52 microcontroller
through serial interface.

This library is written for Python 3, and it will not work with Python 2. This
documentation assumes that `python` executes Python 3. This can be check
through the commands `python --version` or `pip --version`. If those execute
Python 2, the commands `python3` and `pip3` should be used instead, as happen,
for example, with most RaspberryPi OS.

The firmware that should be used in the microcontroller can be found
[here](https://bitbucket.org/tychetools/gw-firmware). This library
is not meant to be used by itself. A CLI app that implements this library
can be found [here](https://bitbucket.org/tychetools/gw-app)

## Installation

The library is intended to be included as a package in a Linux distribution generated using Yocto. However, it can also be installed using pip. In the root directory of the project,
type the following command:

    pip install .

This will install the library and also the required dependencies.

## Examples

Inside the *examples* directory, there are some examples showing how to
use the library. The files *test.py* and *remote_app.py* are examples of usage of the library:

    python test.py

This file is mean to be executed from inside the Python interpreter in the root directory. A
basic usage, can be obtaining executing the following commands:

    $ python
    >>> exec(open("examples/test.py").read())
    >>> gt.start_scan(uuid_filter)
        ... some time later ...
    >>> gt.stop_scan()
        ... on exit ...
    >>> gt.close()
    >>> exit()

## Tests

Inside the *tests* directory, there are unitary and integration tests. You can
run them by executing the following command:

    python -m unittest discover -v tests/

You can also check the test coverage by executing the following commands:

    coverage run -m unittest discover -v tests/
    coverage report

## Generate the documentation

To generate the documentation, the module *Sphinx* is needed:

    pip install --user Sphinx

Whith *Sphinx* installed, go to the *root*/docs directory and type:

    make html latexpdf

This will create the html pages and a pdf file with the documentation.
