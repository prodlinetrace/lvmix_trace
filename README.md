# prodlinetrace
ProdLineTrace - Traceability for PLC based production line.


Pre-requisites
--------------

- Some Python coding experience
- Basic knowledge of ctypes

Requirements
------------

- Python 2.7 or 3.3+ on any supported OS (even Windows!)
- virtualenv (or pyvenv if you are using Python 3.4)
- git
- configured PLC controller. 

Setup
-----

In order to build installer following packages needs to be installed:
ActivePython 2.7.10 :
wxPython3.0-win64-3.0.2.0-py27.exe

Below are step-by-step installation instructions:

**Step 1**: Clone the git repository

    $ git clone https://github.com/wilkpio/prodlinetrace.git
    $ cd prodlinetrace

**Step 2**: Create a virtual environment.

For Linux, OSX or any other platform that uses *bash* as command prompt (including Cygwin on Windows):

    $ virtualenv venv
    $ source venv/bin/activate
    (venv) $ pip install -r requirements.txt

For Windows users working on the standard command prompt:

    > virtualenv venv
    > venv\scripts\activate
    (venv) > pip install -r requirements.txt

**Step 3**: Start the application:

    (venv) $ python prodLineTrace.py
    
**Step 4**: build windows installer (optional)

    (venv) $ python setup.py bdist_msi
