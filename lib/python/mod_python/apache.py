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
 # Originally developed by Gregory Trubetskoy.
 #

import sys
import traceback
import time
import os
import pdb
import stat
import imp
import types
import _apache

# a small hack to improve PythonPath performance. This
# variable stores the last PythonPath in raw (unevaled) form.
_path = None

class CallBack:
    """
    A generic callback object.
    """

    class HStack:
        """
        The actual stack string lives in the request object so
        it can be manipulated by both apache.py and mod_python.c
        """
        
        def __init__(self, req):
            self.req = req

        def pop(self):

            handlers = self.req.hstack.split()

            if not handlers:
                return None
            else:
                self.req.hstack = " ".join(handlers[1:])
                return handlers[0]

    def ConnectionDispatch(self, conn):

        # config
        config = conn.base_server.get_config()
        debug = config.has_key("PythonDebug")

        try:

            handler = conn.hlist.handler
            
            # split module::handler
            l = handler.split('::', 1)
            module_name = l[0]
            if len(l) == 1:
                # no oject, provide default
                object_str = "connectionhandler"
            else:
                object_str = l[1]

            # add the directory to pythonpath if
            # not there yet, or pythonpath specified
            
            if config.has_key("PythonPath"):
                # we want to do as little evaling as possible,
                # so we remember the path in un-evaled form and
                # compare it
                global _path
                pathstring = config["PythonPath"]
                if pathstring != _path:
                    _path = pathstring
                    newpath = eval(pathstring)
                    if sys.path != newpath:
                        sys.path[:] = newpath
            else:
                if filter.dir not in sys.path:
                    sys.path[:0] = [filter.dir]

            # import module
            module = import_module(module_name, config)

            # find the object
            object = resolve_object(module, object_str,
                                    arg=conn, silent=0)

            if object:

                # call the object
                if config.has_key("PythonEnablePdb"):
                    result = pdb.runcall(object, conn)
                else:
                    result = object(conn)

                assert (type(result) == type(int())), \
                       "ConnectionHandler '%s' returned invalid return code." % handler

        except PROG_TRACEBACK, traceblock:
            # Program run-time error
            try:
                (etype, value, traceback) = traceblock
                result = self.ReportError(etype, value, traceback, srv=conn.base_server,
                                          phase="ConnectionHandler",
                                          hname=handler, debug=debug)
            finally:
                traceback = None

        except:
            # Any other rerror (usually parsing)
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                filter.disable()
                result = self.ReportError(exc_type, exc_value, exc_traceback, srv=conn.base_server,
                                          phase=filter.name, hname=handler, debug=debug)
            finally:
                exc_traceback = None

	return result

    def FilterDispatch(self, filter):

        req = filter.req

        # config
        config = req.get_config()
        debug = config.has_key("PythonDebug")

        try:

            # split module::handler
            l = filter.handler.split('::', 1)
            module_name = l[0]
            if len(l) == 1:
                # no oject, provide default
                if filter.is_input:
                    object_str = "inputfilter"
                else:
                    object_str = "outputfilter"
            else:
                object_str = l[1]

            # add the directory to pythonpath if
            # not there yet, or pythonpath specified
            
            if config.has_key("PythonPath"):
                # we want to do as little evaling as possible,
                # so we remember the path in un-evaled form and
                # compare it
                global _path
                pathstring = config["PythonPath"]
                if pathstring != _path:
                    _path = pathstring
                    newpath = eval(pathstring)
                    if sys.path != newpath:
                        sys.path[:] = newpath
            else:
                if filter.dir not in sys.path:
                    sys.path[:0] = [filter.dir]

            # import module
            module = import_module(module_name, config)

            # find the object
            object = resolve_object(module, object_str, arg=filter, silent=0)

            if object:

                # call the object
                if config.has_key("PythonEnablePdb"):
                    pdb.runcall(object, filter)
                else:
                    object(filter)

                # always flush the filter. without a FLUSH or EOS bucket,
                # the content is never written to the network.
                # XXX an alternative is to tell the user to flush() always
                filter.flush()

        except SERVER_RETURN, value:
            # SERVER_RETURN indicates a non-local abort from below
            # with value as (result, status) or (result, None) or result
            try:
                if len(value.args) == 2:
                    (result, status) = value.args
                    if status:
                        req.status = status
                else:
                    result = value.args[0]
                    
                if type(result) != type(7):
                    s = "Value raised with SERVER_RETURN is invalid. It is a "
                    s = s + "%s, but it must be a tuple or an int." % type(result)
                    _apache.log_error(s, APLOG_NOERRNO|APLOG_ERR, req.server)

                    return

            except:
                pass

        except PROG_TRACEBACK, traceblock:
            # Program run-time error
            try:
                (etype, value, traceback) = traceblock
                filter.disable()
                result = self.ReportError(etype, value, traceback, req=req, filter=filter,
                                          phase="Filter: " + filter.name,
                                          hname=filter.handler, debug=debug)
            finally:
                traceback = None

        except:
            # Any other rerror (usually parsing)
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                filter.disable()
                result = self.ReportError(exc_type, exc_value, exc_traceback, req=req, filter=filter,
                                          phase=filter.name, hname=filter.handler,
                                          debug=debug)
            finally:
                exc_traceback = None

	return OK

    def HandlerDispatch(self, req):
        """
        This is the handler dispatcher.
        """

        # be cautious
        result = HTTP_INTERNAL_SERVER_ERROR

        # config
        config = req.get_config()
        debug = config.has_key("PythonDebug")

        try:
            hlist = req.hlist

            while hlist.handler:

                # split module::handler
                l = hlist.handler.split('::', 1)

                module_name = l[0]
                if len(l) == 1:
                    # no oject, provide default
                    object_str = req.phase[len("python"):].lower()
                else:
                    object_str = l[1]

                # add the directory to pythonpath if
                # not there yet, or pythonpath specified
                if config.has_key("PythonPath"):
                    # we want to do as little evaling as possible,
                    # so we remember the path in un-evaled form and
                    # compare it
                    global _path
                    pathstring = config["PythonPath"]
                    if pathstring != _path:
                        _path = pathstring
                        newpath = eval(pathstring)
                        if sys.path != newpath:
                            sys.path[:] = newpath
                else:
                    dir = hlist.directory
                    if dir not in sys.path:
                        sys.path[:0] = [dir]

                # import module
                module = import_module(module_name, config)

                # find the object
                object = resolve_object(module, object_str,
                                        arg=req, silent=hlist.silent)

                if object:

                    # call the object
                    if config.has_key("PythonEnablePdb"):
                        result = pdb.runcall(object, req)
                    else:
                        result = object(req)

                    assert (type(result) == type(int())), \
                           "Handler '%s' returned invalid return code." % hlist.handler

                    # stop cycling through handlers
                    if result != OK:
                        break
                    
                elif hlist.silent:
                    result = DECLINED

                hlist.next()

        except SERVER_RETURN, value:
            # SERVER_RETURN indicates an abort from below
            # with value as (result, status) or (result, None) or result
            try:
                if len(value.args) == 2:
                    (result, status) = value.args
                    if status:
                        req.status = status
                else:
                    result = value.args[0]
                    
                if type(result) != type(7):
                    s = "Value raised with SERVER_RETURN is invalid. It is a "
                    s = s + "%s, but it must be a tuple or an int." % type(result)
                    _apache.log_error(s, APLOG_NOERRNO|APLOG_ERR, req.server)
                    return HTTP_INTERNAL_SERVER_ERROR

            except:
                pass

        except PROG_TRACEBACK, traceblock:
            # Program run-time error
            try:
                (etype, value, traceback) = traceblock
                result = self.ReportError(etype, value, traceback, req=req,
                                          phase=req.phase, hname=hlist.handler,
                                          debug=debug)
            finally:
                traceback = None

        except:
            # Any other rerror (usually parsing)
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                result = self.ReportError(exc_type, exc_value, exc_traceback, req=req,
                                          phase=req.phase, hname=hlist.handler, debug=debug)
            finally:
                exc_traceback = None

	return result


    def ReportError(self, etype, evalue, etb, req=None, filter=None, srv=None,
                    phase="N/A", hname="N/A", debug=0):
	""" 
	This function is only used when debugging is on.
	It sends the output similar to what you'd see
	when using Python interactively to the browser
	"""

        try:       # try/finally
            try:        # try/except

                if str(etype) == "exceptions.IOError" \
                   and str(evalue)[:5] == "Write":
                    # if this is an IOError while writing to client,
                    # it is probably better not to try to write to the cleint
                    # even if debug is on.
                    debug = 0

                # write to log
                for e in traceback.format_exception(etype, evalue, etb):
                    s = "%s %s: %s" % (phase, hname, e[:-1])
                    if req:
                        req.log_error(s, APLOG_NOERRNO|APLOG_ERR)
                    else:
                        _apache.log_error(s, APLOG_NOERRNO|APLOG_ERR, srv)

                if not debug or not req:
                    return HTTP_INTERNAL_SERVER_ERROR
                else:
                    # write to client
                    req.content_type = 'text/plain'

                    s = '\nMod_python error: "%s %s"\n\n' % (phase, hname)
                    for e in traceback.format_exception(etype, evalue, etb):
                        s = s + e + '\n'
                        
                    if filter:
                        filter.write(s)
                        filter.flush()
                    else:
                        req.write(s)

                    return DONE
            except:
                # last try
                traceback.print_exc()

        finally:
            # erase the traceback
            etb = None
            # we do not return anything

def import_module(module_name, config=None, path=None):
    """
    Get the module to handle the request. If
    autoreload is on, then the module will be reloaded
    if it has changed since the last import.
    """

    # Get options
    debug, autoreload = 0, 1
    if config:
        debug = config.has_key("PythonDebug")
        if config.has_key("PythonAutoReload"):
            autoreload = int(config["PythonAutoReload"])

    # (Re)import
    if sys.modules.has_key(module_name):

        # The module has been imported already
        module = sys.modules[module_name]

        # but is it in the path?
        file = module.__dict__.get("__file__")

        # the "and not" part of this condition is to prevent execution
        # of arbitrary already imported modules, such as os. the
        # not-so-obvious filter(lambda...) call means:
        # return entries from path (which is a list) which fully match at
        # beginning the dirname of file. E.g. if file is /a/b/c/d.py, a path
        # of /a/b/c will pass, because the file is below the /a/b/c path, but
        # path of /a/b/c/g will not pass.

        if (not file or path and not
            filter(lambda a: os.path.dirname(file).find(a) == 0, path)):
            raise SERVER_RETURN, HTTP_NOT_FOUND

        if autoreload:
            oldmtime = module.__dict__.get("__mtime__", 0)
            mtime = module_mtime(module)
        else:
            mtime, oldmtime = 0, 0

    else:
        mtime, oldmtime = 0, -1

    if mtime > oldmtime:

        # Import the module
        if debug:
            if path:
                s = "mod_python: (Re)importing module '%s' with path set to '%s'" % (module_name, path)
            else:
                s = "mod_python: (Re)importing module '%s'" % module_name
            _apache.log_error(s, APLOG_NOERRNO|APLOG_NOTICE)

        parts = module_name.split('.')
        for i in range(len(parts)):
            f, p, d = imp.find_module(parts[i], path)
            try:
                mname = ".".join(parts[:i+1])
                module = imp.load_module(mname, f, p, d)
            finally:
                if f: f.close()
            if hasattr(module, "__path__"):
                path = module.__path__

        if mtime == 0:
            mtime = module_mtime(module)

        module.__mtime__ = mtime

    return module

def module_mtime(module):
    """Get modification time of module"""
    mtime = 0
    if module.__dict__.has_key("__file__"):
        
       filepath = module.__file__
       
       try:
           # this try/except block is a workaround for a Python bug in
           # 2.0, 2.1 and 2.1.1. See
           # http://sourceforge.net/tracker/?group_id=5470&atid=105470&func=detail&aid=422004

           if os.path.exists(filepath):
               mtime = os.path.getmtime(filepath)

           if os.path.exists(filepath[:-1]) :
               mtime = max(mtime, os.path.getmtime(filepath[:-1]))

       except OSError: pass

    return mtime

def resolve_object(module, object_str, arg=None, silent=0):
    """
    This function traverses the objects separated by .
    (period) to find the last one we're looking for:

       From left to right, find objects, if it is
       an unbound method of a class, instantiate the
       class passing the request as single argument

    'arg' is sometimes req, sometimes filter,
    sometimes connection
    """

    obj = module

    for obj_str in  object_str.split('.'):

        parent = obj

        # don't throw attribute errors when silent
        if silent and not hasattr(module, obj_str):
            return None

        # this adds a little clarity if we have an attriute error
        if obj == module and not hasattr(module, obj_str):
            if hasattr(module, "__file__"):
                s = "module '%s' contains no '%s'" % (module.__file__, obj_str)
                raise AttributeError, s

        obj = getattr(obj, obj_str)

        if hasattr(obj, "im_self") and not obj.im_self:
            # this is an unbound method, its class
            # needs to be instantiated
            instance = parent(arg)
            obj = getattr(instance, obj_str)

    return obj

def build_cgi_env(req):
    """
    Utility function that returns a dictionary of
    CGI environment variables as described in
    http://hoohoo.ncsa.uiuc.edu/cgi/env.html
    """

    req.add_common_vars()
    env = req.subprocess_env.copy()
        
    if len(req.path_info) > 0:
        env["SCRIPT_NAME"] = req.uri[:-len(req.path_info)]
    else:
        env["SCRIPT_NAME"] = req.uri

    env["GATEWAY_INTERFACE"] = "Python-CGI/1.1"

    # you may want to comment this out for better security
    if req.headers_in.has_key("authorization"):
        env["HTTP_AUTHORIZATION"] = req.headers_in["authorization"]

    return env

class NullIO:
    """ Abstract IO
    """
    def tell(self): return 0
    def read(self, n = -1): return ""
    def readline(self, length = None): return ""
    def readlines(self): return []
    def write(self, s): pass
    def writelines(self, list):
        self.write("".join(list))
    def isatty(self): return 0
    def flush(self): pass
    def close(self): pass
    def seek(self, pos, mode = 0): pass

class CGIStdin(NullIO):

    def __init__(self, req):
        self.pos = 0
        self.req = req
        self.BLOCK = 65536 # 64K
        # note that self.buf sometimes contains leftovers
        # that were read, but not used when readline was used
        self.buf = ""

    def read(self, n = -1):
        if n == 0:
            return ""
        if n == -1:
            s = self.req.read(self.BLOCK)
            while s:
                self.buf = self.buf + s
                self.pos = self.pos + len(s)
                s = self.req.read(self.BLOCK)
            result = self.buf
            self.buf = ""
            return result
        else:
            if self.buf:
                s = self.buf[:n]
                n = n - len(s)
            else:
                s = ""
            s = s + self.req.read(n)
            self.pos = self.pos + len(s)
            return s

    def readlines(self):
        s = (self.buf + self.read()).split('\n')
        return map(lambda s: s + '\n', s)

    def readline(self, n = -1):

        if n == 0:
            return ""

        # fill up the buffer
        self.buf = self.buf + self.req.read(self.BLOCK)

        # look for \n in the buffer
        i = self.buf.find('\n')
        while i == -1: # if \n not found - read more
            if (n != -1) and (len(self.buf) >= n): # we're past n
                i = n - 1
                break
            x = len(self.buf)
            self.buf = self.buf + self.req.read(self.BLOCK)
            if len(self.buf) == x: # nothing read, eof
                i = x - 1
                break 
            i = self.buf.find('\n', x)
        
        # carve out the piece, then shorten the buffer
        result = self.buf[:i+1]
        self.buf = self.buf[i+1:]
        self.pos = self.pos + len(result)
        return result
        

class CGIStdout(NullIO):

    """
    Class that allows writing to the socket directly for CGI.
    """
    
    def __init__(self, req):
        self.pos = 0
        self.req = req
        self.headers_sent = 0
        self.headers = ""
        
    def write(self, s):

        if not s: return

        if not self.headers_sent:
            self.headers = self.headers + s

            # are headers over yet?
            headers_over = 0

            # first try RFC-compliant CRLF
            ss = self.headers.split('\r\n\r\n', 1)
            if len(ss) < 2:
                # second try with \n\n
                ss = self.headers.split('\n\n', 1)
                if len(ss) >= 2:
                    headers_over = 1
            else:
                headers_over = 1
                    
            if headers_over:
                # headers done, process them
                ss[0] = ss[0].replace('\r\n', '\n')
                lines = ss[0].split('\n')
                for line in lines:
                    h, v = line.split(":", 1)
                    v = v.strip()
                    if h.lower() == "status":
                        status = int(v.split()[0])
                        self.req.status = status
                    elif h.lower() == "content-type":
                        self.req.content_type = v
                        self.req.headers_out[h] = v
                    else:
                        self.req.headers_out.add(h, v)

                # write the body if any at this point
                self.req.write(ss[1])
        else:
            self.req.write(str(s))
        
        self.pos = self.pos + len(s)

    def tell(self): return self.pos

def setup_cgi(req):
    """
    Replace sys.stdin and stdout with an objects that read/write to
    the socket, as well as substitute the os.environ.
    Returns (environ, stdin, stdout) which you must save and then use
    with restore_nocgi().
    """

    # save env
    save_env = os.environ.copy()
    
    si = sys.stdin
    so = sys.stdout

    os.environ.update(build_cgi_env(req))
 
    sys.stdout = CGIStdout(req)
    sys.stdin = CGIStdin(req)

    sys.argv = [] # keeps cgi.py happy

    return save_env, si, so
        
def restore_nocgi(sav_env, si, so):
    """ see setup_cgi() """

    osenv = os.environ

    # restore env
    for k in osenv:
        del osenv[k]
    for k in sav_env:
        osenv[k] = env[k]

    sys.stdout = si
    sys.stdin = so

def init():
    """ 
        This function is called by the server at startup time
    """

    return CallBack()

## Some functions made public
make_table = _apache.table
log_error = _apache.log_error
table = _apache.table
config_tree = _apache.config_tree
server_root = _apache.server_root

## Some constants

HTTP_CONTINUE                     = 100
HTTP_SWITCHING_PROTOCOLS          = 101
HTTP_PROCESSING                   = 102
HTTP_OK                           = 200
HTTP_CREATED                      = 201
HTTP_ACCEPTED                     = 202
HTTP_NON_AUTHORITATIVE            = 203
HTTP_NO_CONTENT                   = 204
HTTP_RESET_CONTENT                = 205
HTTP_PARTIAL_CONTENT              = 206
HTTP_MULTI_STATUS                 = 207
HTTP_MULTIPLE_CHOICES             = 300
HTTP_MOVED_PERMANENTLY            = 301
HTTP_MOVED_TEMPORARILY            = 302
HTTP_SEE_OTHER                    = 303
HTTP_NOT_MODIFIED                 = 304
HTTP_USE_PROXY                    = 305
HTTP_TEMPORARY_REDIRECT           = 307
HTTP_BAD_REQUEST                  = 400
HTTP_UNAUTHORIZED                 = 401
HTTP_PAYMENT_REQUIRED             = 402
HTTP_FORBIDDEN                    = 403
HTTP_NOT_FOUND                    = 404
HTTP_METHOD_NOT_ALLOWED           = 405
HTTP_NOT_ACCEPTABLE               = 406
HTTP_PROXY_AUTHENTICATION_REQUIRED= 407
HTTP_REQUEST_TIME_OUT             = 408
HTTP_CONFLICT                     = 409
HTTP_GONE                         = 410
HTTP_LENGTH_REQUIRED              = 411
HTTP_PRECONDITION_FAILED          = 412
HTTP_REQUEST_ENTITY_TOO_LARGE     = 413
HTTP_REQUEST_URI_TOO_LARGE        = 414
HTTP_UNSUPPORTED_MEDIA_TYPE       = 415
HTTP_RANGE_NOT_SATISFIABLE        = 416
HTTP_EXPECTATION_FAILED           = 417
HTTP_UNPROCESSABLE_ENTITY         = 422
HTTP_LOCKED                       = 423
HTTP_FAILED_DEPENDENCY            = 424
HTTP_INTERNAL_SERVER_ERROR        = 500
HTTP_NOT_IMPLEMENTED              = 501
HTTP_BAD_GATEWAY                  = 502
HTTP_SERVICE_UNAVAILABLE          = 503
HTTP_GATEWAY_TIME_OUT             = 504
HTTP_VERSION_NOT_SUPPORTED        = 505
HTTP_VARIANT_ALSO_VARIES          = 506
HTTP_INSUFFICIENT_STORAGE         = 507
HTTP_NOT_EXTENDED                 = 510

# The APLOG constants in Apache are derived from syslog.h
# constants, so we do same here.

try:
    import syslog
    APLOG_EMERG = syslog.LOG_EMERG     # system is unusable
    APLOG_ALERT = syslog.LOG_ALERT     # action must be taken immediately
    APLOG_CRIT = syslog.LOG_CRIT       # critical conditions
    APLOG_ERR = syslog.LOG_ERR         # error conditions 
    APLOG_WARNING = syslog.LOG_WARNING # warning conditions
    APLOG_NOTICE = syslog.LOG_NOTICE   # normal but significant condition
    APLOG_INFO = syslog.LOG_INFO       # informational
    APLOG_DEBUG = syslog.LOG_DEBUG     # debug-level messages
except ImportError:
    APLOG_EMERG = 0
    APLOG_ALERT = 1
    APLOG_CRIT = 2
    APLOG_ERR = 3
    APLOG_WARNING = 4
    APLOG_NOTICE = 5
    APLOG_INFO = 6
    APLOG_DEBUG = 7
    
APLOG_NOERRNO = 8

OK = REQ_PROCEED = 0
DONE = -2
DECLINED = REQ_NOACTION = -1

# constants for get_remote_host
REMOTE_HOST = 0
REMOTE_NAME = 1
REMOTE_NOLOOKUP = 2
REMOTE_DOUBLE_REV = 3

# legacy/mod_python things
REQ_ABORTED = HTTP_INTERNAL_SERVER_ERROR
REQ_EXIT = "REQ_EXIT"         
SERVER_RETURN = _apache.SERVER_RETURN
PROG_TRACEBACK = "PROG_TRACEBACK"

# the req.finfo tuple
FINFO_MODE = 0
FINFO_INO = 1
FINFO_DEV = 2
FINFO_NLINK = 4
FINFO_UID = 5
FINFO_GID = 6
FINFO_SIZE = 7
FINFO_ATIME = 8
FINFO_MTIME = 9
FINFO_CTIME = 10
FINFO_FNAME = 11
FINFO_NAME = 12
#FINFO_FILEHAND = 14

# the req.parsed_uri
URI_SCHEME = 0
URI_HOSTINFO = 1
URI_USER = 2
URI_PASSWORD = 3
URI_HOSTNAME = 4
URI_PORT = 5
URI_PATH = 6
URI_QUERY = 7
URI_FRAGMENT = 8

# for req.proxyreq
PROXYREQ_NONE = 0       # No proxy
PROXYREQ_PROXY = 1	# Standard proxy
PROXYREQ_REVERSE = 2	# Reverse proxy

# methods for req.allow_method()
M_GET = 0               # RFC 2616: HTTP
M_PUT = 1
M_POST = 2
M_DELETE = 3
M_CONNECT = 4
M_OPTIONS = 5
M_TRACE = 6             # RFC 2616: HTTP
M_PATCH = 7 
M_PROPFIND = 8          # RFC 2518: WebDAV
M_PROPPATCH = 9         
M_MKCOL = 10
M_COPY = 11
M_MOVE = 12
M_LOCK = 13
M_UNLOCK = 14           # RFC2518: WebDAV
M_VERSION_CONTROL = 15  # RFC3253: WebDAV Versioning
M_CHECKOUT = 16
M_UNCHECKOUT = 17
M_CHECKIN = 18
M_UPDATE = 19
M_LABEL = 20
M_REPORT = 21
M_MKWORKSPACE = 22
M_MKACTIVITY = 23
M_BASELINE_CONTROL = 24
M_MERGE = 25
M_INVALID = 26           # RFC3253: WebDAV Versioning

# for req.used_path_info
AP_REQ_ACCEPT_PATH_INFO = 0  # Accept request given path_info
AP_REQ_REJECT_PATH_INFO = 1  # Send 404 error if path_info was given
AP_REQ_DEFAULT_PATH_INFO = 2 # Module's choice for handling path_info



















