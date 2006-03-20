 # vim: set sw=4 expandtab :
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
 # The code in this file originally donated by Graham Dumpleton.
 # 
 # $Id: cache.py 374268 2006-02-02 05:31:45Z nlehuen $

from mod_python import apache
from mod_python import publisher

import os
import sys
import new
import types
import pdb
import imp
import md5
import time
import string

try:
    import threading
except:
    import dummy_threading as threading


# Define a transient per request modules cache. This is
# not the same as the true global modules cache used by
# the module importer. Instead, the per request modules
# cache is where references to modules loaded in order
# to satisfy the requirements of a specific request are
# stored for the life of that request. Such a cache is
# required to ensure that two distinct bits of code that
# load the same module do in fact use the same instance
# of the module and that an update of the code for a
# module on disk doesn't cause the latter handler code
# to load its own separate instance. This is in part
# necessary because the module loader does not reload a
# module on top of the old module, but loads the new
# instance into a clean module.

_modules_cache = {}

def _cleanup_modules_cache(thread=None):
    thread = thread or threading.currentThread()
    _modules_cache.pop(thread, None)

def _setup_modules_cache(req=None, thread=None):
    thread = thread or threading.currentThread()
    if not _modules_cache.has_key(thread):
        _modules_cache[thread] = {}
        if req:
            req.register_cleanup(_cleanup_modules_cache, thread)

def _get_modules_cache(thread=None):
    thread = thread or threading.currentThread()
    return _modules_cache.get(thread, None)


# Define a transient per request config cache into which
# the currently active configuration and handler root
# directory pertaining to a request is stored. This is
# done so that it can be accessed directly from the
# module importer function to obtain configuration
# settings indicating if logging and module reloading is
# enabled and to determine where to look for modules.

_config_cache = {}

def _setup_config_cache(config, directory, thread=None):
    thread = thread or threading.currentThread()
    cache  = _config_cache.get(thread, (None, None))
    if config is not None:
        if directory:
            directory = os.path.normpath(directory)
        _config_cache[thread] = (config, directory)
    else:
        del _config_cache[thread]
    return cache

def get_config(thread=None):
    thread = thread or threading.currentThread()
    config, directory = _config_cache.get(thread,
            (apache.main_server.get_config(), None))
    return config

def get_directory(thread=None):
    thread = thread or threading.currentThread()
    config, directory = _config_cache.get(thread, (None, None))
    return directory


# Define an alternate implementation of the module
# importer system and substitute it for the standard one
# in the 'mod_python.apache' module.

apache.ximport_module = apache.import_module

def _parent_context():
    # Determine the enclosing module which has called
    # this function. From that module, return the info
    # stashed in it by the module importer system.

    try:
        raise Exception
    except:
        parent = sys.exc_info()[2].tb_frame.f_back
        while (parent and parent.f_globals.has_key('__file__') and
                parent.f_globals['__file__'] == __file__):
            parent = parent.f_back

    if parent and parent.f_globals.has_key('__info__'):
        return parent.f_globals['__info__']

def _find_module(module_name, path):

    # Search the specified path for a Python code module
    # of the specified name. Note that only Python code
    # files with a '.py' extension will be used. Python
    # packages will be ignored.

    for directory in path:
        file = os.path.join(directory, module_name) + '.py'
        if os.path.exists(file):
            return file

def import_module(module_name, autoreload=None, log=None, path=None):

    file = None
    import_path = []

    # Deal with explicit references to a code file.
    # Allow some shortcuts for referring to code file
    # relative to handler root or directory of parent
    # module. Those relative to parent module are not
    # allowed if parent module not imported using this
    # module importing system.

    if os.path.isabs(module_name):
        file = module_name

    elif module_name[:2] == '~/':
        directory = get_directory()
        if directory is not None:
            file = os.path.join(directory, module_name[2:])

    elif module_name[:2] == './':
        context = _parent_context()
        if context is not None:
            directory = os.path.dirname(context.file)
            file = os.path.join(directory, module_name[2:])

    elif module_name[:3] == '../':
        context = _parent_context()
        if context is not None:
            directory = os.path.dirname(context.file)
            file = os.path.join(directory, module_name)

    if file is None:
        # If not an explicit file reference, it is a
        # module name. Determine the list of directories
        # that need to be searched for a module code
        # file. These directories will be, the handler
        # root directory and any specified search path.
        # The handler root though is only checked if it
        # is known and the 'PythonPath' directive is not
        # specified. The latter check of 'PythonPath' is
        # made purely to ensure backward compatability
        # with old code where the handler root would
        # previously have been added automatically to
        # 'sys.path'. The danger is where users add the
        # handler root to 'PythonPath' explicitly. They
        # need to be educated not to do this with the
        # new module importing system as it is not
        # really necessary and will just continue to
        # cause possible problems if they do so.

        search_path = []

        if path is not None:
            search_path.extend(path)

        config = get_config()
        if config and not config.has_key('PythonPath'):
            directory = get_directory()
            if directory is not None:
                if path is None or directory not in path:
                    search_path.append(directory)

        # Attempt to find the code file for the module
        # if we have directories to actually search.

        if search_path:
            file = _find_module(module_name, search_path)

    else:

        # For module imported using explicit path, the
        # path argument becomes the special embedded
        # search path for 'import' statement executed
        # within that module.

        if path is not None:
            import_path = path

    # Was a Python code file able to be identified.

    if file is not None:

        # Use the module importing and caching system
        # to load the code from the specified file.

        return _moduleCache.import_module(file, autoreload, log, import_path)

    else:
        # If a module code file could not be found,
        # defer to the standard Python module importer.
        # We should always end up here if the request
        # was for a package.

        return __import__(module_name, {}, {}, ['*'])


apache.import_module = import_module


class _CacheInfo:

    def __init__(self, label, file, mtime):
        self.label = label
        self.file = file
        self.mtime = mtime
        self.module = None
        self.instance = 0
        self.generation = 0
        self.children = {}
        self.atime = 0
        self.direct = 0
        self.indirect = 0
        self.lock = threading.Lock()

class _InstanceInfo:

    def __init__(self, label, file, cache):
        self.label = label
        self.file = file
        self.cache = cache
        self.children = {}
        self.path = []

class _ModuleCache:

    _prefix = "_mp_"

    def __init__(self):
        self._cache = {}
        self._lock1 = threading.Lock()
        self._lock2 = threading.Lock()
        self._generation = 0
        self._frozen = False
        self._directories = {}

    def _log_notice(self, msg):
        pid = os.getpid()
        name = apache.interpreter
        server = apache.main_server
        flags = apache.APLOG_NOERRNO|apache.APLOG_NOTICE
        text = "mod_python (pid=%d,interpreter=%s): %s" % (pid, `name`, msg)
        apache.log_error(text, flags, server)

    def _log_warning(self, msg):
        pid = os.getpid()
        name = apache.interpreter
        server = apache.main_server
        flags = apache.APLOG_NOERRNO|apache.APLOG_WARNING
        text = "mod_python (pid=%d,interpreter=%s): %s" % (pid, `name`, msg)
        apache.log_error(text, flags, server)

    def cached_modules(self):
        self._lock1.acquire()
        try:
            return self._cache.keys()
        finally:
            self._lock1.release()

    def module_info(self, label):
        self._lock1.acquire()
        try:
            return self._cache[label]
        finally:
            self._lock1.release()

    def freeze_modules(self):
        self._frozen = True

    def check_directory(self, file):

        directory = os.path.dirname(file)

        if not directory in self._directories:
            self._directories[directory] = None
            if directory in sys.path:
                msg = 'Module directory listed in "sys.path". '
                msg = msg + 'This may cause problems. Please check code. '
                msg = msg + 'Code file being imported is "%s".' % file
                self._log_warning(msg)

    def import_module(self, file, autoreload=None, log=None, path=None):

        # Ensure that file name is normalised so all
        # lookups against the cache equate where they
        # are the same file. This isn't necessarily
        # going to work where symlinks are involved, but
        # not much else that can be done in that case.

        file = os.path.normpath(file)

        # Determine the default values for the module
        # autoreloading and logging arguments direct
        # from the Apache configuration rather than
        # having fixed defaults.

        if autoreload is None or log is None:

            config = get_config()

            if autoreload is None:
                autoreload = int(config.get("PythonAutoReload", 1))

            if log is None:
                log = int(config.get("PythonDebug", 0))

        # Warn of any instances where a code file is
        # imported from a directory which also appears
        # in 'sys.path'.

        if log:
            self.check_directory(file)

        # Retrieve the parent context. That is, the
        # details stashed into the parent module by the
        # module importing system itself.

        context = _parent_context()

        # Check for an attempt by the module to import
        # itself.

        if context:
            assert(file != context.file), "Import cycle in %s." % file

        # Retrieve the per request modules cache entry.

        modules = _get_modules_cache()

        # Calculate a unique label corresponding to the
        # name of the file which is the module. This
        # will be used as the '__name__' attribute of a
        # module and as key in various tables.

        label = self._module_label(file)

        # See if the requested module has already been
        # imported previously within the context of this
        # request or at least visited by way of prior
        # dependency checks where it was deemed that it
        # didn't need to be reloaded. If it has we can
        # skip any additional dependency checks and use
        # the module already identified. This ensures
        # the same actual module instance is used. This
        # check is also required so that we don't get
        # into cyclical import loops. Still need to at
        # least record the fact that the module is a
        # child of the parent.

        if modules:
            if modules.has_key(label):
                if context:
                    context.children[label] = time.time()
                return modules[label]

        # Now move on to trying to find the actual
        # module.

        try:
            cache = None

            # First determine if the module has been loaded
            # previously. If not already loaded or if a
            # dependency of the module has been changed on disk
            # or reloaded since parent was loaded, must load the
            # module.

            (cache, load) = self._reload_required(modules,
                    label, file, autoreload)

            # Make sure that the cache entry is locked by the
            # thread so that other threads in a multithreaded
            # system don't try and load the same module at the
            # same time.

            cache.lock.acquire()

            if load:

                # Setup a new empty module to load the code for
                # the module into.

                cache.instance = cache.instance + 1

                module = imp.new_module(label)

                # If the module was previously loaded we need to
                # manage the transition to the new instance of
                # the module that is being loaded to replace it.
                # This entails calling the special clone method,
                # if provided within the existing module. Using
                # this method the existing module can then
                # selectively indicate what should be transfered
                # over to the next instance of the module,
                # including thread locks. If this process fails
                # the special purge method is called, if
                # provided, to indicate that the existing module
                # is being forcibly purged out of the system. In
                # that case any existing state will not be
                # transferred.

                if cache.module != None:
                    if hasattr(cache.module, "__clone__"):
                        try:
                            # Migrate any existing state data from
                            # existing module instance to new module
                            # instance.

                            if log:
                                msg = "Cloning module '%s'" % file
                                self._log_notice(msg)

                            cache.module.__clone__(module)

                        except:
                            # Forcibly purging module from system.

                            if hasattr(cache.module, "__purge__"):
                                try:
                                    cache.module.__purge__()
                                except:
                                    pass

                            if log:
                                msg = "Purging module '%s'" % file
                                self._log_notice(msg)

                            cache.module = None

                            # Setup a fresh new module yet again.

                            module = imp.new_module(label)

                    if log:
                        if cache.module == None:
                            msg = "Importing module '%s'" % file
                            self._log_notice(msg)
                        else:
                            msg = "Reimporting module '%s'" % file
                            self._log_notice(msg)
                else:
                    if log:
                        msg = "Importing module '%s'" % file
                        self._log_notice(msg)

                # Must add to the module the path to the modules
                # file. This ensures that module looks like a
                # normal module and this path will also be used
                # in certain contexts when the import statement
                # is used within the module.

                module.__file__ = file

                # Setup a new instance object to store in the
                # module. This will refer back to the actual
                # cache entry and is used to record information
                # which is specific to this incarnation of the
                # module when reloading is occuring.

                instance = _InstanceInfo(label, file, cache)

                module.__info__ = instance

                # Cache any additional module search path which
                # should be used for this instance of the module
                # or package. The path shouldn't be able to be
                # changed during the lifetime of the module to
                # ensure that module imports are always done
                # against the same path.

                if path is None:
                    path = []

                instance.path = list(path)

                # Place a reference to the module within the
                # request specific cache of imported modules.
                # This makes module lookup more efficient when
                # the same module is imported more than once
                # within the context of a request. In the case
                # of a cyclical import, avoids a never ending
                # recursive loop.

                if modules:
                    modules[label] = module

                # Perform actual import of the module.

                try:
                    execfile(file, module.__dict__)

                except:

                    # Importation of the module has failed for
                    # some reason. If this is the very first
                    # import of the module, need to discard the
                    # cache entry entirely else a subsequent
                    # attempt to load the module will wrongly
                    # think it was successfully loaded already.
                    # If not a new import, need to ensure that
                    # module will be reloaded again in future.

                    if cache.module is None:
                        del self._cache[label]
                    else:
                        cache.mtime = 0

                    raise

                # If this is a child import of some parent
                # module, add this module as a child of the
                # parent.

                atime = time.time()

                if context:
                    context.children[label] = atime

                # Update the cache.

                cache.module = module

                # Need to also update the list of child modules
                # stored in the cache entry with the actual
                # children found during the import. A copy is
                # made, meaning that any future imports
                # performed within the context of the request
                # handler don't result in the module later being
                # reloaded if they change.

                cache.children = dict(module.__info__.children)

                # Increment the generation count of the global
                # state of all modules. This is used in the
                # dependency management scheme for reloading to
                # determine if a module dependency has been
                # reloaded since it was loaded.

                self._lock2.acquire()
                self._generation = self._generation + 1
                cache.generation = self._generation
                self._lock2.release()

                # Update access time and reset access counts.

                cache.atime = atime
                cache.direct = 1
                cache.indirect = 0

            else:

                # Update the cache.

                module = cache.module

                # Place a reference to the module within the
                # request specific cache of imported modules.
                # This makes module lookup more efficient when
                # the same module is imported more than once
                # within the context of a request. In the case
                # of a cyclical import, avoids a never ending
                # recursive loop.

                if modules:
                    modules[label] = module

                # If this is a child import of some parent
                # module, add this module as a child of the
                # parent.

                atime = time.time()

                if context:
                    context.children[label] = atime

                # Didn't need to reload the module so simply
                # increment access counts and last access time.

                cache.atime = atime
                cache.direct = cache.direct + 1

            return module

        finally:
            # Lock on cache object can now be released.

            if cache is not None:
                cache.lock.release()

    def _reload_required(self, modules, label, file, autoreload):

        # Make sure cache lock is always released.

        try:
            self._lock1.acquire()

            # Check if this is a new module.

            if not self._cache.has_key(label):
                mtime = os.path.getmtime(file)
                cache = _CacheInfo(label, file, mtime)
                self._cache[label] = cache
                return (cache, True)

            # Grab entry from cache.

            cache = self._cache[label]

            # Check if reloads have been disabled.

            if self._frozen or not autoreload:
                return (cache, False)

            # Check if module has been marked as dirty.

            if cache.mtime == 0:
                return (cache, True)

            # Has modification time changed.

            try:
                mtime = os.path.getmtime(file)
            except:

                # Must have been removed just then. We return
                # currently cached module and avoid a reload.
                # Defunct module would need to be purged later.

                return (cache, False)

            if mtime != cache.mtime:
                cache.mtime = mtime
                return (cache, True)

            # Check if children have changed in any way
            # that would require a reload.

            if cache.children:

                visited = {}
                ancestors = [label]

                for tag in cache.children:

                    # If the child isn't in the cache any longer
                    # for some reason, force a reload.

                    if not self._cache.has_key(tag):
                        return (cache, True)

                    child = self._cache[tag]

                    # Now check the actual child module.

                    if self._check_module(modules, cache, child,
                            visited, ancestors):
                        return (cache, True)

            # No need to reload the module. Module
            # should be cached in the request object by
            # the caller if required.

            return (cache, False)

        finally:
            self._lock1.release()

    def _check_module(self, modules, parent, current, visited, ancestors):

        # Update current modules access statistics.

        current.indirect = current.indirect + 1
        current.atime = time.time()

        # Check if current module has been marked as
        # dirty.

        if current.mtime == 0:
            return True

        # Check if current module has been reloaded
        # since the parent was last loaded.

        if current.generation > parent.generation:
            return True

        # If the current module has been visited
        # already, no need to continue further as it
        # should be up to date.

        if visited.has_key(current.label):
            return False

        # Check if current module has been modified on
        # disk since last loaded.

        try:

            mtime = os.path.getmtime(current.file)

            if mtime != current.mtime:
                return True

        except:
            # Current module must have been removed.
            # Don't cause this to force a reload though
            # as can cause problems. Rely on the parent
            # being modified to cause a reload.

            if modules:
                modules[current.label] = current.module

            return False

        # Check to see if all the children of the
        # current module need updating or are newer than
        # the current module.

        if current.children:

            ancestors = ancestors + [current.label]

            for label in current.children.keys():

                # Check for a child which refers to one of its
                # ancestors. Hopefully this will never occur. If
                # it does we will force a reload every time to
                # highlight there is a problem.

                if label in ancestors:
                    return True

                # If the child isn't in the cache any longer for
                # some reason, force a reload.

                if not self._cache.has_key(label):
                    return True

                child = self._cache[label]

                # Recurse back into this function to check
                # child.

                if self._check_module(modules, current, child,
                        visited, ancestors):
                    return True

        # No need to reload the current module. Now safe
        # to mark the current module as having been
        # visited and cache it into the request object
        # for quick later lookup if a parent needs to be
        # reloaded.

        visited[current.label] = current

        if modules:
            modules[current.label] = current.module

        return False

    def _module_label(self, file):

        # The label is used in the __name__ field of the
        # module and then used in determining child
        # module imports. Thus really needs to be
        # unique. We don't really want to use a module
        # name which is a filesystem path. Hope MD5 hex
        # digest is okay.

        stub = os.path.splitext(file)[0]
        label = md5.new(stub).hexdigest()
        label = self._prefix + label
        label = label + "_" + str(len(stub))
        return label


_moduleCache = _ModuleCache()

apache.freeze_modules = _moduleCache.freeze_modules

def ModuleCache():
    return _moduleCache


class _ModuleLoader:

    def __init__(self, file):
        self.__file = file

    def load_module(self, fullname):
        return _moduleCache.import_module(self.__file)

class _ModuleImporter:

    def find_module(self, fullname, path=None):

        # Return straight away if requested to import a
        # sub module of a package.

        if '.' in fullname:
            return None

        # Retrieve the parent context. That is, the
        # details stashed into the parent module by the
        # module importing system itself. Only consider
        # using the module importing system for 'import'
        # statement if parent module was imported using
        # the same.

        context = _parent_context()

        if context is None:
            return None

        # Determine the list of directories that need to
        # be searched for a module code file. These
        # directories will be, the handler root
        # directory, the directory of the parent and any
        # specified search path. The handler root though
        # is only checked if it is known and the
        # 'PythonPath' directive is not specified. The
        # latter check of 'PythonPath' is made purely to
        # ensure backward compatability with old code
        # where the handler root would previously have
        # been added automatically to 'sys.path'. The
        # danger is where users add the handler root to
        # 'PythonPath' explicitly. They need to be
        # educated not to do this with the new module
        # importing system as it is not really necessary
        # and will just continue to cause possible
        # problems if they do so.

        search_path = []

        local_directory = os.path.dirname(context.file)
        search_path.append(local_directory)

        if context.path is not None:
            search_path.extend(context.path)

        config = get_config()
        if config and not config.has_key('PythonPath'):
            root_directory = get_directory()
            if root_directory is not None:
                if root_directory != local_directory:
                    if (context.path is None or
                            root_directory not in context.path):
                        search_path.append(root_directory)

        # Return if we have no search path to search.

        if not search_path:
            return None

        # Attempt to find the code file for the module.

        file = _find_module(fullname, search_path)

        if file is not None:
            return _ModuleLoader(file)

        return None


sys.meta_path.insert(0, _ModuleImporter())



# Replace mod_python.publisher page cache object with a
# dummy object which uses new module importer.

class _PageCache:
    def __getitem__(self,req):
        return import_module(req.filename)

publisher.xpage_cache = publisher.page_cache
publisher.page_cache = _PageCache()


# Define alternate implementations of the top level
# mod_python entry points and substitute them for the
# standard one in the 'mod_python.apache' callback
# object.

_callback = apache._callback

_callback.xConnectionDispatch = _callback.ConnectionDispatch
_callback.xFilterDispatch = _callback.FilterDispatch
_callback.xHandlerDispatch = _callback.HandlerDispatch
_callback.xIncludeDispatch = _callback.IncludeDispatch
_callback.xImportDispatch = _callback.ImportDispatch

_result_warning = """Handler has returned result or raised SERVER_RETURN
exception with argument having non integer type. Type of value returned
was %s, whereas expected """ + str(types.IntType) + "."

_status_values = {
    "postreadrequesthandler":   [ apache.DECLINED, apache.OK ],
    "transhandler":             [ apache.DECLINED ],
    "maptostoragehandler":      [ apache.DECLINED ],
    "inithandler":              [ apache.DECLINED, apache.OK ],
    "headerparserhandler":      [ apache.DECLINED, apache.OK ],
    "accesshandler":            [ apache.DECLINED, apache.OK ],
    "authenhandler":            [ apache.DECLINED ],
    "authzhandler":             [ apache.DECLINED ],
    "typehandler":              [ apache.DECLINED ],
    "fixuphandler":             [ apache.DECLINED, apache.OK ],
    "loghandler":               [ apache.DECLINED, apache.OK ],
    "handler":                  [ apache.OK ],
}

def _execute_target(config, req, object, arg):

    try:
        # Only permit debugging using pdb if Apache has
        # actually been started in single process mode.

        pdb_debug = config.has_key("PythonEnablePdb")
        one_process = apache.exists_config_define("ONE_PROCESS")

        if pdb_debug and one_process:

            # Don't use pdb.runcall() as it results in
            # a bogus 'None' response when pdb session
            # is quit. With this code the exception
            # marking that the session has been quit is
            # propogated back up and it is obvious in
            # the error message what actually occurred.

            debugger = pdb.Pdb()
            debugger.reset()
            sys.settrace(debugger.trace_dispatch)

            try:
                result = object(arg)

            finally:
                debugger.quitting = 1
                sys.settrace(None)

        else:
            result = object(arg)

    except apache.SERVER_RETURN, value:
        # For a connection handler, there is no request
        # object so this form of response is invalid.
        # Thus exception is reraised to be handled later.

        if not req:
            raise

        # The SERVER_RETURN exception type when raised
        # otherwise indicates an abort from below with
        # value as (result, status) or (result, None) or
        # result.

        if len(value.args) == 2:
            (result, status) = value.args
            if status:
                req.status = status
        else:
            result = value.args[0]

    # Only check type of return value for connection
    # handlers and request phase handlers. The return
    # value of filters are ultimately ignored.

    if not req or req == arg:
        assert (type(result) == types.IntType), _result_warning % type(result)

    return result

def _process_target(config, req, directory, handler, default, arg, silent):

    # Determine module name and target object.

    parts = handler.split('::', 1)

    module_name = parts[0]

    if len(parts) == 1:
        object_str = default
    else:
        object_str = parts[1]

    # Update 'sys.path'. This will only be done if we
    # have not encountered the current value of the
    # 'PythonPath' config previously.

    if config.has_key("PythonPath"):

        apache._path_cache_lock.acquire()

        try:

            pathstring = config["PythonPath"]
            if not apache._path_cache.has_key(pathstring):
                newpath = eval(pathstring)
                apache._path_cache[pathstring] = None
                sys.path[:] = newpath

        finally:
            apache._path_cache_lock.release()

    # Import module containing target object. Specify
    # the handler root directory in the search path so
    # that it is still checked even if 'PythonPath' set.

    path = []

    if directory:
        path = [directory]

    module = import_module(module_name, path=path)

    # Lookup expected status values that allow us to
    # continue when multiple handlers exist.

    expected = _status_values.get(default, None)

    # Default to apache.DECLINED unless in content
    # handler phase.

    if not expected or apache.DECLINED not in expected:
        result = apache.OK
    else:
        result = apache.DECLINED

    # Obtain reference to actual target object.

    object = apache.resolve_object(module, object_str, arg, silent=silent)

    if object is not None or not silent:

        result = _execute_target(config, req, object, arg)

        # Stop iteration when target object returns a
        # value other than expected values for the phase.

        if expected and result not in expected:
            return (True, result)

    return (False, result)

def ConnectionDispatch(self, conn):
    """     
    This is the dispatcher for connection handlers.
    """     

    # Determine the default handler name.

    default_handler = "connectionhandler"

    # Be cautious and return server error as default.

    result = apache.HTTP_INTERNAL_SERVER_ERROR

    # Setup transient per request modules cache. Note
    # that this cache will always be thrown away when
    # connection handler returns as there is no way to
    # transfer ownership and responsibility for
    # discarding the cache entry to latter handlers.

    _setup_modules_cache()

    try:

        try:
            # Cache the server configuration for the
            # current request so that it will be
            # available from within 'import_module()'.

            config = conn.base_server.get_config()
            cache = _setup_config_cache(config, None)

            (aborted, result) = _process_target(config=config, req=None,
                    directory=None, handler=conn.hlist.handler,
                    default=default_handler, arg=conn, silent=0)

        finally:
            # Restore any previous cached configuration.
            # There should not actually be any, but this
            # will cause the configuration cache entry to
            # be discarded.

            _setup_config_cache(*cache)

            # Also discard the modules cache entry.

            _cleanup_modules_cache()

    except apache.PROG_TRACEBACK, traceblock:

        # Program runtime error flagged by the application.

        debug = int(config.get("PythonDebug", 0))

        try:
            (exc_type, exc_value, exc_traceback) = traceblock
            result = self.ReportError(exc_type, exc_value, exc_traceback,
                    srv=conn.base_server, phase="ConnectionHandler",
                    hname=conn.hlist.handler, debug=debug)

        finally:
            exc_traceback = None

    except:

        # Module loading error or some other runtime error.

        debug = int(config.get("PythonDebug", 0))

        try:    
            exc_type, exc_value, exc_traceback = sys.exc_info()
            result = self.ReportError(exc_type, exc_value, exc_traceback,
                    srv=conn.base_server, phase="ConnectionHandler",
                    hname=conn.hlist.handler, debug=debug)
        finally:
            exc_traceback = None

    return result

def FilterDispatch(self, filter):
    """     
    This is the dispatcher for input/output filters.
    """     

    # Determine the default handler name.

    if filter.is_input:
        default_handler = "inputfilter"
    else:
        default_handler = "outputfilter"

    # Setup transient per request modules cache. Note
    # that this will only actually do anything in this
    # case if no Python request phase handlers have been
    # specified. A cleanup handler is registered to
    # later discard the cache entry if it was created.

    _setup_modules_cache(filter.req)

    try:

        try:
            # Cache the server configuration for the
            # current request so that it will be
            # available from within 'import_module()'.

            config = filter.req.get_config()
            cache = _setup_config_cache(config, filter.dir)

            (aborted, result) = _process_target(config=config,
                    req=filter.req, directory=filter.dir,
                    handler=filter.handler, default=default_handler,
                    arg=filter, silent=0)

            if not filter.closed:
                filter.flush()

        finally:
            # Restore any previous cached configuration.

            _setup_config_cache(*cache)

    except apache.PROG_TRACEBACK, traceblock:

        # Program runtime error flagged by the application.

        debug = int(config.get("PythonDebug", 0))

        filter.disable()

        try:
            (exc_type, exc_value, exc_traceback) = traceblock
            result = self.ReportError(exc_type, exc_value,
                    exc_traceback, req=filter.req, filter=filter,
                    phase="Filter (%s)"%filter.name,
                    hname=filter.handler, debug=debug)

        finally:
            exc_traceback = None

    except:

        # Module loading error or some other runtime error.

        debug = int(config.get("PythonDebug", 0))

        filter.disable()

        try:    
            exc_type, exc_value, exc_traceback = sys.exc_info()
            result = self.ReportError(exc_type, exc_value,
                    exc_traceback, req=filter.req, filter=filter,
                    phase="Filter: " + filter.name,
                    hname=filter.handler, debug=debug)
        finally:
            exc_traceback = None

    return apache.OK

def HandlerDispatch(self, req):
    """     
    This is the dispatcher for handler phases.
    """     

    # Cache name of phase in case something changes it.

    phase = req.phase

    # Determine the default handler name.

    default_handler = phase[len("python"):].lower()

    # Be cautious and return server error as default.

    result = apache.HTTP_INTERNAL_SERVER_ERROR

    # Setup transient per request modules cache. Note
    # that this will only do something if this is the
    # first Python request handler phase to be executed.
    # A cleanup handler is registered to later discard
    # the cache entry if it needed to be created.

    _setup_modules_cache(req)

    # Cache configuration for later.

    config = req.get_config()

    try:
        # Iterate over the handlers defined for the
        # current phase and execute each in turn
        # until the last is reached or prematurely
        # aborted.

        (aborted, hlist) = False, req.hlist

        while not aborted and hlist.handler is not None:

            try:
                # Cache the server configuration for the
                # current request so that it will be
                # available from within 'import_module()'.

                directory = hlist.directory

                cache = _setup_config_cache(config, directory)

                (aborted, result) = _process_target(config=config, req=req,
                        directory=directory, handler=hlist.handler,
                        default=default_handler, arg=req, silent=hlist.silent)

            finally:
                # Restore any previous cached configuration.

                _setup_config_cache(*cache)

            hlist.next()

    except apache.PROG_TRACEBACK, traceblock:

        # Program runtime error flagged by the application.

        debug = int(config.get("PythonDebug", 0))

        try:
            (exc_type, exc_value, exc_traceback) = traceblock
            result = self.ReportError(exc_type, exc_value,
                    exc_traceback, req=req, phase=phase,
                    hname=hlist.handler, debug=debug)
        finally:
            exc_traceback = None

    except:

        # Module loading error or some other runtime error.

        debug = int(config.get("PythonDebug", 0))

        try:    
            exc_type, exc_value, exc_traceback = sys.exc_info()
            result = self.ReportError(exc_type, exc_value,
                    exc_traceback, req=req, phase=phase,
                    hname=hlist.handler, debug=debug)
        finally:
            exc_traceback = None

    return result

_callback.ConnectionDispatch = new.instancemethod(
        ConnectionDispatch, _callback, apache.CallBack)
_callback.FilterDispatch = new.instancemethod(
        FilterDispatch, _callback, apache.CallBack)
_callback.HandlerDispatch = new.instancemethod(
        HandlerDispatch, _callback, apache.CallBack)

def IncludeDispatch(self, filter, tag, code):

    # Setup transient per request modules cache. Note
    # that this will only actually do anything in this
    # case if no Python request phase handlers have been
    # specified. A cleanup handler is registered to
    # later discard the cache entry if it was created.

    _setup_modules_cache(filter.req)

    try:

        try:
            # Cache the server configuration for the
            # current request so that it will be
            # available from within 'import_module()'.

            config = filter.req.get_config()
            cache = _setup_config_cache(config, None)

            debug = int(config.get("PythonDebug", 0))

            if not hasattr(filter.req,"ssi_globals"):
                filter.req.ssi_globals = {}

            filter.req.ssi_globals["filter"] = filter

            code = code.rstrip()

            if tag == 'eval':
                result = eval(code, filter.req.ssi_globals)
                if result is not None:
                    filter.write(str(result))
            elif tag == 'exec':
                exec(code, filter.req.ssi_globals)

            filter.flush()

        finally:

            filter.req.ssi_globals["filter"] = None

            # Restore any previous cached configuration.

            _setup_config_cache(*cache)

    except:
        try:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            filter.disable()
            result = self.ReportError(exc_type, exc_value, exc_traceback,
                                      req=filter.req, filter=filter,
                                      phase=filter.name,
                                      hname=filter.req.filename,
                                      debug=debug)
        finally:
            exc_traceback = None

        raise

    return apache.OK

_callback.IncludeDispatch = new.instancemethod(
        IncludeDispatch, _callback, apache.CallBack)

def ImportDispatch(self, name):

    config = apache.main_server.get_config()

    debug = int(config.get("PythonDebug", "0"))

    # evaluate pythonpath and set sys.path to
    # resulting value if not already done

    if config.has_key("PythonPath"): 
        apache._path_cache_lock.acquire() 
        try: 
            pathstring = config["PythonPath"] 
            if not apache._path_cache.has_key(pathstring): 
                newpath = eval(pathstring) 
                apache._path_cache[pathstring] = None 
                sys.path[:] = newpath 
        finally: 
            apache._path_cache_lock.release()

    # split module::function
    l = name.split('::', 1)
    module_name = l[0]
    func_name = None
    if len(l) != 1:
        func_name = l[1]

    try:
        # Setup transient per request modules cache.
        # Note that this cache will always be thrown
        # away when the module has been imported.

        _setup_modules_cache()

        # Import the module.

        module = import_module(module_name, log=debug)

        # Optionally call function within module.

        if func_name:
            getattr(module, func_name)()

    finally:

        # Discard the modules cache entry.

        _cleanup_modules_cache()

_callback.ImportDispatch = new.instancemethod(
        ImportDispatch, _callback, apache.CallBack)
