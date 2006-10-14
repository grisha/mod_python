import base64
import os


from mptest.httpdconf import *
from mptest.testconf import * 
from mptest.testsetup import register
from mptest.util import findUnusedPort


class DocumentRootTest(PerRequestTestBase):
    handler = "request::req_document_root"
    server_name = "test_req_document_root"

    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))

    def runTest(self):
        """DocumentRootTest: req.document_root()"""

        print "\n  * Testing req.document_root()"
        rsp = self.vhost_get("test_req_document_root")

        if rsp.upper() != self.document_root.replace("\\", "/").upper():
            self.fail(`rsp`)
register(DocumentRootTest)


class AddHandlerTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_add_handler"
    handler = "request::req_add_handler"
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))

    def runTest(self):
        """AddHandler: req.add_handler()"""

        print "\n  * Testing req.add_handler()"
        rsp = self.vhost_get(self.server_name)

        if (rsp != 2*"test ok"):
            self.fail(`rsp`)
register(AddHandlerTest)


class AddBadHandlerTest(PerRequestTestBase):
    """Adding a non-existent handler with req.add_handler should
    raise an exception.
    """

    server_name = "test_req_add_bad_handler"
    handler = "request::req_add_bad_handler"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))

    def runTest(self):
        """AddBadHandlerTest: req_add_bad_handler"""

        print """\n  * Testing req.add_handler("PythonHandler", "bad_handler")"""
        rsp = self.vhost_get(self.server_name)

        # look for evidence of the exception in the error log 
        time.sleep(1)
        f = open(os.path.join(self.httpd.server_root, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("contains no 'bad_handler'") == -1:
            self.fail("""Could not find "contains no 'bad_handler'" in error_log""")
register(AddBadHandlerTest)


class AddEmptyHandlerStringTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_add_empty_handler_string"
    handler = "request::req_add_empty_handler_string"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """AddEmptyHandlerStringTest: req_add_empty_handler_string"""
        # Adding an empty string as the handler in req.add_handler
        # should raise an exception

        print """\n  * Testing req.add_handler("PythonHandler","")"""
        rsp = self.vhost_get("test_req_add_empty_handler_string")

        if (rsp == "no exception"):
            self.fail("Expected an exception")

register(AddEmptyHandlerStringTest)



class AddHandlerEmptyPhaseTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_add_handler_empty_phase"
    handler = "request::req_add_handler_empty_phase"

    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonInterpPerDirective("On"),
                                  PythonFixupHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """AddHandlerEmptyPhaseTest: req_add_handler_empty_phase"""
        # Adding handler to content phase when no handler already
        # exists for that phase.

        print """\n  * Testing req.add_handler() for empty phase"""
        rsp = self.vhost_get("test_req_add_handler_empty_phase")

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(AddHandlerEmptyPhaseTest)



class AddHandlerEmptyPhaseTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_add_handler_empty_phase"
    handler = "request::req_add_handler_empty_phase"

    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonInterpPerDirective("On"),
                                  PythonFixupHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """AddHandlerEmptyPhaseTest: req_add_handler_empty_phase"""
        # Adding handler to content phase when no handler already
        # exists for that phase.

        print """\n  * Testing req.add_handler() for empty phase"""
        rsp = self.vhost_get("test_req_add_handler_empty_phase")

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(AddHandlerEmptyPhaseTest)


class AddHandlerDirectoryTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_add_handler_directory"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonInterpPerDirective("On"),
                                  PythonFixupHandler("request::test_req_add_handler_directory"),
                                  PythonDebug("On")))

    def runTest(self):
        """AddHandlerDirectoryTest: req_add_handler_directory"""
        # Checking that directory is canonicalized and trailing
        # slash is added.

        print """\n  * Testing req.add_handler() directory"""
        rsp = self.vhost_get("test_req_add_handler_directory")

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(AddHandlerDirectoryTest)



class AccesshandlerAddHandlerToEmptyHlTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_accesshandler_add_handler_to_empty_hl"
    
    def config(self):
        # Note that there is no PythonHandler specified in the the VirtualHost
        # config. We want to see if req.add_handler will work when the 
        # handler list is empty.

        #PythonHandler("request::req_add_empty_handler_string"),
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonAccessHandler("request::accesshandler_add_handler_to_empty_hl"),
                                  PythonDebug("On")))


    def runTest(self):
        """AccesshandlerAddHandlerToEmptyHlTest: accesshandler_add_handler_to_empty_hl"""

        print """\n  * Testing req.add_handler() when handler list is empty"""
        rsp = self.vhost_get("test_accesshandler_add_handler_to_empty_hl")

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(AccesshandlerAddHandlerToEmptyHlTest)


class AllowMethodsTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_allow_methods"
    handler = "request::req_allow_methods"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """AllowMethodsTest: req_allow_methods"""

        print "\n  * Testing req.allow_methods()"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/request.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_allow_methods", self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        server_hdr = response.getheader("Allow", "")
        conn.close()

        self.failUnless(server_hdr.find("PYTHONIZE") > -1, "req.allow_methods() didn't work")

register(AllowMethodsTest)


class GetBasicAuthPwTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_get_basic_auth_pw"
    handler = "request::req_get_basic_auth_pw"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  AuthName("blah"),
                                  AuthType("basic"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """GetBasicAuthPwTest: req_get_basic_auth_pw"""

        print "\n  * Testing req.get_basic_auth_pw()"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/request.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_get_basic_auth_pw", self.httpd.port))
        auth = base64.encodestring("spam:eggs").strip()
        conn.putheader("Authorization", "Basic %s" % auth)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(GetBasicAuthPwTest)


class AuthTypeTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_auth_type"
    handler = "request::req_auth_type"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  AuthName("blah"),
                                  AuthType("dummy"),
                                  Require("valid-user"),
                                  PythonAuthenHandler("request::req_auth_type"),
                                  PythonAuthzHandler("request::req_auth_type"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """AuthTypeTest: req_auth_type"""

        print "\n  * Testing req.auth_type()"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/request.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_auth_type", self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(AuthTypeTest)


class RequiresTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_requires"
    
    def config(self):

        return VirtualHost("*",
                    ServerName(self.server_name),
                    DocumentRoot(self.document_root),
                    Directory(self.document_root,
                              SetHandler("mod_python"),
                              AuthName("blah"),
                              AuthType("dummy"),
                              Require("valid-user"),
                              PythonAuthenHandler("request::req_requires"),
                              PythonDebug("On")))



    def runTest(self):
        """RequiresTest: req_requires"""

        print "\n  * Testing req.requires()"

        rsp = self.vhost_get("test_req_requires")

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/request.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_requires", self.httpd.port))
        auth = base64.encodestring("spam:eggs").strip()
        conn.putheader("Authorization", "Basic %s" % auth)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(RequiresTest)


class InternalRedirectTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_internal_redirect"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler("request::req_internal_redirect | .py"),
                                  PythonHandler("request::req_internal_redirect_int | .int"),
                                  PythonDebug("On")))


    def runTest(self):
        """InternalRedirectTest: req.internal_redirect()"""

        print "\n  * Testing %s" % self.runTest.__doc__

        rsp = self.vhost_get("test_req_internal_redirect")

        if rsp != "test ok":
            self.fail("internal_redirect")

register(InternalRedirectTest)


class ConstructUrlTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_construct_url"
    handler = "request::req_construct_url"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """ConstructUrlTest: req.construct_url()"""

        print "\n  * Testing", self.shortDescription()
        rsp = self.vhost_get("test_req_construct_url")

        if rsp != "test ok":
            self.fail("construct_url")

register(ConstructUrlTest)


class ReadTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_read"
    handler = "request::req_read"
    
    def config(self):

        return str(Timeout("5")) + \
            str(VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On"))))

    def runTest(self):
        """ReadTest: req_read"""

        print "\n  * Testing req.read()"

        params = '1234567890'*10000
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("POST", "/request.py", skip_host=1)
        conn.putheader("Host", "test_req_read:%s" % self.httpd.port)
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
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("POST", "/request.py", skip_host=1)
        conn.putheader("Host", "test_req_read:%s" % self.httpd.port)
        conn.putheader("Content-Length", 10)
        conn.endheaders()
        conn.send("123456789")
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if rsp.find("IOError") < 0:
            self.fail("timeout test failed")


register(ReadTest)

class ReadlineTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_readline"
    handler = "request::req_readline"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """ReadlineTest: req_readline"""

        print "\n  * Testing req.readline()"

        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("POST", "/request.py", skip_host=1)
        conn.putheader("Host", "test_req_readline:%s" % self.httpd.port)
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != params):
            self.fail(`rsp`)

register(ReadlineTest)


class ReadlinesTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_readlines"
    handler = "request::req_readlines"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """ReadlinesTest: req_readlines"""

        print "\n  * Testing req.readlines()"

        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("POST", "/request.py", skip_host=1)
        conn.putheader("Host", "test_req_readlines:%s" % self.httpd.port)
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != params):
            self.fail(`rsp`)

        print "\n  * Testing req.readlines(size_hint=30000)"

        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("POST", "/request.py", skip_host=1)
        conn.putheader("Host", "test_req_readlines:%s" % self.httpd.port)
        conn.putheader("Content-Length", len(params))
        conn.putheader("SizeHint", 30000)
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != ('1234567890'*3000+'\n')):
            self.fail(`rsp`)

        print "\n  * Testing req.readlines(size_hint=32000)"

        params = ('1234567890'*3000+'\n')*4
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("POST", "/request.py", skip_host=1)
        conn.putheader("Host", "test_req_readlines:%s" % self.httpd.port)
        conn.putheader("Content-Length", len(params))
        conn.putheader("SizeHint", 32000)
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print "    response size: %d\n" % len(rsp)
        if (rsp != (('1234567890'*3000+'\n')*2)):
            self.fail(`rsp`)

register(ReadlinesTest)


class DiscardRequestBodyTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_discard_request_body"
    handler = "request::req_discard_request_body"
    
    def config(self):

        return str(Timeout("5")) + \
            str(VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On"))))

    def runTest(self):
        """DiscardRequestBodyTest: req_discard_request_body"""

        print "\n  * Testing req.discard_request_body()"

        params = '1234567890'*2
        print "    writing %d bytes..." % len(params)
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/request.py", skip_host=1)
        conn.putheader("Host", "test_req_discard_request_body:%s" % self.httpd.port)
        conn.putheader("Content-Length", len(params))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(DiscardRequestBodyTest)


class RegisterCleanupTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_register_cleanup"
    handler = "request::req_register_cleanup"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """RegisterCleanupTest: req_register_cleanup"""

        print "\n  * Testing req.register_cleanup()"

        rsp = self.vhost_get("test_req_register_cleanup")
        
        # see what's in the log now
        time.sleep(1)
        f = open(os.path.join(self.httpd.server_root, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("req_register_cleanup test ok") == -1:
            self.fail("Could not find test message in error_log")

register(RegisterCleanupTest)


class HeadersOutTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_headers_out"
    handler = "request::req_headers_out"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """HeadersOutTest: req_headers_out"""

        print "\n  * Testing req.headers_out"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/test.py", skip_host=1)
        conn.putheader("Host", "test_req_headers_out:%s" % self.httpd.port)
        conn.endheaders()
        response = conn.getresponse()
        h = response.getheader("x-test-header", None)
        response.read()
        conn.close()

        if h is None:
            self.fail("Could not find x-test-header")

        if h != "test ok":
            self.fail("x-test-header is there, but does not contain 'test ok'")

register(HeadersOutTest)


class SendfileTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_sendfile"
    handler = "request::req_sendfile"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """SendfileTest: req_sendfile"""

        print "\n  * Testing req.sendfile() with offset and length"

        rsp = self.vhost_get("test_req_sendfile")

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(SendfileTest)


class Sendfile2Test(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_sendfile2"
    handler = "request::req_sendfile2"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """Sendfile2Test: req_sendfile2"""

        print "\n  * Testing req.sendfile() without offset and length"

        rsp = self.vhost_get("test_req_sendfile2")

        if (rsp != "0123456789"*100):
            self.fail(`rsp`)

register(Sendfile2Test)


class Sendfile3Test(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_sendfile3"
    handler = "request::req_sendfile3"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """Sendfile3Test: req_sendfile3"""

        if os.name == 'posix':

            print "\n  * Testing req.sendfile() for a file which is a symbolic link"

            rsp = self.vhost_get("test_req_sendfile3")

            if (rsp != "0123456789"*100):
                self.fail(`rsp`)
        else:
            print "\n  * Skipping req.sendfile() for a file which is a symbolic link"

register(Sendfile3Test)


class HandlerTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_handler"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  PythonFixupHandler("request::req_handler"),
                                  PythonDebug("On")))


    def runTest(self):
        """HandlerTest: req_handler"""

        print "\n  * Testing req.handler"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_handler", self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(HandlerTest)


class NoCacheTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_no_cache"
    handler = "request::req_no_cache"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """NoCacheTest: req_no_cache"""

        print "\n  * Testing req.no_cache"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/request.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_no_cache", self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if response.getheader("expires", None) is None:
            self.fail(`response.getheader("expires", None)`)

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(NoCacheTest)


class UpdateMtimeTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_update_mtime"
    handler = "request::req_update_mtime"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """UpdateMtimeTest: req_update_mtime"""

        print "\n  * Testing req.update_mtime"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/request.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_update_mtime", self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if response.getheader("etag", None) is None:
            self.fail(`response.getheader("etag", None)`)

        if response.getheader("last-modified", None) is None:
            self.fail(`response.getheader("last-modified", None)`)

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(UpdateMtimeTest)


class UtilRedirectTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_util_redirect"
    handler = "request::util_redirect"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  PythonFixupHandler("request::util_redirect"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """UtilRedirectTest: util_redirect"""

        print "\n  * Testing util.redirect()"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_util_redirect", self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if response.status != 302:
            self.fail('did not receive 302 status response')

        if response.getheader("location", None) != "/dummy":
            self.fail('did not receive correct location for redirection')
        
        if rsp != "test ok":
            self.fail(`rsp`)

register(UtilRedirectTest)


class ServerGetConfigTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_server_get_config"
    handler = "request::req_server_get_config"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        PythonDebug("On"),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("Off")))


    def runTest(self):
        """ServerGetConfigTest: req_server_get_config"""

        print "\n  * Testing req.server.get_config()"

        rsp = self.vhost_get("test_req_server_get_config")
        if (rsp != "test ok"):
            self.fail(`rsp`)

register(ServerGetConfigTest)


class ServerGetOptionsTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_server_get_options"
    handler = "request::req_server_get_options"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        PythonDebug("Off"),
                        PythonOption("global 1"),
                        PythonOption("override 1"),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonOption("local 1"),
                                  PythonOption("override 2"),
                                  PythonDebug("On")))


    def runTest(self):
        """ServerGetOptionsTest: req_server_get_options"""

        print "\n  * Testing req.server.get_options()"

        rsp = self.vhost_get("test_req_server_get_options")
        if (rsp != "test ok"):
            self.fail(`rsp`)

register(ServerGetOptionsTest)




class ReqRegisterOutputFilterTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_register_output_filter"
    handler = "request::req_register_output_filter"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % self.document_root),
                        PythonHandler(self.handler),
                        PythonDebug("On"))


    def runTest(self):
        """ReqRegisterOutputFilterTest: req_register_output_filter"""

        print "\n  * Testing req.register_output_filter"
        rsp = self.vhost_get("test_req_register_output_filter")

        if (rsp != "TTEESSTT  OOKK"):
            self.fail(`rsp`)

register(ReqRegisterOutputFilterTest)


class ReqAddOutputFilterTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_req_add_output_filter"
    handler = "request::req_add_output_filter"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % self.document_root),
                        PythonHandler(self.handler),
                        PythonOutputFilter("request::outputfilter1 MP_TEST_FILTER"),
                        PythonDebug("On"))


    def runTest(self):
        """ReqAddOutputFilterTest: req_add_output_filter"""

        print "\n  * Testing req.add_output_filter"
        rsp = self.vhost_get("test_req_add_output_filter")

        if (rsp != "TEST OK"):
            self.fail(`rsp`)

register(ReqAddOutputFilterTest)



class OutputfilterTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_outputfilter"
    handler = "request::simplehandler"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % self.document_root),
                        PythonHandler(self.handler),
                        PythonOutputFilter("request::outputfilter1 MP_TEST_FILTER"),
                        PythonDebug("On"),
                        AddOutputFilter("MP_TEST_FILTER .py"))


    def runTest(self):
        """OutputfilterTest: outputfilter"""

        print "\n  * Testing PythonOutputFilter"
        rsp = self.vhost_get("test_outputfilter")

        if (rsp != "TEST OK"):
            self.fail(`rsp`)

register(OutputfilterTest)



