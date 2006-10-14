#
# Copyright 2006 Apache Software Foundation 
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
# $Id$
#

"""mod_python request object tests"""


import os
import re


from mod_python import apache

def simplehandler(req):
    if req.phase != "PythonHandler":
        req.write("test failed")
        return apache.OK

    req.write("test ok")

    if req.phase != "PythonHandler":
        req.write("test failed")
        return apache.OK

    return apache.OK



def simple_handler(req):
    # for req_add_handler()
    if (req.secret_message == "foo"):
        req.write("test ok")
        
    return apache.OK

def req_add_handler(req):

    req.secret_message = "foo"
    req.add_handler("PythonHandler", "request::simple_handler")
    req.add_handler("PythonHandler", simple_handler)

    return apache.OK

def req_add_bad_handler(req):
    # bad_handler does not exist so adding it should 
    # should raise an AttributeError exception
    
    req.log_error("req_add_bad_handler")
    req.add_handler("PythonHandler", "request::bad_handler")
    req.write("test ok")

    return apache.OK

def req_add_empty_handler_string(req):
    # Adding an empty string as a handler should should 
    # should raise an exception
    
    req.log_error("req_add_empty_handler_string")
    req.add_handler("PythonHandler", "")
    req.write("no exception")

    return apache.OK

def req_handler(req):
    if req.phase == "PythonFixupHandler":
        req.handler = "mod_python"
        req.add_handler("PythonHandler","request::req_handler")
        return apache.OK
    elif req.phase == "PythonHandler":
        req.write('test ok')
        return apache.OK
    else:
        req.write('test failed')
        return apache.OK




def accesshandler_add_handler_to_empty_hl(req):
    # Prior to version 3.2.6, adding a python handler 
    # to and empty handler list would cause a segfault
 
    req.secret_message = "foo"
    req.log_error("accesshandler_add_handler_to_empty_hl")
    req.add_handler("PythonHandler", "request::simple_handler")

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


def req_add_handler_empty_phase(req):
    req.log_error("req_add_handler_empty_phase")
    req.log_error("phase=%s" % req.phase)
    req.log_error("interpreter=%s" % req.interpreter)
    req.log_error("directory=%s" % req.hlist.directory)
    if req.phase != "PythonHandler":
        directory = os.path.dirname(__file__)
        req.add_handler("PythonHandler", "request::req_add_handler_empty_phase", directory)
    else:
        req.write("test ok")

    return apache.OK


def test_req_add_handler_directory(req):
    # dir1 will not have a trailing slash and on Win32
    # will use back slashes and not forward slashes.
    dir1 = os.path.dirname(__file__)
    if req.phase == "PythonFixupHandler":
        req.add_handler("PythonHandler", "request::test_req_add_handler_directory", dir1)
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

def req_auth_type(req):

    if req.phase == "PythonAuthenHandler":
        if req.auth_type() != "dummy":
            req.log_error("auth_type check failed")
            req.write("test failed")
            return apache.DONE
        if req.auth_name() != "blah":
            req.log_error("auth_name check failed")
            req.write("test failed")
            return apache.DONE
        req.user = "dummy"
        req.ap_auth_type = req.auth_type()
    elif req.phase == "PythonAuthzHandler":
        if req.ap_auth_type != "dummy":
            req.log_error("ap_auth_type check failed")
            req.write("test failed")
            return apache.DONE
        if req.user != "dummy":
            req.log_error("user check failed")
            req.write("test failed")
            return apache.DONE
    else:
        if req.ap_auth_type != "dummy":
            req.log_error("ap_auth_type check failed")
            req.write("test failed")
            return apache.DONE
        if req.user != "dummy":
            req.log_error("user check failed")
            req.write("test failed")
            return apache.DONE
        req.write("test ok")

    return apache.OK

def req_construct_url(req):

    url = req.construct_url("/index.html")

    if not re.match("^http://test_req_construct_url:[0-9]+/index.html$",url):
        req.write("test failed")
    else:
        req.write("test ok")

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


def req_add_output_filter(req):

    req.add_output_filter("MP_TEST_FILTER")

    req.write("test ok")

    return apache.OK

def req_register_output_filter(req):

    req.register_output_filter("MP_TEST_FILTER1","request::outputfilter1")
    req.register_output_filter("MP_TEST_FILTER2",outputfilter2)

    req.add_output_filter("MP_TEST_FILTER1")
    req.add_output_filter("MP_TEST_FILTER2")

    req.write("test ok")

    return apache.OK



def outputfilter1(filter):

    s = filter.read()
    while s:
        filter.write(s.upper())
        s = filter.read()

    if s is None:
        filter.close()

    return apache.OK

def outputfilter2(filter):

    s = filter.read()
    while s:
        for c in s:
          filter.write(2*c)
        s = filter.read()

    if s is None:
        filter.close()

    return apache.OK





def req_headers_out_access(req):

    return apache.OK

def req_headers_out(req):

    req.headers_out["X-Test-Header"] = "test ok"
    req.write("test ok")

    return apache.OK

def req_no_cache(req):
    req.no_cache = 1
    req.write('test ok')
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

def req_register_cleanup(req):

    req.cleanup_data = "req_register_cleanup test ok"
    req.register_cleanup(cleanup, req)
    req.write("registered cleanup that will write to log")

    return apache.OK

def cleanup(data):
    # for req_register_cleanup above

    data.log_error(data.cleanup_data)



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



