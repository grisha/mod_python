 #
 # Copyright 2004 Apache Software Foundation 
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
 # Originally developed by Gregory Trubetskoy.
 #
 # $Id$

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

import sys
import os
import imp
import re
import base64

import new
import types
from types import *

imp_suffixes = " ".join([x[0][1:] for x in imp.get_suffixes()])

def handler(req):

    req.allow_methods(["GET", "POST", "HEAD"])
    if req.method not in ["GET", "POST", "HEAD"]:
        raise apache.SERVER_RETURN, apache.HTTP_METHOD_NOT_ALLOWED

    func_path = ""
    if req.path_info:
        func_path = req.path_info[1:] # skip first /
        func_path = func_path.replace("/", ".")
        if func_path[-1:] == ".":
            func_path = func_path[:-1] 

    # default to 'index' if no path_info was given
    if not func_path:
        func_path = "index"

    # if any part of the path begins with "_", abort
    # We need to make this test here, before resolve_object,
    # to prevent the loading of modules whose name begins with
    # an underscore.
    if func_path[0] == '_' or func_path.count("._"):
        req.log_error('Cannot access %s because '
                      'it contains at least an underscore'
                      % func_path, apache.APLOG_WARNING)
        raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

    ## import the script
    path, module_name =  os.path.split(req.filename)
    if not module_name:
        module_name = "index"

    # get rid of the suffix
    #   explanation: Suffixes that will get stripped off
    #   are those that were specified as an argument to the
    #   AddHandler directive. Everything else will be considered
    #   a package.module rather than module.suffix
    exts = req.get_addhandler_exts()
    if not exts:
        # this is SetHandler, make an exception for Python suffixes
        exts = imp_suffixes
    if req.extension:  # this exists if we're running in a | .ext handler
        exts += req.extension[1:] 
    if exts:
        suffixes = exts.strip().split()
        exp = "\\." + "$|\\.".join(suffixes)
        suff_matcher = re.compile(exp) # python caches these, so its fast
        module_name = suff_matcher.sub("", module_name)

    # import module (or reload if needed)
    # the [path] argument tells import_module not to allow modules whose
    # full path is not in [path] or below.
    config = req.get_config()
    autoreload=int(config.get("PythonAutoReload", 1))
    log=int(config.get("PythonDebug", 0))
    try:
        module = apache.import_module(module_name,
                                      autoreload=autoreload,
                                      log=log,
                                      path=[path])
    except ImportError:
        et, ev, etb = sys.exc_info()
        # try again, using default module, perhaps this is a
        # /directory/function (as opposed to /directory/module/function)
        func_path = module_name
        module_name = "index"
        try:
            module = apache.import_module(module_name,
                                          autoreload=autoreload,
                                          log=log,
                                          path=[path])
        except ImportError:
            # raise the original exception
            raise et, ev, etb
        
    # does it have an __auth__?
    realm, user, passwd = process_auth(req, module)

    # resolve the object ('traverse')
    try:
        object = resolve_object(req, module, func_path, realm, user, passwd)
    except AttributeError:
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    
    # not callable, a class or an unbound method
    if (not callable(object) or 
        type(object) is ClassType or
        (hasattr(object, 'im_self') and not object.im_self)):

        result = str(object)
        
    else:
        # callable, (but not a class or unbound method)
        
        # process input, if any
        req.form = util.FieldStorage(req, keep_blank_values=1)
        
        result = util.apply_fs_data(object, req.form, req=req)

    if result or req.bytes_sent > 0 or req.next:
        
        if result is None:
            result = ""
        elif type(result) == UnicodeType:
            return result
        else:
            result = str(result)

        # unless content_type was manually set, we will attempt
        # to guess it
        if not req._content_type_set:
            # make an attempt to guess content-type
            if result[:100].strip()[:6].lower() == '<html>' \
               or result.find('</') > 0:
                req.content_type = 'text/html'
            else:
                req.content_type = 'text/plain'

        if req.method != "HEAD":
            req.write(result)
        else:
            req.write("")
        return apache.OK
    else:
        req.log_error("mod_python.publisher: %s returned nothing." % `object`)
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
            user, passwd = s.split(":", 1)
        except:
            raise apache.SERVER_RETURN, apache.HTTP_BAD_REQUEST

    if hasattr(object, "__auth_realm__"):
        realm = object.__auth_realm__

    if type(object) is FunctionType:
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
            if type(__auth__) is DictionaryType:
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
            if type(__access__) in (ListType, TupleType):
                rc = user in __access__
            else:
                rc = __access__

        if not rc:
            raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

    return realm, user, passwd

### Those are the traversal and publishing rules ###

# tp_rules is a dictionary, indexed by type, with tuple values.
# The first item in the tuple is a boolean telling if the object can be traversed (default is True)
# The second item in the tuple is a boolen telling if the object can be published (default is True)
tp_rules = {}

# by default, built-in types cannot be traversed, but can be published
default_builtins_tp_rule = (False,True)
for t in types.__dict__.values():
    if isinstance(t, type):
        tp_rules[t]=default_builtins_tp_rule

# those are the exceptions to the previous rules
tp_rules.update({
    # Those are not traversable nor publishable
    ModuleType          : (False, False),
    ClassType           : (False, False),
    TypeType            : (False, False),
    BuiltinFunctionType : (False, False),
    
    # XXX Generators should be publishable, see
    # http://issues.apache.org/jira/browse/MODPYTHON-15
    # Until they are, it is not interesting to publish them
    GeneratorType       : (False, False),
    
    # Old-style instances are traversable
    InstanceType        : (True, True),
})

# types which are not referenced in the tp_rules dictionary will be traversable
# AND publishables 
default_tp_rule = (True, True)

def resolve_object(req, obj, object_str, realm=None, user=None, passwd=None):
    """
    This function traverses the objects separated by .
    (period) to find the last one we're looking for.
    """
    parts = object_str.split('.')
        
    for i, obj_str in enumerate(parts):

        # path components starting with an underscore are forbidden
        if obj_str[0]=='_':
            req.log_error('Cannot traverse %s in %s because '
                          'it starts with an underscore'
                          % (obj_str, req.unparsed_uri), apache.APLOG_WARNING)
            raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

        # if we're not in the first object (which is the module)
        if i>0:
        
            # we're going to check whether be can traverse this type or not
            rule = tp_rules.get(type(obj), default_tp_rule)
            if not rule[0]:
                req.log_error('Cannot traverse %s in %s because '
                              '%s is not a traversable object'
                              % (obj_str, req.unparsed_uri, obj), apache.APLOG_WARNING)
                raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN
        
        # we know it's OK to call getattr
        # note that getattr can really call some code because
        # of property objects (or attribute with __get__ special methods)...
        obj = getattr(obj, obj_str)

        # we process the authentication for the object
        realm, user, passwd = process_auth(req, obj, realm, user, passwd)
    
    # we're going to check if the final object is publishable
    rule = tp_rules.get(type(obj), default_tp_rule)
    if not rule[1]:

         req.log_error('Cannot publish %s in %s because '
                       '%s is not publishable'
                       % (obj_str, req.unparsed_uri, obj), apache.APLOG_WARNING)
         raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

    return obj
