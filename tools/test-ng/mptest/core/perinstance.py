import os
import urllib
import httplib
import shutil
import time


from mptest.httpdconf import *
from mptest.testsetup import register
from mptest.testconf import *
from mptest.util import get_ab_path

class LoadModuleTest(PerInstanceTestBase):

    def runTest(self):
        """LoadModuleTest"""
        
        print "\n * Testing", self.shortDescription()

        f = urllib.urlopen("http://127.0.0.1:%s/" % self.httpd.port)
        server_hdr = f.info()["Server"]
        f.close()
        self.failUnless(server_hdr.find("Python") > -1,
                        "%s does not appear to load, Server header does not contain Python"
                        % self.httpd.mod_python_so)

register(LoadModuleTest)

class GlobalLockTest(PerInstanceTestBase):
    handler = "perinstance::global_lock"

    def config(self):
        c = Directory(self.document_root,
                      SetHandler("mod_python"),
                      PythonHandler(self.handler),
                      PythonDebug("On"))

        return c

    def runTest(self):
        """GlobalLockTest: _global_lock"""

        print "\n  * Testing", self.shortDescription()

        f = urllib.urlopen("http://127.0.0.1:%s/perinstance.py" % self.httpd.port)
        rsp = f.read()
        f.close()

        if (rsp != "test ok"):
            self.fail(`rsp`)

        # if the mutex works, this test will take at least 5 secs
        ab = get_ab_path(self.httpd.httpd) 
        if not ab:
            print "    Can't find ab. Skipping _global_lock test"
            return

        t1 = time.time()
        print "    ", time.ctime()
        if os.name == "nt":
            cmd = '%s -c 5 -n 5 http://127.0.0.1:%s/perinstance.py > NUL:' \
                  % (ab, self.httpd.port)
        else:
            cmd = '%s -c 5 -n 5 http://127.0.0.1:%s/perinstance.py > /dev/null' \
                  % (ab, self.httpd.port)
        print "    ", cmd
        os.system(cmd)
        print "    ", time.ctime()
        t2 = time.time()
        if (t2 - t1) < 5:
            self.fail("global_lock is broken (too quick)")

register(GlobalLockTest)

class ServerRegisterCleanupTest(PerInstanceTestBase):
    handler = "perinstance::srv_register_cleanup"

    def config(self):
        return Directory(self.document_root,
                      SetHandler("mod_python"),
                      PythonHandler(self.handler),
                      PythonDebug("On"))

    def runTest(self):
        """ServerRegisterCleanupTest: server.register_cleanup()"""

        print "\n  * Testing", self.shortDescription()

        f = urllib.urlopen("http://127.0.0.1:%s/perinstance.py" % self.httpd.port)
        f.read()
        f.close()

        time.sleep(2)
        self.httpd.stop()

        # see what's in the log now
        time.sleep(2)
        f = open(os.path.join(self.httpd.server_root, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("srv_register_cleanup test ok") == -1:
            self.fail("Could not find test message in error_log")

register(ServerRegisterCleanupTest)


class ApacheRegisterCleanupTest(PerInstanceTestBase):
    handler = "perinstance::apache_register_cleanup"

    def config(self):
        return Directory(self.document_root,
                      SetHandler("mod_python"),
                      PythonHandler(self.handler),
                      PythonDebug("On"))

    def runTest(self):
        """ApacheRegisterCleanupTest: apache.register_cleanup()"""
        print "\n  * Testing", self.shortDescription()

        f = urllib.urlopen("http://127.0.0.1:%s/perinstance.py" % self.httpd.port)
        f.read()
        f.close()

        time.sleep(2)
        self.httpd.stop()
        time.sleep(2)

        # see what's in the log now
        f = open(os.path.join(self.httpd.server_root, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("apache_register_cleanup test ok") == -1:
            self.fail("Could not find test message in error_log")

register(ApacheRegisterCleanupTest)



class ApacheExistsConfigDefineTest(PerInstanceTestBase):
    handler = "perinstance::apache_exists_config_define"

    def config(self):
        return Directory(self.document_root,
                      SetHandler("mod_python"),
                      PythonHandler(self.handler),
                      PythonDebug("On"))

    def runTest(self):
        """ApacheExistsConfigDefineTest: apache.exists_config_define()"""
        print "\n  * Testing", self.shortDescription()

        f = urllib.urlopen("http://127.0.0.1:%s/perinstance.py" % self.httpd.port)
        rsp = f.read()
        f.close()

        self.httpd.stop()
        
        if rsp != 'NO_FOOBAR':
            self.fail('Failure on apache.exists_config_define() : %s' % rsp)

        self.httpd.start(extra="-DFOOBAR")

        f = urllib.urlopen("http://127.0.0.1:%s/perinstance.py" % self.httpd.port)
        rsp = f.read()
        f.close()
        
        if rsp != 'FOOBAR':
            self.fail('Failure on apache.exists_config_define() : %s' % rsp)

register(ApacheExistsConfigDefineTest)

