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
 # $Id: test.py,v 1.12 2002/10/08 21:38:54 grisha Exp $
 #
 
import testconf
from httpdconf import *

import unittest
import commands
import urllib
import httplib
import os
import time

HTTPD = testconf.HTTPD
TESTHOME = testconf.TESTHOME
PARAMS = {
    "server_root": TESTHOME,
    "config": os.path.join(TESTHOME, "conf", "test.conf"),
    "config_tmpl": os.path.join(TESTHOME, "conf", "test.conf.tmpl"),
    "document_root": os.path.join(TESTHOME, "htdocs"),
    "mod_python_so": os.path.join(TESTHOME, "modules", "mod_python.so"),
    "port": "", # this is set in fundUnusedPort()
    }

def findUnusedPort(port=[54321]):

    # bind to port 0 which makes the OS find the next
    # unused port.

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
    except ImportError:
        # try without socket. this uses a python "static" trick,
        # a mutable default value for a keyword argument is defined
        # with the method, see section 7.5 of Python Ref. Manual.
        port += 1

    return port

class HttpdCtrl:
    # a mixin providing ways to control httpd

    def makeConfig(self, append=""):

        # create config files, etc

        print "  Creating config...."

        f = open(PARAMS["config_tmpl"])
        tmpl = f.read()
        f.close()

        PARAMS["port"] = findUnusedPort()
        print "    listen port:", PARAMS["port"]

        f = open(PARAMS["config"], "w")
        f.write(tmpl % PARAMS)
        f.write("\n# --APPENDED-- \n\n"+append)
        f.close()

    def startHttpd(self):

        print "  Starting Apache...."
        commands.getoutput("rm -f %s/logs/*log" % PARAMS["server_root"])
        cmd = '%s -k start -f %s' % (HTTPD, PARAMS["config"])
        print "    ", cmd
        commands.getoutput(cmd)
        self.httpd_running = 1

    def stopHttpd(self):

        print "  Stopping Apache..."
        cmd = '%s -k stop -f %s' % (HTTPD, PARAMS["config"]) 
        print "    ", cmd
        commands.getoutput(cmd)
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

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("GET", path, skip_host=1)
        conn.putheader("Host", "%s:%s" % (vhost, PARAMS["port"]))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        return rsp

    def test_req_document_root_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_document_root"),
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
                                  SetHandler("python-program"),
                                  PythonHandler("tests::req_document_root"),
                                  PythonDebug("On")))
        return str(c)


    def test_req_document_root(self):

        print "\n  * Testing req.document_root()"
        rsp = self.vhost_get("test_req_document_root")

        if (rsp != PARAMS["document_root"]):
            self.fail("test failed")

    def test_req_add_handler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_handler"),
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
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
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
                                  SetHandler("python-program"),
                                  PythonHandler("tests::req_allow_methods"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_allow_methods(self):

        print "\n  * Testing req.allow_methods()"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_allow_methods", PARAMS["port"]))
        conn.endheaders()
        response = conn.getresponse()
        server_hdr = response.getheader("Allow", "")
        conn.close()

        self.failUnless(server_hdr.find("PYTHONIZE") > -1, "req.allow_methods() didn't work")

    def test_req_get_basic_auth_pw_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_get_basic_auth_pw"),
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
                                  SetHandler("python-program"),
                                  AuthName("blah"),
                                  AuthType("basic"),
                                  require("valid-user"),
                                  PythonAuthenHandler("tests::req_get_basic_auth_pw"),
                                  PythonHandler("tests::req_get_basic_auth_pw"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_get_basic_auth_pw(self):

        print "\n  * Testing req.get_basic_auth_pw()"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_get_basic_auth_pw", PARAMS["port"]))
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
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
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
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
                                  SetHandler("python-program"),
                                  PythonHandler("tests::req_read"),
                                  PythonDebug("On"))))
        return c

    def test_req_read(self):

        print "\n  * Testing req.read()"

        params = '1234567890'*10000
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_read:%s" % PARAMS["port"])
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
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_read:%s" % PARAMS["port"])
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
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
                                  SetHandler("python-program"),
                                  PythonHandler("tests::req_readline"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_readline(self):

        print "\n  * Testing req.readline()"

        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_readline:%s" % PARAMS["port"])
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
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
                                  SetHandler("python-program"),
                                  PythonHandler("tests::req_readlines"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_readlines(self):

        print "\n  * Testing req.readlines()"

        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_readlines:%s" % PARAMS["port"])
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
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
                                  SetHandler("python-program"),
                                  PythonHandler("tests::req_register_cleanup"),
                                  PythonDebug("On")))
        return str(c)

    def test_req_register_cleanup(self):

        print "\n  * Testing req.register_cleanup()"

        rsp = self.vhost_get("test_req_register_cleanup")
        
        # see what's in the log now
        time.sleep(1)
        f = open("%s/logs/error_log" % PARAMS["server_root"])
        log = f.read()
        f.close()
        if log.find("test ok") == -1:
            self.fail("Could not find test message in error_log")

    def test_util_fieldstorage_conf(self):

        c = VirtualHost("*",
                        ServerName("test_util_fieldstorage"),
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
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
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.request("POST", "/tests.py", params, headers)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "[Field('spam', '1'), Field('spam', '2'), Field('eggs', '3'), Field('bacon', '4')]"):
            self.fail("test failed")

    def test_postreadrequest_conf(self):

        c = VirtualHost("*",
                        ServerName("test_postreadrequest"),
                        DocumentRoot(PARAMS["document_root"]),
                        SetHandler("python-program"),
                        PythonPath("['%s']+sys.path" % PARAMS["document_root"]),
                        PythonHandler("tests::postreadrequest"),
                        PythonDebug("On"))
        return str(c)

    def test_postreadrequest(self):

        print "\n  * Testing PostReadRequestHandler"
        rsp = self.vhost_get("test_postreadrequest")

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_outputfilter_conf(self):

        c = VirtualHost("*",
                        ServerName("test_outputfilter"),
                        DocumentRoot(PARAMS["document_root"]),
                        SetHandler("python-program"),
                        PythonPath("['%s']+sys.path" % PARAMS["document_root"]),
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
                            PythonPath("['%s']+sys.path" % PARAMS["document_root"]),
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
                        DocumentRoot(PARAMS["document_root"]),
                        Directory(PARAMS["document_root"],
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

        f = urllib.urlopen("http://127.0.0.1:%s/" % PARAMS["port"])
        server_hdr = f.info()["Server"]
        f.close()
        self.failUnless(server_hdr.find("Python") > -1,
                        "%s does not appear to load, Server header does not contain Python"
                        % PARAMS["mod_python_so"])


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
        perRequestSuite.addTest(PerRequestTestCase("test_outputfilter"))
        perRequestSuite.addTest(PerRequestTestCase("test_connectionhandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_internal"))

        self.makeConfig(PerRequestTestCase.appendConfig)
        self.startHttpd()

        tr = unittest.TextTestRunner()
        result = tr.run(perRequestSuite)

        self.failUnless(result.wasSuccessful())


def suite():

    mpTestSuite = unittest.TestSuite()
    mpTestSuite.addTest(PerInstanceTestCase("testLoadModule"))
    mpTestSuite.addTest(PerInstanceTestCase("testPerRequestTests"))
    return mpTestSuite

tr = unittest.TextTestRunner()
tr.run(suite())

