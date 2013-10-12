 #
 # Copyright (C) 2000, 2001, 2013 Gregory Trubetskoy
 # Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007 Apache Software Foundation
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

"""
  This handler is conceptually similar to Zope's ZPublisher, except
  that it:

  1. Is written specifically for mod_python and is therefore much faster
  2. Does not require objects to have a documentation string
  3. Passes all arguments as simply string
  4. Does not try to match Python errors to HTTP errors
  5. Does not give special meaning to '.' and '..'.
"""

from . import apache
from . import util

import sys
import os
from os.path import exists, isabs, normpath, split, isfile, join, dirname
import imp
import re
import base64

import new
import types
from types import *
import collections


imp_suffixes = " ".join([x[0][1:] for x in imp.get_suffixes()])

# Python 2/3 compat workaround
PY2 = sys.version[0] == '2'
def _callable(obj):
    if PY2:
        return callable(obj)
    else:
        return isinstance(__auth__, collections.Callable)

####################### The published page cache ##############################

from .cache import ModuleCache, NOT_INITIALIZED

class PageCache(ModuleCache):
    """ This is the cache for page objects. Handles the automatic reloading of pages. """

    def key(self, req):
        """ Extracts the normalized filename from the request """
        return req.filename

    def check(self, key, req, entry):
        config = req.get_config()
        autoreload=int(config.get("PythonAutoReload", 1))
        if autoreload==0 and entry._value is not NOT_INITIALIZED:
            # if we don't want to reload and we have a value,
            # then we consider it fresh
            return None
        else:
            return ModuleCache.check(self, key, req, entry)

    def build(self, key, req, opened, entry):
        config = req.get_config()
        log=int(config.get("PythonDebug", 0))
        if log:
            if entry._value is NOT_INITIALIZED:
                req.log_error('Publisher loading page %s'%req.filename, apache.APLOG_NOTICE)
            else:
                req.log_error('Publisher reloading page %s'%req.filename, apache.APLOG_NOTICE)
        return ModuleCache.build(self, key, req, opened, entry)

page_cache = PageCache()

####################### Interface to the published page cache ##################

# def get_page(req, path):
#     """
#         This imports a published page. If the path is absolute it is used as is.
#         If it is a relative path it is relative to the published page
#         where the request is really handled (not relative to the path
#         given in the URL).
#
#         Warning : in order to maintain consistency in case of module reloading,
#         do not store the resulting module in a place that outlives the request
#         duration.
#     """
#
#     real_filename = req.filename
#
#     try:
#         if isabs(path):
#             req.filename = path
#         else:
#             req.filename = normpath(join(dirname(req.filename), path))
#
#         return page_cache[req]
#
#     finally:
#         req.filename = real_filename

####################### The publisher handler himself ##########################

def handler(req):

    req.allow_methods(["GET", "POST", "HEAD"])
    if req.method not in ["GET", "POST", "HEAD"]:
        raise apache.SERVER_RETURN(apache.HTTP_METHOD_NOT_ALLOWED)

    # Derive the name of the actual module which will be
    # loaded. In older version of mod_python.publisher
    # you can't actually have a code file name which has
    # an embedded '.' in it except for that used by the
    # extension. This is because the standard Python
    # module import system which is used will think that
    # you are importing a submodule of a package. In
    # this code, because the standard Python module
    # import system isn't used and the actual file is
    # opened directly by name, an embedded '.' besides
    # that used for the extension will technically work.

    path,module_name =  os.path.split(req.filename)

    # If the request is against a directory, fallback to
    # looking for the 'index' module. This is determined
    # by virtue of the fact that Apache will always add
    # a trailing slash to 'req.filename' when it matches
    # a directory. This will mean that the calculated
    # module name will be empty.

    if not module_name:
        module_name = 'index'

    # Now need to strip off any special extension which
    # was used to trigger this handler in the first place.

    suffixes = ['py']
    suffixes += req.get_addhandler_exts().split()
    if req.extension:
        suffixes.append(req.extension[1:])

    exp = '\\.' + '$|\\.'.join(suffixes) + '$'
    suff_matcher = re.compile(exp)
    module_name = suff_matcher.sub('',module_name)

    # Next need to determine the path for the function
    # which will be called from 'req.path_info'. The
    # leading slash and possibly any trailing slash are
    # eliminated. There would normally be at most one
    # trailing slash as Apache eliminates duplicates
    # from the original URI.

    func_path = ''

    if req.path_info:
        func_path = req.path_info[1:]
        if func_path[-1:] == '/':
            func_path = func_path[:-1]

    # Now determine the actual Python module code file
    # to load. This will first try looking for the file
    # '/path/<module_name>.py'. If this doesn't exist,
    # will try fallback of using the 'index' module,
    # ie., look for '/path/index.py'. In doing this, the
    # 'func_path' gets adjusted so the lead part is what
    # 'module_name' was set to.

    req.filename = path + '/' + module_name + '.py'

    if not exists(req.filename):
        if func_path:
            func_path = module_name + '/' + func_path
        else:
            func_path = module_name

        module_name = 'index'
        req.filename = path + '/' + module_name + '.py'

        if not exists(req.filename):
            raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

    # Default to looking for the 'index' function if no
    # function path definition was supplied.

    if not func_path:
        func_path = 'index'

    # Turn slashes into dots.

    func_path = func_path.replace('/', '.')

    # Normalise req.filename to avoid Win32 issues.

    req.filename = normpath(req.filename)


    # We use the page cache to load the module
    module = page_cache[req]

    # does it have an __auth__?
    realm, user, passwd = process_auth(req, module)

    # resolve the object ('traverse')
    object = resolve_object(req, module, func_path, realm, user, passwd)

    # publish the object
    published = publish_object(req, object)

    # we log a message if nothing was published, it helps with debugging
    if (not published) and (req._bytes_queued==0) and (req.__next__ is None):
        log=int(req.get_config().get("PythonDebug", 0))
        if log:
            req.log_error("mod_python.publisher: nothing to publish.")

    return apache.OK

def process_auth(req, object, realm="unknown", user=None, passwd=None):

    found_auth, found_access = 0, 0

    if hasattr(object, "__auth_realm__"):
        realm = object.__auth_realm__

    func_object = None

    if type(object) is FunctionType:
        func_object = object
    elif type(object) == types.MethodType:
        func_object = object.__func__

    if func_object:
        # functions are a bit tricky

        func_code = func_object.__code__
        func_globals = func_object.__globals__

        def lookup(name):
            i = None
            if name in func_code.co_names:
                i = list(func_code.co_names).index(name)
            elif func_code.co_argcount < len(func_code.co_varnames):
                names = func_code.co_varnames[func_code.co_argcount:]
                if name in names:
                    i = list(names).index(name)
            if i is not None:
                return (1, func_code.co_consts[i+1])
            return (0, None)

        (found_auth, __auth__) = lookup('__auth__')
        if found_auth and type(__auth__) == types.CodeType:
            __auth__ = new.function(__auth__, func_globals)

        (found_access, __access__) = lookup('__access__')
        if found_access and type(__access__) == types.CodeType:
            __access__ = new.function(__access__, func_globals)

        (found_realm, __auth_realm__) = lookup('__auth_realm__')
        if found_realm:
            realm = __auth_realm__

    else:
        if hasattr(object, "__auth__"):
            __auth__ = object.__auth__
            found_auth = 1
        if hasattr(object, "__access__"):
            __access__ = object.__access__
            found_access = 1

    if found_auth or found_access:
        # because ap_get_basic insists on making sure that AuthName and
        # AuthType directives are specified and refuses to do anything
        # otherwise (which is technically speaking a good thing), we
        # have to do base64 decoding ourselves.
        #
        # to avoid needless header parsing, user and password are parsed
        # once and the are received as arguments
        if not user and "Authorization" in req.headers_in:
            try:
                s = req.headers_in["Authorization"][6:]
                s = base64.decodestring(s)
                user, passwd = s.split(":", 1)
            except:
                raise apache.SERVER_RETURN(apache.HTTP_BAD_REQUEST)

    if found_auth:

        if not user:
            # note that Opera supposedly doesn't like spaces around "=" below
            s = 'Basic realm="%s"' % realm
            req.err_headers_out["WWW-Authenticate"] = s
            raise apache.SERVER_RETURN(apache.HTTP_UNAUTHORIZED)

        if _callable(__auth__):
            rc = __auth__(req, user, passwd)
        else:
            if type(__auth__) is DictionaryType:
                rc = user in __auth__ and __auth__[user] == passwd
            else:
                rc = __auth__

        if not rc:
            s = 'Basic realm = "%s"' % realm
            req.err_headers_out["WWW-Authenticate"] = s
            raise apache.SERVER_RETURN(apache.HTTP_UNAUTHORIZED)

    if found_access:

        if _callable(__access__):
            rc = __access__(req, user)
        else:
            if type(__access__) in (ListType, TupleType):
                rc = user in __access__
            else:
                rc = __access__

        if not rc:
            raise apache.SERVER_RETURN(apache.HTTP_FORBIDDEN)

    return realm, user, passwd

### Those are the traversal and publishing rules ###

# tp_rules is a dictionary, indexed by type, with tuple values.
# The first item in the tuple is a boolean telling if the object can be traversed (default is True)
# The second item in the tuple is a boolen telling if the object can be published (default is True)
tp_rules = {}

# by default, built-in types cannot be traversed, but can be published
default_builtins_tp_rule = (False, True)
for t in list(types.__dict__.values()):
    if isinstance(t, type):
        tp_rules[t]=default_builtins_tp_rule

# those are the exceptions to the previous rules
tp_rules.update({
    # Those are not traversable nor publishable
    ModuleType          : (False, False),
    BuiltinFunctionType : (False, False),

    # This may change in the near future to (False, True)
    ClassType           : (False, False),
    TypeType            : (False, False),

    # Publishing a generator may not seem to makes sense, because
    # it can only be done once. However, we could get a brand new generator
    # each time a new-style class property is accessed.
    GeneratorType       : (False, True),

    # Old-style instances are traversable
    InstanceType        : (True, True),
})

# types which are not referenced in the tp_rules dictionary will be traversable
# AND publishable
default_tp_rule = (True, True)

def resolve_object(req, obj, object_str, realm=None, user=None, passwd=None):
    """
    This function traverses the objects separated by .
    (period) to find the last one we're looking for.
    """
    parts = object_str.split('.')

    first_object = True
    for obj_str in parts:
        # path components starting with an underscore are forbidden
        if obj_str[0]=='_':
            req.log_error('Cannot traverse %s in %s because '
                          'it starts with an underscore'
                          % (obj_str, req.unparsed_uri), apache.APLOG_WARNING)
            raise apache.SERVER_RETURN(apache.HTTP_FORBIDDEN)

        if first_object:
            first_object = False
        else:
            # if we're not in the first object (which is the module)
            # we're going to check whether be can traverse this type or not
            rule = tp_rules.get(type(obj), default_tp_rule)
            if not rule[0]:
                req.log_error('Cannot traverse %s in %s because '
                              '%s is not a traversable object'
                              % (obj_str, req.unparsed_uri, obj), apache.APLOG_WARNING)
                raise apache.SERVER_RETURN(apache.HTTP_FORBIDDEN)

        # we know it's OK to call getattr
        # note that getattr can really call some code because
        # of property objects (or attribute with __get__ special methods)...
        try:
            obj = getattr(obj, obj_str)
        except AttributeError:
            raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

        # we process the authentication for the object
        realm, user, passwd = process_auth(req, obj, realm, user, passwd)

    # we're going to check if the final object is publishable
    rule = tp_rules.get(type(obj), default_tp_rule)
    if not rule[1]:

         req.log_error('Cannot publish %s in %s because '
                       '%s is not publishable'
                       % (obj_str, req.unparsed_uri, obj), apache.APLOG_WARNING)
         raise apache.SERVER_RETURN(apache.HTTP_FORBIDDEN)

    return obj

# This regular expression is used to test for the presence of an HTML header
# tag, written in upper or lower case.
re_html = re.compile(r"</HTML\s*>\s*$",re.I)
re_charset = re.compile(r"charset\s*=\s*([^\s;]+)",re.I);

def publish_object(req, obj):
    if _callable(obj):

        # To publish callables, we call them and recursively publish the result
        # of the call (as done by util.apply_fs_data)

        req.form = util.FieldStorage(req, keep_blank_values=1)
        return publish_object(req,util.apply_fs_data(obj, req.form, req=req))

# TODO : we removed this as of mod_python 3.2, let's see if we can put it back
# in mod_python 3.3
#     elif hasattr(obj,'__iter__'):
#
#         # To publish iterables, we recursively publish each item
#         # This way, generators can be published
#         result = False
#         for item in obj:
#             result |= publish_object(req,item)
#         return result
#
    else:
        if obj is None:

            # Nothing to publish
            return False

        elif isinstance(obj,UnicodeType):

            # We've got an Unicode string to publish, so we have to encode
            # it to bytes. We try to detect the character encoding
            # from the Content-Type header
            if req._content_type_set:

                charset = re_charset.search(req.content_type)
                if charset:
                    charset = charset.group(1)
                else:
                    # If no character encoding was set, we use UTF8
                    charset = 'UTF8'
                    req.content_type += '; charset=UTF8'

            else:
                # If no character encoding was set, we use UTF8
                charset = 'UTF8'

            result = obj.encode(charset)
        else:
            charset = None
            result = str(obj)

        if not req._content_type_set:
            # make an attempt to guess content-type
            # we look for a </HTML in the last 100 characters.
            # re.search works OK with a negative start index (it starts from 0
            # in that case)
            if re_html.search(result,len(result)-100):
                req.content_type = 'text/html'
            else:
                req.content_type = 'text/plain'
            if charset is not None:
                req.content_type += '; charset=%s'%charset

        # Write result even if req.method is 'HEAD' as Apache
        # will discard the final output anyway. Truncating
        # output here if req.method is 'HEAD' is likely the
        # wrong thing to do as it may cause problems for any
        # output filters. See MODPYTHON-105 for details. We
        # also do not flush output as that will prohibit use
        # of 'CONTENT_LENGTH' filter to add 'Content-Length'
        # header automatically. See MODPYTHON-107 for details.
        req.write(result, 0)

        return True
