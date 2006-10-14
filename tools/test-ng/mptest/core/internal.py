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
                        DocumentRoot(self.document_root),
                        Directory(self.document_root,
                                  SetHandler("mod_python"),
                                  PythonHandler(self.handler),
                                  PythonOption("testing 123"),
                                  PythonDebug("On"))
                        )


    def runTest(self):
        """InternalTest: internal"""

        print "\n  * Testing internally (status messages go to error_log)"

        rsp = self.vhost_get("test_internal")
        if (rsp[-7:] != "test ok"):
            self.fail("Some tests failed, see error_log")

register(InternalTest)

