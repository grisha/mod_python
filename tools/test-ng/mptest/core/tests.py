import httplib
import md5
import random
import socket
import urllib

from mptest.httpdconf import *
from mptest.testconf import * 
from mptest.testsetup import register
from mptest.util import findUnusedPort


class FileuploadTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_fileupload"
    handler = "tests::fileupload"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """FileuploadTest: fileupload"""
    
        print "\n  * Testing 1 MB file upload support"

        content = ''.join( [ chr(random.randrange(256)) for x in xrange(1024*1024) ] )
        digest = md5.new(content).hexdigest()

        rsp = self.vhost_post_multipart_form_data(
            "test_fileupload",
            variables={'test':'abcd'},
            files={'testfile':('test.txt',content)},
        )

        if (rsp != digest):
            self.fail('1 MB file upload failed, its contents were corrupted (%s)'%rsp)
   
register(FileuploadTest)


class FileuploadEmbeddedCrTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_fileupload"
    handler = "tests::fileupload"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """FileuploadEmbeddedCrTest: fileupload_embedded_cr"""
        # Strange things can happen if there is a '\r' character at position
        # readBlockSize of a line being read by FieldStorage.read_to_boundary 
        # where the line length is > readBlockSize.
        # This test will expose this problem.
        
        print "\n  * Testing file upload with \\r char in a line at position == readBlockSize"
        
        content = (
            'a'*100 + '\r\n'
            + 'b'*(readBlockSize-1) + '\r' # trick !
            + 'ccc' + 'd'*100 + '\r\n'
        )
        digest = md5.new(content).hexdigest()
        
        rsp = self.vhost_post_multipart_form_data(
            "test_fileupload",
            variables={'test':'abcd'},
            files={'testfile':('test.txt',content)},
        )

        if (rsp != digest):
            self.fail('file upload embedded \\r test failed, its contents were corrupted (%s)'%rsp)

        # The UNIX-HATERS handbook illustrates this problem. Once we've done some additional
        # investigation to make sure that our synthetic file used above is correct,
        # we can likely remove this conditional test. Also, there is no way to be sure
        # that ugh.pdf will always be the same in the future so the test may not be valid
        # over the long term.
        try:
            ugh = file('ugh.pdf','rb')
            content = ugh.read()
            ugh.close()
        except:
            print "  * Skipping the test for The UNIX-HATERS handbook file upload."
            print "    To make this test, you need to download ugh.pdf from"
            print "    http://research.microsoft.com/~daniel/uhh-download.html"
            print "    into this script's directory."
        else:
            print "  * Testing The UNIX-HATERS handbook file upload support"
    
            digest = md5.new(content).hexdigest()
    
            rsp = self.vhost_post_multipart_form_data(
                "test_fileupload",
                variables={'test':'abcd'},
                files={'testfile':('ugh.pdf',content)},
            )
    
            
            if (rsp != digest):
                self.fail('The UNIX-HATERS handbook file upload failed, its contents was corrupted (%s)'%rsp)

register(FileuploadEmbeddedCrTest)


class FileuploadSplitBoundaryTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_fileupload"
    handler = "tests::fileupload"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """FileuploadSplitBoundaryTest: fileupload_split_boundary"""
        # This test is similar to test_fileupload_embedded_cr, but it is possible to
        # write an implementation of FieldStorage.read_to_boundary that will pass
        # that test but fail this one.
        # 
        # Strange things can happen if the last line in the file being uploaded 
        # has length == readBlockSize -1. The boundary string marking the end of the
        # file (eg. '\r\n--myboundary') will be split between the leading '\r' and the
        # '\n'. Some implementations of read_to_boundary we've tried assume that this
        # '\r' character is part of the file, instead of the boundary string. The '\r'
        # will be appended to the uploaded file, leading to a corrupted file.

        print "\n  * Testing file upload where length of last line == readBlockSize - 1"

        content = (
            'a'*100 + '\r\n'
            + 'b'*(readBlockSize-1)  # trick !
        )
        digest = md5.new(content).hexdigest()
        
        rsp = self.vhost_post_multipart_form_data(
            "test_fileupload",
            variables={'test':'abcd'},
            files={'testfile':('test.txt',content)},
        )

        if (rsp != digest):
            self.fail('file upload long line test failed, its contents were corrupted (%s)'%rsp)

        print "  * Testing file upload where length of last line == readBlockSize - 1 with an extra \\r"

        content = (
            'a'*100 + '\r\n'
            + 'b'*(readBlockSize-1)
            + '\r'  # second trick !
        )
        digest = md5.new(content).hexdigest()
        
        rsp = self.vhost_post_multipart_form_data(
            "test_fileupload",
            variables={'test':'abcd'},
            files={'testfile':('test.txt',content)},
        )

        if (rsp != digest):
            self.fail('file upload long line test failed, its contents were corrupted (%s)'%rsp)

register(FileuploadSplitBoundaryTest)


class SysArgvTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_sys_argv"
    handler = "tests::test_sys_argv"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """SysArgvTest: sys_argv"""

        print "\n  * Testing sys.argv definition"

        rsp = self.vhost_get("test_sys_argv")

        if (rsp != "['mod_python']"):
            self.fail(`rsp`)

register(SysArgvTest)


class PythonoptionTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_PythonOption"
    handler = "tests::PythonOption_items"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """PythonoptionTest: PythonOption"""

        print "\n  * Testing PythonOption"

        rsp = self.vhost_get("test_PythonOption")

        if (rsp != "[('PythonOptionTest', 'sample_value')]"):
            self.fail(`rsp`)

register(PythonoptionTest)


class PythonoptionOverrideTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_PythonOption_override"
    handler = "tests::PythonOption_items"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonOption('PythonOptionTest "new_value"'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonDebug("On")))



    def runTest(self):
        """PythonoptionOverrideTest: PythonOption_override"""

        print "\n  * Testing PythonOption override"

        rsp = self.vhost_get("test_PythonOption_override")

        if (rsp != "[('PythonOptionTest', 'new_value'), ('PythonOptionTest2', 'new_value2')]"):
            self.fail(`rsp`)

register(PythonoptionOverrideTest)


class PythonoptionRemoveTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_PythonOption_remove"
    handler = "tests::PythonOption_items"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonOption('PythonOptionTest ""'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonDebug("On")))



    def runTest(self):
        """PythonoptionRemoveTest: PythonOption_remove"""

        print "\n  * Testing PythonOption remove"

        rsp = self.vhost_get("test_PythonOption_remove")

        if (rsp != "[('PythonOptionTest2', 'new_value2')]"):
            self.fail(`rsp`)

register(PythonoptionRemoveTest)


class PythonoptionRemove2Test(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_PythonOption_remove2"
    handler = "tests::PythonOption_items"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonOption('PythonOptionTest'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonOption('PythonOptionTest3 new_value3'),
                                  PythonDebug("On")))



    def runTest(self):
        """PythonoptionRemove2Test: PythonOption_remove2"""

        print "\n  * Testing PythonOption remove2"

        rsp = self.vhost_get("test_PythonOption_remove2")

        if (rsp != "[('PythonOptionTest2', 'new_value2'), ('PythonOptionTest3', 'new_value3')]"):
            self.fail(`rsp`)

register(PythonoptionRemove2Test)


class InterpreterPerDirectiveTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_interpreter_per_directive"
    handler = "tests::interpreter"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  PythonInterpPerDirective('On'),
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))



    def runTest(self):
        """InterpreterPerDirectiveTest: interpreter_per_directive"""

        print "\n  * Testing interpreter per directive"

        interpreter_name = (self.document_root.replace('\\', '/')+'/').upper()

        rsp = self.vhost_get("test_interpreter_per_directive").upper()
        if (rsp != interpreter_name):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directive", '/subdir/foo.py').upper()
        if (rsp != interpreter_name):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directive", '/subdir/').upper()
        if (rsp != interpreter_name):
            self.fail(`rsp`)

register(InterpreterPerDirectiveTest)


class InterpreterPerDirectoryTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_interpreter_per_directory"
    handler = "tests::interpreter"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  PythonInterpPerDirectory('On'),
                                  SetHandler("mod_python"),
                                  PythonFixupHandler("tests::interpreter"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")),
                        )



    def runTest(self):
        """InterpreterPerDirectoryTest: interpreter_per_directory"""

        print "\n  * Testing interpreter per directory"

        interpreter_name = (self.document_root.replace('\\', '/')+'/').upper()

        rsp = self.vhost_get("test_interpreter_per_directory").upper()
        if (rsp != interpreter_name):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directory", '/subdir/foo.py').upper()
        if (rsp != interpreter_name+'SUBDIR/'):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directory", '/subdir/').upper()
        if (rsp != interpreter_name+'SUBDIR/'):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_interpreter_per_directory", '/subdir').upper()
        if (rsp != interpreter_name+'SUBDIR/'):
            self.fail(`rsp`)

register(InterpreterPerDirectoryTest)


class UtilFieldstorageTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_util_fieldstorage"
    handler = "tests::util_fieldstorage"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """UtilFieldstorageTest: util_fieldstorage"""

        print "\n  * Testing util_fieldstorage()"

        params = urllib.urlencode([('spam', 1), ('spam', 2), ('eggs', 3), ('bacon', 4)])
        headers = {"Host": "test_util_fieldstorage",
                   "Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.request("POST", "/tests.py", params, headers)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "[Field('spam', '1'), Field('spam', '2'), Field('eggs', '3'), Field('bacon', '4')]"):
            self.fail(`rsp`)

register(UtilFieldstorageTest)


class PostreadrequestTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_postreadrequest"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % self.document_root),
                        PythonPostReadRequestHandler("tests::postreadrequest"),
                        PythonDebug("On"))


    def runTest(self):
        """PostreadrequestTest: postreadrequest"""

        print "\n  * Testing PostReadRequestHandler"
        rsp = self.vhost_get("test_postreadrequest")

        if (rsp != "test ok"):
            self.fail(`rsp`)
            
register(PostreadrequestTest)


class TransTest(PerRequestTestBase):
    """See MODPYTHON-171 
    Assignment to req.filename and POSIX style pathnames

    The code change and this test were reverted in r451850.
    This test should be removed.
    """ 

    server_name = "test_trans"
    disable = True
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % self.document_root),
                        PythonTransHandler("tests::trans"),
                        PythonDebug("On"))


    def runTest(self):
        """TransTest: trans"""

        print "\n  * Testing TransHandler"
        rsp = self.vhost_get("test_trans")

        if (rsp[0:2] != " #"): # first line in tests.py
            self.fail(`rsp`)
            
register(TransTest)


class ImportTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_import"
    handler = "tests::import_test"
    
    def config(self):

        # configure apache to import it at startup
        return Container(PythonPath("[r'%s']+sys.path" % self.document_root),
                      PythonImport("dummymodule test_import"),
                      PythonImport("dummymodule::function test_import"),
                      VirtualHost("*",
                                  ServerName(self.server_name),
                                  DocumentRoot(self.document_root),
                                  Directory(self.document_root,
                                            SetHandler("mod_python"),
                                            PythonHandler(self.handler),
                                            PythonDebug("On"))))


    def runTest(self):
        """ImportTest: import"""

        print "\n  * Testing PythonImport"
        rsp = self.vhost_get("test_import")

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(ImportTest)


class ConnectionhandlerTest(PerRequestTestBase):
    """DOCSTRING"""

    
    def config(self):

        try: 
            localip = socket.gethostbyname("localhost") 
        except: 
            localip = "127.0.0.1"

        self.conport = findUnusedPort()
        return str(Listen("%d" % self.conport)) + \
            str(VirtualHost("%s:%d" % (localip, self.conport),
                            SetHandler("mod_python"),
                            PythonPath("[r'%s']+sys.path" % self.document_root),
                            PythonConnectionHandler("tests::connectionhandler")))

    def runTest(self):
        """ConnectionhandlerTest: connectionhandler"""

        print "\n  * Testing PythonConnectionHandler"

        url = "http://127.0.0.1:%s/tests.py" % self.conport
        f = urllib.urlopen(url)
        rsp = f.read()
        f.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(ConnectionhandlerTest)


class InternalTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_internal"
    handler = "internal"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        ServerAdmin("serveradmin@somewhere.com"),
                        ErrorLog("logs/error_log"),
                        ServerPath("some/path"),
                        DocumentRoot(self.document_root + '/core'),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonOption("testing 123"),
                                  PythonDebug("On")))


    def runTest(self):
        """InternalTest: internal"""

        print "\n  * Testing internally (status messages go to error_log)"

        rsp = self.vhost_get("test_internal")
        if (rsp[-7:] != "test ok"):
            self.fail("Some tests failed, see error_log")

#register(InternalTest)


class PipeExtTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_pipe_ext"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher | .py"),
                                  PythonHandler("tests::simplehandler"),
                                  PythonDebug("On")))


    def runTest(self):
        """PipeExtTest: | .ext syntax"""

        print "\n  * Testing %s" % self.runTest.__doc__

        rsp = self.vhost_get("test_pipe_ext", path="/tests.py/pipe_ext")
        if (rsp[-8:] != "pipe ext"):
            self.fail("Expected: 'pipe ext'; got:" + `rsp`)

        rsp = self.vhost_get("test_pipe_ext", path="/tests/anything")
        if (rsp[-7:] != "test ok"):
            self.fail("Expected: 'test ok'; got:" + `rsp`)
        
register(PipeExtTest)


class CgihandlerTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_cgihandler"
    handler = "mod_python.cgihandler"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """CgihandlerTest: cgihandler"""

        print "\n  * Testing mod_python.cgihandler"

        rsp = self.vhost_get("test_cgihandler", path="/cgitest.py")

        if (rsp[-8:] != "test ok\n"):
            self.fail(`rsp`)

register(CgihandlerTest)


class PsphandlerTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_psphandler"
    handler = "mod_python.psp"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PsphandlerTest: psphandler"""

        print "\n  * Testing mod_python.psp"

        rsp = self.vhost_get("test_psphandler", path="/psptest.psp")
        if (rsp[-8:] != "test ok\n"):
            self.fail(`rsp`)

register(PsphandlerTest)


class PspParserTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_psp_parser"
    handler = "mod_python.psp"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PspParserTest: psp_parser"""

        print "\n  * Testing mod_python.psp parser"
                # lines in psp_parser.psp should look like:
        #   test:<char>:<test_string>$
        #
        # For example:
        #   test:n:\n$
        #   test:t:\t$
        
        rsp = self.vhost_get("test_psp_parser", path="/psp_parser.psp")
        lines = [ line.strip() for line in rsp.split('$') if line ]
        failures = []
        for line in lines:
            parts =  line.split(':', 2)
            if len(parts) < 3:
                continue

            t, test_case, test_string = parts[0:3]
            if not t.strip().startswith('test'):
                continue
            expected_result = test_case
            # do the substitutions in expected_result
            for ss, rs in [('-', '\\'),('CR', '\r'), ('LF', '\n'), ('TB', '\t')]:
                expected_result = expected_result.replace(ss, rs)
            
            if expected_result != test_string:
                print '       FAIL',  
                failures.append(test_case)
            else:
                print '       PASS', 
            print 'expect{%s} got{%s}' % (expected_result, test_string)

        if failures:
            msg = 'psp_parser parse errors for: %s' % (', '.join(failures))
            self.fail(msg)

register(PspParserTest)


class PspErrorTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_psp_error"
    handler = "mod_python.psp"
    
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
        """PspErrorTest: psp_error"""

        print "\n  * Testing mod_python.psp error page"

        rsp = self.vhost_get("test_psp_error", path="/psptest_main.psp")
        if (rsp.strip().split() != ["okay","fail"]):
            self.fail(`rsp`)

    def tearDown(self):
        super(PerRequestTestBase, self).tearDown()
        try:
            os.remove(os.path.join(self.httpd.tmp_dir, 'mp_sess.dbm'))
        except:
            pass

register(PspErrorTest)


class CookieCookieTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_Cookie_Cookie"
    handler = "tests::Cookie_Cookie"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """CookieCookieTest: Cookie_Cookie"""

        print "\n  * Testing Cookie.Cookie"


        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        # this is three cookies, nastily formatted
        conn.putheader("Host", "test_Cookie_Cookie:%s" % self.httpd.port)
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

register(CookieCookieTest)


class CookieMarshalcookieTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_Cookie_MarshalCookie"
    handler = "tests::Cookie_Cookie"
    
    def config(self):

        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """CookieMarshalcookieTest: Cookie_MarshalCookie"""

        print "\n  * Testing Cookie.MarshalCookie"

        mc = "eggs=d049b2b61adb6a1d895646719a3dc30bcwQAAABzcGFt"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        conn.putheader("Host", "test_Cookie_MarshalCookie:%s" % self.httpd.port)
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

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        conn.putheader("Host", "test_Cookie_MarshalCookie:%s" % self.httpd.port)
        conn.putheader("Cookie", mc)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != "test ok" or setcookie != mc:
            print `rsp`
            self.fail("long marshalled cookie parsing failed")

register(CookieMarshalcookieTest)


class FilesDirectiveTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_files_directive"
    handler = "tests::files_directive"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  Files("*.py",
                                        SetHandler("mod_python"),
                                        PythonHandler(self.handler),
                                        PythonDebug("On"))))


    def runTest(self):
        """FilesDirectiveTest: files_directive"""

        directory = (self.document_root.replace('\\', '/')+'/').upper()

        print "\n  * Testing Files directive"
        rsp = self.vhost_get("test_files_directive", path="/tests.py").upper()

        if rsp != directory:
            self.fail(`rsp`)

register(FilesDirectiveTest)


class NoneHandlerTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_none_handler"
    handler = "tests::none_handler"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """NoneHandlerTest: none_handler"""

        print "\n  * Testing None handler"

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_none_handler:%s" % self.httpd.port)
        conn.endheaders()
        response = conn.getresponse()
        status = response.status
        rsp = response.read()
        conn.close()
        if status != 500:
            print status, rsp
            self.fail("none handler should generate error")

register(NoneHandlerTest)


class ServerReturnTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_server_return"
    handler = "tests::server_return_2"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """ServerReturnTest: server_return"""

        print "\n  * Testing SERVER_RETURN"
        rsp = self.vhost_get("test_server_return")

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(ServerReturnTest)


class PhaseStatusTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_phase_status"
    handler = "tests::phase_status_8"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  AuthType("bogus"),
                                  AuthName("bogus"),
                                  Require("valid-user"),
                                  PythonAuthenHandler("tests::phase_status_1"),
                                  PythonAuthenHandler("tests::phase_status_2"),
                                  PythonAuthenHandler("tests::phase_status_3"),
                                  PythonAuthzHandler("tests::phase_status_4"),
                                  PythonFixupHandler("tests::phase_status_5"),
                                  PythonFixupHandler("tests::phase_status_6"),
                                  PythonFixupHandler("tests::phase_status_7"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PhaseStatusTest: phase_status"""

        print "\n  * Testing phase status"
        rsp = self.vhost_get("test_phase_status")

        if (rsp != "test ok"):
            self.fail(`rsp`)

register(PhaseStatusTest)


class ServerSideIncludeTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_server_side_include"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  Options("+Includes"),
                                  AddType("text/html .shtml"),
                                  AddOutputFilter("INCLUDES .shtml"),
                                  PythonFixupHandler("tests::server_side_include"),
                                  PythonDebug("On")))


    def runTest(self):
        """ServerSideIncludeTest: server_side_include"""

        print "\n  * Testing server side include"
        rsp = self.vhost_get("test_server_side_include", path="/ssi.shtml")

        rsp = rsp.strip()

        if (rsp != "test ok"):
            self.fail(`rsp`)


register(ServerSideIncludeTest)

