import base64
import commands
from cStringIO import StringIO
import httplib
import md5
import random
import shutil
import socket
import time
import tempfile
import urllib



from mptest.httpdconf import *
from mptest.testconf import * 
from mptest.testsetup import register
from mptest.util import findUnusedPort



class PublisherTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_publisher"
    handler = "mod_python.publisher"
    #document_root = 'htdocs/core'
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PublisherTest: publisher"""
        print "\n  * Testing mod_python.publisher"

        rsp = self.vhost_get(self.server_name, path="/publisher.py")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get(self.server_name, path="/publisher.py/index")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get(self.server_name, path="/publisher.py/test_publisher")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get(self.server_name, path="/")
        if (rsp != "test 1 ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get(self.server_name, path="/foobar")
        if (rsp != "test 2 ok, interpreter=test_publisher"):
            self.fail(`rsp`)

        rsp = self.vhost_get(self.server_name, path="/publisher")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(`rsp`)

register(PublisherTest)


class PublisherAuthNestedTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_publisher_auth_nested"
    handler = "mod_python.publisher"
    #document_root = 'htdocs/core'
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PublisherAuthNestedTest: publisher_auth_nested"""
        print "\n  * Testing mod_python.publisher auth nested"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/publisher.py/test_publisher_auth_nested", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_publisher_auth_nested", self.httpd.port))
        auth = base64.encodestring("spam:eggs").strip()
        conn.putheader("Authorization", "Basic %s" % auth)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok, interpreter=test_publisher_auth_nested"):
            self.fail(`rsp`)

register(PublisherAuthNestedTest)


class PublisherAuthMethodNestedTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_publisher_auth_method_nested"
    #document_root = 'htdocs/core'
    handler = "mod_python.publisher"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PublisherAuthMethodNestedTest: publisher_auth_method_nested"""
        print "\n  * Testing mod_python.publisher auth method nested"
        
        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/publisher.py/test_publisher_auth_method_nested/method", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_publisher_auth_method_nested", self.httpd.port))
        auth = base64.encodestring("spam:eggs").strip()
        conn.putheader("Authorization", "Basic %s" % auth)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok, interpreter=test_publisher_auth_method_nested"):
            self.fail(`rsp`)

register(PublisherAuthMethodNestedTest)


class PublisherAuthDigestTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_publisher_auth_digest"
    #document_root = 'htdocs/core'
    handler = "mod_python.publisher"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PublisherAuthDigestTest: publisher_auth_digest"""
        print "\n  * Testing mod_python.publisher auth digest compatability"

        # The contents of the authorization header is not relevant,
        # as long as it looks valid.

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", "/publisher.py/test_publisher", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_publisher_auth_digest", self.httpd.port))
        conn.putheader("Authorization", 'Digest username="Mufasa", realm="testrealm@host.com", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", uri="/dir/index.html", qop=auth, nc=00000001, cnonce="0a4f113b", response="6629fae49393a05397450978507c4ef1", opaque="5ccc069c403ebaf9f0171e9517f40e41"')
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "test ok, interpreter=test_publisher_auth_digest"):
            self.fail(`rsp`)

register(PublisherAuthDigestTest)


class PublisherSecurityTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_publisher"
    #document_root = 'htdocs/core'
    handler = "mod_python.publisher"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))

    
    def runTest(self):
        """PublisherSecurityTest: publisher_security"""
        print "\n  * Testing mod_python.publisher security"

        def get_status(path):
            conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
            conn.putrequest("GET", path, skip_host=1)
            conn.putheader("Host", "test_publisher:%s" % self.httpd.port)
            conn.endheaders()
            response = conn.getresponse()
            status, response = response.status, response.read()
            conn.close()
            return status, response

        status, response = get_status("/publisher.py/_SECRET_PASSWORD")
        if status != 403:
            self.fail('Vulnerability : underscore prefixed attribute (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/__ANSWER")
        if status != 403:
            self.fail('Vulnerability : underscore prefixed attribute (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/re")
        if status != 403:
            self.fail('Vulnerability : module published (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/OldStyleClassTest")
        if status != 403:
            self.fail('Vulnerability : old style class published (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/InstanceTest")
        if status != 403:
            self.fail('Vulnerability : new style class published (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/index/func_code")
        if status != 403:
            self.fail('Vulnerability : function traversal (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/old_instance/traverse/func_code")
        if status != 403:
            self.fail('Vulnerability : old-style method traversal (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/instance/traverse/func_code")
        if status != 403:
            self.fail('Vulnerability : new-style method traversal (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/test_dict/keys")
        if status != 403:
            self.fail('Vulnerability : built-in type traversal (%i)\n%s' % (status, response))

        status, response = get_status("/publisher.py/test_dict_keys")
        if status != 403:
            self.fail('Vulnerability : built-in type publishing (%i)\n%s' % (status, response))

register(PublisherSecurityTest)


class PublisherIteratorTest(PerRequestTestBase):
    """This test is disabled in the current mod_python version (3.2.10)
    I'm not sure why.
    """
    disable = True

    server_name = "test_publisher"
    #document_root = 'htdocs/core'
    handler = "mod_python.publisher"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PublisherIteratorTest: publisher_iterator"""
        print "\n  * Testing mod_python.publisher iterators"

        rsp = self.vhost_get(self.server_name, path="/publisher.py/test_dict_iteration")
        if (rsp != "123"):
            self.fail(`rsp`)

        rsp = self.vhost_get(self.server_name, path="/publisher.py/test_generator")
        if (rsp != "0123456789"):
            self.fail(`rsp`)

register(PublisherIteratorTest)


class PublisherHierarchyTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_publisher_hierarchy"
    #document_root = 'htdocs/core'
    handler = "mod_python.publisher"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))


    def runTest(self):
        """PublisherHierarchyTest: publisher_hierarchy"""
        print "\n  * Testing mod_python.publisher hierarchy"

        rsp = self.vhost_get("test_publisher_hierarchy", path="/publisher.py/hierarchy_root")
        if (rsp != "Called root"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher_hierarchy", path="/publisher.py/hierarchy_root_2")
        if (rsp != "test ok, interpreter=test_publisher_hierarchy"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher_hierarchy", path="/publisher.py/hierarchy_root/page1")
        if (rsp != "Called page1"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher_hierarchy", path="/publisher.py/hierarchy_root_2/page1")
        if (rsp != "test ok, interpreter=test_publisher_hierarchy"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher_hierarchy", path="/publisher.py/hierarchy_root/page1/subpage1")
        if (rsp != "Called subpage1"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher_hierarchy", path="/publisher.py/hierarchy_root/page2")
        if (rsp != "Called page2"):
            self.fail(`rsp`)

        rsp = self.vhost_get("test_publisher_hierarchy", path="/publisher.py/hierarchy_root_2/page2")
        if (rsp != "test ok, interpreter=test_publisher_hierarchy"):
            self.fail(`rsp`)

register(PublisherHierarchyTest)


class PublisherOldStyleInstanceTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_publisher"
    #document_root = 'htdocs/core'
    handler = "mod_python.publisher"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))

    
    def runTest(self):
        """PublisherOldStyleInstanceTest: publisher_old_style_instance"""
        print "\n  * Testing mod_python.publisher old-style instance publishing"

        rsp = self.vhost_get(self.server_name, path="/publisher.py/old_instance")
        if (rsp != "test callable old-style instance ok"):
            self.fail(`rsp`)

        rsp = self.vhost_get(self.server_name, path="/publisher.py/old_instance/traverse")
        if (rsp != "test traversable old-style instance ok"):
            self.fail(`rsp`)

register(PublisherOldStyleInstanceTest)


class PublisherInstanceTest(PerRequestTestBase):
    """DOCSTRING"""

    server_name = "test_publisher"
    #document_root = 'htdocs/core'
    handler = "mod_python.publisher"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))

    
    def runTest(self):
        """PublisherInstanceTest: publisher_instance"""
        print "\n  * Testing mod_python.publisher instance publishing"

        rsp = self.vhost_get(self.server_name, path="/publisher.py/instance")
        if (rsp != "test callable instance ok"):
            self.fail(`rsp`)

        rsp = self.vhost_get(self.server_name, path="/publisher.py/instance/traverse")
        if (rsp != "test traversable instance ok"):
            self.fail(`rsp`)

register(PublisherInstanceTest)


class PublisherCacheTest(PerRequestTestBase):
    """Test publisher cache reloading.
    It is not possible to get reliable results with this test
    for mpm-prefork and worker, and in fact it may not be possible
    to get consistent results.

    By default, this test will not be run.
    It can be forced to run using
    $ python test.py -f core.tests.PubisherCacheTest
    """
    disable = True
    server_name = "test_publisher"
    #document_root = 'htdocs/core'
    handler = "mod_python.publisher"
    
    def config(self):
        return VirtualHost("*",
                        ServerName(self.server_name),
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonDebug("On")))

    
    def runTest(self):
        """PublisherCacheTest: publisher_cache
        This test is not reliable and will likely fail for mpm-worker
        and mpm-prefork.
        """
       
        print "\n  * Testing mod_python.publisher cache"
        print "      Notes: server name =", self.server_name
        print "             document_root =", self.document_root
        
        def write_published():
            published = file(os.path.join(self.document_root, 'temp.py'),'wb')
            published.write('import time\n')
            published.write('LOAD_TIME = time.time()\n')
            published.write('def index(req):\n')
            published.write('    return "OK %f"%LOAD_TIME\n')
            published.close()
        
        write_published()
        try:
            rsp = self.vhost_get(self.server_name, path="/temp.py")
            
            if not rsp.startswith('OK '):
                self.fail(`rsp`)
            
            rsp2 = self.vhost_get(self.server_name, path="/temp.py")
            if rsp != rsp2:
                self.fail(
                    "The publisher cache has reloaded a published module"
                    " even though it wasn't modified !"
                )
            
            # We wait three seconds to be sure we won't be annoyed
            # by any lack of resolution of the stat().st_mtime member.
            time.sleep(3)
            write_published()
    
            rsp2 = self.vhost_get(self.server_name, path="/temp.py")
            if rsp == rsp2:
                self.fail(
                    "The publisher cache has not reloaded a published module"
                    " even though it was modified !"
                )
    
            rsp = self.vhost_get(self.server_name, path="/temp.py")
            if rsp != rsp2:
                self.fail(
                    "The publisher cache has reloaded a published module"
                    " even though it wasn't modified !"
                )
        finally:        
            os.remove(os.path.join(self.document_root, 'temp.py'))

register(PublisherCacheTest)

