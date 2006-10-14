"""Session unit tests go here"""

import httplib
import shutil

from mptest.testsetup import register
from mptest.testconf import * 
from mptest.httpdconf import *

class SessionSessionTest(PerRequestTestBase):
    handler = "session::Session_Session"

    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonOption('session_directory "%s"' % self.httpd.tmp_dir),
                                  PythonOption('ApplicationPath "/path"'),
                                  PythonOption('mod_python.session.application_domain "test_Session_Session"'),
                                  PythonDebug("On")))

    def runTest(self):
        """SessionTest: Session.Session(self)"""

        print "\n  * Testing", self.shortDescription()

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/session.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % (self.server_name, self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != "test ok" or setcookie == None:
            self.fail("session did not set a cookie")

        parts = setcookie.split('; ')
        fields = {}
        for part in parts:
          key, value = part.split('=')
          fields[key] = value

        if not fields.has_key('path') or fields['path'] != '/path':
            self.fail("session did not contain expected 'path'")

        if not fields.has_key('domain') or fields['domain'] != 'test_Session_Session':
            self.fail("session did not contain expected 'domain'")

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/session.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % (self.server_name, self.httpd.port))
        conn.putheader("Cookie", setcookie)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()
        if rsp != "test ok":
            self.fail("session did not accept our cookie")

    def tearDown(self):
        super(PerRequestTestBase, self).tearDown()
        try:
            os.remove(os.path.join(self.httpd.tmp_dir, 'mp_sess.dbm'))
        except:
            pass

register(SessionSessionTest)


class FileSessionTest(PerRequestTestBase):
    """Tests FileSession created by Session.Session with the
    session class name passed as a PythonOption
    """
    handler = "session::Session_Session"

    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonOption('session FileSession'),
                                  PythonOption('session_directory "%s"' % self.httpd.tmp_dir),
                                  PythonOption('mod_python.session.application_domain "test_Session_FileSession"'),
                                  PythonOption('ApplicationPath "/path"'),
                                  PythonDebug("On")))

    def runTest(self):
        """FileSessionTest: Session(req) using PythonOption session FileSession"""

        print "\n  * Testing", self.shortDescription()

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/session.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % (self.server_name, self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != "test ok" or setcookie == None:
            self.fail("session did not set a cookie")

        parts = setcookie.split('; ')
        fields = {}
        for part in parts:
          key, value = part.split('=')
          fields[key] = value

        if not fields.has_key('path') or fields['path'] != '/path':
            self.fail("session did not contain expected 'path'")

        if not fields.has_key('domain') or fields['domain'] != 'test_Session_FileSession':
            self.fail("session did not contain expected 'domain'")

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/session.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % (self.server_name, self.httpd.port))
        conn.putheader("Cookie", setcookie)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()
        if rsp != "test ok":
            self.fail("session did not accept our cookie")

        if not os.path.exists(os.path.join(self.httpd.tmp_dir, 'mp_sess')):
            self.fail("FileSession directory not properly set")

    def tearDown(self):
        super(PerRequestTestBase, self).tearDown()
        shutil.rmtree(os.path.join(self.httpd.tmp_dir, 'mp_sess'), ignore_errors=True)

register(FileSessionTest)


class SessionIllegalSidTest(PerRequestTestBase):
    handler = "tests::Session_Session"

    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                        SetHandler("mod_python"),
                        PythonHandler(self.handler),
                        PythonOption('session_directory "%s"' % self.httpd.tmp_dir),
                        PythonDebug("On")))

    def runTest(self):
        """SessionIllegalSidTest: session with illegal session id value"""

        print "\n  * Testing", self.shortDescription()
        bad_cookie = 'pysid=/path/traversal/attack/bad; path=/'
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/session.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % (self.server_name, self.httpd.port))
        conn.putheader("Cookie", bad_cookie)
        conn.endheaders()
        response = conn.getresponse()
        status = response.status
        conn.close()
        if status != 500:
            self.fail("session accepted a sid with illegal characters")

        bad_cookie = 'pysid=%s; path=/' % ('abcdef'*64)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/session.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % (self.server_name, self.httpd.port))
        conn.putheader("Cookie", bad_cookie)
        conn.endheaders()
        response = conn.getresponse()
        status = response.status
        conn.close()
        if status != 500:
            self.fail("session accepted a sid which is too long")

    def tearDown(self):
        super(PerRequestTestBase, self).tearDown()
        try:
            os.remove(os.path.join(self.httpd.tmp_dir, 'mp_sess.dbm'))
        except:
            pass

register(SessionIllegalSidTest)
