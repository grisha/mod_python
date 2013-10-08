 #
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
 #

# mod_python tests

from __future__ import generators
from mod_python.python22 import *

from mod_python import apache
import unittest
import re
import time
import os
import cStringIO

# This is used for mod_python.publisher security tests
_SECRET_PASSWORD = 'root'
__ANSWER = 42

class SimpleTestCase(unittest.TestCase):

    def __init__(self, methodName, req):
        unittest.TestCase.__init__(self, methodName)
        self.req = req

    def test_apache_log_error(self):

        s = self.req.server
        c = self.req.connection

        apache.log_error("Testing apache.log_error():", apache.APLOG_INFO, s)

        apache.log_error("xEMERGx", apache.APLOG_EMERG, s)
        apache.log_error("xALERTx", apache.APLOG_ALERT, s)
        apache.log_error("xCRITx", apache.APLOG_CRIT, s)
        apache.log_error("xERRx", apache.APLOG_ERR, s)
        apache.log_error("xWARNINGx", apache.APLOG_WARNING, s)
        apache.log_error("xNOTICEx", apache.APLOG_NOTICE, s)
        apache.log_error("xINFOx", apache.APLOG_INFO, s)
        apache.log_error("xDEBUGx", apache.APLOG_DEBUG, s)

        s.log_error("xEMERGx", apache.APLOG_EMERG)
        s.log_error("xALERTx", apache.APLOG_ALERT)
        s.log_error("xCRITx", apache.APLOG_CRIT)
        s.log_error("xERRx", apache.APLOG_ERR)
        s.log_error("xWARNINGx", apache.APLOG_WARNING)
        s.log_error("xNOTICEx", apache.APLOG_NOTICE)
        s.log_error("xINFOx", apache.APLOG_INFO)
        s.log_error("xDEBUGx", apache.APLOG_DEBUG)

        c.log_error("xEMERGx", apache.APLOG_EMERG)
        c.log_error("xALERTx", apache.APLOG_ALERT)
        c.log_error("xCRITx", apache.APLOG_CRIT)
        c.log_error("xERRx", apache.APLOG_ERR)
        c.log_error("xWARNINGx", apache.APLOG_WARNING)
        c.log_error("xNOTICEx", apache.APLOG_NOTICE)
        c.log_error("xINFOx", apache.APLOG_INFO)
        c.log_error("xDEBUGx", apache.APLOG_DEBUG)

        # see what's in the log now
        f = open("%s/logs/error_log" % apache.server_root())
        # for some reason re doesn't like \n, why?
        import string
        log = "".join(map(string.strip, f.readlines()))
        f.close()

        if not re.search("xEMERGx.*xALERTx.*xCRITx.*xERRx.*xWARNINGx.*xNOTICEx.*xINFOx.*xDEBUGx.*xEMERGx.*xALERTx.*xCRITx.*xERRx.*xWARNINGx.*xNOTICEx.*xINFOx.*xDEBUGx.*xEMERGx.*xALERTx.*xCRITx.*xERRx.*xWARNINGx.*xNOTICEx.*xINFOx.*xDEBUGx", log):
            self.fail("Could not find test messages in error_log")
            

    def test_apache_table(self):

        log = self.req.log_error

        log("Testing table object.")

        # tests borrowed from Python test suite for dict
        _test_table()

        # inheritance
        log("  inheritance")
        class mytable(apache.table):
            def __str__(self):
                return "str() from mytable"
        mt = mytable({'a':'b'})

        # add()
        log("  table.add()")
        a = apache.table({'a':'b'})
        a.add('a', 'c')
        if a['a'] != ['b', 'c']:
            self.fail('table.add() broken: a["a"] is %s' % `a["a"]`)

        log("Table test DONE.")

    def test_req_add_common_vars(self):

        self.req.log_error("Testing req.add_common_vars().")

        a = len(self.req.subprocess_env)
        self.req.add_common_vars()
        b = len(self.req.subprocess_env)
        if a >= b:
            self.fail("req.subprocess_env() is same size before and after")

    def test_req_add_cgi_vars(self):

        self.req.log_error("Testing req.add_cgi_vars().")

        a = len(self.req.subprocess_env)
        self.req.add_cgi_vars()
        b = len(self.req.subprocess_env)
        if a >= b:
            self.fail("req.subprocess_env() is same size before and after")

    def test_req_members(self):

        # just run through request members making sure
        # they make sense

        req = self.req
        log = req.log_error

        log("Examining request memebers:")

        log("    req.connection: %s" % `req.connection`)
        s = str(type(req.connection))
        if s != "<type 'mp_conn'>":
            self.fail("strange req.connection type %s" % `s`)

        log("    req.server: '%s'" % `req.server`)
        s = str(type(req.server))
        if s != "<type 'mp_server'>":
            self.fail("strange req.server type %s" % `s`)

        for x in ((req.next, "next"),
                  (req.prev, "prev"),
                  (req.main, "main")):
            val, name = x
            log("    req.%s: '%s'" % (name, `val`))
            if val:
                self.fail("strange, req.%s should be None, not %s" % (name, `val`))
        
        log("    req.the_request: '%s'" % req.the_request)
        if not re.match(r"GET /.* HTTP/1\.", req.the_request):
            self.fail("strange req.the_request %s" % `req.the_request`)

        for x in ((req.assbackwards, "assbackwards"),
                  (req.proxyreq, "proxyreq"),
                  (req.header_only, "header_only")):
            val, name = x
            log("    req.%s: %s" % (name, `val`))
            if val:
                self.fail("%s should be 0" % name)

        log("    req.protocol: %s" % `req.protocol`)
        if not req.protocol == req.the_request.split()[-1]:
            self.fail("req.protocol doesn't match req.the_request")

        log("    req.proto_num: %s" % `req.proto_num`)
        if req.proto_num != 1000 + int(req.protocol[-1]):
            self.fail("req.proto_num doesn't match req.protocol")

        log("    req.hostname: %s" % `req.hostname`)
        if req.hostname != "test_internal":
            self.fail("req.hostname isn't 'test_internal'")

        log("    req.request_time: %s" % `req.request_time`)
        if (time.time() - req.request_time) > 10:
            self.fail("req.request_time suggests request started more than 10 secs ago")

        log("    req.status_line: %s" % `req.status_line`)
        if req.status_line:
            self.fail("req.status_line should be None at this point")

        log("    req.status: %s" % `req.status`)
        if req.status != 200:
            self.fail("req.status should be 200")
        req.status = req.status # make sure its writable

        log("    req.method: %s" % `req.method`)
        if req.method != "GET":
            self.fail("req.method should be 'GET'")

        log("    req.method_number: %s" % `req.method_number`)        
        if req.method_number != 0:
            self.fail("req.method_number should be 0")

        log("    req.allowed: %s" % `req.allowed`)
        if req.allowed != 0:
            self.fail("req.allowed should be 0")
            
        log("    req.allowed_xmethods: %s" % `req.allowed_xmethods`)
        if req.allowed_xmethods != ():
            self.fail("req.allowed_xmethods should be an empty tuple")
            
        log("    req.allowed_methods: %s" % `req.allowed_methods`)
        if req.allowed_methods != ():
            self.fail("req.allowed_methods should be an empty tuple")
            
        log("    req.sent_bodyct: %s" % `req.sent_bodyct`)
        if req.sent_bodyct != 0:
            self.fail("req.sent_bodyct should be 0")
            
        log("    req.bytes_sent: %s" % `req.bytes_sent`)
        save = req.bytes_sent
        log("       writing 4 bytes...")
        req.write("1234")
        log("       req.bytes_sent: %s" % `req.bytes_sent`)
        if req.bytes_sent - save != 4:
            self.fail("req.bytes_sent should have incremented by 4, but didn't")

        log("    req.mtime: %s" % `req.mtime`)
        if req.mtime != 0:
            self.fail("req.mtime should be 0")
        
        log("    req.chunked: %s" % `req.chunked`)
        if req.chunked != 1:
            self.fail("req.chunked should be 1")
            
        log("    req.range: %s" % `req.range`)
        if req.range:
            self.fail("req.range should be None")
            
        log("    req.clength: %s" % `req.clength`)
        log("        calling req.set_content_length(15)...")
        req.set_content_length(15)
        log("        req.clength: %s" % `req.clength`)
        if req.clength != 15:
            self.fail("req.clength should be 15")
        
        log("    req.remaining: %s" % `req.remaining`)
        if req.remaining != 0:
            self.fail("req.remaining should be 0")
            
        log("    req.read_length: %s" % `req.read_length`)
        if req.read_length != 0:
            self.fail("req.read_length should be 0")
        
        log("    req.read_body: %s" % `req.read_body`)
        if req.read_body != 0:
            self.fail("req.read_body should be 0")
            
        log("    req.read_chunked: %s" % `req.read_chunked`)
        if req.read_chunked != 0:
            self.fail("req.read_chunked should be 0")
            
        log("    req.expecting_100: %s" % `req.expecting_100`)
        if req.expecting_100 != 0:
            self.fail("req.expecting_100 should be 0")

        log("    req.headers_in: %s" % `req.headers_in`) 
        if req.headers_in["Host"][:13].lower() != "test_internal":
            self.fail("The 'Host' header should begin with 'test_internal'")

        log("    req.headers_out: %s" % `req.headers_out`)
        if ((not req.headers_out.has_key("content-length")) or
            req.headers_out["content-length"] != "15"):
            self.fail("req.headers_out['content-length'] should be 15")
            
        log("    req.subprocess_env: %s" % `req.subprocess_env`)
        if req.subprocess_env["SERVER_SOFTWARE"].find("Python") == -1:
            self.fail("req.subprocess_env['SERVER_SOFTWARE'] should contain 'Python'")
            
        log("    req.notes: %s" % `req.notes`)
        log("        doing req.notes['testing'] = '123' ...")
        req.notes['testing'] = '123'
        log("    req.notes: %s" % `req.notes`)
        if req.notes["testing"] != '123':
            self.fail("req.notes['testing'] should be '123'")
        
        log("    req.phase: %s" % `req.phase`)
        if req.phase != "PythonHandler":
            self.fail("req.phase should be 'PythonHandler'")
            
        log("    req.interpreter: %s" % `req.interpreter`)
        if req.interpreter != apache.interpreter:
            self.fail("req.interpreter should be same as apache.interpreter" % `apache.interpreter`)
        if req.interpreter != req.server.server_hostname:
            self.fail("req.interpreter should be same as req.server.server_hostname: %s" % `req.server.server_hostname`)
            
        log("    req.content_type: %s" % `req.content_type`)
        log("        doing req.content_type = 'test/123' ...")
        req.content_type = 'test/123'
        log("        req.content_type: %s" % `req.content_type`)
        if req.content_type != 'test/123' or not req._content_type_set:
            self.fail("req.content_type should be 'test/123' and req._content_type_set 1")
        
        log("    req.handler: %s" % `req.handler`)
        if req.handler != "mod_python":
            self.fail("req.handler should be 'mod_python'")
            
        log("    req.content_encoding: %s" % `req.content_encoding`)
        if req.content_encoding:
            self.fail("req.content_encoding should be None")
             
        log("    req.content_languages: %s" % `req.content_languages`)
        if req.content_languages != ():
            self.fail("req.content_languages should be an empty tuple")
            
        log("    req.vlist_validator: %s" % `req.vlist_validator`)
        if req.vlist_validator:
            self.fail("req.vlist_validator should be None")
            
        log("    req.user: %s" % `req.user`)
        if req.user:
            self.fail("req.user should be None")
            
        log("    req.ap_auth_type: %s" % `req.ap_auth_type`)
        if req.ap_auth_type:
            self.fail("req.ap_auth_type should be None")
            
        log("    req.no_cache: %s" % `req.no_cache`)
        if req.no_cache != 0:
            self.fail("req.no_cache should be 0")
            
        log("    req.no_local_copy: %s" % `req.no_local_copy`)
        if req.no_local_copy != 0:
            self.fail("req.no_local_copy should be 0")
            
        log("    req.unparsed_uri: %s" % `req.unparsed_uri`)
        if req.unparsed_uri != "/tests.py":
            self.fail("req.unparsed_uri should be '/tests.py'")
            
        log("    req.uri: %s" % `req.uri`)
        if req.uri != "/tests.py":
            self.fail("req.uri should be '/tests.py'")
            
        log("    req.filename: %s" % `req.filename`)
        if req.filename != req.document_root() + req.uri:
            self.fail("req.filename should be req.document_root() + req.uri, but it isn't")
            
        log("    req.canonical_filename: %s" % `req.canonical_filename`)
        if not req.canonical_filename:
            self.fail("req.canonical_filename should not be blank")
        
        log("    req.path_info: %s" % `req.path_info`)
        if req.path_info != '':
            self.fail("req.path_info should be ''")
        
        log("    req.args: %s" % `req.args`)
        if req.args:
            self.fail("req.args should be None")
            
        log("    req.finfo: %s" % `req.finfo`)
        if req.finfo[apache.FINFO_FNAME] and (req.finfo[apache.FINFO_FNAME] != req.canonical_filename):
            self.fail("req.finfo[apache.FINFO_FNAME] should be the (canonical) filename")
        
        log("    req.parsed_uri: %s" % `req.parsed_uri`)
        if req.parsed_uri[apache.URI_PATH] != '/tests.py':
            self.fail("req.parsed_uri[apache.URI_PATH] should be '/tests.py'")
            
        log("    req.used_path_info: %s" % `req.used_path_info`)
        if req.used_path_info != 2:
            self.fail("req.used_path_info should be 2") # XXX really? :-)
            
        log("    req.eos_sent: %s" % `req.eos_sent`)
        if req.eos_sent:
            self.fail("req.eos_sent says we sent EOS, but we didn't")

        if apache.MODULE_MAGIC_NUMBER_MAJOR > 20111130:

            try:
                import socket
                localip = socket.gethostbyname("localhost")
            except:
                localip = "127.0.0.1"

            log("    req.useragent_ip: %s" % `req.useragent_ip`)
            if not req.useragent_ip in ("127.0.0.1", localip):
                self.fail("req.useragent_ip should be '127.0.0.1'")

            log("    req.useragent_addr: %s" % `req.useragent_addr`)
            if not req.useragent_addr[0] in ("127.0.0.1", "0.0.0.0", localip):
                self.fail("req.useragent_addr[0] should be '127.0.0.1' or '0.0.0.0'")


    def test_req_get_config(self):

        req = self.req
        log = req.log_error

        log("req.get_config(): %s" % `req.get_config()`)
        if req.get_config()["PythonDebug"] != "1":
            self.fail("get_config return should show PythonDebug 1")

        log("req.get_options(): %s" % `req.get_options()`)
        if req.get_options() != apache.table({"testing":"123"}):
            self.fail("get_options() should contain 'testing':'123', contains %s"%req.get_options().items())

    def test_req_get_remote_host(self):

        # simulating this test for real is too complex...
        req = self.req
        log = req.log_error
        log("req.get_get_remote_host(): %s" % `req.get_remote_host(apache.REMOTE_HOST)`)
        log("req.get_get_remote_host(): %s" % `req.get_remote_host()`)
        if (req.get_remote_host(apache.REMOTE_HOST) != None) or \
           (req.get_remote_host() != "127.0.0.1"):
            self.fail("remote host test failed")

    def test_server_members(self):

        req = self.req
        log = req.log_error
        server = req.server

        log("Examining server memebers:")

        log("    server.defn_name: %s" % `server.defn_name`)
        if server.defn_name[-9:] != "test.conf":
            self.fail("server.defn_name does not end in 'test.conf'")
        
        log("    server.defn_line_number: %s" % `server.defn_line_number`)
        if server.defn_line_number == 0:
            self.fail("server.defn_line_number should not be 0")
        
        log("    server.server_admin: %s" % `server.server_admin`)
        if server.server_admin != "serveradmin@somewhere.com":
            self.fail("server.server_admin must be 'serveradmin@somewhere.com'")
        
        log("    server.server_hostname: %s" % `server.server_hostname`)
        if server.server_hostname != "test_internal":
            self.fail("server.server_hostname must be 'test_internal'")
        
        log("    server.port: %s" % `server.port`)
        # hmm it really is 0...
        #if server.port == 0:
        #    self.fail("server.port should not be 0")
            
        log("    server.error_fname: %s" % `server.error_fname`)
        if server.error_fname != "logs/error_log":
            self.fail("server.error_fname should be 'logs/error_log'")
        
        log("    server.loglevel: %s" % `server.loglevel`)
        if server.loglevel != 7:
            self.fail("server.loglevel should be 7")
        
        log("    server.is_virtual: %s" % `server.is_virtual`)
        if server.is_virtual != 1:
            self.fail("server.is_virtual should be 1")
        
        log("    server.timeout: %s" % `server.timeout`)
        if not server.timeout in (5.0, 60.0):
            self.fail("server.timeout should be 5.0 or 60.0")
        
        log("    server.keep_alive_timeout: %s" % `server.keep_alive_timeout`)
        if server.keep_alive_timeout != 15.0:
            self.fail("server.keep_alive_timeout should be 15.0")
            
        log("    server.keep_alive_max: %s" % `server.keep_alive_max`)
        if server.keep_alive_max != 100:
            self.fail("server.keep_alive_max should be 100")
            
        log("    server.keep_alive: %s" % `server.keep_alive`)
        if server.keep_alive != 1:
            self.fail("server.keep_alive should be 1")
        
        log("    server.path: %s" % `server.path`)
        if server.path != "some/path":
            self.fail("server.path should be 'some/path'")
        
        log("    server.pathlen: %s" % `server.pathlen`)
        if server.pathlen != len('some/path'):
            self.fail("server.pathlen should be %d" % len('some/path'))
        
        log("    server.limit_req_line: %s" % `server.limit_req_line`)
        if server.limit_req_line != 8190:
            self.fail("server.limit_req_line should be 8190")
            
        log("    server.limit_req_fieldsize: %s" % `server.limit_req_fieldsize`)
        if server.limit_req_fieldsize != 8190:
            self.fail("server.limit_req_fieldsize should be 8190")
            
        log("    server.limit_req_fields: %s" % `server.limit_req_fields`)
        if server.limit_req_fields != 100:
            self.fail("server.limit_req_fields should be 100")
  
        log("    server.names: %s" % `server.names`)
        if server.names != ():
            self.fail("server.names should be an empty tuple")           
 
        log("    server.wild_names: %s" % `server.wild_names`)
        if server.wild_names != ():
            self.fail("server.wild_names should be an empty tuple")
            

    def test_connection_members(self):

        req = self.req
        log = req.log_error
        conn = req.connection

        try: 
            import socket
            localip = socket.gethostbyname("localhost") 
        except: 
            localip = "127.0.0.1"

        log("Examining connection memebers:")

        log("    connection.base_server: %s" % `conn.base_server`)
        if type(conn.base_server) is not type(req.server):
            self.fail("conn.base_server should be same type as req.server")
        
        log("    connection.local_addr: %s" % `conn.local_addr`)
        if not conn.local_addr[0] in ("127.0.0.1", "0.0.0.0", localip):
            self.fail("conn.local_addr[0] should be '127.0.0.1' or '0.0.0.0'")
        
        if apache.MODULE_MAGIC_NUMBER_MAJOR > 20111130:

            log("    connection.client_addr: %s" % `conn.client_addr`)
            if not conn.client_addr[0] in ("127.0.0.1", "0.0.0.0", localip):
                self.fail("conn.client_addr[0] should be '127.0.0.1' or '0.0.0.0'")

            log("    connection.client_ip: %s" % `conn.client_ip`)
            if not conn.client_ip in ("127.0.0.1", localip):
                self.fail("conn.client_ip should be '127.0.0.1'")

        else:

            log("    connection.remote_addr: %s" % `conn.remote_addr`)
            if not conn.remote_addr[0] in ("127.0.0.1", "0.0.0.0", localip):
                self.fail("conn.remote_addr[0] should be '127.0.0.1' or '0.0.0.0'")

            log("    connection.remote_ip: %s" % `conn.remote_ip`)
            if not conn.remote_ip in ("127.0.0.1", localip):
                self.fail("conn.remote_ip should be '127.0.0.1'")

        log("    connection.remote_host: %s" % `conn.remote_host`)
        if conn.remote_host is not None:
            self.fail("conn.remote_host should be None")

        log("    connection.remote_logname: %s" % `conn.remote_logname`)
        if conn.remote_logname is not None:
            self.fail("conn.remote_logname should be None")
        
        log("    connection.aborted: %s" % `conn.aborted`)
        if conn.aborted != 0:
            self.fail("conn.aborted should be 0")

        log("    connection.keepalive: %s" % `conn.keepalive`)
        if conn.keepalive != 2:
            self.fail("conn.keepalive should be 2")
        
        log("    connection.double_reverse: %s" % `conn.double_reverse`)
        if conn.double_reverse != 0:
            self.fail("conn.double_reverse should be 0")
        
        log("    connection.keepalives: %s" % `conn.keepalives`)
        if conn.keepalives != 1:
            self.fail("conn.keepalives should be 1")

        log("    connection.local_ip: %s" % `conn.local_ip`)
        if not conn.local_ip in ("127.0.0.1", localip):
            self.fail("conn.local_ip should be '127.0.0.1'")

        log("    connection.local_host: %s" % `conn.local_host`)
        if conn.local_host is not None:
            self.fail("conn.local_host should be None")

        log("    connection.id: %s" % `conn.id`)
        if conn.id > 10000:
            self.fail("conn.id probably should not be this high?")

        log("    connection.notes: %s" % `conn.notes`)
        if `conn.notes` != '{}':
            self.fail("conn.notes should be {}")

def make_suite(req):

    mpTestSuite = unittest.TestSuite()
    mpTestSuite.addTest(SimpleTestCase("test_apache_log_error", req))
    mpTestSuite.addTest(SimpleTestCase("test_apache_table", req))
    # NB: add_common_vars must be before cgi_vars
    mpTestSuite.addTest(SimpleTestCase("test_req_add_common_vars", req))
    mpTestSuite.addTest(SimpleTestCase("test_req_add_cgi_vars", req))
    mpTestSuite.addTest(SimpleTestCase("test_req_members", req))
    mpTestSuite.addTest(SimpleTestCase("test_req_get_config", req))
    mpTestSuite.addTest(SimpleTestCase("test_req_get_remote_host", req))
    mpTestSuite.addTest(SimpleTestCase("test_server_members", req))
    mpTestSuite.addTest(SimpleTestCase("test_connection_members", req))
    return mpTestSuite


def handler(req):

    out = cStringIO.StringIO()

    tr = unittest.TextTestRunner(out)
    result = tr.run(make_suite(req))

    req.log_error(out.getvalue())

    if result.wasSuccessful():
        req.write("test ok")
    else:
        req.write("test failed")

    return apache.OK

def req_add_handler(req):

    req.secret_message = "foo"
    req.add_handler("PythonHandler", "tests::simple_handler")

    return apache.OK

def simple_handler(req):
    # for req_add_handler()
    if (req.secret_message == "foo"):
        req.write("test ok")
        
    return apache.OK

def req_add_bad_handler(req):
    # bad_handler does not exist so adding it should 
    # should raise an AttributeError exception

    req.log_error("req_add_bad_handler " + req.hlist.handler)
    req.add_handler("PythonHandler", "tests::bad_handler")
    req.log_error("req_add_bad_handler " + req.hlist.handler)
    req.write("test ok")

    return apache.OK

def req_add_empty_handler_string(req):
    # Adding an empty string as a handler should should 
    # should raise an exception
    
    req.log_error("req_add_empty_handler_string")
    req.add_handler("PythonHandler", "")
    req.write("no exception")

    return apache.OK

def req_add_handler_empty_phase(req):
    req.log_error("req_add_handler_empty_phase")
    req.log_error("phase=%s" % req.phase)
    req.log_error("interpreter=%s" % req.interpreter)
    req.log_error("directory=%s" % req.hlist.directory)
    if req.phase != "PythonHandler":
        directory = os.path.dirname(__file__)
        req.add_handler("PythonHandler", "tests::req_add_handler_empty_phase", directory)
    else:
        req.write("test ok")

    return apache.OK

def accesshandler_add_handler_to_empty_hl(req):
    # Prior to version 3.2.6, adding a python handler 
    # to and empty handler list would cause a segfault
 
    req.secret_message = "foo"
    req.log_error("accesshandler_add_handler_to_empty_hl")
    req.add_handler("PythonHandler", "tests::simple_handler")

    return apache.OK

def test_req_add_handler_directory(req):
    # dir1 will not have a trailing slash and on Win32
    # will use back slashes and not forward slashes.
    dir1 = os.path.dirname(__file__)
    if req.phase == "PythonFixupHandler":
        req.add_handler("PythonHandler", "tests::test_req_add_handler_directory", dir1)
    else:
	# dir2 should only use forward slashes and
	# should have a trailing forward slash added by
	# call to req.add_handler(). When dir1 and dir2
	# are normalised for current operating system,
        # they should be equivalent.
        dir2 = req.hlist.directory
        if dir2[-1] != '/' or dir2.count('\\') != 0:
            req.write('test failed')
        else:
            dir1 = os.path.normpath(dir1)
            dir2 = os.path.normpath(dir2)
            if dir2 != dir1:
                req.write('test failed')
            else:
                req.write('test ok')
        
    return apache.OK


def req_allow_methods(req):

    req.allow_methods(["PYTHONIZE"])
    return apache.HTTP_METHOD_NOT_ALLOWED

def req_get_basic_auth_pw(req):

    pw = req.get_basic_auth_pw()
    if req.user != "spam" or pw != "eggs":
        req.write("test failed")
    else:
        req.write("test ok")

    return apache.OK

def req_unauthorized(req):

    pw = req.get_basic_auth_pw()
    if req.user == "spam" and pw == "eggs":
        req.write("test ok")
        return apache.OK

    return apache.HTTP_UNAUTHORIZED

def req_auth_type(req):

    if req.auth_type() != "dummy":
        req.log_error("auth_type check failed")
        req.write("test failed")
        return apache.DONE
    if req.auth_name() != "blah":
        req.log_error("auth_name check failed")
        req.write("test failed")
        return apache.DONE

    if req.phase == "PythonAuthenHandler":

        req.user = "dummy"
        req.ap_auth_type = req.auth_type()

    elif req.phase != "PythonAuthzHandler":

        req.write("test ok")

    return apache.OK

def req_requires(req):

    if req.requires() == ('valid-user',):
        req.write("test ok")
        return apache.DONE

    req.write("test failed")
    return apache.DONE

def req_document_root(req):

    req.write(req.document_root())
    return apache.OK

def req_internal_redirect(req):

    req.internal_redirect("/test.int")

    return apache.OK

def req_internal_redirect_int(req):
    # used by req_internal_redirect

    req.prev.write("test ")
    req.write("ok")

    return apache.OK

def req_construct_url(req):

    url = req.construct_url("/index.html")

    if not re.match("^http://test_req_construct_url:[0-9]+/index.html$",url):
        req.write("test failed")
    else:
        req.write("test ok")

    return apache.OK

def req_read(req):

    s = req.read()
    req.write(s)

    return apache.OK

def req_readline(req):

    s = req.readline()
    while s:
        req.write(s)
        s = req.readline()

    return apache.OK

def req_readlines(req):

    
    if 'SizeHint' in req.headers_in:
        lines = req.readlines(int(req.headers_in['SizeHint']))
    else:
        lines = req.readlines()

    req.write("".join(lines))

    return apache.OK

def req_discard_request_body(req):

    s = req.read(10)
    if s != '1234567890':
        req.log_error('read() #1 returned %s' % `s`)
        req.write('test failed')
        return apache.OK

    status = req.discard_request_body()
    if status != apache.OK:
        req.log_error('discard_request_body() returned %d' % status)
        return status

    s = req.read()
    if s:
        req.log_error('read() #2 returned %s' % `s`)
        req.write('test failed')
        return apache.OK

    req.write('test ok')

    return apache.OK

def req_register_cleanup(req):

    req.cleanup_data = "req_register_cleanup test ok"
    req.register_cleanup(cleanup, req)
    req.write("registered cleanup that will write to log")

    return apache.OK

def cleanup(data):
    # for req_register_cleanup above

    data.log_error(data.cleanup_data)

def server_cleanup(data):
    # for srv_register_cleanup and apache_register_cleanup below

    apache.log_error(data)

def req_headers_out(req):

    req.headers_out["X-Test-Header"] = "test ok"
    req.write("test ok")

    return apache.OK

def req_headers_out_access(req):

    return apache.OK

def req_sendfile(req):

    import tempfile
    fname  = tempfile.mktemp("txt")
    f = open(fname, "w")
    f.write("  test ok  ");
    f.close()

    req.sendfile(fname, 2, 7)

    # os.remove(fname)
    return apache.OK

def req_sendfile2(req):

    import tempfile
    fname  = tempfile.mktemp("txt")
    f = open(fname, "w")
    f.write("0123456789"*100);
    f.close()

    req.sendfile(fname)

    # os.remove(fname)
    return apache.OK
 
def req_sendfile3(req):
    """Check if sendfile handles symlinks properly.
       This is only valid on posix systems.
    """

    import tempfile
    # note mktemp is deprecated in python 2.3. Should use mkstemp instead.
    fname  = tempfile.mktemp("txt")
    f = open(fname, "w")
    f.write("0123456789"*100);
    f.close()
    fname_symlink =  '%s.lnk' % fname
    os.symlink(fname, fname_symlink)
    req.sendfile(fname_symlink)
    os.remove(fname_symlink)
    os.remove(fname)
    return apache.OK

def req_handler(req):
    if req.phase == "PythonFixupHandler":
        req.handler = "mod_python"
        req.handler = None
        req.handler = "mod_python"
        req.add_handler("PythonHandler","tests::req_handler")
        return apache.OK
    elif req.phase == "PythonHandler":
        req.write('test ok')
        return apache.OK
    else:
        req.write('test failed')
        return apache.OK

def req_no_cache(req):
    req.no_cache = 1
    req.write('test ok')
    return apache.OK

def req_update_mtime(req):
    assert(req.mtime == 0.0)
    req.update_mtime(100.0)
    assert(req.mtime == 100.0)
    req.set_etag()
    req.set_last_modified()
    req.write('test ok')
    return apache.OK

def util_redirect(req):
    from mod_python import util
    if req.main:
        # Sub request for ErrorDocument.
        req.write("test failed")
        return apache.DONE
    else:
        if req.phase == "PythonFixupHandler":
            util.redirect(req,location="/dummy",text="test ok")
        else:
            req.write('test failed')
            return apache.OK

def req_server_get_config(req):

    if req.server.get_config().get("PythonDebug","0") != "1" or \
            req.get_config().get("PythonDebug","0") != "0":
        req.write('test failed')
    else:
        req.write('test ok')

    return apache.OK

def req_server_get_options(req):

    try:
        server_options = apache.main_server.get_options()
        assert(server_options.get("global","0") == "0")
        assert(server_options.get("override","0") == "0")

        server_options = req.connection.base_server.get_options()
        assert(server_options.get("global","0") == "0")
        assert(server_options.get("override","0") == "0")

        server_options = req.server.get_options()
        assert(server_options["global"] == "1")
        assert(server_options["override"] == "1")

        request_options = req.get_options()
        assert(request_options["global"] == "1")
        assert(request_options["override"] == "2")
        assert(request_options["local"] == "1")
    except:
        req.write('test failed')
    else:
        req.write('test ok')

    return apache.OK

def fileupload(req):
    from mod_python import util
    import md5
    fields = util.FieldStorage(req)
    f = fields.getfirst('testfile')
    
    req.write(md5.new(f.file.read()).hexdigest())
    return apache.OK

def srv_register_cleanup(req):

    req.server.register_cleanup(req, server_cleanup, "srv_register_cleanup test ok")
    req.write("registered server cleanup that will write to log")

    return apache.OK

def apache_register_cleanup(req):

    apache.register_cleanup(server_cleanup, "apache_register_cleanup test ok")
    req.write("registered server cleanup that will write to log")

    return apache.OK

def apache_exists_config_define(req):
    if apache.exists_config_define('FOOBAR'):
        req.write('FOOBAR')
    else:
        req.write('NO_FOOBAR')
    return apache.OK

def util_fieldstorage(req):

    from mod_python import util
    req.write(`util.FieldStorage(req).list`)
    return apache.OK

def postreadrequest(req):

    req.log_error('postreadrequest')

    req.add_common_vars()

    req.subprocess_env['TEST1'] = "'"
    req.subprocess_env['TEST2'] = '"'

    req.log_error('subprocess_env = %s' % req.subprocess_env)
    req.log_error('subprocess_env.values() = %s' % req.subprocess_env.values())

    for value in req.subprocess_env.itervalues():
        req.log_error('VALUE = %s' % value)

    for item in req.subprocess_env.iteritems():
        req.log_error('ITEM = %s' % (item,))

    req.log_error('SCRIPT_FILENAME = %s' % req.subprocess_env.get('SCRIPT_FILENAME'))
    req.log_error('SCRIPT_FILENAME = %s' % req.subprocess_env['SCRIPT_FILENAME'])

    req.write("test ok")

    return apache.DONE


def trans(req):

    req.filename = req.document_root()+"/tests.py"

    return apache.OK

def import_test(req):

    import sys, os
    directory = os.path.dirname(__file__)
    assert(map(os.path.normpath, sys.path).count(directory) == 1)
    if sys.modules.has_key("dummymodule"):
        if not apache.main_server.get_options().has_key("dummymodule::function"):
            req.log_error("dummymodule::function not executed")
            req.write("test failed")
        else:
            req.write("test ok")
    else:
        req.log_error("dummymodule not found in sys.modules")
        req.write("test failed")

    return apache.OK

def outputfilter(filter):

    s = filter.read()
    while s:
        filter.write(s.upper())
        s = filter.read()

    if s is None:
        filter.close()

    return apache.OK

def simplehandler(req):

    if req.phase != "PythonHandler":
        req.write("test failed")
        return apache.OK

    req.write("test ok")

    if req.phase != "PythonHandler":
        req.write("test failed")
        return apache.OK

    return apache.OK

def req_add_output_filter(req):

    req.add_output_filter("MP_TEST_FILTER")

    req.write("test ok")

    return apache.OK

def req_register_output_filter(req):

    req.register_output_filter("MP_TEST_FILTER","tests::outputfilter")

    req.add_output_filter("MP_TEST_FILTER")

    req.write("test ok")

    return apache.OK

def connectionhandler(conn):

    # read whatever
    s = conn.readline().strip()
    while s:
        s = conn.readline().strip()

    # fake an HTTP response
    conn.write("HTTP/1.1 200 OK\r\n")
    conn.write("Content-Length: 7\r\n\r\n")
    conn.write("test ok")

    return apache.OK

def pipe_ext(req):

    # this is called by publisher

    return "pipe ext"


def Cookie_Cookie(req):

    from mod_python import Cookie

    cookies = Cookie.get_cookies(req)

    for k in cookies:
        Cookie.add_cookie(req, cookies[k])

    req.write("test ok")
    
    return apache.OK

def Cookie_MarshalCookie(req):

    from mod_python import Cookie

    cookies = Cookie.get_cookies(req, Cookie.MarshalCookie,
                                secret="secret")

    for k in cookies:
        Cookie.add_cookie(req, cookies[k])

    req.write("test ok")
    
    return apache.OK
    

def global_lock(req):

    import _apache

    _apache._global_lock(req.server, 1)
    time.sleep(1)
    _apache._global_unlock(req.server, 1)

    req.write("test ok")
    
    return apache.OK

def Session_Session(req):

    from mod_python import Session, Cookie
    s = Session.Session(req)
    if s.is_new():
        s.save()
        
    cookies = Cookie.get_cookies(req)
    if cookies.has_key(Session.COOKIE_NAME) and s.is_new():
        req.write(str(cookies[Session.COOKIE_NAME]))
    else:
        req.write("test ok")

    return apache.OK

def files_directive(req):

    req.write(str(req.hlist.directory))
    return apache.OK

none_handler = None

def server_return_1(req):
    raise apache.SERVER_RETURN, apache.OK

def server_return_2(req):
    req.write("test ok")
    return apache.OK

def phase_status_1(req):
    apache.log_error("phase_status_1")
    req.phases = [1]
    return apache.DECLINED

def phase_status_2(req):
    apache.log_error("phase_status_2")
    req.phases.append(2)
    req.user = "bogus"
    req.ap_auth_type = "bogus"
    return apache.OK

def phase_status_3(req):
    apache.log_error("phase_status_3")
    req.phases.append(3)
    return apache.OK

def phase_status_4(req):
    apache.log_error("phase_status_4")
    #req.phases.append(4)
    return apache.OK

def phase_status_5(req):
    apache.log_error("phase_status_5")
    req.phases.append(5)
    return apache.DECLINED

def phase_status_6(req):
    apache.log_error("phase_status_6")
    req.phases.append(6)
    return apache.OK

def phase_status_7(req):
    apache.log_error("phase_status_7")
    req.phases.append(7)
    return apache.OK

def phase_status_8(req):
    apache.log_error("phase_status_8")
    apache.log_error("phases = %s" % req.phases)
    if req.phases != [1, 2, 5, 6, 7]:
        req.write("test failed")
    else:
        req.write("test ok")
    return apache.OK

def phase_status_cleanup(req):
    apache.log_error("phase_status_cleanup_log_entry")
    return apache.OK

def test_sys_argv(req):
    import sys
    req.write(repr(sys.argv))
    return apache.OK
        
def PythonOption_items(req):
    options = req.get_options().items()
    
    # The tests may using PythonOption mod_python.* in the test configuration
    # We need to remove those particular options so they don't interfer
    # with this test result.
    options = [ o for o in options if not o[0].startswith('mod_python') ]
    
    options.sort()
    req.write(str(options))
    return apache.OK

def interpreter(req):
    req.write(req.interpreter)
    return apache.DONE

def index(req):
    return "test ok, interpreter=%s" % req.interpreter

def test_publisher(req):
    return "test ok, interpreter=%s" % req.interpreter

def test_publisher_auth_nested(req):
    def __auth__(req, user, password):
        test_globals = test_publisher
        req.notes["auth_called"] = "1"
        return user == "spam" and password == "eggs"
    def __access__(req, user):
        req.notes["access_called"] = "1"
        return 1
    assert(int(req.notes.get("auth_called",0)))
    assert(int(req.notes.get("access_called",0)))
    return "test ok, interpreter=%s" % req.interpreter

class _test_publisher_auth_method_nested:
    def method(self, req):
        def __auth__(req, user, password):
            test_globals = test_publisher
            req.notes["auth_called"] = "1"
            return user == "spam" and password == "eggs"
        def __access__(req, user):
            req.notes["access_called"] = "1"
            return 1
        assert(int(req.notes.get("auth_called",0)))
        assert(int(req.notes.get("access_called",0)))
        return "test ok, interpreter=%s" % req.interpreter

test_publisher_auth_method_nested = _test_publisher_auth_method_nested()

class OldStyleClassTest:
    def __init__(self):
        pass
    def __call__(self, req):
        return "test callable old-style instance ok"
    def traverse(self, req):
        return "test traversable old-style instance ok"
old_instance = OldStyleClassTest()

test_dict = {1:1, 2:2, 3:3}
test_dict_keys = test_dict.keys

def test_dict_iteration(req):
    return test_dict_keys()
    
def test_generator(req):
    c = 0
    while c < 10:
        yield c
        c += 1

def server_side_include(req):
    req.ssi_globals = { "data": "test" }
    return apache.OK

class InstanceTest(object):
    def __call__(self, req):
        return "test callable instance ok"
    def traverse(self, req):
        return "test traversable instance ok"
instance = InstanceTest()

# Hierarchy traversal tests
class Mapping(object):
    def __init__(self,name):
        self.name = name

    def __call__(self,req):
        return "Called %s"%self.name
hierarchy_root = Mapping("root");
hierarchy_root.page1 = Mapping("page1")
hierarchy_root.page1.subpage1 = Mapping("subpage1")
hierarchy_root.page2 = Mapping("page2")

class Mapping2:
    pass
hierarchy_root_2 = Mapping2()
hierarchy_root_2.__call__ = index
hierarchy_root_2.page1 = index
hierarchy_root_2.page2 = index

def _test_table():

    log = apache.log_error

    log("    starting _test_table")
    d = apache.table()
    if d.keys() != []: raise TestFailed, '{}.keys()'
    if d.has_key('a') != 0: raise TestFailed, '{}.has_key(\'a\')'
    if ('a' in d) != 0: raise TestFailed, "'a' in {}"
    if ('a' not in d) != 1: raise TestFailed, "'a' not in {}"
    if len(d) != 0: raise TestFailed, 'len({})'
    d = {'a': 1, 'b': 2}
    if len(d) != 2: raise TestFailed, 'len(dict)'
    k = d.keys()
    k.sort()
    if k != ['a', 'b']: raise TestFailed, 'dict keys()'
    if d.has_key('a') and d.has_key('b') and not d.has_key('c'): pass
    else: raise TestFailed, 'dict keys()'
    if 'a' in d and 'b' in d and 'c' not in d: pass
    else: raise TestFailed, 'dict keys() # in/not in version'
    if d['a'] != 1 or d['b'] != 2: raise TestFailed, 'dict item'
    d['c'] = 3
    d['a'] = 4
    if d['c'] != 3 or d['a'] != 4: raise TestFailed, 'dict item assignment'
    del d['b']
    if d != {'a': 4, 'c': 3}: raise TestFailed, 'dict item deletion'
    
    # dict.clear()
    log("    table.clear()")
    d = apache.table()
    d['1'] = '1'
    d['2'] = '2'
    d['3'] = '3'
    d.clear()
    if d != apache.table(): raise TestFailed, 'dict clear'
    
    # dict.update()
    log("    table.update()")
    d.update({'1':'100'})
    d.update({'2':'20'})
    d.update({'1':'1', '2':'2', '3':'3'})
    if d != apache.table({'1':'1', '2':'2', '3':'3'}): raise TestFailed, 'dict update'
    d.clear()
    try: d.update(None)
    except AttributeError: pass
    else: raise TestFailed, 'dict.update(None), AttributeError expected'
    class SimpleUserDict:
        def __init__(self):
            self.d = {1:1, 2:2, 3:3}
        def keys(self):
            return self.d.keys()
        def __getitem__(self, i):
            return self.d[i]
    d.update(SimpleUserDict())
    if d != apache.table({1:1, 2:2, 3:3}): raise TestFailed, 'dict.update(instance)'
    d.clear()
    class FailingUserDict:
        def keys(self):
            raise ValueError
    try: d.update(FailingUserDict())
    except ValueError: pass
    else: raise TestFailed, 'dict.keys() expected ValueError'
    class FailingUserDict:
        def keys(self):
            class BogonIter:
                def __iter__(self):
                    raise ValueError
            return BogonIter()
    try: d.update(FailingUserDict())
    except ValueError: pass
    else: raise TestFailed, 'iter(dict.keys()) expected ValueError'
    class FailingUserDict:
        def keys(self):
            class BogonIter:
                def __init__(self):
                    self.i = 1
                def __iter__(self):
                    return self
                def next(self):
                    if self.i:
                        self.i = 0
                        return 'a'
                    raise ValueError
            return BogonIter()
        def __getitem__(self, key):
            return key
    try: d.update(FailingUserDict())
    except ValueError: pass
    else: raise TestFailed, 'iter(dict.keys()).next() expected ValueError'
    class FailingUserDict:
        def keys(self):
            class BogonIter:
                def __init__(self):
                    self.i = ord('a')
                def __iter__(self):
                    return self
                def next(self):
                    if self.i <= ord('z'):
                        rtn = chr(self.i)
                        self.i += 1
                        return rtn
                    raise StopIteration
            return BogonIter()
        def __getitem__(self, key):
            raise ValueError
    try: d.update(FailingUserDict())
    except ValueError: pass
    else: raise TestFailed, 'dict.update(), __getitem__ expected ValueError'
    # dict.copy()
    log("    table.copy()")
    d = {1:1, 2:2, 3:3}
    if d.copy() != {1:1, 2:2, 3:3}: raise TestFailed, 'dict copy'
    if apache.table().copy() != apache.table(): raise TestFailed, 'empty dict copy'
    # dict.get()
    log("    table.get()")
    d = apache.table()
    if d.get('c') is not None: raise TestFailed, 'missing {} get, no 2nd arg'
    if d.get('c', '3') != '3': raise TestFailed, 'missing {} get, w/ 2nd arg'
    d = apache.table({'a' : '1', 'b' : '2'})
    if d.get('c') is not None: raise TestFailed, 'missing dict get, no 2nd arg'
    if d.get('c', '3') != '3': raise TestFailed, 'missing dict get, w/ 2nd arg'
    if d.get('a') != '1': raise TestFailed, 'present dict get, no 2nd arg'
    if d.get('a', '3') != '1': raise TestFailed, 'present dict get, w/ 2nd arg'
    # dict.setdefault()
    log("    table.setdefault()")
    d = apache.table()
    d.setdefault('key0')
    if d.setdefault('key0') is not "":
        raise TestFailed, 'missing {} setdefault, no 2nd arg'
    if d.setdefault('key0') is not "":
        raise TestFailed, 'present {} setdefault, no 2nd arg'
    # dict.popitem()
    log("    table.popitem()")
    for copymode in -1, +1:
        # -1: b has same structure as a
        # +1: b is a.copy()
        for log2size in range(12):
            size = 2**log2size
            a = apache.table()
            b = apache.table()
            for i in range(size):
                a[`i`] = str(i)
                if copymode < 0:
                    b[`i`] = str(i)
            if copymode > 0:
                b = a.copy()
            for i in range(size):
                ka, va = ta = a.popitem()
                if va != ka: raise TestFailed, "a.popitem: %s" % str(ta)
                kb, vb = tb = b.popitem()
                if vb != kb: raise TestFailed, "b.popitem: %s" % str(tb)
                if copymode < 0 and ta != tb:
                    raise TestFailed, "a.popitem != b.popitem: %s, %s" % (
                        str(ta), str(tb))
            if a: raise TestFailed, 'a not empty after popitems: %s' % str(a)
            if b: raise TestFailed, 'b not empty after popitems: %s' % str(b)

    # iteration (just make sure we can iterate without a segfault)
    d = apache.table({'a' : '1', 'b' : '2', 'c' : '3'})
    log("    for k in table")
    for k in d:
        pass

    log("    _test_table test finished")

def okay(req):
    req.write("test ok")
    return apache.OK

def memory(req):

    # NB: This only works on Linux.

    ## warm up
    for x in xrange(10000):
        req.write("test ok")

    ## check memory usage before
    before = map(int, open("/proc/self/statm").read().split())

    for x in xrange(100000):
        req.write("test ok")
        req.flush()

    ## check memory usage after
    after = map(int, open("/proc/self/statm").read().split())

    req.write("|%s|%s" % (before[0], after[0]))

    return apache.OK
