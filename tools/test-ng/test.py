#!/usr/bin/env python

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


__version__ = "0.2.0"

import glob
import inspect
import os
import shutil
import socket
import sys
import time
import unittest

from optparse import OptionParser
import ConfigParser

import mptest
import mptest.testrunner
from mptest.httpdconf import *
import mptest.testconf
from mptest.util import quoteIfSpace, findUnusedPort
from mptest import testsetup



def dist_clean(path=None):
    """This is the same as make dist-clean in the old test framework."""

    if path is None:
        path = os.path.split(__file__)[0]

    shutil.rmtree(os.path.join(path, 'logs/'), ignore_errors=True)
    shutil.rmtree(os.path.join(path, 'tmp/'), ignore_errors=True)
    shutil.rmtree(os.path.join(path, 'modules/'), ignore_errors=True)

    for name in ['failure.log', 'conf/test.conf']:
        f = os.path.join(path, name)
        if os.path.exists(f):
            os.remove(f)

    
    for root, dirs, files in os.walk(path):
        # Don't visit any subversion subdirectories
        # This makes it safe to run dist_clean() in place
        # in a checked out svn copy.
        try:
            dirs.remove('.svn')
        except:
            pass

        for f in files:
            if f.endswith('.pyc'):
                os.remove(os.path.join(root, f))


def get_test_name(obj):
    return '%s.%s' % (obj.__module__.split('.',1)[1], obj.__name__)

def list_tests(args, verbose=0):
    test_list = []
    for t in testsetup.tests:
        name = get_test_name(t)

        if hasattr(t, 'disable') and t.disable == True:
            msg = '  ' + ' (DISABLED)'.rjust(64 -len(name)).replace(' ', '.')
        else:
            msg = ''

        if not args:
            test_list.append('%s%s' % (name,msg))
        else:
            for arg in args:
                if name.lower().startswith(arg.lower()):
                    test_list.append('%s%s' % (name,msg))

    test_list.sort()
    for t in test_list:
        print t

    # prepend the test count with a '#' character so the output of
    # this list can be used as the input of a new test run.
    print '#', len(test_list), 'tests found'

def list_test_groups(args=None, path='mptest/', verbose=0):
    """TODO - implement globbing"""
    exclude = ['__init__.py',]
    # get the test packages
    pkg_dirs = [d for d in os.listdir(path)
        if os.path.isdir(os.path.join(path,d)) 
        and not d.startswith('.svn')]

    if args:
        pkg_dirs = filter(lambda n: n in args, pkg_dirs)
    
    pkg_dirs.sort()
    count = 0
    for pkg in pkg_dirs:
        files = [ os.path.split(f)[1]
                    for f in glob.glob(os.path.join(path, pkg, '*.py')) ]
        files.sort()
        for f in [ os.path.splitext(f)[0] for f in files if f not in exclude ]:
            count += 1
            print '%s.%s' % (pkg,f)
    
    print "#", count, "test groups found"

def list_test_packages(args=None, path='mptest/', verbose=0):
    # TODO - implement globbing
    dirs = [d for d in os.listdir(path)
        if os.path.isdir(os.path.join(path,d)) 
        and not d.startswith('.svn')]

    if args:
        dirs = filter(lambda n: n in args  , dirs)
    
    dirs.sort()
    for d in dirs:
        print d

    print "#", len(dirs), "test groups found"

def add_test(args, options):
    # add_test can only handle one test at a time
    name = args[0]
    names = {}

    parts = name.split('.')
    print parts

    pkg,grp,cls = parts
    names['test_class'] = cls
    names['base_class'] = 'PerRequestTestBase'
    pkg_path = os.path.join('mptest', pkg)
    if not os.path.exists(pkg_path):
        os.mkdir(pkg_path)
        f = open(os.path.join(pkg_path, '__init__.py'), 'w')
        print >>f, '"""TEST PACKAGE DESCRIPTION DOCSTRING GOES HERE"""'
        f.close()
    
    module_file = os.path.join(pkg_path,'%s.py' % grp)
    if not os.path.exists(module_file):
        # FIXME - this should just copy a template file into the new module
        f = open(module_file, 'w')
        print >>f, '''"""TEST GROUP DESCRIPTION GOES HERE"""
        

from mptest.httpdconf import *
from mptest.testconf import * 
from mptest.testsetup import register, apache_version
from mptest.util import findUnusedPort
'''
      
        f.close()
   

    f = open(module_file, 'a+')
    print >>f, ''' 

class %(test_class)s(%(base_class)s):
    #handler = "override default handler here"
    #server_name = "override default server_name here"
    #document_root = "ovrride default document_root here"
    disable = False # set disable = True to disable this test

    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))

    def runTest(self):
        """%(test_class)s: SHORT DESCRIPTION OF FEATURE BEING TESTED"""

        print "\\n  * Testing", self.shortDescription()
        rsp = self.vhost_get(self.server_name)

        if rsp != 'test ok': 
            self.fail(`rsp`)

register(%(test_class)s)

''' % (names)
    
    # create the handler
    document_root = os.path.join('htdocs', pkg)
    if not os.path.exists(document_root):
        os.mkdir(document_root)
    module_file = os.path.join(document_root, '%s.py' % grp)
    if not os.path.exists(module_file):
        # FIXME - this should just copy a template file into the new module
        f = open(module_file, 'w')
        print >>f, '''"""DOCSTRING"""
        
from mod_python import apache 
'''
      
        f.close()
   

    f = open(module_file, 'a+')
    print >>f, '''

def handler_%(test_class)s(req):
    req.write('test ok')
    return apache.OK

''' % names

def get_httpd(search_path=None, apxs=None):
    # This needs to be integrated into or used by the HttpdControl class
    # TODO: pass in a search path paramter to restrict the search
    # TODO: pass in the value of --with-apxs to skip searching the path
    # completely
    
    httpd_list = []

    # apxs may be named apxs or apxs2
    apxs_names = ['apxs2', 'apxs']

    # build the search path
    if not search_path:
        if os.name == 'posix':
            path_env_sep = ':'
        
        elif os.name == 'nt':
            path_env_sep = ';'
        else:
            raise Exception, 'Unknown OS'
        search_path = os.environ['PATH'].split(path_env_sep)
    

    apxs_path = None

    # build a list of apxs candidates
    apxs_list = []
    if apxs:
        apxs_list.append(apxs)
    else:
        for p in search_path:
            for name in apxs_names:
                apxs = quoteIfSpace(os.path.join(p, name))
                if os.path.exists(apxs):
                    apxs_list.append(apxs)

    # get the httpd version
    for apxs in apxs_list:
        if not os.path.exists(apxs):
            print apxs, 'does not exist'
        else:
            (stdin,stdout) = os.popen2('%s -q TARGET' % apxs)
            httpd = stdout.readline().strip()
            
            (stdin,stdout) = os.popen2('%s -q SBINDIR' % apxs)
            sbindir = stdout.readline().strip()

            (stdin,stdout) = os.popen2('%s -q LIBEXECDIR' % apxs)
            libexecdir = stdout.readline().strip()

            httpd = os.path.join(sbindir, httpd)
            httpd = quoteIfSpace(httpd)

            cmd = '%s -v' % (httpd)
            (stdin,stdout) = os.popen2(cmd)
            for line in stdout:
                if line.startswith('Server version'):
                    version_str = line.strip()
                    break
            else:
                print "Can't find Apache 'Server version' string for ", httpd

            version_str = version_str.split('/')[1]
            version = [ int(p) for p in version_str.split('.',3) ]

            httpd_list.append([httpd, version, libexecdir, apxs])

    return httpd_list

class HttpdControl(object):

    def __init__(self, options, document_root='htdocs'):
        self._apxs = options.apxs_path  # path to the apxs binary
        self._httpd = None      # path to the httpd binary
        self._libexecdir = None # path to apache modules
        self._modpython_so = None # path to the mod_python.so module
        self._version = None    # the apache version

        # attrbutes used in the apache conf file
        self.test_home = os.getcwd()
        self.server_root = self.test_home
        self.document_root = os.path.join(self.test_home, document_root)
        self.config_file = os.path.join(self.test_home, 'conf', 'test.conf')
        self.error_log = 'logs/error_log'
        self.tmp_dir = os.path.join(self.test_home, 'tmp')
        self.port = 0
        self.httpd_running = 0

        self.legacy_importer_enabled = options.legacy_importer

        # rotate_count is used to keep track of log files for
        # log rotation
        self.rotate_count = 1

        self.tests = {} 
        self.checkFiles()

    def _get_apxs(self):
        if not self._apxs:

            # apxs may be named apxs or apxs2
            apxs_names = ['apxs2', 'apxs']
            if os.name == 'posix':
                path_env_sep = ':'
            
            elif os.name == 'nt':
                path_env_sep = ';'
            else:
                raise Exception, 'Unknown OS'
           
            path_parts = os.environ['PATH'].split(path_env_sep)

            apxs_path = None
            for p in path_parts:
                for name in apxs_names:
                    apxs_path = os.path.join(p, name)
                    if os.path.exists(apxs_path):
                        self._apxs = apxs_path
                        break
                else:
                    continue
                break

        # TODO - check if apxs was not found and raise an exception
        if self._apxs is None:
            raise Exception, "Can't find apxs or apxs2 on PATH - aborting\n  Try using 'test.py --with-apxs=/path/to/apxs'"

        elif not os.path.exists(self._apxs):
            raise Exception, """Can't find apxs "%s" - aborting""" % self._apxs
        
        return quoteIfSpace(self._apxs)

    def _set_apxs(self, value):
        self._apxs = value

    apxs = property(_get_apxs, _set_apxs) 

    def _get_httpd(self):
        if not self._httpd:
            (stdin,stdout) = os.popen2('%s -q TARGET' % self.apxs)
            httpd = stdout.readline().strip()
            
            (stdin,stdout) = os.popen2('%s -q SBINDIR' % self.apxs)
            path = stdout.readline().strip()

            httpd_path = os.path.join(path, httpd)
            self._httpd = httpd_path
        return quoteIfSpace(self._httpd)

    def _set_httpd(self, value):
        self._httpd = value
        # just in case this is a different http
        # we'll force the version to re-read
        # next time it's accessed
        self._version = None

    httpd = property(_get_httpd, _set_httpd)

    def _get_libexecdir(self):
        if not self._libexecdir:
            (stdin,stdout) = os.popen2('%s -q LIBEXECDIR' % self.apxs)
            self._libexecdir = stdout.readline().strip()

        return quoteIfSpace(self._libexecdir)

    def _set_libexecdir(self, value):
        self._libexecdir = value

    libexecdir = property(_get_libexecdir, _set_libexecdir)


    def _set_modpython_so(self, value):
        self._modpython_so = value

    def _get_modpython_so(self):
        if not self._modpython_so:
            self._modpython_so = os.path.join(self.libexecdir, 'mod_python.so')

        return quoteIfSpace(self._modpython_so)

    mod_python_so = property(_get_modpython_so, _set_modpython_so)

    def _get_version(self):
        if not self._version:
            httpd = quoteIfSpace(self.httpd)
            cmd = '%s -v' % (httpd)
            (stdin,stdout) = os.popen2(cmd)
            for line in stdout:
                if line.startswith('Server version'):
                    version_str = line.strip()
                    break
            else:
                # TODO - should raise an exception here
                pass

            version_str = version_str.split('/')[1]
            self._version = [ int(p) for p in version_str.split('.',3) ]

        return self._version

    version = property(_get_version)

    def start(self, extra=''):
        print "  Starting Apache...."
        cmd = '%s %s -k start -f %s' % (self.httpd, extra, self.config_file)
        print "    ", cmd
        os.system(cmd)
        time.sleep(1)
        self.httpd_running = 1

    def stop(self):
        print "  Stopping Apache..."
        cmd = '%s -k stop -f %s' % (self.httpd, self.config_file)
        print "    ", cmd
        os.system(cmd)
        time.sleep(1)

        # Wait for apache to stop by checking for the existence of pid the 
        # file. If pid file still exists after 20 seconds raise an error.
        # This check is here to facilitate testing on the qemu emulator.
        # Qemu will run about 1/10 the native speed, so 1 second may
        # not be long enough for apache to shut down.
        count = 0
        pid_file = os.path.join(self.test_home, 'logs/httpd.pid')
        while os.path.exists(pid_file):
            time.sleep(1)
            count += 1
            if count > 20:
                # give up - apache refuses to die - or died a horrible
                # death and never removed the pid_file.
                raise RuntimeError, "  Trouble stopping apache"

        self.httpd_running = 0

    def rotate_logs(self):
        # this code is adapted from python logging.RotatingFileHandler.doRollover()
        # TODO - FIXME
        log_files = ['access_log', 'error_log'] 

        if self.rotate_count > 0:
            for baseFilename in log_files:
                for i in range(self.rotate_count - 1, 0, -1):
                    sfn = os.path.join(self.test_home, 'logs', "%s.%d" % (baseFilename, i))
                    dfn = os.path.join(self.test_home, 'logs', "%s.%d" % (baseFilename, i + 1))
                    if os.path.exists(sfn):
                        #print "%s -> %s" % (sfn, dfn)
                        if os.path.exists(dfn):
                            os.remove(dfn)
                        os.rename(sfn, dfn)
                dfn =  os.path.join(self.test_home, 'logs', baseFilename + ".1")
                if os.path.exists(dfn):
                    os.remove(dfn)
                try:
                    os.rename(os.path.join(self.test_home, 'logs', baseFilename), dfn)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    print 'oops'
                    #self.handleError(record)
                    raise
        self.rotate_count += 1

    def checkFiles(self):
        modules = os.path.join(self.server_root, "modules")
        if not os.path.exists(modules):
            os.mkdir(modules)
        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)

    def clean(self):
        self.clean_logs()
        self.clean_tmp()

    def clean_logs(self):
        logs = os.path.join(self.server_root, "logs")
        if os.path.exists(logs):
            shutil.rmtree(logs)
        os.mkdir(logs)

    def clean_tmp(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
        os.mkdir(self.tmp_dir)


    def makeConfig(self, append=""):

        # create config files, etc

        print "  Creating config...."

        self.checkFiles()

        self.port = findUnusedPort()
        print "    listen port:", self.port

        s = Container(
            IfModule("prefork.c",
                     StartServers("3"),
                     MaxSpareServers("1")),
            IfModule("worker.c",
                     StartServers("2"),
                     MaxClients("6"),
                     MinSpareThreads("1"),
                     MaxSpareThreads("1"),
                     ThreadsPerChild("3"),
                     MaxRequestsPerChild("0")),
            IfModule("perchild.c",
                     NumServers("2"),
                     StartThreads("2"),
                     MaxSpareThreads("1"),
                     MaxThreadsPerChild("2")),
            IfModule("mpm_winnt.c",
                     ThreadsPerChild("5"),
                     MaxRequestsPerChild("0")),
            IfModule("!mod_mime.c",
                     LoadModule("mime_module %s" %
                                quoteIfSpace(os.path.join(self.libexecdir, "mod_mime.so")))),
            IfModule("!mod_log_config.c",
                     LoadModule("log_config_module %s" %
                                quoteIfSpace(os.path.join(self.libexecdir, "mod_log_config.so")))),
            IfModule("!mod_dir.c",
                     LoadModule("dir_module %s" %
                                quoteIfSpace(os.path.join(self.libexecdir, "mod_dir.so")))),
            IfModule("!mod_include.c",
                     LoadModule("include_module %s" %
                                quoteIfSpace(os.path.join(self.libexecdir, "mod_include.so")))),
            ServerRoot(self.server_root),
            ErrorLog(self.error_log),
            LogLevel("debug"),
            LogFormat(r'"%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined'),
            CustomLog("logs/access_log combined"),
            LockFile("logs/accept.lock"),
            TypesConfig("conf/mime.types"),
            PidFile("logs/httpd.pid"),
            ServerName("127.0.0.1"),
            Listen(self.port),
            PythonOption('mod_python.mutex_directory %s' % self.tmp_dir),
            PythonOption('PythonOptionTest sample_value'),
            PythonOption('mod_python.legacy.importer *', self.legacy_importer_enabled),
            DocumentRoot(self.document_root),
            LoadModule("python_module %s" % quoteIfSpace(self.mod_python_so)))

        if self.version[0] == 2 and self.version[1] == 2:
            # mod_auth has been split into mod_auth_basic and some other modules
            s.append(IfModule("!mod_auth_basic.c",
                     LoadModule("auth_basic_module %s" %
                                quoteIfSpace(os.path.join(self.libexecdir, "mod_auth_basic.so")))))

            # Default KeepAliveTimeout is 5 for apache 2.2, but 15 in apache 2.0
            # Explicitly set the value so it's the same as 2.0
            s.append(KeepAliveTimeout("15"))
        else:
            s.append(IfModule("!mod_auth.c",
                     LoadModule("auth_module %s" %
                                quoteIfSpace(os.path.join(self.libexecdir, "mod_auth.so")))))

        s.append("\n# --APPENDED-- \n\n" + str(append))

        f = open(self.config_file, "w")
        f.write(str(s))
        f.close()
        self.config_exists = True
        
    def appendConfig(self, append):
        append = str(append)
        if not self.config_exists:
            self.makeConfig(append)
        else:
            f = open(self.config_file, "a+")
            f.write(str(append))
            f.close()

    def deleteConfig(self):
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        self.config_exists = False



def run_tests(options, args=None):
    server_tests = []
    vhost_tests = []


    for obj in testsetup.tests:
        grp,module = obj.__module__.split('.')[1:]
        name = '%s.%s.%s' % (grp, module, obj.__name__)
        if hasattr(obj, 'disable') and obj.disable == True \
                    and not options.force:
            if options.verbose or options.debug:
                print 'skipping', name, '(DISABLED)' 
                
            continue
        
        include_test = False
        # TODO - need to do proper filtering of names
        for arg in args:
            if name.startswith(arg):
                include_test = True
                if options.verbose or options.debug:
                    print 'including', name
                break
        if include_test:
            if issubclass(obj, (mptest.testconf.PerInstanceTestBase)):
                server_tests.append(obj)
            else:
                vhost_tests.append(obj)
                

    tr = mptest.testrunner.TextTestRunner()

    # run the server tests first
    # each test gets a new httpd instance
    for obj in server_tests:
        document_root = 'htdocs/%s' % obj.__module__.split('.')[1]
        httpd = HttpdControl(options, document_root=document_root)
        httpd.clean()
        httpd.makeConfig()
        t = obj(httpd=httpd, document_root=httpd.document_root)
        httpd.appendConfig(t.config())
        tr.run(t)

    # run the virtual host tests
    # All tests use the same httpd instance

    if vhost_tests:
        httpd = HttpdControl(options)
        httpd.clean()
        httpd.makeConfig()
        httpd.appendConfig("\nNameVirtualHost *\n\n")
        suite = unittest.TestSuite()
        for obj in vhost_tests:
            t = obj(httpd=httpd)
            t.config_file = httpd.appendConfig(t.config())
            suite.addTest(t)
        tr.run(suite)

    # print the final report
    test_results = tr.report()

    # make sure httpd is stopped
    httpd.stop()

   
    # Dump logs and test.conf for failed tests
    # FIXME - This really should be written to a file rather
    # than stdout.
    failure_log = []

    for tc,tb in test_results.failures:
        name = '%s.%s' % (tc.__module__,tc.__class__.__name__)
        failure_log.append('%s FAIL' % (name))
        if options.debug:
            print '=' * 50
            print 'FAIL', name
            print '=' * 50
            print "TEST CONF"
            print '-' * 50
            print tc.config_archive
            print '-' * 50
            print "ERROR LOG"
            print '-' * 50
            print tc.log_archive
        
    for tc,tb in test_results.errors:
        name = '%s.%s' % (tc.__module__,tc.__class__.__name__)
        failure_log.append('%s ERR' % (name))
        if options.debug:
            print '=' * 50
            print 'ERROR', name
            print '=' * 50
            print tc.log_start
            print '-' * 50
            print "TEST CONF"
            print '-' * 50
            print tc.config_archive
            print '-' * 50
            print "ERROR LOG"
            print '-' * 50
            print tc.log_archive

    failure_filename = 'failures.txt'    
    if os.path.exists(failure_filename):
        os.remove(failure_filename)
        if failure_log:
            failure_log.sort()
            fout = open(failure_filename, 'w')
            fout.write('\n'.join(failure_log))
            fout.write('\n')
            fout.close()

def main():
    usage = """usage: %prog [options] [tests]
   
    When [tests] are omitted the default behaviour is to run all the tests
    in the core package. This is equivalent to running "python test.py"
    in the old test framework.

    You can specify test packages, test groups or individual tests cases or
    use globbing to select the tests to run.

    

    Test Names
        TODO - Some of this should go in the README instead as it
        contains information on writing tests rather than using them.

        Test names are case insensitive..

        The format of a test name is:
            <test_package>.<test_group>.<test_case>
        where
            test_package:
                corresponds to a subdirectory of mptest/.
            
            test_group:
                corresponds to a *.py module file in directory 
                mptest/test_group/.  The test_group directory must contain
                a __init__.py file for the tests to be properly registered.
            
            test_case:
                corresponds to a test class in the test_group module file.
                The test_case must regisiter itself in order to be found
                by the test system.

                eg.
                from mptest.testset import register
                
                class MyTestCase(object): pass

                register(MyTestCase)
                
            

    Examples

        Run all tests in the core package
        $ python test.py core

        Run all tests in the leaktests package
        $ python test.py leaktests

        Run all tests the core.session get package 
        $ python test.py core.session

        Specify individual tests
        $ python test.py core.session.tests.foo core.session.BadSid

        Specify tests in 2 different test groups
        $ python test.py core.session core.publisher
 
        Specify tests using globbing
        $ python test.py core.publisher.auth*
        would run any test cases starting with "auth".
        Note that test.py --list always assumes test_name.*

        At this time only test_name* globbing is supported. If there is demand
        for it full globbing or regex match can be added in the future.

        Also be aware that you may get unexpected results if 
        test_name_frament* matches any files or directories in the current
        working directory, due to shell file globbing. To avoid this you can
        put your test name pattern. eg.

        $ python test.py "con*"
       
    """
    parser = OptionParser(usage=usage, version="%s" % __version__)
   
    # no config file handling just yet.
    # parser.add_option("-c", "--config", dest="config_file",
                      # metavar="FILE",
                      # help="Configuration file")

    parser.add_option("-a", "--add",
                      action="store_true", dest="add_test", default=False,
                      help="Add a new test package, test group or test case. "
                      "NOT IMPLEMENTED")

    parser.add_option("--clean",
                      action="store_true", dest="cleanup", default=False,
                      help="Removes conf/test.conf, logs/*, tmp/ "
                      "and *.pyc files and the exits. "
                      "This corresponds to 'make dist-clean' in "
                      "the old test framework.")

    parser.add_option("-f", "--force",
                      action="store_true", dest="force", default=False,
                      help="Force disable tests to run.")

    parser.add_option("-i", "--in-file", 
                      dest="tests_file", default=None,
                      metavar="FILE",
                      help="Run tests listed in FILE. "
                      "These tests will be added to the command line arguments.")

    parser.add_option("-k", "--keep",
                      action="store_true", dest="keep", default=False,
                      help="Keep a copy of test.conf and logs for later "
                           "analysis. NOT IMPLEMENTED.")

    parser.add_option("-l", "--list-tests",
                      action="store_true", dest="list_test_cases", default=False,
                      help="List test modules."
                           "")

    parser.add_option("-p", "--list-packages",
                      action="store_true", dest="list_test_packages", default=False,
                      help="List test packages."
                           "")

    parser.add_option("-g", "--list-groups",
                      action="store_true", dest="list_test_groups", default=False,
                      help="List test groups."
                           "")

    parser.add_option("-v", "--verbose", 
                      action="count", dest="verbose", default=0,
                      help="Increase verbosity. "\
                           "You can specify -v up to 3 times to get a greater"
                           "level of detail. Using -v -v -v will cause the http"
                           "response to be printed to stderr. The most verbose"
                           "setting could result in a large amount of output "
                           "and should likely be used in conjuction with -n 1.")

    parser.add_option("--with-apxs",
                      dest="apxs_path", type="string", default=None,
                      metavar="FILE",
                      help="Specify an alternative path to apxs. "
                           "By default test.py will attempt to locate apxs2 "
                           "or apxs in the current PATH. "
                           "--with-apxs allows you to override this.")

    parser.add_option("--with-legacy-importer",
                      action="store_true", dest="legacy_importer", default=False,
                      help="Enable the legacy importer.")


    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Output debugging messages.")

    parser.add_option("--find-httpd",
                      action="store_true", dest="thing", default=False,
                      help="Searches the PATH for apxs and exits."
                      "prints a list of [httpd_path, httpd_version, libexecdir, apxs_path)")



    (options, args) = parser.parse_args()

    # end of cmd line parsing


    if options.cleanup:
        dist_clean()
        sys.exit(0)

    testsetup.debug = options.debug


    if options.thing:
        rs = get_httpd()
        for r in rs:
            print r
        
        sys.exit(0)

    # test modules may need the apache version
    # to decide if they are going to register themselves
    testsetup.apache_version = HttpdControl(options).version
    testsetup.load_tests()

    if options.add_test:
        if not args:
            print 'Usage: test.py -a <test_package>.<test_group>.<test_case>' 
            sys.exit(0)
        add_test(args, options)
        sys.exit(0)

    if options.list_test_packages:
        list_test_packages(args,verbose=options.verbose)
        sys.exit(0)

    if options.list_test_groups:
        list_test_groups(args,verbose=options.verbose)
        sys.exit(0)

    if options.list_test_cases:
        list_tests(args, verbose=options.verbose)
        sys.exit(0)
        
    if options.tests_file:
        # include tests list in file
        # lines starting with # will be ignored
        # testnames must not include whitespace
        if not os.path.exists(options.tests_file):
            print "No such file: '%s'" % options.tests_file
            sys.exit(0)

        test_list = open(options.tests_file, 'r').readlines()
        test_list = [ line.strip().split(' ')[0]
                        for line in test_list 
                        if not line.startswith('#') ] 

        args = args + test_list


    if not args:
        # run the default tests
        # this is the same as the old test framework
        args = ['core', ]
    run_tests(options, args)

if __name__ == '__main__':
    main()
