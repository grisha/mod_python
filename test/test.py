 # ====================================================================
 # The Apache Software License, Version 1.1
 #
 # Copyright (c) 2000-2002 The Apache Software Foundation.  All rights
 # reserved.
 #
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions
 # are met:
 #
 # 1. Redistributions of source code must retain the above copyright
 #    notice, this list of conditions and the following disclaimer.
 #
 # 2. Redistributions in binary form must reproduce the above copyright
 #    notice, this list of conditions and the following disclaimer in
 #    the documentation and/or other materials provided with the
 #    distribution.
 #
 # 3. The end-user documentation included with the redistribution,
 #    if any, must include the following acknowledgment:
 #       "This product includes software developed by the
 #        Apache Software Foundation (http://www.apache.org/)."
 #    Alternately, this acknowledgment may appear in the software itself,
 #    if and wherever such third-party acknowledgments normally appear.
 #
 # 4. The names "Apache" and "Apache Software Foundation" must
 #    not be used to endorse or promote products derived from this
 #    software without prior written permission. For written
 #    permission, please contact apache@apache.org.
 #
 # 5. Products derived from this software may not be called "Apache",
 #    "mod_python", or "modpython", nor may these terms appear in their
 #    name, without prior written permission of the Apache Software
 #    Foundation.
 #
 # THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
 # WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 # OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 # DISCLAIMED.  IN NO EVENT SHALL THE APACHE SOFTWARE FOUNDATION OR
 # ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 # SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 # LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 # USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 # ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 # OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 # OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 # SUCH DAMAGE.
 # ====================================================================
 #
 # This software consists of voluntary contributions made by many
 # individuals on behalf of the Apache Software Foundation.  For more
 # information on the Apache Software Foundation, please see
 # <http://www.apache.org/>.
 #
 # $Id: test.py,v 1.22 2002/12/17 20:44:04 grisha Exp $
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

HTTPD = testconf.HTTPD
TESTHOME = testconf.TESTHOME
MOD_PYTHON_SO = testconf.MOD_PYTHON_SO

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
        modpath = os.path.split(os.path.split(HTTPD)[0])[0]
        modpath = os.path.join(modpath, "modules")

        s = Container(
            IfModule("prefork.c",
                     StartServers("1"),
                     MaxSpareServers("1")),
            IfModule("worker.c",
                     StartServers("1"),
                     MaxClients("1"),
                     MinSpareThreads("1"),
                     MaxSpareThreads("1"),
                     ThreadsPerChild("1"),
                     MaxRequestsPerChild("0")),
            IfModule("perchild.c",
                     NumServers("1"),
                     StartThreads("1"),
                     MaxSpareThreads("1"),
                     MaxThreadsPerChild("2")),
            IfModule("mpm_winnt.c",
                     ThreadsPerChild("3"),
                     MaxRequestsPerChild("0")),
            IfModule("!mod_mime.c",
                     LoadModule("mime_module %s" %
                                self.quoteIfSpace(os.path.join(modpath, "mod_mime.so")))),
            IfModule("!mod_log_config.c",
                     LoadModule("log_config_module %s" %
                                self.quoteIfSpace(os.path.join(modpath, "mod_log_config.so")))),
            ServerRoot(SERVER_ROOT),
            ErrorLog("logs/error_log"),
            LogLevel("debug"),
            LogFormat(r'"%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined'),
            CustomLog("logs/access_log combined"),
            TypesConfig("conf/mime.types"),
            PidFile("logs/httpd.pid"),
            ServerName("127.0.0.1"),
            Listen(PORT),
            DocumentRoot(DOCUMENT_ROOT),
            LoadModule("python_module %s" % MOD_PYTHON_SO))

        f = open(CONFIG, "w")
        f.write(str(s))
        f.write("\n# --APPENDED-- \n\n"+append)
        f.close()

    def quoteIfSpace(self, s):

        # Windows doesn't like quotes when there are
        # no spaces, but needs them otherwise
        if s.find(" ") != -1:
            s = '"%s"' % s
        return s

    def startHttpd(self):

        print "  Starting Apache...."
        httpd = self.quoteIfSpace(HTTPD)
        config = self.quoteIfSpace(CONFIG)
        cmd = '%s -k start -f %s' % (httpd, config)
        print "    ", cmd
        os.system(cmd)
        time.sleep(1)
        self.httpd_running = 1

    def stopHttpd(self):

        print "  Stopping Apache..."
        httpd = self.quoteIfSpace(HTTPD)
        config = self.quoteIfSpace(CONFIG)
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
                                  SetHandler("python-program"),
                                  PythonHandler("tests::req_document_root"),
                                  PythonDebug("On")))
        return str(c)


    def test_req_document_root(self):

        print "\n  * Testing req.document_root()"
        rsp = self.vhost_get("test_req_document_root")

        if rsp != DOCUMENT_ROOT.replace("\\", "/"):
            self.fail("test failed")

    def test_req_add_handler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_handler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("python-program"),
                                  PythonHandler("tests::req_add_handler"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_add_handler(self):

        print "\n  * Testing req.add_handler()"
        rsp = self.vhost_get("test_req_add_handler")

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_req_allow_methods_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_allow_methods"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("python-program"),
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
                                  SetHandler("python-program"),
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
        import base64
        auth = base64.encodestring("spam:eggs").strip()
        conn.putheader("Authorization", "Basic %s" % auth)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_req_internal_redirect_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_internal_redirect"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("python-program"),
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
                                  SetHandler("python-program"),
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
            self.fail("test failed")

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
                                  SetHandler("python-program"),
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
            self.fail("test failed")

    def test_req_readlines_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_readlines"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("python-program"),
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
            self.fail("test failed")

    def test_req_register_cleanup_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_register_cleanup"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("python-program"),
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

    def test_util_fieldstorage_conf(self):

        c = VirtualHost("*",
                        ServerName("test_util_fieldstorage"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("python-program"),
                                  PythonHandler("tests::util_fieldstorage"),
                                  PythonDebug("On")))
        return str(c)

    def test_util_fieldstorage(self):

        print "\n  * Testing util_fieldstorage()"

        params = urllib.urlencode([('spam',1),('spam',2),('eggs',3),('bacon',4)])
        headers = {"Host": "test_util_fieldstorage",
                   "Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PORT)
        conn.request("POST", "/tests.py", params, headers)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "[Field('spam', '1'), Field('spam', '2'), Field('eggs', '3'), Field('bacon', '4')]"):
            self.fail("test failed")

    def test_postreadrequest_conf(self):

        c = VirtualHost("*",
                        ServerName("test_postreadrequest"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("python-program"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonPostReadRequestHandler("tests::postreadrequest"),
                        PythonDebug("On"))
        return str(c)

    def test_postreadrequest(self):

        print "\n  * Testing PostReadRequestHandler"
        rsp = self.vhost_get("test_postreadrequest")

        if (rsp != "test ok"):
            self.fail("test failed")
            
    def test_trans_conf(self):

        c = VirtualHost("*",
                        ServerName("test_trans"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("python-program"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonTransHandler("tests::trans"),
                        PythonDebug("On"))
        return str(c)

    def test_trans(self):

        print "\n  * Testing TransHandler"
        rsp = self.vhost_get("test_trans")

        if (rsp[3:5] != "=="): # first line in tests.py
            self.fail("test failed")
            
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
                                            SetHandler("python-program"),
                                            PythonHandler("tests::import_test"),
                                            PythonDebug("On"))))
        return str(c)

    def test_import(self):

        print "\n  * Testing PythonImport"
        rsp = self.vhost_get("test_import")

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_outputfilter_conf(self):

        c = VirtualHost("*",
                        ServerName("test_outputfilter"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("python-program"),
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
            self.fail("test failed")

    def test_connectionhandler_conf(self):

        self.conport = findUnusedPort()
        c = str(Listen("%d" % self.conport)) + \
            str(VirtualHost("127.0.0.1:%d" % self.conport,
                            SetHandler("python-program"),
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
            self.fail("test failed")

    def test_internal_conf(self):

        c = VirtualHost("*",
                        ServerName("test_internal"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("python-program"),
                                  PythonHandler("tests"),
                                  PythonOption("testing 123"),
                                  PythonDebug("On")))
        return str(c)

    def test_internal(self):

        print "\n  * Testing internally"

        rsp = self.vhost_get("test_internal")
        if (rsp[-7:] != "test ok"):
            self.fail("Some tests failed, see error_log")

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


    def testPerRequestTests(self):

        print "\n* Running the per-request test suite..."

        perRequestSuite = unittest.TestSuite()
        perRequestSuite.addTest(PerRequestTestCase("test_req_document_root"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_add_handler"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_allow_methods"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_get_basic_auth_pw"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_internal_redirect"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_read"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_readline"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_readlines"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_register_cleanup"))
        perRequestSuite.addTest(PerRequestTestCase("test_util_fieldstorage"))
        perRequestSuite.addTest(PerRequestTestCase("test_postreadrequest"))
        perRequestSuite.addTest(PerRequestTestCase("test_trans"))
        perRequestSuite.addTest(PerRequestTestCase("test_outputfilter"))
        perRequestSuite.addTest(PerRequestTestCase("test_connectionhandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_import"))
        perRequestSuite.addTest(PerRequestTestCase("test_internal"))

        self.makeConfig(PerRequestTestCase.appendConfig)
        self.startHttpd()

        tr = unittest.TextTestRunner()
        result = tr.run(perRequestSuite)

        self.failUnless(result.wasSuccessful())

    def test_srv_register_cleanup(self):

        print "\n* Testing server.register_cleanup()..."

        c = Directory(DOCUMENT_ROOT,
                      SetHandler("python-program"),
                      PythonHandler("tests::srv_register_cleanup"),
                      PythonDebug("On"))

        self.makeConfig(str(c))

        self.startHttpd()

        f = urllib.urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        f.read()
        f.close()

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
    mpTestSuite.addTest(PerInstanceTestCase("testPerRequestTests"))
    mpTestSuite.addTest(PerInstanceTestCase("test_srv_register_cleanup"))
    return mpTestSuite

tr = unittest.TextTestRunner()
tr.run(suite())

