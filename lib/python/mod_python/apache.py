 # Copyright (c) 2000 Gregory Trubetskoy.  All rights reserved.
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
 # 3. The end-user documentation included with the redistribution, if
 #    any, must include the following acknowledgment: "This product 
 #    includes software developed by Gregory Trubetskoy."
 #    Alternately, this acknowledgment may appear in the software itself, 
 #    if and wherever such third-party acknowledgments normally appear.
 #
 # 4. The names "mod_python", "modpython" or "Gregory Trubetskoy" must not 
 #    be used to endorse or promote products derived from this software 
 #    without prior written permission. For written permission, please 
 #    contact grisha@modpython.org.
 #
 # 5. Products derived from this software may not be called "mod_python"
 #    or "modpython", nor may "mod_python" or "modpython" appear in their 
 #    names without prior written permission of Gregory Trubetskoy.
 #
 # THIS SOFTWARE IS PROVIDED BY GREGORY TRUBETSKOY ``AS IS'' AND ANY
 # EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 # IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 # PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL GREGORY TRUBETSKOY OR
 # HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 # SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 # NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 # LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 # HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 # STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 # ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 # OF THE POSSIBILITY OF SUCH DAMAGE.
 # ====================================================================
 #
 # $Id: apache.py,v 1.35 2001/08/18 22:43:45 gtrubetskoy Exp $

import sys
import string
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

# this is used in Request.__init__
def _cleanup_request(_req):
    _req._Request = None

class Request:
    """ This is a normal Python Class that can be subclassed.
        However, most of its functionality comes from a built-in
        object of type mp_request provided by mod_python at
        initialization and stored in self._req.
    """

    def __init__(self, _req):
        # look at __setattr__ if changing this line!
        self._req = _req
        
        # this will decrement the reference to the _req
        # object at cleanup time. If we don't do this, we
        # get a cirular reference and _req never gets destroyed.
        _req.register_cleanup(_cleanup_request, _req)

    def __getattr__(self, attr):
        try:
            return getattr(self._req, attr)
        except AttributeError:
            raise AttributeError, attr

    def __setattr__(self, attr, val):
        try:
            if attr != "_req":
                setattr(self._req, attr, val)
            else:
                self.__dict__["_req"] = val
        except AttributeError:
            self.__dict__[attr] = val

    def __nonzero__(self):
        return 1

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

            handlers = string.split(self.req.hstack)
            if not handlers:
                return None
            else:
                self.req.hstack = string.join(handlers[1:], " ")
                return handlers[0]

    def FilterDispatch(self, filter, func):

        _req = filter._req

        # is there a Request object for this request?
        if not _req._Request:
            _req._Request = Request(_req)
            
        req = filter.req = _req._Request

        # config
        config = _req.get_config()
        debug = config.has_key("PythonDebug")

        try:

            # split module::handler
            l = string.split(func, '::', 1)
            module_name = l[0]
            if len(l) == 1:
                # no oject, provide default
                if filter.is_input:
                    object_str = "inputfilter"
                else:
                    object_str = "outputfilter"
            else:
                object_str = l[1]

            # add the direcotry to pythonpath if
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
                if filter.is_input:
                    dir = _req.get_input_filter_dirs()[filter.name]
                else:
                    dir = _req.get_output_filter_dirs()[filter.name]
                if dir not in sys.path:
                    sys.path[:0] = [dir]

            # import module
            module = import_module(module_name, _req)

            # find the object
            silent = config.has_key("PythonHandlerModule")
            object = resolve_object(req, module, object_str, silent)

            if object:

                # call the object
                if config.has_key("PythonEnablePdb"):
                    result = pdb.runcall(object, filter)
                else:
                    result = object(filter)

                # always close the filter
                filter.close()

        except SERVER_RETURN, value:
            # SERVER_RETURN indicates a non-local abort from below
            # with value as (result, status) or (result, None) or result
            try:
                if len(value.args) == 2:
                    (result, status) = value.args
                    if status:
                        _req.status = status
                else:
                    result = value.args[0]
                    
                if type(result) != type(7):
                    s = "Value raised with SERVER_RETURN is invalid. It is a "
                    s = s + "%s, but it must be a tuple or an int." % type(result)
                    _apache.log_error(s, APLOG_NOERRNO|APLOG_ERR, _req.server)

                    return

            except:
                pass

        except PROG_TRACEBACK, traceblock:
            # Program run-time error
            try:
                (etype, value, traceback) = traceblock
                filter.disable()
                result = self.ReportError(req, etype, value, traceback,
                                          htype="Filter: " + filter.name,
                                          hname=func, debug=debug)
            finally:
                traceback = None

        except:
            # Any other rerror (usually parsing)
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                filter.disable()
                result = self.ReportError(req, exc_type, exc_value, exc_traceback,
                                          htype=filter.name, hname=func, debug=debug)
            finally:
                exc_traceback = None

	return

    def HandlerDispatch(self, _req, htype):
        """
        This is the handler dispatcher.
        """

        # be cautious
        result, handler = HTTP_INTERNAL_SERVER_ERROR, ""

        # is there a Request object for this request?
        if not _req._Request:
            _req._Request = Request(_req)
            
        req = _req._Request

        # config
        config = _req.get_config()
        debug = config.has_key("PythonDebug")

        try:

            # cycle through the handlers
            dirs = _req.get_all_dirs()

            hstack = self.HStack(_req)

            handler = hstack.pop()
            while handler:

                # split module::handler
                l = string.split(handler, '::', 1)
                module_name = l[0]
                if len(l) == 1:
                    # no oject, provide default
                    object_str = string.lower(htype[len("python"):])
                else:
                    object_str = l[1]
                
                # add the direcotry to pythonpath if
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
                    if config.has_key("PythonHandlerModule"):
                        dir = _req.get_all_dirs()["PythonHandlerModule"]
                    else:
                        dir = _req.get_all_dirs()[htype]
                    if dir not in sys.path:
                        sys.path[:0] = [dir]

                # import module
                module = import_module(module_name, _req)

                # find the object
                silent = config.has_key("PythonHandlerModule")
                object = resolve_object(req, module, object_str, silent)

                if object:

                    # call the object
                    if config.has_key("PythonEnablePdb"):
                        result = pdb.runcall(object, req)
                    else:
                        result = object(req)

                    # stop cycling through handlers
                    if result != OK:
                        break
                    
                elif silent:
                    result = DECLINED
                        
                handler = hstack.pop()

        except SERVER_RETURN, value:
            # SERVER_RETURN indicates a non-local abort from below
            # with value as (result, status) or (result, None) or result
            try:
                if len(value.args) == 2:
                    (result, status) = value.args
                    if status:
                        _req.status = status
                else:
                    result = value.args[0]
                    
                if type(result) != type(7):
                    s = "Value raised with SERVER_RETURN is invalid. It is a "
                    s = s + "%s, but it must be a tuple or an int." % type(result)
                    _apache.log_error(s, APLOG_NOERRNO|APLOG_ERR, _req.server)
                    return HTTP_INTERNAL_SERVER_ERROR

            except:
                pass

        except PROG_TRACEBACK, traceblock:
            # Program run-time error
            try:
                (etype, value, traceback) = traceblock
                result = self.ReportError(req, etype, value, traceback,
                                          htype=htype, hname=handler,
                                          debug=debug)
            finally:
                traceback = None

        except:
            # Any other rerror (usually parsing)
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                result = self.ReportError(req, exc_type, exc_value, exc_traceback,
                                          htype=htype, hname=handler, debug=debug)
            finally:
                exc_traceback = None

	return result


    def ReportError(self, req, etype, evalue, etb, htype="N/A", hname="N/A", debug=0):
	""" 
	This function is only used when debugging is on.
	It sends the output similar to what you'd see
	when using Python interactively to the browser
	"""

        try:

            if str(etype) == "exceptions.IOError" \
               and str(evalue)[:5] == "Write":
                # if this is an IOError while writing to client,
                # it is probably better not to try to write to the cleint
                # even if debug is on.
                debug = 0
            
            # write to log
            for e in traceback.format_exception(etype, evalue, etb):
                s = "%s %s: %s" % (htype, hname, e[:-1])
                _apache.log_error(s, APLOG_NOERRNO|APLOG_ERR, req.server)

            if not debug:
                return HTTP_INTERNAL_SERVER_ERROR
            else:
                # write to client

                req.content_type = 'text/plain'

                s = '\nMod_python error: "%s %s"\n\n' % (htype, hname)
                for e in traceback.format_exception(etype, evalue, etb):
                    s = s + e + '\n'

                req.write(s)

                return DONE

        finally:
            # erase the traceback
            etb = None
            # we do not return anything

def import_module(module_name, req=None, path=None):
    """ 
    Get the module to handle the request. If
    autoreload is on, then the module will be reloaded
    if it has changed since the last import.
    """

    # get the options
    autoreload, debug = 1, None
    if req:
        config = req.get_config()
        if config.has_key("PythonAutoReload"):
            autoreload = int(config["PythonAutoReload"])
        debug = config.has_key("PythonDebug")

    # try to import the module

    oldmtime = None
    mtime = None

    if  not autoreload:

        # import module
        module = __import__(module_name)
        components = string.split(module_name, '.')
        for cmp in components[1:]:
            module = getattr(module, cmp)

    else:

        # keep track of file modification time and
        # try to reload it if it is newer
        if sys.modules.has_key(module_name):

            # the we won't even bother importing
            module = sys.modules[module_name]

            # does it have __mtime__ ?
            if sys.modules[module_name].__dict__.has_key("__mtime__"):
                # remember it
                oldmtime = sys.modules[ module_name ].__mtime__

        # import the module for the first time
        else:

            parts = string.split(module_name, '.')
            for i in range(len(parts)):
                f, p, d = imp.find_module(parts[i], path)
                try:
                    mname = string.join(parts[:i+1], ".")
                    module = imp.load_module(mname, f, p, d)
                finally:
                    if f: f.close()
                if hasattr(module, "__path__"):
                    path = module.__path__

        # find out the last modification time
        # but only if there is a __file__ attr
        if module.__dict__.has_key("__file__"):

            filepath = module.__file__

            if os.path.exists(filepath):

                mod = os.stat(filepath)
                mtime = mod[stat.ST_MTIME]

            # check also .py and take the newest
            if os.path.exists(filepath[:-1]) :

                # get the time of the .py file
                mod = os.stat(filepath[:-1])
                mtime = max(mtime, mod[stat.ST_MTIME])

    # if module is newer - reload
    if (autoreload and (oldmtime < mtime)):
        module = reload(module)

    # save mtime
    module.__mtime__ = mtime

    return module

def resolve_object(req, module, object_str, silent=0):
    """
    This function traverses the objects separated by .
    (period) to find the last one we're looking for:

       From left to right, find objects, if it is
       an unbound method of a class, instantiate the
       class passing the request as single argument
    """

    obj = module

    for obj_str in  string.split(object_str, '.'):

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
            instance = parent(req)
            obj = getattr(instance, obj_str)

    return obj

def build_cgi_env(req):
    """
    Utility function that returns a dictionary of
    CGI environment variables as described in
    http://hoohoo.ncsa.uiuc.edu/cgi/env.html
    """

    req.add_common_vars()
    env = {}
    for k in req.subprocess_env.keys():
        env[k] = req.subprocess_env[k]
        
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
        self.write(string.joinfields(list, ''))
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
        s = string.split(self.buf + self.read(), '\n')
        return map(lambda s: s + '\n', s)

    def readline(self, n = -1):

        if n == 0:
            return ""

        # fill up the buffer
        self.buf = self.buf + self.req.read(self.BLOCK)

        # look for \n in the buffer
        i = string.find(self.buf, '\n')
        while i == -1: # if \n not found - read more
            if (n != -1) and (len(self.buf) >= n): # we're past n
                i = n - 1
                break
            x = len(self.buf)
            self.buf = self.buf + self.req.read(self.BLOCK)
            if len(self.buf) == x: # nothing read, eof
                i = x - 1
                break 
            i = string.find(self.buf, '\n', x)
        
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
            ss = string.split(self.headers, '\r\n\r\n', 1)
            if len(ss) < 2:
                # second try with \n\n
                ss = string.split(self.headers, '\n\n', 1)
                if len(ss) >= 2:
                    headers_over = 1
            else:
                headers_over = 1
                    
            if headers_over:
                # headers done, process them
                string.replace(ss[0], '\r\n', '\n')
                lines = string.split(ss[0], '\n')
                for line in lines:
                    h, v = string.split(line, ":", 1)
                    v = string.strip(v)
                    if string.lower(h) == "status":
                        status = int(string.split(v)[0])
                        self.req.status = status
                    elif string.lower(h) == "content-type":
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
    env = os.environ.copy()
    
    si = sys.stdin
    so = sys.stdout

    env = build_cgi_env(req)
 
    for k in env.keys():
        os.environ[k] = env[k]

    sys.stdout = CGIStdout(req)
    sys.stdin = CGIStdin(req)

    sys.argv = [] # keeps cgi.py happy

    return env, si, so
        
def restore_nocgi(env, si, so):
    """ see setup_cgi() """

    osenv = os.environ

    # restore env
    for k in osenv.keys():
        del osenv[k]
    for k in env.keys():
        osenv[k] = env[k]

    sys.stdout = si
    sys.stdin = so

def init():
    """ 
        This function is called by the server at startup time
    """

    return CallBack()

## Some functions made public
make_table = _apache.make_table
log_error = _apache.log_error
parse_qs = _apache.parse_qs
parse_qsl = _apache.parse_qsl

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
FINFO_VALID = 0
FINFO_PROTECTION = 1
FINFO_USER = 2
FINFO_GROUP = 3
FINFO_INODE = 4
FINFO_DEVICE = 5
FINFO_NLINK = 6
FINFO_SIZE = 7
FINFO_CSIZE = 8
FINFO_ATIME = 9
FINFO_MTIME = 10
FINFO_CTIME = 11
FINFO_FNAME = 12
FINFO_NAME = 13
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






















