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

"""mod_python.publisher tests"""

from __future__ import generators
from mod_python.python22 import *

from mod_python import apache
import unittest
import re
import time
import os
import cStringIO
import posixpath

# This is used for mod_python.publisher security tests
_SECRET_PASSWORD = 'root'
__ANSWER = 42


def index(req):
    return "test ok, interpreter=%s" % req.interpreter

def test_publisher(req):
    return "test ok, interpreter=%s" % req.interpreter

def test_publisher_auth_nested(req):
    def __auth__(req, user, password):
        test_globals = test_publisher
        req.notes["auth_called"] = "1"
        return user == "spam" and password == "eggs"
    def __access__(req, user):
        req.notes["access_called"] = "1"
        return 1
    assert(int(req.notes.get("auth_called",0)))
    assert(int(req.notes.get("access_called",0)))
    return "test ok, interpreter=%s" % req.interpreter

class _test_publisher_auth_method_nested:
    def method(self, req):
        def __auth__(req, user, password):
            test_globals = test_publisher
            req.notes["auth_called"] = "1"
            return user == "spam" and password == "eggs"
        def __access__(req, user):
            req.notes["access_called"] = "1"
            return 1
        assert(int(req.notes.get("auth_called",0)))
        assert(int(req.notes.get("access_called",0)))
        return "test ok, interpreter=%s" % req.interpreter

test_publisher_auth_method_nested = _test_publisher_auth_method_nested()

class OldStyleClassTest:
    def __init__(self):
        pass
    def __call__(self, req):
        return "test callable old-style instance ok"
    def traverse(self, req):
        return "test traversable old-style instance ok"
old_instance = OldStyleClassTest()

test_dict = {1:1, 2:2, 3:3}
test_dict_keys = test_dict.keys

def test_dict_iteration(req):
    return test_dict_keys()
    
def test_generator(req):
    c = 0
    while c < 10:
        yield c
        c += 1

class InstanceTest(object):
    def __call__(self, req):
        return "test callable instance ok"
    def traverse(self, req):
        return "test traversable instance ok"
instance = InstanceTest()

# Hierarchy traversal tests
class Mapping(object):
    def __init__(self,name):
        self.name = name

    def __call__(self,req):
        return "Called %s"%self.name
hierarchy_root = Mapping("root");
hierarchy_root.page1 = Mapping("page1")
hierarchy_root.page1.subpage1 = Mapping("subpage1")
hierarchy_root.page2 = Mapping("page2")

class Mapping2:
    pass
hierarchy_root_2 = Mapping2()
hierarchy_root_2.__call__ = index
hierarchy_root_2.page1 = index
hierarchy_root_2.page2 = index
