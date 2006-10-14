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

"""testsetup provides facilities for registering new tests with the framework.
Test class should register themselves by calling

testsetup.register(YourTestClass)
"""


import os

tests = [] 
failed_tests = []
debug = False

exclude = ['__init__.py',]

        
def load_tests(path=None, root='mptest'):
    if path is None:
        path = os.path.split(__file__)[0]

    package_names = [ d for d in os.listdir(path)
                if os.path.isdir(os.path.join(path,d))
                and not d.startswith('.') ]


    for pkg_name in package_names:
        module_path = os.path.join(path, pkg_name)
        for module_file in filter(
                    lambda n: n[-3:]=='.py' and n not in exclude,
                    os.listdir(module_path)):

            f, e = os.path.splitext(module_file)
            if debug:
                print 'loading tests in %s.%s' % (pkg_name, f)
            __import__('%s.%s.%s' % (root,pkg_name,f), globals(), locals(), [])



def register(obj):
    if debug:
        node = '%s.%s' % (obj.__module__.split('.', 1)[1], obj.__name__)
        print '  registered', node
    tests.append(obj)


def log_failure(obj):
    failed_tests.append(obj)
