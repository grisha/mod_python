
#
# Copyright 2006 Apache Software Foundation 
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You
# may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.
#
# $Id$
#

"""Useful utility functions for running tests."""


import os
import socket
import unittest

def get_ab_path(httpd):
    """ Find the location of the ab (apache benchmark) program """
    for name in ['ab', 'ab2', 'ab.exe', 'ab2.exe']:
        path = os.path.join(os.path.split(httpd)[0], name)
        if os.path.exists(path):
            return quoteIfSpace(path)

    return None

def quoteIfSpace(s):

    # Windows doesn't like quotes when there are
    # no spaces, but needs them otherwise
    if s.find(" ") != -1:
        s = '"%s"' % s
    return s

def findUnusedPort():

    # bind to port 0 which makes the OS find the next
    # unused port.

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    return port


