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
 #    contact grisha@ispol.com.
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
 # $Id: publisher.py,v 1.5 2000/12/14 19:19:58 gtrubetskoy Exp $

"""
  This handler is conceputally similar to Zope's ZPublisher, except
  that it:

  1. Is written specifically for mod_python and is therefore much faster
  2. Does not require objects to have a documentation string
  3. Passes all arguments as simply string
  4. Does not try to match Python errors to HTTP errors
  5. Does not give special meaning to '.' and '..'.
"""

import apache
import util

import os
import string
import imp
import re
import base64

import new

# list of suffixes - .py, .pyc, etc.
suffixes = map(lambda x: x[0], imp.get_suffixes())

# now compile a regular expression out of it:
exp = "\\" + string.join(suffixes, "$|\\")
suff_matcher = re.compile(exp)

def handler(req):

    # use direct access to _req for speed
    _req = req._req

    args = {}

    # get the path PATH_INFO (everthing after script)
    if not _req.subprocess_env.has_key("PATH_INFO"):
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    
    func_path = _req.subprocess_env["PATH_INFO"][1:] # skip fist /
    func_path = string.replace(func_path, "/", ".")
    if func_path[-1] == ".":
        func_path = func_path[:-1] 

    # if any part of the path begins with "_", abort
    if func_path[0] == '_' or string.count(func_path, "._"):
        raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

    # process input, if any
    fs = util.FieldStorage(req, keep_blank_values=1)
    req.form = fs

    # step through fields
    for field in fs.list:

       # if it is a file, make File()
       if field.filename:
           val = File(field)
       else:
           val = field.value

       if args.has_key(field.name):
           args[field.name].append(val)
       else:
           args[field.name] = [val]

    # at the end, we replace lists with single values
    for arg in args.keys():
        if len(args[arg]) == 1:
            args[arg] = args[arg][0]

    # add req
    args["req"] = req

    # import the script
    path, module_name =  os.path.split(_req.filename)

    # get rid of the suffix
    module_name = suff_matcher.sub("", module_name)

    # import module (or reload if needed)
    module = apache.import_module(module_name, _req, [path])

    # does it have an __auth__?
    auth_realm = process_auth(req, module)

    # resolve the object ('traverse')
    try:
        object = resolve_object(req, module, func_path, auth_realm)
    except AttributeError:
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

    # does it have an __auth__?
    process_auth(req, object)

    # not callable, a class or an aunbound method
    if not callable(object) or \
       str(type(object)) == "<type 'class'>" \
       or (hasattr(object, 'im_self') and not object.im_self):

        result = str(object)
        
    else:
        # callable, (but not a class or unbound method)

        # we need to weed out unexpected keyword arguments
        # and for that we need to get a list of them. There
        # are a few options for callable objects here:

        if str(type(object)) == "<type 'instance'>":
            # instances are callable when they have __call__()
            object = object.__call__

        if hasattr(object, "func_code"):
            # function
            fc = object.func_code
            expected = fc.co_varnames[0:fc.co_argcount]
        elif hasattr(object, 'im_func'):
            # method
            fc = object.im_func.func_code
            expected = fc.co_varnames[1:fc.co_argcount]

        # remove unexpected args
        for name in args.keys():
            if name not in expected:
                del args[name]

        result = apply(object, (), args)

    if result:
        result = str(result)

        # mod_negotiation will default to application/x-httpd-cgi
        # for POST requests, but we know that always to be false.....
        if not req.content_type or req.content_type == "application/x-httpd-cgi":
            # make an attempt to guess content-type
            if string.lower(string.strip(result[:100])[:6]) == '<html>' \
               or string.find(result,'</') > 0:
                req.content_type = 'text/html'
            else:
                req.content_type = 'text/plain'

        req.send_http_header()
        req.write(result)
        return apache.OK
    else:
        return apache.HTTP_INTERNAL_SERVER_ERROR

def process_auth(req, object, realm=None):

    __auth__ = None

    if type(object) == type(process_auth):
        # functions are a bit tricky
        if hasattr(object, "func_code"):
            consts = object.func_code.co_consts
            for const in consts:
                if hasattr(const, "co_name"):
                    if const.co_name == "__auth__":
                        __auth__ = new.function(const, globals())
                        break

    elif hasattr(object, "__auth__"):
        
        __auth__ = object.__auth__

    if __auth__:

        # because ap_get_basic insists on making sure that AuthName and
        # AuthType directives are specified and refuses to do anything
        # otherwise (which is technically speaking a good thing), we
        # have to do base64 decoding ourselves.
        if not req.headers_in.has_key("Authorization"):
            raise apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED
        else:
            try:
                s = req.headers_in["Authorization"][6:]
                s = base64.decodestring(s)
                user, passwd = string.split(s, ":")
            except:
                raise apache.SERVER_RETURN, apache.HTTP_BAD_REQUEST

        if hasattr(object, "__auth_realm__"):
            realm = object.__auth_realm__
            
        rc = __auth__(req, user, passwd)
        if not rc:
            if realm:
                s = 'Basic realm = "%s"' % realm
                req.err_headers_out["WWW-Authenticate"] = s
            raise apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED    

    return realm

def resolve_object(req, obj, object_str, auth_realm=None):
    """
    This function traverses the objects separated by .
    (period) to find the last one we're looking for.
    """

    for obj_str in  string.split(object_str, '.'):
        obj = getattr(obj, obj_str)
        auth_realm = process_auth(req, obj, auth_realm)

    return obj


class File:
    """ Like a file, but also has headers and filename
    """

    def __init__(self, field):

        # steal all the file-like methods
        methods = field.file.__methods__
        for m in methods:
            self.__dict__[m] = methods[m]

        self.headers = field.headers
        self.filename = field.filename
    
