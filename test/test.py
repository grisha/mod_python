
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

    def startApache(self):

        print "  Starting Apache...."
        print commands.getoutput("rm -f %s/logs/*log" % PARAMS["server_root"])
        cmd = '%s -f %s' % (HTTPD, PARAMS["config"])
        print "  ", cmd
        print commands.getoutput(cmd)

    def tearDown(self):

        print "  Stopping Apache..."
        pid = commands.getoutput("cat %s/logs/httpd.pid" % PARAMS["server_root"])
        commands.getoutput("kill "+pid)

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
              "  PythonOption secret sauce\n" + \
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

    def test_req_get_config(self):

        print "\n* Testing req.get_config() and get_options()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_get_config\n" + \
              "  PythonDebug On\n" + \
              "  PythonOption secret sauce\n" + \
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

    def test_req_get_remote_host(self):

        print "\n* Testing req.get_remote_host()"

        cfg = "<Directory %s/htdocs>\n" % PARAMS["server_root"]+ \
              "  SetHandler python-program\n" + \
              "  PythonHandler tests::req_get_remote_host\n" + \
              "  PythonDebug On\n" + \
              "</Directory>\n" + \
              "HostNameLookups Off\n"

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
              "  PythonOutputFilter tests::outputfilter myfilter\n" + \
              "  PythonDebug On\n" + \
              "  AddOutputFilter myfilter .py\n"

        self.makeConfig(cfg)
        self.startApache()

        url = "http://127.0.0.1:%s/tests.py" % PARAMS["port"]
        print "    url: "+url

        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()
        print "    response: ", rsp


        import time
        time.sleep(2)
        
        if (rsp != "test ok"):
            self.fail("test failed")

def findUnusedPort():

    # bind to port 0 which makes the OS find the next
    # unused port.

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    return port

def suite():

    mpTestSuite = unittest.TestSuite()
#    mpTestSuite.addTest(ModPythonTestCase("testLoadModule"))
#    mpTestSuite.addTest(ModPythonTestCase("test_apache_log_error"))
#    mpTestSuite.addTest(ModPythonTestCase("test_apache_table"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_add_common_vars"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_add_handler"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_allow_methods"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_document_root"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_get_basic_auth_pw"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_get_config"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_get_remote_host"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_read"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_readline"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_readlines"))
#    mpTestSuite.addTest(ModPythonTestCase("test_req_register_cleanup"))
#    mpTestSuite.addTest(ModPythonTestCase("test_util_fieldstorage"))
#    mpTestSuite.addTest(ModPythonTestCase("test_postreadrequest"))
    mpTestSuite.addTest(ModPythonTestCase("test_outputfilter"))
    return mpTestSuite

tr = unittest.TextTestRunner()
tr.run(suite())

