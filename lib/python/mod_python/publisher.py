"""
  Copyright (c) 2000 Gregory Trubetskoy.  All rights reserved.
 
  This file is part of mod_python. See COPYRIGHT file for details.

  $Id: publisher.py,v 1.1 2000/11/12 05:01:22 gtrubetskoy Exp $

  This handler is conceputally similar to Zope's ZPublisher, except
  that it:

  1. Is written specifically for mod_python and is therefore much faster
  2. Does not require objects to have a documentation string
  3. Passes all arguments as simply string
  4. Does not try to match Python errors to HTTP errors

"""

import apache
import util

import os
import string
import imp
import re

# list of suffixes - .py, .pyc, etc.
suffixes = map(lambda x: x[0], imp.get_suffixes())

# now compile a regular expression out of it:
exp = "\\" + string.join(suffixes, "$|\\")
suff_matcher = re.compile(exp)

def handler(req):

    _req = req._req

    args = {}

    fs = util.FieldStorage(req)

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
        if len(arg) == 1:
            args[arg] = arg[0]

    # add req
    args["req"] = req

    # import the script
    path, module_name =  os.path.split(_req.filename)

    # get rid of the suffix
    module_name = suff_matcher.sub("", module_name)

    # import module (or reload if needed)
    module = apache.import_module(module_name, _req, [path])
    
    # now get the path PATH_INFO (everthing after script)
    # and begin traversal
    if not _req.subprocess_env.has_key("PATH_INFO"):
        raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
    
    func_path = _req.subprocess_env["PATH_INFO"][1:] # skip fist /
    func_path = string.replace(func_path, "/", ".")

    # if any part of the path begins with "_", abort
    if func_path[0] == '_' or string.count(func_path, "._"):
        raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

    # resolve the object ('traverse')
    object = apache.resolve_object(module, func_path, silent=0)

    # callable?
    if callable(object):
        # call it!
        result = apply(object, (), args)
    else:
        result = object
    
    req.send_http_header()

    req.write(str(result))

    return apache.OK

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
    
