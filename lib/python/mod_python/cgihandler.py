"""
 (C) Gregory Trubetskoy, 1998 <grisha@ispol.com>

 $Id: cgihandler.py,v 1.6 2000/10/29 01:29:06 gtrubetskoy Exp $

 This file is part of mod_python. See COPYRIGHT file for details.

"""

import apache
import imp
import os

# if threads are not available
# create a functionless lock object
try:
    import threading
    _lock = threading.Lock()
except (ImportError, AttributeError):
    class DummyLock:
        def acquire(self):
            pass
        def release(self):
            pass
    _lock = DummyLock()

# the next statement  deserves some explaining.
# it seems that the standard os.environ object looses
# memory if the environment is manipulated frequently. Since for
# CGI you have to rebuild it for every request, your httpd will
# grow rather fast. I am not exactly sure why it happens and if there
# is a more sensible remedy, but this seems to work OK.
os.environ = {}

# uncomment the 5 lines beginning ### to enable experimental reload feature
# remember all imported modules
###import sys
###original = sys.modules.keys()

def handler(req):

###    # if there are any new modules since the import of this module,
###    # delete them
###    for m in sys.modules.keys():
###        if m not in original:
###            del sys.modules[m]

    # get the filename of the script
    if req.subprocess_env.has_key("script_filename"):
        dir, file = os.path.split(req.subprocess_env["script_filename"])
    else:
        dir, file = os.path.split(req.filename)
    module_name, ext = os.path.splitext(file)

    _lock.acquire()
    try:

        try:

            # The CGI spec requires us to set current working
            # directory to that of the script. This is not
            # thread safe, this is why we must obtain the lock.
            cwd = os.getcwd()
            os.chdir(dir)

            # simulate cgi environment
            env, si, so = apache.setup_cgi(req)

            try:
                # we do not search the pythonpath (security reasons)
                fd, path, desc = imp.find_module(module_name, [dir])
            except ImportError:
                raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

            # this executes the module
            imp.load_module(module_name, fd, path, desc)

            return apache.OK

        finally:
            # unsimulate the cgi environment
            apache.restore_nocgi(env, si, so)
            try:
                fd.close()
            except: pass
            os.chdir(cwd)
    finally:
        _lock.release()

