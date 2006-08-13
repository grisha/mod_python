Mod_python Memory Leak Test Suite
=================================

This documentation is obviously incomplete. Your best bet is to read the 
source.

This test suite does not currently use the unittest framework, but I
will eventually refactor it to do so. However it will remain independent
of the mod_python unit tests as these leak tests can be very time consuming,
depending on the number of requests require by a test to confirm a leak.
Some leaks may not be obvious with anything less that 500k requests.

Requirements
------------

Install
-------

tar zxvf leaktest.tgz

Apache Config
-------------


Usage
-----

$ leakclient.py -h


OS Notes
--------

On Debian the default ip_conntrack_max may not be sufficient
if you are really hammering the server. Increase by doing:
# echo 48000 > /proc/sys/net/ipv4/ip_conntrack_max
