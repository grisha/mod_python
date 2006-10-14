 #
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
 #
 # $Id: index.py 379638 2006-02-22 00:41:51Z jgallacher $
 #

# mod_python tests

from mod_python import apache
import unittest
import re
import time
import os
import cStringIO

def index(req):
    return "test 1 ok, interpreter=%s" % req.interpreter

def foobar(req):
    return "test 2 ok, interpreter=%s" % req.interpreter
