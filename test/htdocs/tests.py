 # ====================================================================
 # The Apache Software License, Version 1.1
 #
 # Copyright (c) 2000-2002 The Apache Software Foundation.  All rights
 # reserved.
 #
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions
 # are met:
 #
 # 1. Redistributions of source code must retain the above copyright
 #    notice, this list of conditions and the following disclaimer.
 #
 # 2. Redistributions in binary form must reproduce the above copyright
 #    notice, this list of conditions and the following disclaimer in
 #    the documentation and/or other materials provided with the
 #    distribution.
 #
 # 3. The end-user documentation included with the redistribution,
 #    if any, must include the following acknowledgment:
 #       "This product includes software developed by the
 #        Apache Software Foundation (http://www.apache.org/)."
 #    Alternately, this acknowledgment may appear in the software itself,
 #    if and wherever such third-party acknowledgments normally appear.
 #
 # 4. The names "Apache" and "Apache Software Foundation" must
 #    not be used to endorse or promote products derived from this
 #    software without prior written permission. For written
 #    permission, please contact apache@apache.org.
 #
 # 5. Products derived from this software may not be called "Apache",
 #    "mod_python", or "modpython", nor may these terms appear in their
 #    name, without prior written permission of the Apache Software
 #    Foundation.
 #
 # THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
 # WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 # OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 # DISCLAIMED.  IN NO EVENT SHALL THE APACHE SOFTWARE FOUNDATION OR
 # ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 # SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 # LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 # USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 # ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 # OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 # OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 # SUCH DAMAGE.
 # ====================================================================
 #
 # This software consists of voluntary contributions made by many
 # individuals on behalf of the Apache Software Foundation.  For more
 # information on the Apache Software Foundation, please see
 # <http://www.apache.org/>.
 #
 # $Id: tests.py,v 1.15 2002/10/12 20:02:03 grisha Exp $
 #

# mod_python tests

from mod_python import apache
import unittest
import re
import time
import os
import cStringIO

class SimpleTestCase(unittest.TestCase):

    def __init__(self, methodName, req):
        unittest.TestCase.__init__(self, methodName)
        self.req = req

    def test_apache_log_error(self):

        s = self.req.server
        apache.log_error("Testing apache.log_error():", apache.APLOG_INFO, s)
        apache.log_error("xEMERGx", apache.APLOG_EMERG, s)
        apache.log_error("xALERTx", apache.APLOG_ALERT, s)
        apache.log_error("xCRITx", apache.APLOG_CRIT, s)
        apache.log_error("xERRx", apache.APLOG_ERR, s)
        apache.log_error("xWARNINGx", apache.APLOG_WARNING, s)
        apache.log_error("xNOTICEx", apache.APLOG_NOTICE, s)
        apache.log_error("xINFOx", apache.APLOG_INFO, s)
        apache.log_error("xDEBUGx", apache.APLOG_DEBUG, s)

        # see what's in the log now
        f = open("%s/logs/error_log" % apache.server_root())
        # for some reason re doesn't like \n, why?
        import string
        log = "".join(map(string.strip, f.readlines()))
        f.close()

        if not re.search("xEMERGx.*xALERTx.*xCRITx.*xERRx.*xWARNINGx.*xNOTICEx.*xINFOx.*xDEBUGx", log):
            self.fail("Could not find test messages in error_log")
            

    def test_apache_table(self):

        self.req.log_error("Testing table object.")

        # tests borrowed from Python test quite for dict
        _test_table()

        # inheritance
        class mytable(apache.table):
            def __str__(self):
                return "str() from mytable"
        mt = mytable({'a':'b'})

        # add()
        a = apache.table({'a':'b'})
        a.add('a', 'c')
        if a['a'] != ['b', 'c']:
            self.fail('table.add() broken: a["a"] is %s' % `a["a"]`)

    def test_req_add_common_vars(self):

        self.req.log_error("Testing req.add_common_vars().")

        a = len(self.req.subprocess_env)
        self.req.add_common_vars()
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
        if req.allowed_methods:
            self.fail("req.allowed_methods should be None")
            
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
        if req.interpreter != req.server.server_hostname:
            self.fail("req.interpreter should be same as req.server_hostname: %s" % `req.server_hostname`)
            
        log("    req.content_type: %s" % `req.content_type`)
        log("        doing req.content_type = 'test/123' ...")
        req.content_type = 'test/123'
        log("        req.content_type: %s" % `req.content_type`)
        if req.content_type != 'test/123' or not req._content_type_set:
            self.fail("req.content_type should be 'test/123' and req._content_type_set 1")
        
        log("    req.handler: %s" % `req.handler`)
        if req.handler != "python-program":
            self.fail("req.handler should be 'python-program'")
            
        log("    req.content_encoding: %s" % `req.content_encoding`)
        if req.content_encoding:
            self.fail("req.content_encoding should be None")
            
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
            self.fail("req.unparse_uri should be '/tests.py'")
            
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
        if req.finfo[10] and (req.finfo[10] != req.canonical_filename):
            self.fail("req.finfo[10] should be the (canonical) filename")
        
        log("    req.parsed_uri: %s" % `req.parsed_uri`)
        if req.parsed_uri[6] != '/tests.py':
            self.fail("req.parsed_uri[6] should be '/tests.py'")
            
        log("    req.used_path_info: %s" % `req.used_path_info`)
        if req.used_path_info != 2:
            self.fail("req.used_path_info should be 2") # XXX really? :-)
            
        log("    req.eos_sent: %s" % `req.eos_sent`)
        if req.eos_sent:
            self.fail("req.eos_sent says we sent EOS, but we didn't")

    def test_req_get_config(self):

        req = self.req
        log = req.log_error

        log("req.get_config(): %s" % `req.get_config()`)
        if req.get_config()["PythonDebug"] != "1":
            self.fail("get_config return should show PythonDebug 1")

        log("req.get_options(): %s" % `req.get_options()`)
        if req.get_options() != apache.table({"testing":"123"}):
            self.fail("get_options() should contain 'testing':'123'")

    def test_req_get_remote_host(self):

        # simulating this test for real is too complex...
        req = self.req
        log = req.log_error
        log("req.get_get_remote_host(): %s" % `req.get_remote_host(apache.REMOTE_HOST)`)
        log("req.get_get_remote_host(): %s" % `req.get_remote_host()`)
        if (req.get_remote_host(apache.REMOTE_HOST) != None) or \
           (req.get_remote_host() != "127.0.0.1"):
            self.fail("remote host test failed")


def make_suite(req):

    mpTestSuite = unittest.TestSuite()
    mpTestSuite.addTest(SimpleTestCase("test_apache_log_error", req))
    mpTestSuite.addTest(SimpleTestCase("test_apache_table", req))
    mpTestSuite.addTest(SimpleTestCase("test_req_add_common_vars", req))
    mpTestSuite.addTest(SimpleTestCase("test_req_members", req))
    mpTestSuite.addTest(SimpleTestCase("test_req_get_config", req))
    mpTestSuite.addTest(SimpleTestCase("test_req_get_remote_host", req))
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

def req_allow_methods(req):

    req.allow_methods(["PYTHONIZE"])
    return apache.HTTP_METHOD_NOT_ALLOWED

def req_get_basic_auth_pw(req):

    if (req.phase == "PythonAuthenHandler"):
        if req.user != "spam":
            return apache.HTTP_UNAUTHORIZED
    else:
        req.write("test ok")

    return apache.OK

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

    lines = req.readlines()
    req.write("".join(lines))

    return apache.OK

def req_register_cleanup(req):

    req.cleanup_data = "test ok"
    req.register_cleanup(cleanup, req)
    req.write("registered cleanup that will write to log")

    return apache.OK

def cleanup(data):
    # for req_register_cleanup above

    data.log_error(data.cleanup_data)

def util_fieldstorage(req):

    from mod_python import util
    req.write(`util.FieldStorage(req).list`)
    return apache.OK

def postreadrequest(req):

    req.write("test ok")

    return apache.DONE


def trans(req):

    req.filename = req.document_root()+"/tests.py"

    return apache.OK

def import_test(req):

    import sys
    if sys.modules.has_key("dummymodule"):
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

def _test_table():

    log = apache.log_error

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
    d = apache.table()
    d['1'] = '1'
    d['2'] = '2'
    d['3'] = '3'
    d.clear()
    if d != apache.table(): raise TestFailed, 'dict clear'
    # dict.update()
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
    d = {1:1, 2:2, 3:3}
    if d.copy() != {1:1, 2:2, 3:3}: raise TestFailed, 'dict copy'
    if apache.table().copy() != apache.table(): raise TestFailed, 'empty dict copy'
    # dict.get()
    d = apache.table()
    if d.get('c') is not None: raise TestFailed, 'missing {} get, no 2nd arg'
    if d.get('c', '3') != '3': raise TestFailed, 'missing {} get, w/ 2nd arg'
    d = apache.table({'a' : '1', 'b' : '2'})
    if d.get('c') is not None: raise TestFailed, 'missing dict get, no 2nd arg'
    if d.get('c', '3') != '3': raise TestFailed, 'missing dict get, w/ 2nd arg'
    if d.get('a') != '1': raise TestFailed, 'present dict get, no 2nd arg'
    if d.get('a', '3') != '1': raise TestFailed, 'present dict get, w/ 2nd arg'
    # dict.setdefault()
    d = apache.table()
    d.setdefault('key0')
    if d.setdefault('key0') is not "":
        raise TestFailed, 'missing {} setdefault, no 2nd arg'
    if d.setdefault('key0') is not "":
        raise TestFailed, 'present {} setdefault, no 2nd arg'
    # dict.popitem()
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

