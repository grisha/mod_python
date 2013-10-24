 #
 # Copyright (C) 2000, 2001, 2013 Gregory Trubetskoy
 # Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007 Apache Software Foundation
 #
 # Licensed under the Apache License, Version 2.0 (the "License"); you
 # may not use this file except in compliance with the License.  You
 # may obtain a copy of the License at
 #
 #      http://www.apache.org/licenses/LICENSE-2.0
 #
 # Unless required by applicable law or agreed to in writing, software
 # distributed under the License is distributed on an "AS IS" BASIS,
 # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 # implied.  See the License for the specific language governing
 # permissions and limitations under the License.
 #
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
from __future__ import print_function
import sys
import os

PY2 = sys.version[0] == '2'

try:
    import mod_python.version
except:
    print (
        "Cannot import mod_python.version. Either you didn't "
        "run the ./configure script, or you're running this script "
        "in a Win32 environment, in which case you have to make it by hand."
    )
    sys.exit()
else:
    def testpath(variable,isfile):
        value = getattr(mod_python.version,variable,'<undefined>')

        if isfile:
            if os.path.isfile(value):
                return True
        else:
            if os.path.isdir(value):
                return True
        print('Bad value for mod_python.version.%s : %s'%(
            variable,
            value
        ))
        return False

    good = testpath('HTTPD',True)
    good = testpath('TESTHOME',False) and good
    good = testpath('LIBEXECDIR',False) and good
    good = testpath('TEST_MOD_PYTHON_SO',True) and good
    if not good:
        print("Please check your mod_python/version.py file")
        sys.exit()

    del testpath
    del good


from mod_python.httpdconf import *

import unittest
if PY2:
    from commands import getoutput
    import urllib2
    import httplib
    from httplib import UNAUTHORIZED
    import md5
    from cStringIO import StringIO
    from urllib2 import urlopen
    from urllib import urlencode
else:
    from subprocess import getoutput
    import urllib.request, urllib.error
    import http.client
    from http.client import UNAUTHORIZED
    from hashlib import md5
    from io import StringIO, BytesIO, TextIOWrapper
    from urllib.request import urlopen
    from urllib.parse import urlencode
import shutil
import time
import socket
import tempfile
import base64
import random

try:
    import threading
    THREADS = True
except:
    THREADS = False

HTTPD = mod_python.version.HTTPD
TESTHOME = mod_python.version.TESTHOME
MOD_PYTHON_SO = mod_python.version.TEST_MOD_PYTHON_SO
LIBEXECDIR = mod_python.version.LIBEXECDIR
SERVER_ROOT = TESTHOME
CONFIG = os.path.join(TESTHOME, "conf", "test.conf")
DOCUMENT_ROOT = os.path.join(TESTHOME, "htdocs")
TMP_DIR = os.path.join(TESTHOME, "tmp")
PORT = 0 # this is set in fundUnusedPort()


# readBlockSize is required for the test_fileupload_* tests.
# We can't import mod_python.util.readBlockSize from a cmd line
# interpreter, so we'll hard code it here.
# If util.readBlockSize changes, it MUST be changed here as well.
# Maybe we should set up a separate test to query the server to
# get the correct readBlockSize?
#
readBlockSize = 65368

def findUnusedPort():

    # bind to port 0 which makes the OS find the next
    # unused port.

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    return port

def http_connection(conn_str):
    if PY2:
        return httplib.HTTPConnection(conn_str)
    else:
        return http.client.HTTPConnection(conn_str)

def md5_hash(s):
    if PY2:
        return md5.new(s).hexdigest()
    else:
        if isinstance(s, str):
            s = s.encode('latin1')
        return md5(s).hexdigest().encode('latin1')

def get_ab_path():
    """ Find the location of the ab (apache benchmark) program """
    for name in ['ab', 'ab2', 'ab.exe', 'ab2.exe']:
        path = os.path.join(os.path.split(HTTPD)[0], name)
        if os.path.exists(path):
            return quote_if_space(path)

    return None

def get_apache_version():

    print("Checking Apache version....")
    httpd = quote_if_space(HTTPD)
    stdout = getoutput('%s -v' % (httpd))

    version_str = None
    for line in stdout.splitlines():
        if line.startswith('Server version'):
             version_str = line.strip()
             break

    if version_str:
        version_str = version_str.split('/')[1]
        major,minor,patch = version_str.split('.',3)
        version = '%s.%s' % (major,minor)
    else:

        print("Can't determine Apache version. Assuming 2.0")
        version = '2.0'
    print(version)
    return version

APACHE_VERSION = get_apache_version()
if not mod_python.version.HTTPD_VERSION.startswith(APACHE_VERSION):
    print("ERROR: Build version %s does not match version reported by %s: %s, re-run ./configure?" % \
        (mod_python.version.HTTPD_VERSION, HTTPD, APACHE_VERSION))
    sys.exit()

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

        # place
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)
        os.mkdir(TMP_DIR)


    def makeConfig(self, append=Container()):

        # create config files, etc

        print("  Creating config....")

        self.checkFiles()

        global PORT
        PORT = findUnusedPort()
        print("    listen port:", PORT)

        # where other modules might be
        modpath = LIBEXECDIR

        s = Container(
            IfModule("prefork.c",
                     StartServers("3"),
                     MaxSpareServers("1")),
            IfModule("worker.c",
                     StartServers("2"),
                     MaxClients("6"),
                     MinSpareThreads("1"),
                     MaxSpareThreads("1"),
                     ThreadsPerChild("3"),
                     MaxRequestsPerChild("0")),
            IfModule("perchild.c",
                     NumServers("2"),
                     StartThreads("2"),
                     MaxSpareThreads("1"),
                     MaxThreadsPerChild("2")),
            IfModule("mpm_winnt.c",
                     ThreadsPerChild("5"),
                     MaxRequestsPerChild("0")),
            IfModule("!mod_mime.c",
                     LoadModule("mime_module %s" %
                                quote_if_space(os.path.join(modpath, "mod_mime.so")))),
            IfModule("!mod_log_config.c",
                     LoadModule("log_config_module %s" %
                                quote_if_space(os.path.join(modpath, "mod_log_config.so")))),
            IfModule("!mod_dir.c",
                     LoadModule("dir_module %s" %
                                quote_if_space(os.path.join(modpath, "mod_dir.so")))),
            IfModule("!mod_include.c",
                     LoadModule("include_module %s" %
                                quote_if_space(os.path.join(modpath, "mod_include.so")))),
            ServerRoot(SERVER_ROOT),
            ErrorLog("logs/error_log"),
            LogLevel("debug"),
            LogFormat(r'"%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined'),
            CustomLog("logs/access_log combined"),
            TypesConfig("conf/mime.types"),
            PidFile("logs/httpd.pid"),
            ServerName("127.0.0.1"),
            Listen(PORT),
            Timeout(60),
            PythonOption('mod_python.mutex_directory %s' % TMP_DIR),
            PythonOption('PythonOptionTest sample_value'),
            DocumentRoot(DOCUMENT_ROOT),
            LoadModule("python_module %s" % quote_if_space(MOD_PYTHON_SO)))

        if APACHE_VERSION == '2.4':
            s.append(Mutex("file:logs"))
        else:
            s.append(LockFile("logs/accept.lock"))

        if APACHE_VERSION == '2.4':
            s.append(IfModule("!mod_unixd.c",
                              LoadModule("unixd_module %s" %
                                         quote_if_space(os.path.join(modpath, "mod_unixd.so")))))
            s.append(IfModule("!mod_authn_core.c",
                              LoadModule("authn_core_module %s" %
                                         quote_if_space(os.path.join(modpath, "mod_authn_core.so")))))
            s.append(IfModule("!mod_authz_core.c",
                              LoadModule("authz_core_module %s" %
                                         quote_if_space(os.path.join(modpath, "mod_authz_core.so")))))
            s.append(IfModule("!mod_authn_file.c",
                              LoadModule("authn_file_module %s" %
                                         quote_if_space(os.path.join(modpath, "mod_authn_file.so")))))
            s.append(IfModule("!mod_authz_user.c",
                              LoadModule("authz_user_module %s" %
                                         quote_if_space(os.path.join(modpath, "mod_authz_user.so")))))

        if APACHE_VERSION in ['2.2', '2.4']:
            # mod_auth has been split into mod_auth_basic and some other modules
            s.append(IfModule("!mod_auth_basic.c",
                     LoadModule("auth_basic_module %s" %
                                quote_if_space(os.path.join(modpath, "mod_auth_basic.so")))))

            # Default KeepAliveTimeout is 5 for apache 2.2, but 15 in apache 2.0
            # Explicitly set the value so it's the same as 2.0
            s.append(KeepAliveTimeout("15"))
        else:
            s.append(IfModule("!mod_auth.c",
                     LoadModule("auth_module %s" %
                                quote_if_space(os.path.join(modpath, "mod_auth.so")))))


        s.append(Comment(" --APPENDED--"))
        s.append(append)

        f = open(CONFIG, "w")
        f.write(str(s))
        f.close()

    def startHttpd(self,extra=''):

        print("  Starting Apache....")
        httpd = quote_if_space(HTTPD)
        config = quote_if_space(CONFIG)
        cmd = '%s %s -k start -f %s' % (httpd, extra, config)
        print("    ", cmd)
        os.system(cmd)
        time.sleep(1)
        self.httpd_running = 1

    def stopHttpd(self):

        print("  Stopping Apache...")
        httpd = quote_if_space(HTTPD)
        config = quote_if_space(CONFIG)
        cmd = '%s -k stop -f %s' % (httpd, config)
        print("    ", cmd)
        os.system(cmd)
        time.sleep(1)

        # Wait for apache to stop by checking for the existence of pid the
        # file. If pid file still exists after 20 seconds raise an error.
        # This check is here to facilitate testing on the qemu emulator.
        # Qemu will run about 1/10 the native speed, so 1 second may
        # not be long enough for apache to shut down.
        count = 0
        pid_file = os.path.join(os.getcwd(), 'logs/httpd.pid')
        while os.path.exists(pid_file):
            time.sleep(1)
            count += 1
            if count > 20:
                # give up - apache refuses to die - or died a horrible
                # death and never removed the pid_file.
                raise RuntimeError("  Trouble stopping apache")

        self.httpd_running = 0

class PerRequestTestCase(unittest.TestCase):

    appendConfig = APACHE_VERSION < '2.4' and Container(NameVirtualHost('*')) or Container()

    def __init__(self, methodName="runTest"):
        unittest.TestCase.__init__(self, methodName)

        # add to config
        try:
            confMeth = getattr(self, methodName+"_conf")
            self.__class__.appendConfig.append(confMeth())
        except AttributeError:
            pass

    def vhost_get(self, vhost, path="/tests.py"):

        # this is so that tests could easily be staged with curl
        curl = "curl --verbose --header 'Host: %s' http://127.0.0.1:%s%s" % (vhost, PORT, path)
        print("    $ %s" % curl)

        # allows to specify a custom host: header
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", path, skip_host=1)
        conn.putheader("Host", "%s:%s" % (vhost, PORT))
        conn.endheaders()
        response = conn.getresponse()
        if PY2:
            rsp = response.read()
        else:
            rsp = response.read().decode('latin1')
        conn.close()

        return rsp

    def vhost_post_multipart_form_data(self, vhost, path="/tests.py",variables={}, files={}):
        # variables is a { name : value } dict
        # files is a { name : (filename, content) } dict

        # build the POST entity
        if PY2:
            entity = StringIO()
            boundary = "============="+''.join( [ random.choice('0123456789') for x in range(10) ] )+'=='
        else:
            bio = BytesIO()
            entity = TextIOWrapper(bio, encoding='latin1')
            boundary = "============="+''.join( [ random.choice('0123456789') for x in range(10) ] )+'=='

        # A part for each variable
        for name, value in variables.items():
            entity.write('--')
            entity.write(boundary)
            entity.write('\r\n')
            entity.write('Content-Type: text/plain\r\n')
            entity.write('Content-Disposition: form-data;\r\n name="%s"\r\n' % name)
            entity.write('\r\n')
            entity.write(str(value))
            entity.write('\r\n')

        # A part for each file
        for name, filespec in files.items():
            filename, content = filespec
            # if content is readable, read it
            try:
                content = content.read()
            except:
                pass

            if not isinstance(content, str): # always false on 2.x
                content = content.decode('latin1')

            entity.write('--')
            entity.write(boundary)
            entity.write('\r\n')
            entity.write('Content-Type: application/octet-stream\r\n')
            entity.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (name, filename))
            entity.write('\r\n')
            entity.write(content)
            entity.write('\r\n')

        # The final boundary
        entity.write('--')
        entity.write(boundary)
        entity.write('--\r\n')

        entity.flush()
        if PY2:
            entity = entity.getvalue()
        else:
            entity = bio.getvalue()

        conn = http_connection("127.0.0.1:%s" % PORT)
        #conn.set_debuglevel(1000)
        conn.putrequest("POST", path, skip_host=1)
        conn.putheader("Host", "%s:%s" % (vhost, PORT))
        conn.putheader("Content-Type", 'multipart/form-data; boundary="%s"' % boundary)
        conn.putheader("Content-Length", '%s'%(len(entity)))
        conn.endheaders()

        start = time.time()
        conn.send(entity)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()
        print('    --> Send + process + receive took %.3f s'%(time.time()-start))

        return rsp

    ### Tests begin here

    def test_req_document_root_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_document_root"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_document_root"),
                                  PythonDebug("On")))
        return c


    def test_req_document_root(self):

        print("\n  * Testing req.document_root()")
        rsp = self.vhost_get("test_req_document_root")

        if rsp.upper() != DOCUMENT_ROOT.replace("\\", "/").upper():
            self.fail(repr(rsp))

    def test_req_add_handler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_handler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_add_handler"),
                                  PythonDebug("On")))
        return c

    def test_req_add_handler(self):

        print("\n  * Testing req.add_handler()")
        rsp = self.vhost_get("test_req_add_handler")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_req_add_bad_handler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_bad_handler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_add_bad_handler"),
                                  PythonDebug("On")))
        return c

    def test_req_add_bad_handler(self):
        # adding a non-existent handler with req.add_handler should raise
        # an exception.

        print("""\n  * Testing req.add_handler("PythonHandler", "bad_handler")""")
        rsp = self.vhost_get("test_req_add_bad_handler")

        # look for evidence of the exception in the error log
        time.sleep(1)
        f = open(os.path.join(SERVER_ROOT, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("contains no 'bad_handler'") == -1:
            self.fail("""Could not find "contains no 'bad_handler'" in error_log""")

    def test_req_add_empty_handler_string_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_empty_handler_string"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_add_empty_handler_string"),
                                  PythonDebug("On")))
        return c

    def test_req_add_empty_handler_string(self):
        # Adding an empty string as the handler in req.add_handler
        # should raise an exception

        print("""\n  * Testing req.add_handler("PythonHandler","")""")
        rsp = self.vhost_get("test_req_add_empty_handler_string")

        if (rsp == "no exception"):
            self.fail("Expected an exception")

    def test_req_add_handler_empty_phase_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_handler_empty_phase"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonInterpPerDirective("On"),
                                  PythonFixupHandler("tests::req_add_handler_empty_phase"),
                                  PythonDebug("On")))
        return c

    def test_req_add_handler_empty_phase(self):
        # Adding handler to content phase when no handler already
        # exists for that phase.

        print("""\n  * Testing req.add_handler() for empty phase""")
        rsp = self.vhost_get("test_req_add_handler_empty_phase")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_req_add_handler_directory_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_handler_directory"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonInterpPerDirective("On"),
                                  PythonFixupHandler("tests::test_req_add_handler_directory"),
                                  PythonDebug("On")))
        return c

    def test_req_add_handler_directory(self):
        # Checking that directory is canonicalized and trailing
        # slash is added.

        print("""\n  * Testing req.add_handler() directory""")
        rsp = self.vhost_get("test_req_add_handler_directory")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_accesshandler_add_handler_to_empty_hl_conf(self):
        # Note that there is no PythonHandler specified in the the VirtualHost
        # config. We want to see if req.add_handler will work when the
        # handler list is empty.

        #PythonHandler("tests::req_add_empty_handler_string"),
        c = VirtualHost("*",
                        ServerName("test_accesshandler_add_handler_to_empty_hl"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonAccessHandler("tests::accesshandler_add_handler_to_empty_hl"),
                                  PythonDebug("On")))
        return c

    def test_accesshandler_add_handler_to_empty_hl(self):

        print("""\n  * Testing req.add_handler() when handler list is empty""")
        rsp = self.vhost_get("test_accesshandler_add_handler_to_empty_hl")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_req_allow_methods_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_allow_methods"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_allow_methods"),
                                  PythonDebug("On")))
        return c

    def test_req_allow_methods(self):

        print("\n  * Testing req.allow_methods()")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_allow_methods", PORT))
        conn.endheaders()
        response = conn.getresponse()
        server_hdr = response.getheader("Allow", "")
        conn.close()

        self.failUnless(server_hdr.find("PYTHONIZE") > -1, "req.allow_methods() didn't work")

    def test_req_unauthorized_conf(self):

        if APACHE_VERSION == '2.4':
            c = VirtualHost("*",
                            ServerName("test_req_unauthorized"),
                            DocumentRoot(DOCUMENT_ROOT),
                            Directory(DOCUMENT_ROOT,
                                      SetHandler("mod_python"),
                                      AuthName("blah"),
                                      AuthType("basic"),
                                      Require("all granted"),
                                      PythonHandler("tests::req_unauthorized"),
                                      PythonDebug("On")))
        else:
            c = VirtualHost("*",
                            ServerName("test_req_unauthorized"),
                            DocumentRoot(DOCUMENT_ROOT),
                            Directory(DOCUMENT_ROOT,
                                      SetHandler("mod_python"),
                                      AuthName("blah"),
                                      AuthType("basic"),
                                      PythonHandler("tests::req_unauthorized"),
                                      PythonDebug("On")))

        return c

    def test_req_unauthorized(self):

        print("\n  * Testing whether returning HTTP_UNAUTHORIZED works")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_unauthorized", PORT))
        auth = base64.encodestring(b"spam:eggs").strip()
        if PY2:
            conn.putheader("Authorization", "Basic %s" % auth)
        else:
            conn.putheader("Authorization", "Basic %s" % auth.decode("latin1"))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok"):
            self.fail(repr(rsp))

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_unauthorized", PORT))
        auth = base64.encodestring(b"spam:BAD PASSWD").strip()
        if PY2:
            conn.putheader("Authorization", "Basic %s" % auth)
        else:
            conn.putheader("Authorization", "Basic %s" % auth.decode("latin1"))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if response.status != UNAUTHORIZED:
            self.fail("req.status is not httplib.UNAUTHORIZED, but: %s" % repr(response.status))

        if rsp == b"test ok":
            self.fail("We were supposed to get HTTP_UNAUTHORIZED")

    def test_req_get_basic_auth_pw_conf(self):

        if APACHE_VERSION == '2.4':
            c = VirtualHost("*",
                            ServerName("test_req_get_basic_auth_pw"),
                            DocumentRoot(DOCUMENT_ROOT),
                            Directory(DOCUMENT_ROOT,
                                      SetHandler("mod_python"),
                                      AuthName("blah"),
                                      AuthType("basic"),
                                      Require("all granted"),
                                      PythonHandler("tests::req_get_basic_auth_pw"),
                                      PythonDebug("On")))
        else:
            c = VirtualHost("*",
                            ServerName("test_req_get_basic_auth_pw"),
                            DocumentRoot(DOCUMENT_ROOT),
                            Directory(DOCUMENT_ROOT,
                                      SetHandler("mod_python"),
                                      AuthName("blah"),
                                      AuthType("basic"),
                                      PythonHandler("tests::req_get_basic_auth_pw"),
                                      PythonDebug("On")))

        return c

    def test_req_get_basic_auth_pw(self):

        print("\n  * Testing req.get_basic_auth_pw()")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_get_basic_auth_pw", PORT))
        auth = base64.encodestring(b"spam:eggs").strip()
        if PY2:
            conn.putheader("Authorization", "Basic %s" % auth)
        else:
            conn.putheader("Authorization", "Basic %s" % auth.decode("latin1"))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok"):
            self.fail(repr(rsp))

    def test_req_auth_type_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_auth_type"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  AuthName("blah"),
                                  AuthType("dummy"),
                                  Require("valid-user"),
                                  PythonAuthenHandler("tests::req_auth_type"),
                                  PythonAuthzHandler("tests::req_auth_type"),
                                  PythonHandler("tests::req_auth_type"),
                                  PythonDebug("On")))
        return c

    def test_req_auth_type(self):

        print("\n  * Testing req.auth_type()")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_auth_type", PORT))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok"):
            self.fail(repr(rsp))

    def test_req_requires_conf(self):

        c = VirtualHost("*",
                    ServerName("test_req_requires"),
                    DocumentRoot(DOCUMENT_ROOT),
                    Directory(DOCUMENT_ROOT,
                              SetHandler("mod_python"),
                              AuthName("blah"),
                              AuthType("dummy"),
                              Require("valid-user"),
                              PythonAuthenHandler("tests::req_requires"),
                              PythonDebug("On")))

        return c

    def test_req_requires(self):

        print("\n  * Testing req.requires()")

        rsp = self.vhost_get("test_req_requires")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_requires", PORT))
        auth = base64.encodestring(b"spam:eggs").strip()
        if PY2:
            conn.putheader("Authorization", "Basic %s" % auth)
        else:
            conn.putheader("Authorization", "Basic %s" % auth.decode("latin1"))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok"):
            self.fail(repr(rsp))

    def test_req_internal_redirect_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_internal_redirect"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_internal_redirect | .py"),
                                  PythonHandler("tests::req_internal_redirect_int | .int"),
                                  PythonDebug("On")))
        return c

    def test_req_internal_redirect(self):

        print("\n  * Testing req.internal_redirect()")
        rsp = self.vhost_get("test_req_internal_redirect")

        if rsp != "test ok":
            self.fail("internal_redirect")

    def test_req_construct_url_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_construct_url"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_construct_url"),
                                  PythonDebug("On")))
        return c

    def test_req_construct_url(self):

        print("\n  * Testing req.construct_url()")
        rsp = self.vhost_get("test_req_construct_url")

        if rsp != "test ok":
            self.fail("construct_url")

    def test_req_read_conf(self):

        c = Container(Timeout("5"),
                      VirtualHost("*",
                                  ServerName("test_req_read"),
                                  DocumentRoot(DOCUMENT_ROOT),
                                  Directory(DOCUMENT_ROOT,
                                            SetHandler("mod_python"),
                                            PythonHandler("tests::req_read"),
                                            PythonDebug("On"))))
        return c

    def test_req_read(self):

        print("\n  * Testing req.read()")

        params = b'1234567890'*10000
        print("    writing %d bytes..." % len(params))
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_read:%s" % PORT)
        conn.putheader("Content-Length", str(len(params)))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print("    response size: %d\n" % len(rsp))
        if (rsp != params):
            self.fail(repr(rsp))

        print("    read/write ok, now lets try causing a timeout (should be 5 secs)")
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_read:%s" % PORT)
        conn.putheader("Content-Length", str(10))
        conn.endheaders()
        conn.send(b"123456789")
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if rsp.find(b"IOError") < 0 and rsp.find(b"OSError") < 0:
            self.fail("timeout test failed")


    def test_req_readline_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_readline"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_readline"),
                                  PythonDebug("On")))
        return c

    def test_req_readline(self):

        print("\n  * Testing req.readline()")

        params = (b'1234567890'*3000+b'\n')*4
        print("    writing %d bytes..." % len(params))
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_readline:%s" % PORT)
        conn.putheader("Content-Length", str(len(params)))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print("    response size: %d\n" % len(rsp))
        if (rsp != params):
            self.fail(repr(rsp))

    def test_req_readlines_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_readlines"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_readlines"),
                                  PythonDebug("On")))
        return c

    def test_req_readlines(self):

        print("\n  * Testing req.readlines()")

        params = (b'1234567890'*3000+b'\n')*4
        print("    writing %d bytes..." % len(params))
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_readlines:%s" % PORT)
        conn.putheader("Content-Length", str(len(params)))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print("    response size: %d\n" % len(rsp))
        if (rsp != params):
            self.fail(repr(rsp))

        print("\n  * Testing req.readlines(size_hint=30000)")

        params = (b'1234567890'*3000+b'\n')*4
        print("    writing %d bytes..." % len(params))
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_readlines:%s" % PORT)
        conn.putheader("Content-Length", str(len(params)))
        conn.putheader("SizeHint", str(30000))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print("    response size: %d\n" % len(rsp))
        if (rsp != (b'1234567890'*3000+b'\n')):
            self.fail(repr(rsp))

        print("\n  * Testing req.readlines(size_hint=32000)")

        params = (b'1234567890'*3000+b'\n')*4
        print("    writing %d bytes..." % len(params))
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("POST", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_readlines:%s" % PORT)
        conn.putheader("Content-Length", str(len(params)))
        conn.putheader("SizeHint", str(32000))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        print("    response size: %d\n" % len(rsp))
        if (rsp != ((b'1234567890'*3000+b'\n')*2)):
            self.fail(repr(rsp))

    def test_req_discard_request_body_conf(self):

        c = Container(Timeout("5"),
                      VirtualHost("*",
                                  ServerName("test_req_discard_request_body"),
                                  DocumentRoot(DOCUMENT_ROOT),
                                  Directory(DOCUMENT_ROOT,
                                            SetHandler("mod_python"),
                                            PythonHandler("tests::req_discard_request_body"),
                                            PythonDebug("On"))))
        return c

    def test_req_discard_request_body(self):

        print("\n  * Testing req.discard_request_body()")

        params = b'1234567890'*2
        print("    writing %d bytes..." % len(params))
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_req_discard_request_body:%s" % PORT)
        conn.putheader("Content-Length", str(len(params)))
        conn.endheaders()
        conn.send(params)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok"):
            self.fail(repr(rsp))

    def test_req_register_cleanup_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_register_cleanup"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_register_cleanup"),
                                  PythonDebug("On")))
        return c

    def test_req_register_cleanup(self):

        print("\n  * Testing req.register_cleanup()")

        rsp = self.vhost_get("test_req_register_cleanup")

        # see what's in the log now
        time.sleep(1)
        f = open(os.path.join(SERVER_ROOT, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("req_register_cleanup test ok") == -1:
            self.fail("Could not find test message in error_log")

    def test_req_headers_out_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_headers_out"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_headers_out"),
                                  PythonDebug("On")))
        return c

    def test_req_headers_out(self):

        print("\n  * Testing req.headers_out")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/test.py", skip_host=1)
        conn.putheader("Host", "test_req_headers_out:%s" % PORT)
        conn.endheaders()
        response = conn.getresponse()
        h = response.getheader("x-test-header", None)
        response.read()
        conn.close()

        if h is None:
            self.fail("Could not find x-test-header")

        if h != "test ok":
            self.fail("x-test-header is there, but does not contain 'test ok'")

    def test_req_sendfile_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_sendfile"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_sendfile"),
                                  PythonDebug("On")))

        return c

    def test_req_sendfile(self):

        print("\n  * Testing req.sendfile() with offset and length")

        rsp = self.vhost_get("test_req_sendfile")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_req_sendfile2_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_sendfile2"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_sendfile2"),
                                  PythonDebug("On")))

        return c

    def test_req_sendfile2(self):

        print("\n  * Testing req.sendfile() without offset and length")

        rsp = self.vhost_get("test_req_sendfile2")

        if (rsp != "0123456789"*100):
            self.fail(repr(rsp))

    def test_req_sendfile3_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_sendfile3"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_sendfile3"),
                                  PythonDebug("On")))

        return c

    def test_req_sendfile3(self):

        if os.name == 'posix':

            print("\n  * Testing req.sendfile() for a file which is a symbolic link")

            rsp = self.vhost_get("test_req_sendfile3")

            if (rsp != "0123456789"*100):
                self.fail(repr(rsp))
        else:
            print("\n  * Skipping req.sendfile() for a file which is a symbolic link")

    def test_req_handler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_handler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  PythonFixupHandler("tests::req_handler"),
                                  PythonDebug("On")))
        return c

    def test_req_handler(self):

        print("\n  * Testing req.handler")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_handler", PORT))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok"):
            self.fail(repr(rsp))

    def test_req_no_cache_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_no_cache"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_no_cache"),
                                  PythonDebug("On")))
        return c

    def test_req_no_cache(self):

        print("\n  * Testing req.no_cache")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_no_cache", PORT))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if response.getheader("expires", None) is None:
            self.fail(repr(response.getheader("expires", None)))

        if (rsp != b"test ok"):
            self.fail(repr(rsp))

    def test_req_update_mtime_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_update_mtime"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_update_mtime"),
                                  PythonDebug("On")))
        return c

    def test_req_update_mtime(self):

        print("\n  * Testing req.update_mtime")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_req_update_mtime", PORT))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if response.getheader("etag", None) is None:
            self.fail(repr(response.getheader("etag", None)))

        if response.getheader("last-modified", None) is None:
            self.fail(repr(response.getheader("last-modified", None)))

        if (rsp != b"test ok"):
            self.fail(repr(rsp))

    def test_util_redirect_conf(self):

        c = VirtualHost("*",
                        ServerName("test_util_redirect"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  PythonFixupHandler("tests::util_redirect"),
                                  PythonHandler("tests::util_redirect"),
                                  PythonDebug("On")))
        return c

    def test_util_redirect(self):

        print("\n  * Testing util.redirect()")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_util_redirect", PORT))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if response.status != 302:
            self.fail('did not receive 302 status response: %s' % repr(response.status))

        if response.getheader("location", None) != "/dummy":
            self.fail('did not receive correct location for redirection')

        if rsp != b"test ok":
            self.fail(repr(rsp))

    def test_req_server_get_config_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_server_get_config"),
                        DocumentRoot(DOCUMENT_ROOT),
                        PythonDebug("On"),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_server_get_config"),
                                  PythonDebug("Off")))
        return c

    def test_req_server_get_config(self):

        print("\n  * Testing req.server.get_config()")

        rsp = self.vhost_get("test_req_server_get_config")
        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_req_server_get_options_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_server_get_options"),
                        DocumentRoot(DOCUMENT_ROOT),
                        PythonDebug("Off"),
                        PythonOption("global 1"),
                        PythonOption("override 1"),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::req_server_get_options"),
                                  PythonOption("local 1"),
                                  PythonOption("override 2"),
                                  PythonDebug("On")))
        return c

    def test_req_server_get_options(self):

        print("\n  * Testing req.server.get_options()")

        rsp = self.vhost_get("test_req_server_get_options")
        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_fileupload_conf(self):

        c = VirtualHost("*",
                        ServerName("test_fileupload"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::fileupload"),
                                  PythonDebug("On")))

        return c

    def test_fileupload(self):

        print("\n  * Testing 1 MB file upload support")

        content = ''.join( [ chr(random.randrange(256)) for x in range(1024*1024) ] )
        digest = md5_hash(content)

        rsp = self.vhost_post_multipart_form_data(
            "test_fileupload",
            variables={'test':'abcd'},
            files={'testfile':('test.txt',content)},
        )

        if (rsp != digest):
            self.fail('1 MB file upload failed, its contents were corrupted. Expected (%s), got (%s)' % (repr(digest), repr(rsp)))

    def test_fileupload_embedded_cr_conf(self):

        c = VirtualHost("*",
                        ServerName("test_fileupload"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::fileupload"),
                                  PythonDebug("On")))

        return c

    def test_fileupload_embedded_cr(self):
        # Strange things can happen if there is a '\r' character at position
        # readBlockSize of a line being read by FieldStorage.read_to_boundary
        # where the line length is > readBlockSize.
        # This test will expose this problem.

        print("\n  * Testing file upload with \\r char in a line at position == readBlockSize")

        content = (
            'a'*100 + '\r\n'
            + 'b'*(readBlockSize-1) + '\r' # trick !
            + 'ccc' + 'd'*100 + '\r\n'
        )
        digest = md5_hash(content)

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
            ugh = open('ugh.pdf','rb')
            content = ugh.read()
            ugh.close()
        except:
            print("  * Skipping the test for The UNIX-HATERS handbook file upload.")
            print("    To make this test, you need to download ugh.pdf from")
            print("    http://web.mit.edu/~simsong/www/ugh.pdf")
            print("    into this script's directory.")
        else:
            print("  * Testing The UNIX-HATERS handbook file upload support")

            digest = md5_hash(content)

            rsp = self.vhost_post_multipart_form_data(
                "test_fileupload",
                variables={'test':'abcd'},
                files={'testfile':('ugh.pdf',content)},
            )


            if (rsp != digest):
                self.fail('The UNIX-HATERS handbook file upload failed, its contents was corrupted (%s)'%rsp)

    def test_fileupload_split_boundary_conf(self):

        c = VirtualHost("*",
                        ServerName("test_fileupload"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::fileupload"),
                                  PythonDebug("On")))

        return c

    def test_fileupload_split_boundary(self):
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

        print("\n  * Testing file upload where length of last line == readBlockSize - 1")

        content = (
            'a'*100 + '\r\n'
            + 'b'*(readBlockSize-1)  # trick !
        )
        digest = md5_hash(content)

        rsp = self.vhost_post_multipart_form_data(
            "test_fileupload",
            variables={'test':'abcd'},
            files={'testfile':('test.txt',content)},
        )

        if (rsp != digest):
            self.fail('file upload long line test failed, its contents were corrupted (%s)'%rsp)

        print("  * Testing file upload where length of last line == readBlockSize - 1 with an extra \\r")

        content = (
            'a'*100 + '\r\n'
            + 'b'*(readBlockSize-1)
            + '\r'  # second trick !
        )
        digest = md5_hash(content)

        rsp = self.vhost_post_multipart_form_data(
            "test_fileupload",
            variables={'test':'abcd'},
            files={'testfile':('test.txt',content)},
        )

        if (rsp != digest):
            self.fail('file upload long line test failed, its contents were corrupted (%s)'%rsp)

    def test_sys_argv_conf(self):

        c = VirtualHost("*",
                        ServerName("test_sys_argv"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::test_sys_argv"),
                                  PythonDebug("On")))

        return c

    def test_sys_argv(self):

        print("\n  * Testing sys.argv definition")

        rsp = self.vhost_get("test_sys_argv")

        if (rsp != "['mod_python']"):
            self.fail(repr(rsp))

    def test_PythonOption_conf(self):

        c = VirtualHost("*",
                        ServerName("test_PythonOption"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::PythonOption_items"),
                                  PythonDebug("On")))

        return c

    def test_PythonOption(self):

        print("\n  * Testing PythonOption")

        rsp = self.vhost_get("test_PythonOption")

        if (rsp != "[('PythonOptionTest', 'sample_value')]"):
            self.fail(repr(rsp))

    def test_PythonOption_override_conf(self):

        c = VirtualHost("*",
                        ServerName("test_PythonOption_override"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::PythonOption_items"),
                                  PythonOption('PythonOptionTest "new_value"'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonDebug("On")))

        return c

    def test_PythonOption_override(self):

        print("\n  * Testing PythonOption override")

        rsp = self.vhost_get("test_PythonOption_override")

        if (rsp != "[('PythonOptionTest', 'new_value'), ('PythonOptionTest2', 'new_value2')]"):
            self.fail(repr(rsp))

    def test_PythonOption_remove_conf(self):

        c = VirtualHost("*",
                        ServerName("test_PythonOption_remove"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::PythonOption_items"),
                                  PythonOption('PythonOptionTest ""'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonDebug("On")))

        return c

    def test_PythonOption_remove(self):

        print("\n  * Testing PythonOption remove")

        rsp = self.vhost_get("test_PythonOption_remove")

        if (rsp != "[('PythonOptionTest2', 'new_value2')]"):
            self.fail(repr(rsp))

    def test_PythonOption_remove2_conf(self):

        c = VirtualHost("*",
                        ServerName("test_PythonOption_remove2"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::PythonOption_items"),
                                  PythonOption('PythonOptionTest'),
                                  PythonOption('PythonOptionTest2 "new_value2"'),
                                  PythonOption('PythonOptionTest3 new_value3'),
                                  PythonDebug("On")))

        return c

    def test_PythonOption_remove2(self):

        print("\n  * Testing PythonOption remove2")

        rsp = self.vhost_get("test_PythonOption_remove2")

        if (rsp != "[('PythonOptionTest2', 'new_value2'), ('PythonOptionTest3', 'new_value3')]"):
            self.fail(repr(rsp))

    def test_interpreter_per_directive_conf(self):

        c = VirtualHost("*",
                        ServerName("test_interpreter_per_directive"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  PythonInterpPerDirective('On'),
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::interpreter"),
                                  PythonDebug("On")))

        return c

    def test_interpreter_per_directive(self):

        print("\n  * Testing interpreter per directive")

        interpreter_name = (DOCUMENT_ROOT.replace('\\', '/')+'/').upper()

        rsp = self.vhost_get("test_interpreter_per_directive").upper()
        if (rsp != interpreter_name):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_interpreter_per_directive", '/subdir/foo.py').upper()
        if (rsp != interpreter_name):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_interpreter_per_directive", '/subdir/').upper()
        if (rsp != interpreter_name):
            self.fail(repr(rsp))

    def test_interpreter_per_directory_conf(self):

        c = VirtualHost("*",
                        ServerName("test_interpreter_per_directory"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  PythonInterpPerDirectory('On'),
                                  SetHandler("mod_python"),
                                  PythonFixupHandler("tests::interpreter"),
                                  PythonDebug("On")),
                        )

        return c

    def test_interpreter_per_directory(self):

        print("\n  * Testing interpreter per directory")

        interpreter_name = (DOCUMENT_ROOT.replace('\\', '/')+'/').upper()

        rsp = self.vhost_get("test_interpreter_per_directory").upper()
        if (rsp != interpreter_name):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_interpreter_per_directory", '/subdir/foo.py').upper()
        if (rsp != interpreter_name+'SUBDIR/'):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_interpreter_per_directory", '/subdir/').upper()
        if (rsp != interpreter_name+'SUBDIR/'):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_interpreter_per_directory", '/subdir').upper()
        if (rsp != interpreter_name+'SUBDIR/'):
            self.fail(repr(rsp))

    def test_util_fieldstorage_conf(self):

        c = VirtualHost("*",
                        ServerName("test_util_fieldstorage"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::util_fieldstorage"),
                                  PythonDebug("On")))
        return c

    def test_util_fieldstorage(self):

        print("\n  * Testing util_fieldstorage()")

        params = urlencode([('spam', 1), ('spam', 2), ('eggs', 3), ('bacon', 4)])
        headers = {"Host": "test_util_fieldstorage",
                   "Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.request("POST", "/tests.py", params, headers)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != "[Field('spam', '1'), Field('spam', '2'), Field('eggs', '3'), Field('bacon', '4')]" and
            rsp != b"[Field(b'spam', b'1'), Field(b'spam', b'2'), Field(b'eggs', b'3'), Field(b'bacon', b'4')]"):
            self.fail(repr(rsp))

    def test_postreadrequest_conf(self):

        c = VirtualHost("*",
                        ServerName("test_postreadrequest"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonPostReadRequestHandler("tests::postreadrequest"),
                        PythonDebug("On"))
        return c

    def test_postreadrequest(self):

        print("\n  * Testing PostReadRequestHandler")
        rsp = self.vhost_get("test_postreadrequest")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_trans_conf(self):

        c = VirtualHost("*",
                        ServerName("test_trans"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonTransHandler("tests::trans"),
                        PythonDebug("On"))
        return c

    def test_trans(self):

        print("\n  * Testing TransHandler")
        rsp = self.vhost_get("test_trans")

        if (rsp[0:2] != " #"): # first line in tests.py
            self.fail(repr(rsp))

    def test_import_conf(self):

        # configure apache to import it at startup
        c = Container(PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                      PythonImport("dummymodule test_import"),
                      PythonImport("dummymodule::function test_import"),
                      VirtualHost("*",
                                  ServerName("test_import"),
                                  DocumentRoot(DOCUMENT_ROOT),
                                  Directory(DOCUMENT_ROOT,
                                            SetHandler("mod_python"),
                                            PythonHandler("tests::import_test"),
                                            PythonDebug("On"))))
        return c

    def test_import(self):

        print("\n  * Testing PythonImport")
        rsp = self.vhost_get("test_import")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_outputfilter_conf(self):

        c = VirtualHost("*",
                        ServerName("test_outputfilter"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonHandler("tests::simplehandler"),
                        PythonOutputFilter("tests::outputfilter MP_TEST_FILTER"),
                        PythonDebug("On"),
                        AddOutputFilter("MP_TEST_FILTER .py"))
        return c

    def test_outputfilter(self):

        print("\n  * Testing PythonOutputFilter")
        rsp = self.vhost_get("test_outputfilter")

        if (rsp != "TEST OK"):
            self.fail(repr(rsp))

    def test_req_add_output_filter_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_add_output_filter"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonHandler("tests::req_add_output_filter"),
                        PythonOutputFilter("tests::outputfilter MP_TEST_FILTER"),
                        PythonDebug("On"))
        return c

    def test_req_add_output_filter(self):

        print("\n  * Testing req.add_output_filter")
        rsp = self.vhost_get("test_req_add_output_filter")

        if (rsp != "TEST OK"):
            self.fail(repr(rsp))

    def test_req_register_output_filter_conf(self):

        c = VirtualHost("*",
                        ServerName("test_req_register_output_filter"),
                        DocumentRoot(DOCUMENT_ROOT),
                        SetHandler("mod_python"),
                        PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                        PythonHandler("tests::req_register_output_filter"),
                        PythonDebug("On"))
        return c

    def test_req_register_output_filter(self):

        print("\n  * Testing req.register_output_filter")
        rsp = self.vhost_get("test_req_register_output_filter")

        if (rsp != "TEST OK"):
            self.fail(repr(rsp))

    def test_connectionhandler_conf(self):

        try:
            localip = socket.gethostbyname("localhost")
        except:
            localip = "127.0.0.1"

        self.conport = findUnusedPort()
        c = Container(Listen("%d" % self.conport),
                      VirtualHost("%s:%d" % (localip, self.conport),
                                  SetHandler("mod_python"),
                                  PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                                  PythonConnectionHandler("tests::connectionhandler")))
        return c

    def test_connectionhandler(self):

        print("\n  * Testing PythonConnectionHandler on port %d" % self.conport)

        url = "http://127.0.0.1:%s/tests.py" % self.conport
        f = urlopen(url)
        if PY2:
            rsp = f.read()
        else:
            rsp = f.read().decode('latin1')
        f.close()

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_internal_conf(self):

        c = VirtualHost("*",
                        ServerName("test_internal"),
                        ServerAdmin("serveradmin@somewhere.com"),
                        ErrorLog("logs/error_log"),
                        ServerPath("some/path"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests"),
                                  PythonOption('PythonOptionTest ""'),
                                  PythonOption('mod_python.mutex_directory ""'),
                                  PythonOption("testing 123"),
                                  PythonDebug("On")))
        return c

    def test_internal(self):

        print("\n  * Testing internally (status messages go to error_log)")

        rsp = self.vhost_get("test_internal")
        if (rsp[-7:] != "test ok"):
            self.fail("Some tests failed, see error_log")

    def test_pipe_ext_conf(self):

        c = VirtualHost("*",
                        ServerName("test_pipe_ext"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher | .py"),
                                  PythonHandler("tests::simplehandler"),
                                  PythonDebug("On")))
        return c

    def test_pipe_ext(self):

        print("\n  * Testing | .ext syntax")

        rsp = self.vhost_get("test_pipe_ext", path="/tests.py/pipe_ext")
        if (rsp[-8:] != "pipe ext"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_pipe_ext", path="/tests/anything")
        if (rsp[-7:] != "test ok"):
            self.fail(repr(rsp))

    def test_wsgihandler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_wsgihandler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.wsgi"),
                                  PythonOption("mod_python.wsgi.application wsgitest"),
                                  PythonDebug("On")))
        return c

    def test_wsgihandler(self):

        print("\n  * Testing mod_python.wsgi")

        rsp = self.vhost_get("test_wsgihandler")
        if (rsp[-8:] != "test ok\n"):
            self.fail(repr(rsp))

        # see what's in the log now
        time.sleep(0.1)
        log = open(os.path.join(SERVER_ROOT, "logs/error_log")).read()
        if "written_from_wsgi_test" not in log:
            self.fail("string 'written_from_wsgi_test' not found in error log.")

    def test_wsgihandler_location_conf(self):

        c = VirtualHost("*",
                        ServerName("test_wsgihandler_location"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Location("/foo",
                                 SetHandler("mod_python"),
                                 PythonHandler("mod_python.wsgi"),
                                 PythonPath("[r'%s']+sys.path" % DOCUMENT_ROOT),
                                 PythonOption("mod_python.wsgi.application wsgitest::base_uri"),
                                 PythonDebug("On")))
        return c

    def test_wsgihandler_location(self):

        print("\n  * Testing mod_python.wsgi")

        rsp = self.vhost_get("test_wsgihandler_location", "/foo/bar")
        if (rsp[-8:] != "test ok\n"):
            self.fail(repr(rsp))

    def test_cgihandler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_cgihandler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.cgihandler"),
                                  PythonDebug("On")))
        return c

    def test_cgihandler(self):

        print("\n  * Testing mod_python.cgihandler")

        rsp = self.vhost_get("test_cgihandler", path="/cgitest.py")

        if (rsp[-8:] != "test ok\n"):
            self.fail(repr(rsp))

    def test_psphandler_conf(self):

        c = VirtualHost("*",
                        ServerName("test_psphandler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.psp"),
                                  PythonDebug("On")))
        return c

    def test_psphandler(self):

        print("\n  * Testing mod_python.psp")

        rsp = self.vhost_get("test_psphandler", path="/psptest.psp")
        if (rsp[-8:] != "test ok\n"):
            self.fail(repr(rsp))

    def test_psp_parser_conf(self):

        c = VirtualHost("*",
                        ServerName("test_psp_parser"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.psp"),
                                  PythonDebug("On")))
        return c

    def test_psp_parser(self):

        print("\n  * Testing mod_python.psp parser")
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
                failures.append(test_case)
            #print 'expect{%s} got{%s}' % (expected_result, test_string)

        if failures:
            msg = 'psp_parser parse errors for: %s' % (', '.join(failures))
            self.fail(msg)

    def test_psp_error_conf(self):

        c = VirtualHost("*",
                        ServerName("test_psp_error"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.psp"),
                                  PythonOption('mod_python.session.database_directory "%s"' % TMP_DIR),
                                  PythonDebug("On")))
        return c

    def test_psp_error(self):

        print("\n  * Testing mod_python.psp error page")

        rsp = self.vhost_get("test_psp_error", path="/psptest_main.psp")
        if (rsp.strip().split() != ["okay","fail"]):
            self.fail(repr(rsp))

    def test_Cookie_Cookie_conf(self):

        c = VirtualHost("*",
                        ServerName("test_Cookie_Cookie"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::Cookie_Cookie"),
                                  PythonDebug("On")))
        return c

    def test_Cookie_Cookie(self):

        print("\n  * Testing Cookie.Cookie")


        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        # this is three cookies, nastily formatted
        conn.putheader("Host", "test_Cookie_Cookie:%s" % PORT)
        conn.putheader("Cookie", "spam=foo; path=blah;;eggs=bar;")
        conn.putheader("Cookie", "bar=foo")
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != b"test ok" or ('path=blah' not in setcookie or
                                 'eggs=bar'  not in setcookie or
                                 'bar=foo'   not in setcookie or
                                 'spam=foo'  not in setcookie):
            print(repr(rsp))
            print(repr(setcookie))
            self.fail("cookie parsing failed")

    def test_Cookie_MarshalCookie_conf(self):

        c = VirtualHost("*",
                        ServerName("test_Cookie_MarshalCookie"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::Cookie_Cookie"),
                                  PythonDebug("On")))
        return c

    def test_Cookie_MarshalCookie(self):

        print("\n  * Testing Cookie.MarshalCookie")

        mc = "eggs=d049b2b61adb6a1d895646719a3dc30bcwQAAABzcGFt"

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        conn.putheader("Host", "test_Cookie_MarshalCookie:%s" % PORT)
        conn.putheader("Cookie", mc)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != b"test ok" or setcookie != mc:
            print(repr(rsp))
            self.fail("marshalled cookie parsing failed")

        # and now a long MarshalledCookie test !

        mc = ('test=859690207856ec75fc641a7566894e40c1QAAAB0'
             'aGlzIGlzIGEgdmVyeSBsb25nIHZhbHVlLCBsb25nIGxvb'
             'mcgbG9uZyBsb25nIGxvbmcgc28gbG9uZyBidXQgd2UnbG'
             'wgZmluaXNoIGl0IHNvb24=')

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/testz.py", skip_host=1)
        conn.putheader("Host", "test_Cookie_MarshalCookie:%s" % PORT)
        conn.putheader("Cookie", mc)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != b"test ok" or setcookie != mc:
            print(repr(rsp))
            self.fail("long marshalled cookie parsing failed")

    def test_Session_Session_conf(self):

        c = VirtualHost("*",
                        ServerName("test_Session_Session"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::Session_Session"),
                                  PythonOption('mod_python.session.database_directory "%s"' % TMP_DIR),
                                  PythonOption('mod_python.session.application_path "/path"'),
                                  PythonOption('mod_python.session.application_domain "test_Session_Session"'),
                                  PythonDebug("On")))
        return c

    def test_Session_Session(self):

        print("\n  * Testing Session.Session")

        conn = http_connection("127.0.0.1:%s" % PORT)
        #conn.set_debuglevel(1000)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_Session_Session:%s" % PORT)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        rsp = response.read()
        conn.close()

        if rsp != b"test ok" or setcookie == None:
            self.fail("session did not set a cookie")

        parts = setcookie.split('; ')
        fields = {}
        for part in parts:
          key, value = part.split('=')
          fields[key] = value

        if 'path' not in fields or fields['path'] != '/path':
            self.fail("session did not contain expected 'path'")

        if 'domain' not in fields or fields['domain'] != 'test_Session_Session':
            self.fail("session did not contain expected 'domain'")

        conn = http_connection("127.0.0.1:%s" % PORT)
        #conn.set_debuglevel(1000)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_Session_Session:%s" % PORT)
        conn.putheader("Cookie", setcookie)
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()
        if rsp != b"test ok":
            self.fail("session did not accept our cookie: %s" % repr(rsp))

    def test_Session_illegal_sid_conf(self):

        c = VirtualHost("*",
                        ServerName("test_Session_Session"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::Session_Session"),
                                  PythonOption('mod_python.session.database_directory "%s"' % TMP_DIR),
                                  PythonDebug("On")))
        return c

    def test_Session_illegal_sid(self):

        print("\n  * Testing Session with illegal session id value")
        bad_cookie = 'pysid=/path/traversal/attack/bad; path=/'
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_Session_Session:%s" % PORT)
        conn.putheader("Cookie", bad_cookie)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        status = response.status
        conn.close()
        if status != 200 or not setcookie:
            self.fail("session id with illegal characters not replaced")

        bad_cookie = 'pysid=%s; path=/' % ('abcdef'*64)
        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_Session_Session:%s" % PORT)
        conn.putheader("Cookie", bad_cookie)
        conn.endheaders()
        response = conn.getresponse()
        setcookie = response.getheader("set-cookie", None)
        status = response.status
        conn.close()
        if status != 200 or not setcookie:
            self.fail("session id which is too long not replaced")

    def test_files_directive_conf(self):
        c = VirtualHost("*",
                        ServerName("test_files_directive"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  Files("*.py",
                                        SetHandler("mod_python"),
                                        PythonHandler("tests::files_directive"),
                                        PythonDebug("On"))))
        return c

    def test_files_directive(self):

        directory = (DOCUMENT_ROOT.replace('\\', '/')+'/').upper()

        print("\n  * Testing Files directive")
        rsp = self.vhost_get("test_files_directive", path="/tests.py").upper()

        if rsp != directory:
            self.fail(repr(rsp))

    def test_none_handler_conf(self):
        c = VirtualHost("*",
                        ServerName("test_none_handler"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::none_handler"),
                                  PythonDebug("On")))
        return c

    def test_none_handler(self):

        print("\n  * Testing None handler")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py", skip_host=1)
        conn.putheader("Host", "test_none_handler:%s" % PORT)
        conn.endheaders()
        response = conn.getresponse()
        status = response.status
        rsp = response.read()
        conn.close()
        if status != 500:
            print(status, rsp)
            self.fail("none handler should generate error")

    def test_server_return_conf(self):
        c = VirtualHost("*",
                        ServerName("test_server_return"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::server_return_1"),
                                  PythonHandler("tests::server_return_2"),
                                  PythonDebug("On")))
        return c

    def test_server_return(self):

        print("\n  * Testing SERVER_RETURN")
        rsp = self.vhost_get("test_server_return")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_phase_status_conf(self):
        c = VirtualHost("*",
                        ServerName("test_phase_status"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
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
                                  PythonHandler("tests::phase_status_8"),
                                  PythonCleanupHandler("tests::phase_status_cleanup"),
                                  PythonDebug("On")))
        return c

    def test_phase_status(self):

        print("\n  * Testing phase status")
        rsp = self.vhost_get("test_phase_status")

        if (rsp != "test ok"):
            self.fail(repr(rsp))

        # see what's in the log now
        time.sleep(0.1)
        log = open(os.path.join(SERVER_ROOT, "logs/error_log")).read()
        if "phase_status_cleanup_log_entry" not in log:
            self.fail("phase_status_cleanup_log_entry not found in logs, cleanup handler never ran?")

    def test_publisher_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher(self):
        print("\n  * Testing mod_python.publisher")

        rsp = self.vhost_get("test_publisher", path="/tests.py")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher", path="/tests.py/index")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher", path="/tests.py/test_publisher")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher", path="/")
        if (rsp != "test 1 ok, interpreter=test_publisher"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher", path="/foobar")
        if (rsp != "test 2 ok, interpreter=test_publisher"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher", path="/tests")
        if (rsp != "test ok, interpreter=test_publisher"):
            self.fail(repr(rsp))

    def test_publisher_auth_nested_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher_auth_nested"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_auth_nested(self):
        print("\n  * Testing mod_python.publisher auth nested")

        conn = http_connection("127.0.0.1:%s" % PORT)
        #conn.set_debuglevel(1000)
        conn.putrequest("GET", "/tests.py/test_publisher_auth_nested", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_publisher_auth_nested", PORT))
        auth = base64.encodestring(b"spam:eggs").strip()
        if PY2:
            conn.putheader("Authorization", "Basic %s" % auth)
        else:
            conn.putheader("Authorization", "Basic %s" % auth.decode("latin1"))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok, interpreter=test_publisher_auth_nested"):
            self.fail(repr(rsp))

    def test_publisher_auth_method_nested_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher_auth_method_nested"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_auth_method_nested(self):
        print("\n  * Testing mod_python.publisher auth method nested")

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py/test_publisher_auth_method_nested/method", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_publisher_auth_method_nested", PORT))
        auth = base64.encodestring(b"spam:eggs").strip()
        if PY2:
            conn.putheader("Authorization", "Basic %s" % auth)
        else:
            conn.putheader("Authorization", "Basic %s" % auth.decode("latin1"))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok, interpreter=test_publisher_auth_method_nested"):
            self.fail(repr(rsp))

    def test_publisher_auth_digest_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher_auth_digest"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_auth_digest(self):
        print("\n  * Testing mod_python.publisher auth digest compatability")

        # The contents of the authorization header is not relevant,
        # as long as it looks valid.

        conn = http_connection("127.0.0.1:%s" % PORT)
        conn.putrequest("GET", "/tests.py/test_publisher", skip_host=1)
        conn.putheader("Host", "%s:%s" % ("test_publisher_auth_digest", PORT))
        conn.putheader("Authorization", 'Digest username="Mufasa", realm="testrealm@host.com", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", uri="/dir/index.html", qop=auth, nc=00000001, cnonce="0a4f113b", response="6629fae49393a05397450978507c4ef1", opaque="5ccc069c403ebaf9f0171e9517f40e41"')
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        if (rsp != b"test ok, interpreter=test_publisher_auth_digest"):
            self.fail(repr(rsp))

    def test_publisher_security_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_security(self):
        print("\n  * Testing mod_python.publisher security")

        def get_status(path):
            conn = http_connection("127.0.0.1:%s" % PORT)
            #conn.set_debuglevel(1000)
            conn.putrequest("GET", path, skip_host=1)
            conn.putheader("Host", "test_publisher:%s" % PORT)
            conn.endheaders()
            response = conn.getresponse()
            status, response = response.status, response.read()
            conn.close()
            return status, response

        status, response = get_status("/tests.py/_SECRET_PASSWORD")
        if status != 403:
            self.fail('Vulnerability : underscore prefixed attribute (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/__ANSWER")
        if status != 403:
            self.fail('Vulnerability : underscore prefixed attribute (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/re")
        if status != 403:
            self.fail('Vulnerability : module published (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/OldStyleClassTest")
        if status != 403:
            self.fail('Vulnerability : old style class published (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/InstanceTest")
        if status != 403:
            self.fail('Vulnerability : new style class published (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/index/func_code")
        if status != 403:
            self.fail('Vulnerability : function traversal (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/old_instance/traverse/func_code")
        if status != 403:
            self.fail('Vulnerability : old-style method traversal (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/instance/traverse/func_code")
        if status != 403:
            self.fail('Vulnerability : new-style method traversal (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/test_dict/keys")
        if status != 403:
            self.fail('Vulnerability : built-in type traversal (%i)\n%s' % (status, response))

        status, response = get_status("/tests.py/test_dict_keys")
        if status != 403:
            self.fail('Vulnerability : built-in type publishing (%i)\n%s' % (status, response))

    def test_publisher_iterator_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_iterator(self):
        print("\n  * Testing mod_python.publisher iterators")

        rsp = self.vhost_get("test_publisher", path="/tests.py/test_dict_iteration")
        if (rsp != "123"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher", path="/tests.py/test_generator")
        if (rsp != "0123456789"):
            self.fail(repr(rsp))

    def test_publisher_hierarchy_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher_hierarchy"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_hierarchy(self):
        print("\n  * Testing mod_python.publisher hierarchy")

        rsp = self.vhost_get("test_publisher_hierarchy", path="/tests.py/hierarchy_root")
        if (rsp != "Called root"):
            self.fail(repr(rsp))

        if PY2:
            rsp = self.vhost_get("test_publisher_hierarchy", path="/tests.py/hierarchy_root_2")
            if (rsp != "test ok, interpreter=test_publisher_hierarchy"):
                self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher_hierarchy", path="/tests.py/hierarchy_root/page1")
        if (rsp != "Called page1"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher_hierarchy", path="/tests.py/hierarchy_root_2/page1")
        if (rsp != "test ok, interpreter=test_publisher_hierarchy"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher_hierarchy", path="/tests.py/hierarchy_root/page1/subpage1")
        if (rsp != "Called subpage1"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher_hierarchy", path="/tests.py/hierarchy_root/page2")
        if (rsp != "Called page2"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher_hierarchy", path="/tests.py/hierarchy_root_2/page2")
        if (rsp != "test ok, interpreter=test_publisher_hierarchy"):
            self.fail(repr(rsp))

    def test_publisher_old_style_instance_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_old_style_instance(self):
        print("\n  * Testing mod_python.publisher old-style instance publishing")

        rsp = self.vhost_get("test_publisher", path="/tests.py/old_instance")
        if (rsp != "test callable old-style instance ok"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher", path="/tests.py/old_instance/traverse")
        if (rsp != "test traversable old-style instance ok"):
            self.fail(repr(rsp))

    def test_publisher_instance_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_instance(self):
        print("\n  * Testing mod_python.publisher instance publishing")

        rsp = self.vhost_get("test_publisher", path="/tests.py/instance")
        if (rsp != "test callable instance ok"):
            self.fail(repr(rsp))

        rsp = self.vhost_get("test_publisher", path="/tests.py/instance/traverse")
        if (rsp != "test traversable instance ok"):
            self.fail(repr(rsp))

    def test_publisher_cache_conf(self):
        c = VirtualHost("*",
                        ServerName("test_publisher"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("mod_python.publisher"),
                                  PythonDebug("On")))
        return c

    def test_publisher_cache(self):
        ## It is not possible to get reliable results with this test
        #  for mpm-prefork and worker, and in fact it may not be possible
        #  to get consistent results.
        #  Therefore this test is currently disabled in the
        #  testPerRequestTests setup.

        print("\n  * Testing mod_python.publisher cache")

        def write_published():
            published = file('htdocs/temp.py','wb')
            published.write('import time\n')
            published.write('LOAD_TIME = time.time()\n')
            published.write('def index(req):\n')
            published.write('    return "OK %f"%LOAD_TIME\n')
            published.close()

        write_published()
        try:
            rsp = self.vhost_get("test_publisher", path="/temp.py")

            if not rsp.startswith('OK '):
                self.fail(repr(rsp))

            rsp2 = self.vhost_get("test_publisher", path="/temp.py")
            if rsp != rsp2:
                self.fail(
                    "The publisher cache has reloaded a published module"
                    " even though it wasn't modified !"
                )

            # We wait three seconds to be sure we won't be annoyed
            # by any lack of resolution of the stat().st_mtime member.
            time.sleep(3)
            write_published()

            rsp2 = self.vhost_get("test_publisher", path="/temp.py")
            if rsp == rsp2:
                self.fail(
                    "The publisher cache has not reloaded a published module"
                    " even though it was modified !"
                )

            rsp = self.vhost_get("test_publisher", path="/temp.py")
            if rsp != rsp2:
                self.fail(
                    "The publisher cache has reloaded a published module"
                    " even though it wasn't modified !"
                )
        finally:
            os.remove('htdocs/temp.py')

    def test_server_side_include_conf(self):
        c = VirtualHost("*",
                        ServerName("test_server_side_include"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  Options("+Includes"),
                                  AddType("text/html .shtml"),
                                  AddOutputFilter("INCLUDES .shtml"),
                                  PythonFixupHandler("tests::server_side_include"),
                                  PythonDebug("On")))
        return c

    def test_server_side_include(self):

        print("\n  * Testing server side include")
        rsp = self.vhost_get("test_server_side_include", path="/ssi.shtml")

        rsp = rsp.strip()

        if (rsp != "test ok"):
            self.fail(repr(rsp))

    def test_memory_conf(self):

        c = VirtualHost("*",
                        ServerName("test_memory"),
                        DocumentRoot(DOCUMENT_ROOT),
                        Directory(DOCUMENT_ROOT,
                                  SetHandler("mod_python"),
                                  PythonHandler("tests::memory"),
                                  PythonDebug("On")))
        return c


    def test_memory(self):

        # Note: This test will fail on Apache 2.2 because of a bug,
        # but will pass on 2.4 where it is fixed (2.4 reuses the
        # brigade on ap_rflush() rather than creating a new one each
        # time). http://modpython.org/pipermail/mod_python/2007-July/023974.html

        print("\n  * Testing req.write() and req.flush() memory usage (100,000 iterations)")
        rsp = self.vhost_get("test_memory")

        before, after = list(map(int, rsp.split("|")[1:]))

        if before != after:
            self.fail("Memory before: %s, memory after: %s" % (before, after))

class PerInstanceTestCase(unittest.TestCase, HttpdCtrl):
    # this is a test case which requires a complete
    # restart of httpd (e.g. we're using a fancy config)

    def tearDown(self):
        if self.httpd_running:
            self.stopHttpd()

    def testLoadModule(self):

        print("\n* Testing LoadModule")

        self.makeConfig()
        self.startHttpd()

        f = urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        server_hdr = f.info()["Server"]
        f.close()
        self.failUnless(server_hdr.find("Python") > -1,
                        "%s does not appear to load, Server header does not contain Python"
                        % MOD_PYTHON_SO)

    def testVersionCheck(self):

        print("\n* Testing C/Py version mismatch warning")

        c = Directory(DOCUMENT_ROOT,
                      SetHandler("mod_python"),
                      PythonHandler("tests::okay"),
                      PythonDebug("On"))
        self.makeConfig(c)

        self.startHttpd()
        urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        self.stopHttpd()

        # see what's in the log now
        time.sleep(0.1)
        log = open(os.path.join(SERVER_ROOT, "logs/error_log")).read()
        if "mod_python version mismatch" in log:
            self.fail("version mismatch found in logs, but versions should be same?")

        from distutils.sysconfig import get_python_lib
        version_path = os.path.join(get_python_lib(), "mod_python", "version.py")

        # the rest of this test requires write perms to site-packages/mod_python
        if os.access(version_path, os.W_OK):

            # change the version to not match
            v = open(version_path).read()
            wrong_v = v + "\nversion = 'WRONG VERSION'\n"
            open(version_path, "w").write(wrong_v)

            try:
                self.startHttpd()
                urlopen("http://127.0.0.1:%s/tests.py" % PORT)
                self.stopHttpd()

                time.sleep(0.1)
                log = open(os.path.join(SERVER_ROOT, "logs/error_log")).read()
                if "mod_python version mismatch" not in log:
                    self.fail("version are different, no version mismatch found in logs")
            finally:
                # restore version.py
                open(version_path, "w").write(v)

    def test_global_lock(self):

        print("\n  * Testing _global_lock")

        c = Directory(DOCUMENT_ROOT,
                      SetHandler("mod_python"),
                      PythonHandler("tests::global_lock"),
                      PythonDebug("On"))

        self.makeConfig(c)

        self.startHttpd()

        f = urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        if PY2:
            rsp = f.read()
        else:
            rsp = f.read().decode('latin1')
        f.close()

        if (rsp != "test ok"):
            self.fail(repr(rsp))

        # if the mutex works, this test will take at least 5 secs
        ab = get_ab_path()
        if not ab:
            print("    Can't find ab. Skipping _global_lock test")
            return

        t1 = time.time()
        print("    ", time.ctime())
        if os.name == "nt":
            cmd = '%s -c 5 -n 5 http://127.0.0.1:%s/tests.py > NUL:' \
                  % (ab, PORT)
        else:
            cmd = '%s -c 5 -n 5 http://127.0.0.1:%s/tests.py > /dev/null' \
                  % (ab, PORT)
        print("    ", cmd)
        os.system(cmd)
        print("    ", time.ctime())
        t2 = time.time()
        if (t2 - t1) < 5:
            self.fail("global_lock is broken (too quick): %f" % (t2 - t1))

    def testPerRequestTests(self):

        print("\n* Running the per-request test suite...")

        perRequestSuite = unittest.TestSuite()
        perRequestSuite.addTest(PerRequestTestCase("test_req_document_root"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_add_handler"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_add_bad_handler"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_add_empty_handler_string"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_add_handler_empty_phase"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_add_handler_directory"))
        perRequestSuite.addTest(PerRequestTestCase("test_accesshandler_add_handler_to_empty_hl"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_allow_methods"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_unauthorized"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_get_basic_auth_pw"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_auth_type"))
        if APACHE_VERSION != '2.4':
            perRequestSuite.addTest(PerRequestTestCase("test_req_requires"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_internal_redirect"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_construct_url"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_read"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_readline"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_readlines"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_discard_request_body"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_register_cleanup"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_headers_out"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_sendfile"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_sendfile2"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_sendfile3"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_handler"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_no_cache"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_update_mtime"))
        perRequestSuite.addTest(PerRequestTestCase("test_util_redirect"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_server_get_config"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_server_get_options"))
        perRequestSuite.addTest(PerRequestTestCase("test_fileupload"))
        perRequestSuite.addTest(PerRequestTestCase("test_fileupload_embedded_cr"))
        perRequestSuite.addTest(PerRequestTestCase("test_fileupload_split_boundary"))
        perRequestSuite.addTest(PerRequestTestCase("test_sys_argv"))
        perRequestSuite.addTest(PerRequestTestCase("test_PythonOption_override"))
        perRequestSuite.addTest(PerRequestTestCase("test_PythonOption_remove"))
        perRequestSuite.addTest(PerRequestTestCase("test_PythonOption_remove2"))
        perRequestSuite.addTest(PerRequestTestCase("test_util_fieldstorage"))
        perRequestSuite.addTest(PerRequestTestCase("test_postreadrequest"))
        perRequestSuite.addTest(PerRequestTestCase("test_trans"))
        perRequestSuite.addTest(PerRequestTestCase("test_outputfilter"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_add_output_filter"))
        perRequestSuite.addTest(PerRequestTestCase("test_req_register_output_filter"))
        perRequestSuite.addTest(PerRequestTestCase("test_connectionhandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_import"))
        perRequestSuite.addTest(PerRequestTestCase("test_pipe_ext"))
        perRequestSuite.addTest(PerRequestTestCase("test_cgihandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_psphandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_psp_parser"))
        perRequestSuite.addTest(PerRequestTestCase("test_psp_error"))
        perRequestSuite.addTest(PerRequestTestCase("test_Cookie_Cookie"))
        perRequestSuite.addTest(PerRequestTestCase("test_Cookie_MarshalCookie"))
        perRequestSuite.addTest(PerRequestTestCase("test_Session_Session"))
        perRequestSuite.addTest(PerRequestTestCase("test_Session_illegal_sid"))
        perRequestSuite.addTest(PerRequestTestCase("test_interpreter_per_directive"))
        perRequestSuite.addTest(PerRequestTestCase("test_interpreter_per_directory"))
        perRequestSuite.addTest(PerRequestTestCase("test_files_directive"))
        perRequestSuite.addTest(PerRequestTestCase("test_none_handler"))
        perRequestSuite.addTest(PerRequestTestCase("test_server_return"))
        perRequestSuite.addTest(PerRequestTestCase("test_phase_status"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_auth_nested"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_auth_method_nested"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_auth_digest"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_old_style_instance"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_instance"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_security"))
        # perRequestSuite.addTest(PerRequestTestCase("test_publisher_iterator"))
        perRequestSuite.addTest(PerRequestTestCase("test_publisher_hierarchy"))
        perRequestSuite.addTest(PerRequestTestCase("test_server_side_include"))
        if APACHE_VERSION == '2.4' and sys.platform.startswith("linux") and THREADS:
            perRequestSuite.addTest(PerRequestTestCase("test_memory"))
        perRequestSuite.addTest(PerRequestTestCase("test_wsgihandler"))
        perRequestSuite.addTest(PerRequestTestCase("test_wsgihandler_location"))

        # test_publisher_cache does not work correctly for mpm-prefork/worker
        # and it may not be possible to get a reliable test for all
        # configurations, so disable it.
        # perRequestSuite.addTest(PerRequestTestCase("test_publisher_cache"))

        # this must be last so its error_log is not overwritten
        perRequestSuite.addTest(PerRequestTestCase("test_internal"))

        self.makeConfig(PerRequestTestCase.appendConfig)
        self.startHttpd()

        tr = unittest.TextTestRunner()
        result = tr.run(perRequestSuite)

        self.failUnless(result.wasSuccessful())

    def test_srv_register_cleanup(self):

        print("\n* Testing server.register_cleanup()...")

        c = Directory(DOCUMENT_ROOT,
                      SetHandler("mod_python"),
                      PythonHandler("tests::srv_register_cleanup"),
                      PythonDebug("On"))

        self.makeConfig(c)

        self.startHttpd()

        f = urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        f.read()
        f.close()

        time.sleep(2)

        self.stopHttpd()

        # see what's in the log now
        time.sleep(2)
        f = open(os.path.join(SERVER_ROOT, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("srv_register_cleanup test ok") == -1:
            self.fail("Could not find test message in error_log")

    def test_apache_register_cleanup(self):

        print("\n* Testing apache.register_cleanup()...")

        c = Directory(DOCUMENT_ROOT,
                      SetHandler("mod_python"),
                      PythonHandler("tests::apache_register_cleanup"),
                      PythonDebug("On"))

        self.makeConfig(c)

        self.startHttpd()

        f = urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        f.read()
        f.close()

        time.sleep(2)

        self.stopHttpd()

        # see what's in the log now
        time.sleep(2)
        f = open(os.path.join(SERVER_ROOT, "logs/error_log"))
        log = f.read()
        f.close()
        if log.find("apache_register_cleanup test ok") == -1:
            self.fail("Could not find test message in error_log")

    def test_apache_exists_config_define(self):

        print("\n* Testing apache.exists_config_define()...")

        c = Directory(DOCUMENT_ROOT,
                      SetHandler("mod_python"),
                      PythonHandler("tests::apache_exists_config_define"),
                      PythonDebug("On"))

        self.makeConfig(c)

        self.startHttpd()

        f = urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        if PY2:
            rsp = f.read()
        else:
            rsp = f.read().decode('latin1')
        f.close()

        self.stopHttpd()

        if rsp != 'NO_FOOBAR':
            self.fail('Failure on apache.exists_config_define() : %s'%rsp)

        self.startHttpd(extra="-DFOOBAR")

        f = urlopen("http://127.0.0.1:%s/tests.py" % PORT)
        if PY2:
            rsp = f.read()
        else:
            rsp = f.read().decode('latin1')
        f.close()
        f.close()

        self.stopHttpd()

        if rsp != 'FOOBAR':
            self.fail('Failure on apache.exists_config_define() : %s'%rsp)

def suite():

    mpTestSuite = unittest.TestSuite()
    mpTestSuite.addTest(PerInstanceTestCase("testLoadModule"))
    mpTestSuite.addTest(PerInstanceTestCase("testVersionCheck"))
    mpTestSuite.addTest(PerInstanceTestCase("test_srv_register_cleanup"))
    mpTestSuite.addTest(PerInstanceTestCase("test_apache_register_cleanup"))
    mpTestSuite.addTest(PerInstanceTestCase("test_apache_exists_config_define"))
    mpTestSuite.addTest(PerInstanceTestCase("test_global_lock"))
    mpTestSuite.addTest(PerInstanceTestCase("testPerRequestTests"))
    return mpTestSuite

tr = unittest.TextTestRunner()
tr.run(suite())

