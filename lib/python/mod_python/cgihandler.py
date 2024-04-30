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

from . import apache
import os
import sys
PY2 = sys.version[0] == '2'

if PY2 or sys.hexversion < 0x03120000:
    import imp
else:
    import importlib.util

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

original = list(sys.modules.keys())

# find out the standard library location
stdlib, x = os.path.split(os.__file__)

def handler(req):

    ### if you don't need indirect modules reloaded, comment out
    ### code unitl ### end

    # if there are any new modules since the import of this module,
    # delete them.
    for m in list(sys.modules.keys()):
        if m not in original:
            # unless they are part of standard library
            mod = sys.modules[m]
            if hasattr(mod, "__file__"):
                path, x = os.path.split(mod.__file__)
                if path != stdlib:
                    del sys.modules[m]
    ### end

    # get the filename of the script
    if "script_filename" in req.subprocess_env:
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

            scriptPath = os.path.join(dir, file)

            if not os.path.exists(scriptPath):
                raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

            # avoid loading modules outside dir
            # (e.g. shenanigans like ../../../../etc/passwd)
            scriptPath = os.path.abspath(scriptPath)
            if not scriptPath.startswith(dir):
                raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

            if PY2 or sys.hexversion < 0x03120000:

                try:
                    # we do not search the pythonpath (security reasons)
                    fd, path, desc = imp.find_module(module_name, [dir])
                except ImportError:
                    raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

                # this executes the module
                imp.load_module(module_name, fd, path, desc)

            else:

                try:
                    # we do not search the pythonpath (security reasons)
                    spec = importlib.util.spec_from_file_location(module_name, scriptPath)
                except (ModuleNotFoundError, ValueError):
                    raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

                if spec is None:
                    raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            return apache.OK

        finally:
            # unsimulate the cgi environment
            apache.restore_nocgi(env, si, so)
            if PY2:
                try:
                    fd.close()
                except: pass
            os.chdir(cwd)

    finally:
        _lock.release()
