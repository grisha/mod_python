 #
 # Copyright 2004 Apache Software Foundation 
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

"""

  Writing Tests

  Writing mod_python tests can be a tricky task. This module
  attempts to lay out a framework for making the testing process
  consistent and quick to implement.

  All tests are based on Python Unit Test framework, it's a good
  idea to study the docs for the unittest module before going any
  further.

  To write a test, first decide in which of the 3 following categories
  it falls:

      o Simple tests that do not require any special server configuration
        and can be conducted along with other similar tests all in one
        request.

      o Per-Request tests. These tests require a whole separate request
        (or several requests) for a complete test.

      o Per-Instance tests. These require restarting the instance of
        http and running it in a particular way, perhaps with a special
        config to complete the test. An example might be load testing, or
        checking for memory leaks.

  There are two modules involved in testing - the one you're looking at
  now (test.py), which is responsible for setting up the http config
  running it and initiating requests, AND htdocs/tests.py (sorry for
  boring names), which is where all mod_python handlers reside.

  To write a Simple test:

     o Look at tests.SimpleTestCase class and the test methods in it,
       then write your own following the example.
       
     o Look at the tests.make_suite function, and make sure your test
       is added to the suite in there.

     o Keep in mind that the only way for Simple tests to communicate
       with the outside world is via the error log, do not be shy about
       writing to it.

   To write a Per-Request test:

   Most, if not all per-request tests require special server configuration
   as part of the fixture. To avoid having to restart the server with a
   different config (which would, btw, effectively turn this into a per-
   instance test), we separate configs by placing them in separate virtual
   hosts. This will become clearer if you follow the code.

     o Look at test.PerRequestCase class.

     o Note that for every test there are two methods defined: the test
       method itself, plus a method with the same name ending with
       "_conf". The _conf methods are supposed to return the virtual
       host config necessary for this test. As tests are instantiated,
       the configs are appended to a class variable (meaning its shared
       across all instances) appendConfig, then before the suite is run,
       the httpd config is built and httpd started. Each test will
       know to query its own virtual host. This way all tests can be
       conducted using a single instance of httpd.

     o Note how the _config methods generate the config - they use the
       httpdconf module to generate an object whose string representation
       is the config part, simlar to the way HTMLgen produces html. You
       do not have to do it this way, but it makes for cleaner code.

     o Every Per-Request test must also have a corresponding handler in
       the tests module. The convention is name everything based on the
       subject of the test, e.g. the test of req.document_root() will have
       a test method in PerRequestCase class called test_req_documet_root,
       a config method PerRequestCase.test_req_document_root_conf, the
       VirtualHost name will be test_req_document_root, and the handler
       in tests.py will be called req_document_root.

     o Note that you cannot use urllib if you have to specify a custom
       host: header, which is required for this whole thing to work.
       There is a convenience method, vhost_get, which takes the host
       name as the first argument, and optionally path as the second
       (though that is almost never needed). If vhost_get does not
       suffice, use httplib. Note the very useful skip_host=1 argument.

     o Remember to have your test added to the suite in
       PerInstanceTestCase.testPerRequestTests

  To write a Per-Instance test:

     o Look at test.PerInstanceTestCase class.

     o You have to start httpd in your test, but no need to stop it,
       it will be stopped for you in tearDown()

     o Add the test to the suite in test.suite() method

"""
import testconf
from httpdconf import *

import unittest
import commands
import urllib
import httplib
import os
import shutil
import time
import socket
import tempfile
import base64

HTTPD = testconf.HTTPD
TESTHOME = testconf.TESTHOME
MOD_PYTHON_SO = testconf.MOD_PYTHON_SO
LIBEXECDIR = testconf.LIBEXECDIR
AB = os.path.join(os.path.split(HTTPD)[0], "ab")

SERVER_ROOT = TESTHOME
CONFIG = os.path.join(TESTHOME, "conf", "test.conf")
DOCUMENT_ROOT = os.path.join(TESTHOME, "htdocs")
PORT = 0 # this is set in fundUnusedPort()


def findUnusedPort():

    # bind to port 0 which makes the OS find the next
    # unused port.

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    return port

def quoteIfSpace(s):

    # Windows doesn't like quotes when there are
    # no spaces, but needs them otherwise
    if s.find(" ") != -1:
        s = '"%s"' % s
    return s

class HttpdCtrl:
    # a mixin providing ways to control httpd

    def checkFiles(self):

        modules = os.path.join(SERVER_ROOT, "modules")
        if not os.path.exists(modules):
            os.mkdir(modules)

        logs = os.path.join(SERVER_ROOT, "logs")
        if os.path.exists(logs):
            shutil.rmtree(logs)
        os.mkdir(logs)

    def makeConfig(self, append=""):

        # create config files, etc

        print "  Creating config...."

        self.checkFiles()

        global PORT
        PORT = findUnusedPort()
        print "    listen port:", PORT

        # where other modules might be
        modpath = LIBEXECDIR

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
                                quoteIfSpace(os.path.join(modpath, "mod_mime.so")))),
            IfModule("!mod_log_config.c",
                     LoadModule("log_config_module %s" %
                                quoteIfSpace(os.path.join(modpath, "mod_log_config.so")))),
            IfModule("!mod_dir.c",
                     LoadModule("dir_module %s" %
                                quoteIfSpace(os.path.join(modpath, "mod_dir.so")))),
            ServerRoot(SERVER_ROOT),
            ErrorLog("logs/error_log"),
            LogLevel("debug"),
            LogFormat(r'"%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined'),
            CustomLog("logs/access_log combined"),
            # LockFile("logs/accept.lock"),
            TypesConfig("conf/mime.types"),
            PidFile("logs/httpd.pid"),
            ServerName("127.0.0.1"),
            Listen(PORT),
            PythonOption('PythonOptionTest sample_value'),
            DocumentRoot(DOCUMENT_ROOT),
            LoadModule("python_module %s" % MOD_PYTHON_SO),
            IfModule("!mod_auth.c",
                     LoadModule("auth_module %s" %
                                quoteIfSpace(os.path.join(modpath, "mod_auth.so")))))

        f = open(CONFIG, "w")
        f.write(str(s))
        f.write("\n# --APPENDED-- \n\n"+append)
        f.close()

    def startHttpd(self):

        print "  Starting Apache...."
        httpd = quoteIfSpace(HTTPD)
        config = quoteIfSpace(CONFIG)
        cmd = '%s -k start -f %s' % (httpd, config)
        print "    ", cmd
        os.system(cmd)
        time.sleep(1)
        self.httpd_running = 1

    def stopHttpd(self):

        print "  Stopping Apache..."
        httpd = quoteIfSpace(HTTPD)
        config = quoteIfSpace(CONFIG)
        cmd = '%s -k stop -f %s' % (httpd, config)
        print "    ", cmd
        os.system(cmd)
        time.sleep(1)
        self.httpd_running = 0

class PerRequestTestCase(unittest.TestCase):

    appendConfig = "\nNameVirtualHost *\n\n"

    def __init__(self, methodName="runTest"):
        unittest.TestCase.__init__(self, methodName)

        # add to config
        try:
            confMeth = getattr(self, methodName+"_conf")
            self.__class__.appendConfig += confMeth() + "\n"
        except AttributeError:
            pass

    def vhost_get(self, vhost, path="/tests.py"):
        # allows to specify a custom host: header

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", path, skip_host=1)
        conn.putheader("Host", "%s:%s" % (vhost, PORT))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        return rsp

    ### Tests begin here

    def test_req_document_root_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_document_root"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_document_root"),
                                  PythonDebug("On")))
        return str(c)


    def test_req_document_root(self):

        print "\n  * Testing req.document_root()"
        rsp = self.vhost_get("test_req_document_root")

        if rsp != DOCUMENT_ROOT.replace("\\", "/"):
            self.fail(`rsp`)

    def test_req_add_handler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_handler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_add_handler"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_add_handler(self):

        print "\n  * Testing req.add_handler()"
        rsp = self.vhost_get("test_req_add_handler")

        if (rsp != "test ok"):
            self.fail(`rsp`)

    def test_req_allow_methods_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_allow_methods"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_allow_methods"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_allow_methods(self):

        print "\n  * Testing req.allow_methods()"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_allow_methods", PORT))
        conn.endheaders()
        response = conn.getresponse()
        server_hdr = response.getheader("Allow", "")
        conn.close()

        self.failUnless(server_hdr.find("PYTHONIZE") > -1, "req.allow_methods() didn't work")

    def test_req_get_basic_auth_pw_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_get_basic_auth_pw"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  AuthName("blah"),
                                  AuthType("basic"),
                                  PythonAuthenHandler("tests::req_get_basic_auth_pw"),
                                  PythonHandler("tests::req_get_basic_auth_pw"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_get_basic_auth_pw(self):

        print "\n  * Testing req.get_basic_auth_pw()"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_get_basic_auth_pw", PORT))
        auth = base64.encodestring("spam:eggs").strip()
        conn.putheader("Authorization", "Basic %s" % auth)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

    def test_req_requires_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_requires"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  AuthName("blah"),
                                  AuthType("basic"),
                                  Require("valid-user"),
                                  PythonAuthenHandler("tests::req_requires"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_requires(self):

        print "\n  * Testing req.requires()"

        rsp = self.vhost_get("test_req_requires")

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_requires", PORT))
        auth = base64.encodestring("spam:eggs").strip()
        conn.putheader("Authorization", "Basic %s" % auth)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

    def test_req_internal_redirect_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_internal_redirect"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_internal_redirect | .py"),
                                  PythonHandler("tests::req_internal_redirect_int | .int"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_internal_redirect(self):

        print "\n  * Testing req.internal_redirect()"
        rsp = self.vhost_get("test_req_internal_redirect")

        if rsp != "test ok":
            self.fail("internal_redirect")

    def test_req_read_conf(self):

        c = str(Timeout("5")) + \
            str(VirtualHost("*",
                        ServerName("test_req_read"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_read"),
                                  PythonDebug("On"))))
        return c

    def test_req_read(self):

        print "\n  * Testing req.read()"

        params = '1234567890'*10000
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_read:%s" % PORT)
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != params):
            self.fail(`rsp`)

        print "    read/write ok, now lets try causing a timeout (should be 5 secs)"
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_read:%s" % PORT)
        conn.putheader("Content-Length", 10)
        conn.endheaders()
        conn.send("123456789")
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if rsp.find("IOError") < 0:
            self.fail("timeout test failed")


    def test_req_readline_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_readline"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_readline"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_readline(self):

        print "\n  * Testing req.readline()"

        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_readline:%s" % PORT)
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != params):
            self.fail(`rsp`)

    def test_req_readlines_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_readlines"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_readlines"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_readlines(self):

        print "\n  * Testing req.readlines()"

        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_readlines:%s" % PORT)
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != params):
            self.fail(`rsp`)

    def test_req_register_cleanup_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_register_cleanup"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_register_cleanup"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_register_cleanup(self):

        print "\n  * Testing req.register_cleanup()"

        rsp = self.vhost_get("test_req_register_cleanup")
        
        # see what's in the log now
        time.sleep(1)
        f = open(os.path.join(SERVER_ROOT, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("test ok") == -1:
            self.fail("Could not find test message in error_log")

    def test_req_headers_out_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_headers_out"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  AddHandler("mod_python .py"),
                                  DirectoryIndex("/tests.py"),
                                  PythonHandler("tests::req_headers_out"),
                                  PythonAccessHandler("tests::req_headers_out_access"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_headers_out(self):

        print "\n  * Testing req.headers_out"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/", skip_host=1)
        conn.putheader("Host", "test_req_headers_out:%s" % PORT)
        conn.endheaders()
        response = conn.getresponse()
        h = response.getheader("x-test-header", None)
        response.read()
        conn.close()

        if h is None:
            self.fail("Could not find x-test-header")

        if h != "test ok":
            self.fail("x-test-header is there, but does not contain 'test ok'")

    def test_req_sendfile_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_sendfile"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_sendfile"),
                                  PythonDebug("On")))

        return str(c)

    def test_req_sendfile(self):

        print "\n  * Testing req.sendfile()"

        rsp = self.vhost_get("test_req_sendfile")

        if (rsp != "test ok"):
            self.fail(`rsp`)

    def test_PythonOption_conf(self):

        c = VirtualHost("*",
                        ServerName("test_PythonOption"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::PythonOption_items"),
                                  PythonDebug("On")))

        return str(c)

    def test_PythonOption(self):

        print "\n  * Testing PythonOption"

        rsp = self.vhost_get("test_PythonOption")

        if (rsp != "[('PythonOptionTest', 'sample_value')]"):
            self.fail(`rsp`)

    def test_PythonOption_override_conf(self):

        c = VirtualHost("*",
                        ServerName("test_PythonOption_override"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::PythonOption_items"),
                                  PythonOption('PythonOptionTest "new_value"'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonDebug("On")))

        return str(c)

    def test_PythonOption_override(self):

        print "\n  * Testing PythonOption override"

        rsp = self.vhost_get("test_PythonOption_override")

        if (rsp != "[('PythonOptionTest', 'new_value'), ('PythonOptionTest2', 'new_value2')]"):
            self.fail(`rsp`)

    def test_PythonOption_remove_conf(self):

        c = VirtualHost("*",
                        ServerName("test_PythonOption_remove"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::PythonOption_items"),
                                  PythonOption('PythonOptionTest ""'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonDebug("On")))

        return str(c)

    def test_PythonOption_remove(self):

        print "\n  * Testing PythonOption remove"

        rsp = self.vhost_get("test_PythonOption_remove")

        if (rsp != "[('PythonOptionTest2', 'new_value2')]"):
            self.fail(`rsp`)

    def test_PythonOption_remove2_conf(self):

        c = VirtualHost("*",
                        ServerName("test_PythonOption_remove2"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::PythonOption_items"),
                                  PythonOption('PythonOptionTest'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonOption('PythonOptionTest3 new_value3'),
                                  PythonDebug("On")))

        return str(c)

    def test_PythonOption_remove2(self):

        print "\n  * Testing PythonOption remove2"

        rsp = self.vhost_get("test_PythonOption_remove2")

        if (rsp != "[('PythonOptionTest2', 'new_value2'), ('PythonOptionTest3', 'new_value3')]"):
            self.fail(`rsp`)

    def test_interpreter_per_directive_conf(self):

        c = VirtualHost("*",
                        ServerName("test_interpreter_per_directive"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  PythonInterpPerDirective('On'),
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::interpreter"),
                                  PythonDebug("On")))

        return str(c)

    def test_interpreter_per_directive(self):

        print "\n  * Testing interpreter per directive"

        interpreter_name = DOCUMENT_ROOT.replace('\\', '/')+'/'

        rsp = self.vhost_get("test_interpreter_per_directive")
        if (rsp != interpreter_name):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directive", '/subdir/foo.py')
        if (rsp != interpreter_name):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directive", '/subdir/')
        if (rsp != interpreter_name):
            self.fail(`rsp`)

    def test_interpreter_per_directory_conf(self):

        c = VirtualHost("*",
                        ServerName("test_interpreter_per_directory"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  PythonInterpPerDirectory('On'),
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::interpreter"),
                                  PythonDebug("On")),
                        )

        return str(c)

    def test_interpreter_per_directory(self):

        print "\n  * Testing interpreter per directory"

        interpreter_name = DOCUMENT_ROOT.replace('\\', '/')+'/'

        rsp = self.vhost_get("test_interpreter_per_directory")
        if (rsp != interpreter_name):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directory", '/subdir/foo.py')
        if (rsp != interpreter_name+'subdir/'):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directory", '/subdir/')
        if (rsp != interpreter_name+'subdir/'):
            self.fail(`rsp`)

    def test_util_fieldstorage_conf(self):

        c = VirtualHost("*",
                        ServerName("test_util_fieldstorage"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::util_fieldstorage"),
                                  PythonDebug("On")))
        return str(c)

    def test_util_fieldstorage(self):

        print "\n  * Testing util_fieldstorage()"

        params = urllib.urlencode([('spam', 1), ('spam', 2), ('eggs', 3), ('bacon', 4)])
        headers = {"Host": "test_util_fieldstorage",
                   "Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.request("POST", "/tests.py", params, headers)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "[Field('spam', '1'), Field('spam', '2'), Field('eggs', '3'), Field('bacon', '4')]"):
            self.fail(`rsp`)

    def test_postreadrequest_conf(self):

        c = VirtualHost("*",
                        ServerName("test_postreadrequest"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonPostReadRequestHandler("tests::postreadrequest"),
                        PythonDebug("On"))
        return str(c)

    def test_postreadrequest(self):

        print "\n  * Testing PostReadRequestHandler"
        rsp = self.vhost_get("test_postreadrequest")

        if (rsp != "test ok"):
            self.fail(`rsp`)
            
    def test_trans_conf(self):

        c = VirtualHost("*",
                        ServerName("test_trans"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonTransHandler("tests::trans"),
                        PythonDebug("On"))
        return str(c)

    def test_trans(self):

        print "\n  * Testing TransHandler"
        rsp = self.vhost_get("test_trans")

        if (rsp[3:5] != "=="): # first line in tests.py
            self.fail(`rsp`)
            
    def test_import_conf(self):

        # create a dummy module
        f = open(os.path.join(DOCUMENT_ROOT, "dummymodule.py"), "w")
        f.write("# nothing here")
        f.close()

        # configure apache to import it at startup
        c = Container(PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                      PythonImport("dummymodule test_import"),
                      VirtualHost("*",
                                  ServerName("test_import"),
                                  DocumentRoot(DOCUMENT_ROOT),
                                  Directory(DOCUMENT_ROOT,
                                            SetHandler("mod_python"),
                                            PythonHandler("tests::import_test"),
                                            PythonDebug("On"))))
        return str(c)

    def test_import(self):

        print "\n  * Testing PythonImport"
        rsp = self.vhost_get("test_import")

        if (rsp != "test ok"):
            self.fail(`rsp`)

    def test_outputfilter_conf(self):

        c = VirtualHost("*",
                        ServerName("test_outputfilter"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonHandler("tests::simplehandler"),
                        PythonOutputFilter("tests::outputfilter MP_TEST_FILTER"),
                        PythonDebug("On"),
                        AddOutputFilter("MP_TEST_FILTER .py"))
        return str(c)

    def test_outputfilter(self):

        print "\n  * Testing PythonOutputFilter"
        rsp = self.vhost_get("test_outputfilter")

        if (rsp != "TEST OK"):
            self.fail(`rsp`)

    def test_connectionhandler_conf(self):

        self.conport = findUnusedPort()
        c = str(Listen("%d" % self.conport)) + \
            str(VirtualHost("127.0.0.1:%d" % self.conport,
                            SetHandler("mod_python"),
                            PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                            PythonConnectionHandler("tests::connectionhandler")))
        return c

    def test_connectionhandler(self):

        print "\n  * Testing PythonConnectionHandler"

        url = "http://127.0.0.1:%s/tests.py" % self.conport
        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

    def test_internal_conf(self):

        c = VirtualHost("*",
                        ServerName("test_internal"),
                        ServerAdmin("serveradmin@somewhere.com"),
                        ErrorLog("logs/error_log"),
                        ServerPath("some/path"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests"),
                                  PythonOption("testing 123"),
                                  PythonDebug("On")))
        return str(c)

    def test_internal(self):

        print "\n  * Testing internally (status messages go to error_log)"

        rsp = self.vhost_get("test_internal")
        if (rsp[-7:] != "test ok"):
            self.fail("Some tests failed, see error_log")

    def test_pipe_ext_conf(self):

        c = VirtualHost("*",
                        ServerName("test_pipe_ext"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher | .py"),
                                  PythonHandler("tests::simplehandler"),
                                  PythonDebug("On")))
        return str(c)

    def test_pipe_ext(self):

        print "\n  * Testing | .ext syntax"

        rsp = self.vhost_get("test_pipe_ext", path="/tests.py/pipe_ext")
        if (rsp[-8:] != "pipe ext"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_pipe_ext", path="/tests/anything")
        if (rsp[-7:] != "test ok"):
            self.fail(`rsp`)
        
    def test_cgihandler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_cgihandler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.cgihandler"),
                                  PythonDebug("On")))
        return str(c)

    def test_cgihandler(self):

        print "\n  * Testing mod_python.cgihandler"

        rsp = self.vhost_get("test_cgihandler", path="/cgitest.py")

        if (rsp[-8:] != "test ok\n"):
            self.fail(`rsp`)

    def test_psphandler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_psphandler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.psp"),
                                  PythonDebug("On")))
        return str(c)

    def test_psphandler(self):

        print "\n  * Testing mod_python.psp"

        rsp = self.vhost_get("test_psphandler", path="/psptest.psp")
        if (rsp[-8:] != "test ok\n"):
            self.fail(`rsp`)

    def test_Cookie_Cookie_conf(self):

        c = VirtualHost("*",
                        ServerName("test_Cookie_Cookie"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::Cookie_Cookie"),
                                  PythonDebug("On")))
        return str(c)

    def test_Cookie_Cookie(self):

        print "\n  * Testing Cookie.Cookie"


        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        # this is three cookies, nastily formatted
        conn.putheader("Host", "test_Cookie_Cookie:%s" % PORT)
        conn.putheader("Cookie", "spam=foo; path=blah;;eggs=bar;")
        conn.putheader("Cookie", "bar=foo")
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != "test ok" or setcookie != 'path=blah, eggs=bar, bar=foo, spam=foo':
            print `rsp`
            print `setcookie`
            self.fail("cookie parsing failed")

    def test_Cookie_MarshalCookie_conf(self):

        c = VirtualHost("*",
                        ServerName("test_Cookie_MarshalCookie"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::Cookie_Cookie"),
                                  PythonDebug("On")))
        return str(c)

    def test_Cookie_MarshalCookie(self):

        print "\n  * Testing Cookie.MarshalCookie"

        mc = "eggs=d049b2b61adb6a1d895646719a3dc30bcwQAAABzcGFt"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        conn.putheader("Host", "test_Cookie_MarshalCookie:%s" % PORT)
        conn.putheader("Cookie", mc)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != "test ok" or setcookie != mc:
            print `rsp`
            self.fail("marshalled cookie parsing failed")

        # and now a long MarshalledCookie test !

        mc = ('test=859690207856ec75fc641a7566894e40c1QAAAB0'
             'aGlzIGlzIGEgdmVyeSBsb25nIHZhbHVlLCBsb25nIGxvb'
             'mcgbG9uZyBsb25nIGxvbmcgc28gbG9uZyBidXQgd2UnbG'
             'wgZmluaXNoIGl0IHNvb24=')

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        conn.putheader("Host", "test_Cookie_MarshalCookie:%s" % PORT)
        conn.putheader("Cookie", mc)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != "test ok" or setcookie != mc:
            print `rsp`
            self.fail("long marshalled cookie parsing failed")

    def test_Session_Session_conf(self):

        c = VirtualHost("*",
                        ServerName("test_Session_Session"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::Session_Session"),
                                  PythonDebug("On")))
        return str(c)

    def test_Session_Session(self):

        print "\n  * Testing Session.Session"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_Session_Session:%s" % PORT)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != "test ok" or setcookie == None:
            self.fail("session did not set a cookie")

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_Session_Session:%s" % PORT)
        conn.putheader("Cookie", setcookie)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if rsp != "test ok":
            self.fail("session did not accept our cookie")

    def test_publisher_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return str(c)
    
    def test_publisher(self):
        print "\n  * Testing mod_python.publisher"

        rsp = self.vhost_get("test_publisher", path="/tests.py")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher", path="/tests.py/index")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher", path="/tests.py/test_publisher")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher", path="/")
        if (rsp != "test 1 ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher", path="/foobar")
        if (rsp != "test 2 ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher", path="/tests")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(`rsp`)

    def test_publisher_security_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return str(c)
    
    def test_publisher_security(self):
        print "\n  * Testing mod_python.publisher security"

        def get_status(path):
            conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
            conn.putrequest("GET", path, skip_host=1)
            conn.putheader("Host", "test_publisher:%s" % PORT)
            conn.endheaders()
            response = conn.getresponse()
            status, response = response.status, response.read()
            conn.close()
            return status, response

        status, response = get_status("/tests.py/_SECRET_PASSWORD")
        if status != 403:
            self.fail('Vulnerability : underscore prefixed attribute (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/__ANSWER")
        if status != 403:
            self.fail('Vulnerability : underscore prefixed attribute (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/re")
        if status != 403:
            self.fail('Vulnerability : module published (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/OldStyleClassTest")
        if status != 403:
            self.fail('Vulnerability : old style class published (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/InstanceTest")
        if status != 403:
            self.fail('Vulnerability : new style class published (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/index/func_code")
        if status != 403:
            self.fail('Vulnerability : function traversal (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/old_instance/traverse/func_code")
        if status != 403:
            self.fail('Vulnerability : old-style method traversal (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/instance/traverse/func_code")
        if status != 403:
            self.fail('Vulnerability : new-style method traversal (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/test_dict/keys")
        if status != 403:
            self.fail('Vulnerability : built-in type traversal (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/test_dict_keys")
        if status != 403:
            self.fail('Vulnerability : built-in type publishing (%i)\n%s' % (status, response))

    def test_publisher_old_style_instance_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return str(c)
    
    def test_publisher_old_style_instance(self):
        print "\n  * Testing mod_python.publisher old-style instance publishing"

        rsp = self.vhost_get("test_publisher", path="/tests.py/old_instance")
        if (rsp != "test callable old-style instance ok"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher", path="/tests.py/old_instance/traverse")
        if (rsp != "test traversable old-style instance ok"):
            self.fail(`rsp`)

    def test_publisher_instance_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return str(c)
    
    def test_publisher_instance(self):
        print "\n  * Testing mod_python.publisher instance publishing"

        rsp = self.vhost_get("test_publisher", path="/tests.py/instance")
        if (rsp != "test callable instance ok"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher", path="/tests.py/instance/traverse")
        if (rsp != "test traversable instance ok"):
            self.fail(`rsp`)

class PerInstanceTestCase(unittest.TestCase, HttpdCtrl):
    # this is a test case which requires a complete
    # restart of httpd (e.g. we're using a fancy config)

    def tearDown(self):
        if self.httpd_running:
            self.stopHttpd()

    def testLoadModule(self):

        print "\n* Testing LoadModule"

        self.makeConfig()
        self.startHttpd()

        f = urllib.urlopen("http://127.0.0.1:%s/" % PORT)
        server_hdr = f.info()["Server"]
        f.close()
        self.failUnless(server_hdr.find("Python") > -1,
                        "%s does not appear to load, Server header does not contain Python"
                        % MOD_PYTHON_SO)
    def test_global_lock(self):

        print "\n  * Testing _global_lock"

        c = Directory(DOCUMENT_ROOT,
                      SetHandler("mod_python"),
                      PythonHandler("tests::global_lock"),
                      PythonDebug("On"))

        self.makeConfig(str(c))

        self.startHttpd()

        f = urllib.urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        rsp = f.read()
        f.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

        # if the mutex works, this test will take at least 5 secs
        t1 = time.time()
        print "    ", time.ctime()
        ab = quoteIfSpace(AB)
        if os.name == "nt":
            cmd = '%s -c 5 -n 5 http://127.0.0.1:%s/tests.py > null' \
                  % (ab, PORT)
        else:
            cmd = '%s -c 5 -n 5 http://127.0.0.1:%s/tests.py > /dev/null' \
                  % (ab, PORT)
        print "    ", cmd
        os.system(cmd)
        print "    ", time.ctime()
        t2 = time.time()
        if (t2 - t1) < 5:
            self.fail("global_lock is broken (too quick)")
         
    def testPerRequestTests(self):

        print "\n* Running the per-request test suite..."

        perRequestSuite = unittest.TestSuite()
        perRequestSuite.addTest(PerRequestTestCase("test_req_document_root"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_add_handler"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_allow_methods"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_get_basic_auth_pw"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_requires"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_internal_redirect"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_read"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_readline"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_readlines"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_register_cleanup"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_headers_out"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_sendfile"))
        perRequestSuite.addTest(PerRequestTestCase("test_PythonOption"))
        perRequestSuite.addTest(PerRequestTestCase("test_PythonOption_override"))
        perRequestSuite.addTest(PerRequestTestCase("test_PythonOption_remove"))
        perRequestSuite.addTest(PerRequestTestCase("test_PythonOption_remove2"))
        perRequestSuite.addTest(PerRequestTestCase("test_util_fieldstorage"))
        perRequestSuite.addTest(PerRequestTestCase("test_postreadrequest"))
        perRequestSuite.addTest(PerRequestTestCase("test_trans"))
        perRequestSuite.addTest(PerRequestTestCase("test_outputfilter"))
        perRequestSuite.addTest(PerRequestTestCase("test_connectionhandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_import"))
        perRequestSuite.addTest(PerRequestTestCase("test_pipe_ext"))
        perRequestSuite.addTest(PerRequestTestCase("test_cgihandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_psphandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_Cookie_Cookie"))
        perRequestSuite.addTest(PerRequestTestCase("test_Cookie_MarshalCookie"))
        perRequestSuite.addTest(PerRequestTestCase("test_Session_Session"))
        perRequestSuite.addTest(PerRequestTestCase("test_interpreter_per_directive"))
        perRequestSuite.addTest(PerRequestTestCase("test_interpreter_per_directory"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_old_style_instance"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_instance"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_security"))
        # this must be last so its error_log is not overwritten
        # perRequestSuite.addTest(PerRequestTestCase("test_internal"))

        self.makeConfig(PerRequestTestCase.appendConfig)
        self.startHttpd()

        tr = unittest.TextTestRunner()
        result = tr.run(perRequestSuite)

        self.failUnless(result.wasSuccessful())

    def test_srv_register_cleanup(self):

        print "\n* Testing server.register_cleanup()..."

        c = Directory(DOCUMENT_ROOT,
                      SetHandler("mod_python"),
                      PythonHandler("tests::srv_register_cleanup"),
                      PythonDebug("On"))

        self.makeConfig(str(c))

        self.startHttpd()

        f = urllib.urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        f.read()
        f.close()

        time.sleep(2)

        self.stopHttpd()

        # see what's in the log now
        time.sleep(2)
        f = open(os.path.join(SERVER_ROOT, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("test ok") == -1:
            self.fail("Could not find test message in error_log")

def suite():

    mpTestSuite = unittest.TestSuite()
    mpTestSuite.addTest(PerInstanceTestCase("testLoadModule"))
    mpTestSuite.addTest(PerInstanceTestCase("test_srv_register_cleanup"))
    # XXX comment out until ab is fixed, or we have another way
##     mpTestSuite.addTest(PerInstanceTestCase("test_global_lock"))
    mpTestSuite.addTest(PerInstanceTestCase("testPerRequestTests"))
    return mpTestSuite

tr = unittest.TextTestRunner()
tr.run(suite())

