"""
     (C) Gregory Trubetskoy <grisha@ispol.com> May 1998, Nov 1998, Apr 2000

     Httpdapy handler module.
"""

import string
import sys
import apache
import os

# Response status codes for use with rq.protocol_status(sn, *)

SERVER_RETURN = apache.SERVER_RETURN
PROG_TRACEBACK = apache.PROG_TRACEBACK
REQ_PROCEED = apache.REQ_PROCEED
REQ_ABORTED = apache.REQ_ABORTED
REQ_NOACTION = apache.REQ_NOACTION
REQ_EXIT = apache.REQ_EXIT

PROTOCOL_CONTINUE = apache.HTTP_CONTINUE
PROTOCOL_SWITCHING = apache.HTTP_SWITCHING_PROTOCOLS
PROTOCOL_OK = apache.HTTP_OK
PROTOCOL_CREATED = apache.HTTP_CREATED
PROTOCOL_NO_RESPONSE = apache.HTTP_NO_CONTENT
PROTOCOL_PARTIAL_CONTENT = apache.HTTP_PARTIAL_CONTENT
PROTOCOL_REDIRECT = apache.HTTP_MOVED_TEMPORARILY 
PROTOCOL_NOT_MODIFIED = apache.HTTP_NOT_MODIFIED 
PROTOCOL_BAD_REQUEST = apache.HTTP_BAD_REQUEST
PROTOCOL_UNAUTHORIZED = apache.HTTP_UNAUTHORIZED
PROTOCOL_FORBIDDEN = apache.HTTP_FORBIDDEN 
PROTOCOL_NOT_FOUND = apache.HTTP_NOT_FOUND 
PROTOCOL_METHOD_NOT_ALLOWED = apache.HTTP_METHOD_NOT_ALLOWED
PROTOCOL_PROXY_UNAUTHORIZED = apache.HTTP_PROXY_AUTHENTICATION_REQUIRED
PROTOCOL_CONFLICT = apache.HTTP_CONFLICT
PROTOCOL_LENGTH_REQUIRED = apache.HTTP_LENGTH_REQUIRED
PROTOCOL_PRECONDITION_FAIL = apache.HTTP_PRECONDITION_FAILED
PROTOCOL_ENTITY_TOO_LARGE = apache.HTTP_REQUEST_ENTITY_TOO_LARGE
PROTOCOL_URI_TOO_LARGE = apache. HTTP_REQUEST_URI_TOO_LARGE
PROTOCOL_SERVER_ERROR = apache.HTTP_INTERNAL_SERVER_ERROR
PROTOCOL_VERSION_NOT_SUPPORTED = apache.HTTP_VERSION_NOT_SUPPORTED
PROTOCOL_NOT_IMPLEMENTED = apache.HTTP_NOT_IMPLEMENTED

Status = {
    "100" : PROTOCOL_CONTINUE,
    "101" : PROTOCOL_SWITCHING,
    "200" : PROTOCOL_OK,
    "201" : PROTOCOL_CREATED,
    "204" : PROTOCOL_NO_RESPONSE,
    "206" : PROTOCOL_PARTIAL_CONTENT,
    "302" : PROTOCOL_REDIRECT,
    "304" : PROTOCOL_NOT_MODIFIED,
    "400" : PROTOCOL_BAD_REQUEST,
    "401" : PROTOCOL_UNAUTHORIZED,
    "403" : PROTOCOL_FORBIDDEN,
    "404" : PROTOCOL_NOT_FOUND,
    "405" : PROTOCOL_METHOD_NOT_ALLOWED,
    "407" : PROTOCOL_PROXY_UNAUTHORIZED,
    "409" : PROTOCOL_CONFLICT,
    "411" : PROTOCOL_LENGTH_REQUIRED,
    "412" : PROTOCOL_PRECONDITION_FAIL,
    "413" : PROTOCOL_ENTITY_TOO_LARGE,
    "414" : PROTOCOL_URI_TOO_LARGE,
    "500" : PROTOCOL_SERVER_ERROR,
    "501" : PROTOCOL_NOT_IMPLEMENTED,
    "505" : PROTOCOL_VERSION_NOT_SUPPORTED
    }

def Service(req):
    """ 
    """

    # be pessimistic
    result = apache.DECLINED

    try:

        opt = req.get_options()

        # get filename
        filename = req.filename

        # module names do not have to end with .py
        # they can have any extension or no extention at all
        # the extention will be discarded

        # find the module name by getting the string between the
        # last slash and the last dot, if any.

        slash = string.rfind(filename, "/")
        dot = string.rfind(filename, ".")

        if dot > slash:
            module_name = filename[slash + 1:dot]
        else:
            # this file has no extension
            module_name = filename[slash + 1:]

        # if we're using packages
        if opt.has_key("rootpkg"):
            module_name = opt["rootpkg"] + "." + module_name

        if opt.has_key("debug"):
            debug = opt["debug"]
        else:
            debug = 0
            
        if opt.has_key("handler"):
            module_name = opt["handler"]

        # cd into the uri directory
        if os.path.isdir(filename):
            os.chdir(filename)
        else:
            os.chdir(filename[:slash])

        # import the module
        module = apache.import_module(module_name, req)

        # instantiate the handler class
        Class = module.RequestHandler

        # construct and return an instance of the handler class
        handler = Class(req)

        # do it
        result = handler.Handle(debug=debug)

    except apache.SERVER_RETURN, value:
        # SERVER_RETURN indicates a non-local abort from below
        # with value as (result, status) or (result, None)
        try:
            (result, status) = value
            if status:
                req.status = status
        except:
            pass

    return result


class RequestHandler:
    """
    A superclass that may be used to create RequestHandlers
    in other modules, for use with this module.
    """

    def __init__(self, req):

	self.req = req

        ## backward compatibility objects - pb, sn, rq
        self.pb = NSAPI_ParameterBlock(req)
        self.rq = NSAPI_Request(req)
        self.sn = NSAPI_Session(req)

	# default content-type
	self.content_type = 'text/html'

	# no redirect
	self.redirect = ''

    def Send(self, content):

	if content:
	    # Apache doesn't want us to send content when using
	    # redirects, it puts up a default page.
	    if not self.redirect:
		self.rq.start_response(self.sn)
		self.sn.net_write(str(content))

    def Header(self):
	""" 
	This prepares the headers
	"""

	srvhdrs = self.rq.srvhdrs

	# content-type
	srvhdrs["content-type"] = self.content_type

	# for redirects, add Location header
	if self.redirect:
	    srvhdrs["Location"] = self.redirect

    def Status(self):
	""" 
	The status is set here.
	"""
	if self.redirect:
	    self.rq.protocol_status(self.sn, PROTOCOL_REDIRECT)
	else:
	    self.rq.protocol_status(self.sn, PROTOCOL_OK)

    def Handle(self, debug=0):
	"""
	This method handles the request. Although, you may be 
	tempted to override this method, you should consider 
	overriding Content() first, it may be all you need.
	"""
	try:
	    content = self.Content()
	    self.Header()
	    self.Status()
	    self.Send(content)
	except:
	    # debugging ?
	    if debug:
                exc_type, exc_value, exc_traceback = sys.exc_info()
		raise PROG_TRACEBACK, (exc_type, exc_value, exc_traceback)
	    return HTTP_INTERNAL_SERVER_ERROR
	
	return REQ_PROCEED

    def Content(self):
        """
        For testing and reference
        """
        return "Welcome to Httpdapi!"

    def form_data(self):
        """
        Utility function to get the data passed via
        POST or GET. Returns a dictionary keyed by name.
        """
        
        method = self.rq.reqpb['method']

        if method == 'POST':
            fdlen = int(self.rq.request_header("content-length", self.sn))
            fd = cgi.parse_qs(self.sn.form_data(fdlen))
        else:
            fd = cgi.parse_qs(self.rq.reqpb['query'])
           
        return fd

    def build_cgi_env(self):
        """
        Utility function that returns a dictionary of
        CGI environment variables as described in
        http://hoohoo.ncsa.uiuc.edu/cgi/env.html
        """

        return apache.build_cgi_env(self.req)

    def hook_stdout(self):
        """
        Replace sys.stdout with an object that writes to the output
        socket. Saves a copy of stdout so you can use unhook_stdout
        later.
        """

        self.save_stdout = sys.stdout
        sys.stdout = UnbufferedStdout(self.rq, self.sn)
        
    def unhook_stdout(self):
        """ see hook_stdout() """

        try:
            sys.stdout = self.save_stdout
        except:
            pass


class AuthHandler(RequestHandler):

    def Handle(self):

	return REQ_PROCEED


class UnbufferedStdout:

    """Class that allows writing to stdout a la CGI
    """
    
    def __init__(self, rq, sn):
        self.pos = 0
        self.sn = sn
        self.rq = rq
        
    def close(self):
        pass
            
    def isatty(self):
        return 0
    
    def seek(self, pos, mode = 0):
        pass

    def tell(self):
        return self.pos
    
    def read(self, n = -1):
        return ""

    def readline(self, length = None):
        return ""
    
    def readlines(self):
        return []

    def write(self, s):

        if not s: return
        
	self.rq.start_response(self.sn)
	self.sn.net_write(str(s))
        
        self.pos = self.pos + len(s)
        
    def writelines(self, list):
        self.write(string.joinfields(list, ''))
        
    def flush(self):
        pass

#####
#    from here on - backward compatibility

class NSAPI_Pblock:
    
    """This is basically a wrapper around the table object
    """

    def __init__(self, table):
	self.table = table

    def pblock2str(self):
	s = ''
	for key in self.table.keys():
	    s = s + '%s="%s" ' % (key, value)
	return s

    def nvinsert(self, name, value):
	self.table[name] = value

    def findval(name):
	return self.table[name]

    def pblock_remove(self, name):
	del self.table[name]

    def has_key(self, name):
	return self.table.has_key(name)

    def keys(self):
	return self.table.keys()

    def __getitem__(self, name):
	return self.table[name]

    def __setitem__(self, name, value):
	self.table[name] = value

    def __repr__(self):
        return `self.table`


def NSAPI_ParameterBlock(req):

    pb = apache.make_table()
    conf = req.get_config()
    opt = req.get_options()

    for k in conf.keys():
        pb[k] = conf[k]
    for k in opt.keys():
        pb[k] = opt[k]
    pb["fn"] = "python_request_handler"
    pb["method"] = "GET|HEAD|POST"
    pb["server-software"] = "Apache"
    pb["type"] = req.content_type
    pw = req.get_basic_auth_pw()
    if pw:
        pb["auth-password"] = pw
        pb["auth-type"] = req.connection.ap_auth_type
        pb["auth-user"] = req.connection.user

    return NSAPI_Pblock(pb)


class NSAPI_Request:

    """ This is the old request object
    """

    def __init__(self, req):
	self.req = req
	self.response_started = 0

	# reqpb
	self.reqpb = apache.make_table()
	self.reqpb["clf-request"] = self.req.the_request
	self.reqpb["method"] = self.req.method
	self.reqpb["protocol"] = self.req.subprocess_env["SERVER_PROTOCOL"]
	self.reqpb["uri"] = self.req.uri
	self.reqpb["query"] = self.req.subprocess_env["QUERY_STRING"]

	# headers
	self.headers = self.req.headers_in

	# srvhdrs
	self.srvhdrs = self.req.headers_out

        # vars
        self.vars = apache.make_table()
        pw = self.req.get_basic_auth_pw()
        if pw:
            self.vars["auth-password"] = pw
        if self.req.connection.ap_auth_type:
            self.vars["auth-type"] = self.req.connection.ap_auth_type
        if self.req.connection.user:
            self.vars["auth-user"] = self.req.connection.user
        if self.req.path_info:
            self.vars["path-info"] = self.req.path_info
        if self.req.subprocess_env.has_key("PATH_TRANSLATED"):
            self.vars["path-translated"] = self.req.subprocess_env["PATH_TRANSLATED"]
        if self.req.filename:
            self.vars["path"] = self.req.filename


    def start_response(self, sn):

	if not self.response_started:
            self.req.content_type = self.req.headers_out["content-type"]
	    self.req.send_http_header()
	    self.response_started = 1

    def request_header(self, header, session=None):
	return self.req.headers_in[string.lower(header)]


    def protocol_status(self, sn, status):
	self.req.status = status
	
    def log_err(self, function, message, sno):
	s = "for host %s trying to %s, %s reports: %s" % \
	    (self.req.connection.remote_ip, self.req.the_request, function, message)
	apache.log_error(APLOG_NOERRNO|APLOG_ERR, self.req.server, s)


class NSAPI_Session:

    def __init__(self, req):
        self.req = req

    def session_dns(self):
        return self.req.connection.remote_logname

    def net_write(self, what):
        return self.req.write(what)

    def client(self):
        client = apache.make_table()
        client["ip"] = self.req.connection.remote_ip
        client["dns"] = self.req.connection.remote_host
        return client

    def net_read(self, len):
        return self.req.read(len)

