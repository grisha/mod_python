
import testconf

HTTPD = testconf.HTTPD
TESTHOME = testconf.TESTHOME
PARAMS = {
    "server_root": TESTHOME,
    "config": TESTHOME + "/conf/test.conf",
    "config_tmpl": TESTHOME + "/conf/test.conf.tmpl",
    "document_root": TESTHOME + "/htdocs",
    "mod_python_so": TESTHOME + "/modules/mod_python.so",
    "port": "", # this is set in fundUnusedPort()
    }

import unittest
import commands
import urllib


# need to incorporate the gdb into the testing process....
# httpd needs to be invoked under gdb [make optional], and
# the url fetching should be forked.
# what's the deal with gdb's being different?


def findUnusedPort():

    # bind to port 0 which makes the OS find the next
    # unused port.

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    return port

class ModPythonTestCase(unittest.TestCase):

    def __init__(self, methodName="runTest", configPart=""):
        unittest.TestCase.__init__(self, methodName)
        self.configPart = configPart

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

    def makeGdbFile(file):
        f = open(file, "w")
        f.write("run -f %s -X" % PARAMS("config"))
        f.close()

    def startApache(self):

        print "  Starting Apache...."
        print commands.getoutput("rm -f %s/logs/*log" % PARAMS["server_root"])
        cmd = '%s -f %s' % (HTTPD, PARAMS["config"])
        print "  ", cmd
        print commands.getoutput(cmd)
        self.apache_running = 1

    def stopApache(self):
        print "  Stopping Apache..."
        pid = commands.getoutput("cat %s/logs/httpd.pid" % PARAMS["server_root"])
        commands.getoutput("kill "+pid)
        self.apache_running = 0

    def tearDown(self):
        if self.apache_running:
            self.stopApache()

    def testLoadModule(self):

        print "\n* Testing LoadModule"

        self.makeConfig()
        self.startApache()

        f = urllib.urlopen("http://127.0.0.1:%s/" % PARAMS["port"])
        server_hdr = f.info()["Server"]
        f.close()
        self.failUnless(server_hdr.find("Python") > -1,
                        "%s does not appear to load, Server header does not contain Python"
                        % PARAMS["mod_python_so"])

    def test_apache_log_error(self):

        print "\n* Testing apache.log_error()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::apache_log_error\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        print "    response: "+f.read()
        f.close()

        # see what's in the log now
        f = open("%s/logs/error_log" % PARAMS["server_root"])
        log = f.read()
        f.close()
        if log.find("This is a test message") == -1:
            self.fail("Could not find test message in error_log")

    def test_apache_table(self):

        print "\n* Testing apache.table()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::apache_table\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: "+rsp

        if (rsp != "test ok"):
            self.fail("table test failed")

    def test_req_add_common_vars(self):

        print "\n* Testing req.add_common_vars()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_add_common_vars\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: "+rsp

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_req_add_handler(self):

        print "\n* Testing req.add_handler()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_add_handler\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: "+rsp

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_req_allow_methods(self):

        print "\n* Testing req.allow_methods()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_allow_methods\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        server_hdr = f.info()["Allow"]
        f.close()
        self.failUnless(server_hdr.find("PYTHONIZE") > -1, "req.allow_methods() didn't work")

    def test_req_get_basic_auth_pw(self):

        print "\n* Testing req.get_basic_auth_pw()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  AuthType basic\n" + \
              "  require valid-user\n" + \
              "  AuthName restricted\n" + \
              "  PythonAuthenHandler tests::req_get_basic_auth_pw\n" + \
              "  PythonHandler tests::req_get_basic_auth_pw\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://spam:eggs@127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: "+rsp

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_req_document_root(self):

        print "\n* Testing req.document_root()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_document_root\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: "+rsp

        if (rsp != PARAMS["document_root"]):
            self.fail("test failed")

    def test_req_internal_redirect(self):

        print "\n* Testing req.internal_redirect()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_internal_redirect | .py\n" + \
              "  PythonHandler tests::req_internal_redirect_int | .int\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "response: ", rsp
        
        if rsp != "test ok":
            self.fail("internal_redirect")

    def test_req_read(self):

        print "\n* Testing req.read()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_read\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n" + \
              "Timeout 10\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        import httplib
        params = '1234567890'*10000
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("POST", "/tests.py")
        conn.putheader("Host", "127.0.0.1:%s" % PARAMS["port"])
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != params):
            self.fail("test failed")

        print "    read/write ok, now lets try causing a timeout (should be 10 secs)"
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("POST", "/tests.py")
        conn.putheader("Host", "127.0.0.1:%s" % PARAMS["port"])
        conn.putheader("Content-Length", 10)
        conn.endheaders()
        conn.send("123456789")
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if rsp.find("IOError") < 0:
            self.fail("timeout test failed")

    def test_req_readline(self):

        print "\n* Testing req.readline()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_readline\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n" + \
              "Timeout 10\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        import httplib
        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("POST", "/tests.py")
        conn.putheader("Host", "127.0.0.1:%s" % PARAMS["port"])
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != params):
            self.fail("test failed")

    def test_req_readlines(self):

        print "\n* Testing req.readlines()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_readlines\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n" + \
              "Timeout 10\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        import httplib
        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.putrequest("POST", "/tests.py")
        conn.putheader("Host", "127.0.0.1:%s" % PARAMS["port"])
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != params):
            self.fail("test failed")

    def test_req_register_cleanup(self):

        print "\n* Testing req.register_cleanup()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_register_cleanup\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url
        
        f = urllib.urlopen(url)
        print "    response: "+f.read()
        f.close()
        import time
        time.sleep(1)
        
        # see what's in the log now
        f = open("%s/logs/error_log" % PARAMS["server_root"])
        log = f.read()
        f.close()
        if log.find("test ok") == -1:
            self.fail("Could not find test message in error_log")

    def test_util_fieldstorage(self):

        print "\n* Testing util_fieldstorage()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::util_fieldstorage\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        import httplib

        params = urllib.urlencode([('spam',1),('spam',2),('eggs',3),('bacon',4)])
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        conn = httplib.HTTPConnection("127.0.0.1:%s" % PARAMS["port"])
        conn.request("POST", "/tests.py", params, headers)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response: ", rsp
        if (rsp != "[Field('spam', '1'), Field('spam', '2'), Field('eggs', '3'), Field('bacon', '4')]"):
            self.fail("test failed")

    def test_postreadrequest(self):

        print "\n* Testing PostReadRequestHandler"

        cfg = "  SetHandler python-program\n" + \
              "  PythonPath ['%s']+sys.path\n" % PARAMS["document_root"] + \
              "  PythonPostReadRequestHandler tests::postreadrequest\n" + \
              "  PythonDebug On\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: "

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_outputfilter(self):

        print "\n* Testing PythonOutputFilter"

        cfg = "  SetHandler python-program\n" + \
              "  PythonPath ['%s']+sys.path\n" % PARAMS["document_root"] + \
              "  PythonHandler tests::simplehandler\n" + \
              "  PythonOutputFilter tests::outputfilter MP_TEST_FILTER\n" + \
              "  PythonDebug On\n" + \
              "  AddOutputFilter MP_TEST_FILTER .py\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: ", rsp

        if (rsp != "TEST OK"):
            self.fail("test failed")

    def test_connectionhandler(self):

        print "\n* Testing PythonConnectionHandler"

        cfg = "  SetHandler python-program\n" + \
              "  PythonPath ['%s']+sys.path\n" % PARAMS["document_root"] + \
              "  PythonConnectionHandler tests::connectionhandler\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: ", rsp

        if (rsp != "test ok"):
            self.fail("test failed")

    def test_internal(self):

        print "\n* Testing internally"

        cfg = "  SetHandler python-program\n" + \
              "  PythonPath ['%s']+sys.path\n" % PARAMS["document_root"] + \
              "  PythonHandler tests\n" + \
              "  PythonOption testing 123\n" + \
              "  PythonDebug On\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: ", rsp

        if (rsp[-7:] != "test ok"):
            self.fail("Some tests failed, see error_log")

def suite():

    mpTestSuite = unittest.TestSuite()
    mpTestSuite.addTest(ModPythonTestCase("testLoadModule"))
    mpTestSuite.addTest(ModPythonTestCase("test_internal"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_add_handler"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_allow_methods"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_document_root"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_get_basic_auth_pw"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_internal_redirect"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_read"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_readline"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_readlines"))
    mpTestSuite.addTest(ModPythonTestCase("test_req_register_cleanup"))
    mpTestSuite.addTest(ModPythonTestCase("test_util_fieldstorage"))
    mpTestSuite.addTest(ModPythonTestCase("test_postreadrequest"))
    mpTestSuite.addTest(ModPythonTestCase("test_outputfilter"))
    mpTestSuite.addTest(ModPythonTestCase("test_connectionhandler"))
    return mpTestSuite

tr = unittest.TextTestRunner()
tr.run(suite())

