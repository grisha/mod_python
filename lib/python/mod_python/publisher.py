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
 # $Id: publisher.py,v 1.18 2002/09/06 22:06:28 gtrubetskoy Exp $

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


def handler(req):

    req.allow_methods(["GET", "POST"])
    if req.method not in ["GET", "POST"]:
        raise apache.SERVER_RETURN, apache.HTTP_METHOD_NOT_ALLOWED

    # get the path PATH_INFO (everthing after script)
    if not req.subprocess_env.has_key("PATH_INFO"):
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    
    func_path = req.subprocess_env["PATH_INFO"][1:] # skip first /
    func_path = string.replace(func_path, "/", ".")
    if func_path[-1] == ".":
        func_path = func_path[:-1] 

    # if any part of the path begins with "_", abort
    if func_path[0] == '_' or string.count(func_path, "._"):
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

    # process input, if any
    fs = util.FieldStorage(req, keep_blank_values=1)
    req.form = fs

    args = {}

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

    ## import the script
    path, module_name =  os.path.split(req.filename)

    # get rid of the suffix
    #   explanation: Suffixes that will get stripped off
    #   are those that were specified as an argument to the
    #   AddHandler directive. Everything else will be considered
    #   a package.module rather than module.suffix
    exts = req.get_addhandler_exts()
    if exts:
        suffixes = exts.strip().split()
        exp = "\\." + string.join(suffixes, "$|\\.")
        suff_matcher = re.compile(exp) # python caches these, so its fast
        module_name = suff_matcher.sub("", module_name)

    # import module (or reload if needed)
    # the [path] argument tells import_module not to allow modules whose
    # full path is not in [path] or below.
    module = apache.import_module(module_name, req.get_config(), [path])

    # does it have an __auth__?
    realm, user, passwd = process_auth(req, module)

    # resolve the object ('traverse')
    try:
        object = resolve_object(req, module, func_path, realm, user, passwd)
    except AttributeError:
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    
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

        # unless content_type was manually set, we will attempt
        # to guess it
        if not req._content_type_set:
            # make an attempt to guess content-type
            if string.lower(string.strip(result[:100])[:6]) == '<html>' \
               or string.find(result,'</') > 0:
                req.content_type = 'text/html'
            else:
                req.content_type = 'text/plain'

        if req.method != "HEAD":
            req.write(result)
        else:
            req.write("")
        return apache.OK
    else:
        return apache.HTTP_INTERNAL_SERVER_ERROR

def process_auth(req, object, realm="unknown", user=None, passwd=None):

    found_auth, found_access = 0, 0

    # because ap_get_basic insists on making sure that AuthName and
    # AuthType directives are specified and refuses to do anything
    # otherwise (which is technically speaking a good thing), we
    # have to do base64 decoding ourselves.
    #
    # to avoid needless header parsing, user and password are parsed
    # once and the are received as arguments
    if not user and req.headers_in.has_key("Authorization"):
        try:
            s = req.headers_in["Authorization"][6:]
            s = base64.decodestring(s)
            user, passwd = string.split(s, ":", 1)
        except:
            raise apache.SERVER_RETURN, apache.HTTP_BAD_REQUEST

    if hasattr(object, "__auth_realm__"):
        realm = object.__auth_realm__

    if type(object) == type(process_auth):
        # functions are a bit tricky

        if hasattr(object, "func_code"):
            func_code = object.func_code

            if "__auth__" in func_code.co_names:
                i = list(func_code.co_names).index("__auth__")
                __auth__ = func_code.co_consts[i+1]
                if hasattr(__auth__, "co_name"):
                    __auth__ = new.function(__auth__, globals())
                found_auth = 1

            if "__access__" in func_code.co_names:
                # first check the constant names
                i = list(func_code.co_names).index("__access__")
                __access__ = func_code.co_consts[i+1]
                if hasattr(__access__, "co_name"):
                    __access__ = new.function(__access__, globals())
                found_access = 1

            if "__auth_realm__" in func_code.co_names:
                i = list(func_code.co_names).index("__auth_realm__")
                realm = func_code.co_consts[i+1]

    else:
        if hasattr(object, "__auth__"):
            __auth__ = object.__auth__
            found_auth = 1
        if hasattr(object, "__access__"):
            __access__ = object.__access__
            found_access = 1

    if found_auth:

        if not user:
            # note that Opera supposedly doesn't like spaces around "=" below
            s = 'Basic realm="%s"' % realm 
            req.err_headers_out["WWW-Authenticate"] = s
            raise apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED    

        if callable(__auth__):
            rc = __auth__(req, user, passwd)
        else:
            if type(__auth__) == type({}): # dictionary
                rc = __auth__.has_key(user) and __auth__[user] == passwd
            else:
                rc = __auth__
            
        if not rc:
            s = 'Basic realm = "%s"' % realm
            req.err_headers_out["WWW-Authenticate"] = s
            raise apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED    

    if found_access:

        if callable(__access__):
            rc = __access__(req, user)
        else:
            if type(__access__) in (type([]), type(())):
                rc = user in __access__
            else:
                rc = __access__

        if not rc:
            raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

    return realm, user, passwd

def resolve_object(req, obj, object_str, realm=None, user=None, passwd=None):
    """
    This function traverses the objects separated by .
    (period) to find the last one we're looking for.
    """

    for obj_str in  string.split(object_str, '.'):
        obj = getattr(obj, obj_str)

        # object cannot be a module
        if type(obj) == type(apache):
            raise apache.SERVER_RETURN, apache.HTTP_NOTFOUND

        realm, user, passwd = process_auth(req, obj, realm,
                                           user, passwd)

    return obj


class File:
    """ Like a file, but also has headers and filename
    """

    def __init__(self, field):

        # steal all the file-like methods
        for m in dir(field.file):
            self.__dict__[m] = getattr(field.file, m)

        self.headers = field.headers
        self.filename = field.filename
    
        

