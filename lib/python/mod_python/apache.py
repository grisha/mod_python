
"""
  (C) Gregory Trubetskoy <grisha@ispol.com> May 1998, Nov 1998

  This file is part of mod_python. See COPYRIGHT file for details.

  $Id: apache.py,v 1.5 2000/05/13 02:22:37 grisha Exp $

"""

import sys
import string
import traceback
import time
import os
import stat
import imp
import types
import _apache

# XXX consider using intern() for some strings

class CallBack:
    """
    A generic callback object.
    """

    def resolve_object(self, module_name, object_str):
        """
        This function traverses the objects separated by .
        (period) to find the last one we're looking for.

        The rules are:
        1. try the object directly,
           failing that
        2. from left to right, find objects, if it is
           a class, instantiate it passing the request
           as single argument
        """

        # to bring the module in the local scope, we need to
        # import it again, this shouldn't have any significant
        # performance impact, since it's already imported

        exec "import " + module_name

        try:
            obj = eval("%s.%s" % (module_name, object_str))
            if hasattr(obj, "im_self") and not obj.im_self:
                # this is an unbound method, it's class
                # needs to be insantiated
                raise AttributeError, obj.__name__
            else:
                # we found our object
                return obj

        except AttributeError, attr:
            _apache.log_error(object_str)
            # try to instantiate attr before attr in error
            list = string.split(object_str, '.')

            i = list.index(str(attr))
            klass = eval(string.join([module_name] + list[:i], "."))

            # is this a class?
            if type(klass) == types.ClassType:
                obj = klass()
                return eval("obj." + string.join(list[i:], "."))
            else:
                raise "ResolveError", "Couldn't resolve object '%s' in module '%s'." % \
                      (object_str, module_name)

    def Dispatch(self, req, htype):
        """
        This is the handler dispatcher.
        """

        # be cautious
        result = HTTP_INTERNAL_SERVER_ERROR

        # request
        self.req = req

        # config
        self.config = req.get_config()
        debug = self.config.has_key("PythonDebug")

        try:
            # cycle through the handlers
            handlers = string.split(self.config[htype])

            for handler in handlers:

                # split module::handler
                l = string.split(handler, '::', 1)
                module_name = l[0]
                if len(l) == 1:
                    # no oject, provide default
                    object_str = string.lower(htype[len("python"):])
                else:
                    object_str = l[1]

                # import module
                module = import_module(module_name, req)

                # find the object
                object = self.resolve_object(module_name, object_str)

                # call the object
                result = object(req)

                # stop cycling through handlers
                if result != OK:
                    break

        except SERVER_RETURN, value:
            # SERVER_RETURN indicates a non-local abort from below
            # with value as (result, status) or (result, None) or result
            try:
                if type(value) == type(()):
                    (result, status) = value
                    if status:
                        req.status = status
                else:
                    result, status = value, value
            except:
                pass

        except PROG_TRACEBACK, traceblock:
            # Program run-time error
            try:
                (etype, value, traceback) = traceblock
                result = self.ReportError(etype, value, traceback,
                                          htype=htype, hname=handler,
                                          debug=debug)
            finally:
                traceback = None

        except:
            # Any other rerror (usually parsing)
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                result = self.ReportError(exc_type, exc_value, exc_traceback,
                                          htype=htype, hname=handler, debug=debug)
            finally:
                exc_traceback = None

	return result


    def ReportError(self, etype, evalue, etb, htype="N/A", hname="N/A", debug=0):
	""" 
	This function is only used when debugging is on.
	It sends the output similar to what you'd see
	when using Python interactively to the browser
	"""

        try:
            req = self.req

            if str(etype) == "exceptions.IOError" \
               and str(evalue)[:5] == "Write":
                # if this is an IOError while writing to client,
                # it is probably better to write to the log file
                # even if debug is on.
                debug = 0

            if debug:

                # replace magnus-internal/X-python-e with text/html
                req.content_type = 'text/plain'

                #req.status = 200 # OK
                req.send_http_header()

                s = '\\nERROR mod_python: "%s %s"\n\n' % (htype, hname)
                for e in traceback.format_exception(etype, evalue, etb):
                    s = s + e + '\n'
                s = s + "\nNOTE: More output from other handlers, if any, may follow.\n"
                s = s + "This will NOT happen, and request processing will STOP\n"
                s = s + "at this point when you remove PythonDebug directive.\n\n"

                req.write(s)

                return OK

            else:
                for e in traceback.format_exception(etype, evalue, etb):
                    s = "%s %s: %s" % (htype, hname, e[:-1])
                    _apache.log_error(s, APLOG_NOERRNO|APLOG_ERR, req.server)

                return HTTP_INTERNAL_SERVER_ERROR
        finally:
            # erase the traceback
            etb = None

def import_module(module_name, req=None):
    """ 
    Get the module to handle the request. If
    autoreload is on, then the module will be reloaded
    if it has changed since the last import.
    """

    # get the options
    autoreload, debug, pythonpath = 1, None, None
    if req:
        config = req.get_config()
        autoreload = not config.has_key("PythonNoReload")
        debug = not config.has_key("PythonDebug")
        if config.has_key("PythonPath"):
            pythonpath = config["PythonPath"]

    # unless pythonpath is set explicitely
    if pythonpath:
        sys.path = eval(pythonpath)
    else:
        # add '.' to sys.path 
        if '.' not in sys.path:
            sys.path[:0] = ['.']

    # try to import the module
    try:

        oldmtime = None
        mtime = None

        if  not autoreload:

            # import module
            exec "import " + module_name
            module = eval(module_name)

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

                exec "import " + module_name
                module = eval(module_name)

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

    except (ImportError, AttributeError, SyntaxError):

        if debug :
            # pass it on
            traceblock = sys.exc_info()
            raise PROG_TRACEBACK, traceblock

        else:
            # show and HTTP error
            raise SERVER_RETURN, HTTP_INTERNAL_SERVER_ERROR

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
            s = self.req.read(n)
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
            ss = string.split(self.headers, '\n\n', 1)
            if len(ss) < 2:
                # headers not over yet
                pass
            else:
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
                        self.req.headers_out[h] = v
                self.req.send_http_header()
                self.headers_sent = 1
                # write the body if any at this point
                self.req.write(ss[1])
        else:
            self.req.write(str(s))
        
        self.pos = self.pos + len(s)

    def tell(self): return self.pos

def setup_cgi(req):
    """
    Replace sys.stdin and stdout with an objects that reead/write to
    the socket, as well as substitute the os.environ.
    Returns (environ, stdin, stdout) which you must save and then use
    with restore_nocgi().
    """

    osenv = os.environ

    # save env
    env = eval(`osenv`)
    
    si = sys.stdin
    so = sys.stdout

    env = build_cgi_env(req)
    # the environment dictionary cannot be replace
    # because some other parts of python already hold
    # a reference to it. it must be edited "by hand"

    #for k in osenv.keys():
    #    del osenv[k]
    for k in env.keys():
        osenv[k] = env[k]

    sys.stdout = CGIStdout(req)
    sys.stdin = CGIStdin(req)

    sys.argv = [] # keeps cgi.py happy

    return env, si, so
        
def restore_nocgi(env, si, so):
    """ see setup_cgi() """

    osenv = os.environ

    # restore env
    #for k in osenv.keys():
    #    del osenv[k]
    #for k in env.keys():
    #        osenv[k] = env[k]

    sys.stdout = si
    sys.stdin = so



def init():
    """ 
        This function is called by the server at startup time
    """

    # create a callback object
    obCallBack = CallBack()

    import _apache

    # "give it back" to the server
    _apache.SetCallBack(obCallBack)

## Some functions made public
make_table = _apache.make_table
log_error = _apache.log_error

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

SERVER_RETURN = "SERVER_RETURN"
PROG_TRACEBACK = "PROG_TRACEBACK"
OK = REQ_PROCEED = 0
HTTP_INTERNAL_SERVER_ERROR = REQ_ABORTED = 500
DECLINED = REQ_NOACTION = -1
REQ_EXIT = "REQ_EXIT"         

























