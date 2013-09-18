
.. _pythonapi:

**********
Python API
**********

.. _pyapi-interps:

Multiple Interpreters
=====================

When working with mod_python, it is important to be aware of a feature
of Python that is normally not used when using the language for
writing scripts to be run from command line. (In fact, this feature is not
available from within Python itself and can only be accessed through
the `C language API <http://www.python.org/doc/current/api/api.html>`_.)
Python C API provides the ability to create :dfn:`subinterpreters`. A
more detailed description of a subinterpreter is given in the
documentation for the
`Py_NewInterpreter() <http://www.python.org/doc/current/api/initialization.html>`_
function. For this discussion, it will suffice to say that each
subinterpreter has its own separate namespace, not accessible from
other subinterpreters. Subinterpreters are very useful to make sure
that separate programs running under the same Apache server do not
interfere with one another.

.. index::
   single: main_interpreter

At server start-up or mod_python initialization time, mod_python
initializes the *main interpeter*. The main interpreter contains a
dictionary of subinterpreters. Initially, this dictionary is
empty. With every request, as needed, subinterpreters are created, and
references to them are stored in this dictionary. The dictionary is
keyed on a string, also known as *interpreter name*.  This name can be
any string.  The main interpreter is named ``'main_interpreter'``.
The way all other interpreters are named can be controlled by
``PythonInterp*`` directives. Default behaviour is to name
interpreters using the Apache virtual server name (``ServerName``
directive). This means that all scripts in the same virtual server
execute in the same subinterpreter, but scripts in different virtual
servers execute in different subinterpreters with completely separate
namespaces.  :ref:`dir-other-ipd` and :ref:`dir-other-ipdv` directives
alter the naming convention to use the absolute path of the directory
being accessed, or the directory in which the ``Python*Handler`` was
encountered, respectively.  :ref:`dir-other-pi` can be used to force
the interpreter name to a specific string overriding any naming
conventions.

Once created, a subinterpreter will be reused for subsequent requests.
It is never destroyed and exists until the Apache process ends.

You can find out the name of the interpreter under which you're
running by peeking at :attr:`request.interpreter`.

.. note::

  If any module is being used which has a C code component that uses
  the simplified API for access to the Global Interpreter Lock (GIL)
  for Python extension modules, then the interpreter name must be
  forcibly set to be ``'main_interpreter'``. This is necessary as such
  a module will only work correctly if run within the context of the
  first Python interpreter created by the process. If not forced to
  run under the ``'main_interpreter'``, a range of Python errors can
  arise, each typically referring to code being run in *restricted
  mode*.

.. seealso::

  `<http://www.python.org/doc/current/api/api.html>`_
     Python C Language API
  `<http://www.python.org/peps/pep-0311.html>`_
     PEP 0311 - Simplified Global Interpreter Lock Acquisition for Extensions

.. _pyapi-handler:

Overview of a Request Handler
=============================

.. index::
   pair: request; handler

A :dfn:`handler` is a function that processes a particular phase of a
request. Apache processes requests in phases - read the request,
process headers, provide content, etc. For every phase, it will call
handlers, provided by either the Apache core or one of its modules,
such as mod_python which passes control to functions provided by the
user and written in Python. A handler written in Python is not any
different from a handler written in C, and follows these rules:

.. index::
   single: req
   pair: request; object

A handler function will always be passed a reference to a request
object. (Throughout this manual, the request object is often referred
to by the ``req`` variable.)

Every handler can return:

* :const:`apache.OK`, meaning this phase of the request was handled by this 
  handler and no errors occurred. 

* :const:`apache.DECLINED`, meaning this handler has not handled this
  phase of the request to completion and Apache needs to look for
  another handler in subsequent modules.
  
* :const:`apache.HTTP_ERROR`, meaning an HTTP error occurred. 
  *HTTP_ERROR* can be any of the following::

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

As an alternative to *returning* an HTTP error code, handlers can
signal an error by *raising* the :const:`apache.SERVER_RETURN`
exception, and providing an HTTP error code as the exception value,
e.g.::

   raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

Handlers can send content to the client using the :meth:`request.write()`
method. 

Client data, such as POST requests, can be read by using the
:meth:`request.read()` function.

.. note::

   The directory of the Apache ``Python*Handler``
   directive in effect is prepended to the \code{sys.path}. If the
   directive was specified in a server config file outside any
   ``<Directory>``, then the directory is unknown and not prepended.

An example of a minimalistic handler might be::

   from mod_python import apache

   def requesthandler(req):
       req.content_type = "text/plain"
       req.write("Hello World!")
       return apache.OK

.. _pyapi-filter:

Overview of a Filter Handler
============================

.. index::
   pair: filter; handler

A :dfn:`filter handler` is a function that can alter the input or the
output of the server. There are two kinds of filters - :dfn:`input` and
:dfn:`output` that apply to input from the client and output to the
client respectively.

At this time mod_python supports only request-level filters, meaning
that only the body of HTTP request or response can be filtered. Apache
provides support for connection-level filters, which will be supported
in the future.

A filter handler receives a *filter* object as its argument. The
request object is available as well via ``filter.req``, but all
writing and reading should be done via the filter's object read and
write methods.

Filters need to be closed when a read operation returns None 
(indicating End-Of-Stream).

The return value of a filter is ignored. Filters cannot decline
processing like handlers, but the same effect can be achieved
by using the :meth:`filter.pass_on()` method.

Filters must first be registered using ``PythonInputFilter`` or
``PythonOutputFilter``, then added using the Apache
``Add/SetInputFilter`` or ``Add/SetOutputFilter`` directives. 

Here is an example of how to specify an output filter, it tells the
server that all .py files should processed by CAPITALIZE filter::

   PythonOutputFilter capitalize CAPITALIZE
   AddOutputFilter CAPITALIZE .py

And here is what the code for the :file:`capitalize.py` might look
like::

   from mod_python import apache
  
   def outputfilter(filter):

       s = filter.read()
       while s:
           filter.write(s.upper())
           s = filter.read()

       if s is None:
           filter.close()

When writing filters, keep in mind that a filter will be called any
time anything upstream requests an IO operation, and the filter has no
control over the amount of data passed through it and no notion of
where in the request processing it is called. For example, within a
single request, a filter may be called once or five times, and there
is no way for the filter to know beforehand that the request is over
and which of calls is last or first for this request, thought
encounter of an EOS (None returned from a read operation) is a fairly
strong indication of an end of a request.

Also note that filters may end up being called recursively in
subrequests. To avoid the data being altered more than once, always
make sure you are not in a subrequest by examining the :attr:`request.main`
value.

For more information on filters, see `<http://httpd.apache.org/docs-2.4/developer/filters.html>`_.

.. _pyapi-conn:

Overview of a Connection Handler
================================

.. index::
   pair: connection; handler

A :dfn:`connection handler` handles the connection, starting almost
immediately from the point the TCP connection to the server was
made. 

Unlike HTTP handlers, connection handlers receive a *connection*
object as an argument.

Connection handlers can be used to implement protocols. Here is an
example of a simple echo server:

Apache configuration::

   PythonConnectionHandler echo

Contents of :file:`echo.py` file::

   from mod_python import apache

   def connectionhandler(conn):

       while 1:
           conn.write(conn.readline())

       return apache.OK

:mod:`apache` -- Access to Apache Internals.
===============================================

.. module:: apache
   :synopsis: Access to Apache Internals.
.. moduleauthor:: Gregory Trubetskoy grisha@modpython.org

The Python interface to Apache internals is contained in a module
appropriately named :mod:`apache`, located inside the
:mod:`mod_python` package. This module provides some important
objects that map to Apache internal structures, as well as some useful
functions, all documented below. (The request object also provides an
interface to Apache internals, it is covered in its own section of
this manual.)

.. index::
   pair: _apache; module

The :mod:`apache` module can only be imported by a script running
under mod_python. This is because it depends on a built-in module
:mod:`_apache` provided by mod_python.

It is best imported like this::

   from mod_python import apache

:mod:`mod_python.apache` module defines the following functions and
objects. For a more in-depth look at Apache internals, see the
`Apache Developer Page <http://httpd.apache.org/dev/>`_

.. _pyapi-apmeth:

Functions
---------

.. function:: log_error(message[, level[, server]])

   An interface to the Apache ``ap_log_error()``
   function. *message* is a string with the error message,
   *level* is one of the following flags constants::

      APLOG_EMERG
      APLOG_ALERT
      APLOG_CRIT
      APLOG_ERR
      APLOG_WARNING
      APLOG_NOTICE
      APLOG_INFO
      APLOG_DEBUG
      APLOG_NOERRNO // DEPRECATED
  
  *server* is a reference to a :meth:`request.server` object. If
  *server* is not specified, then the error will be logged to the
  default error log, otherwise it will be written to the error log for
  the appropriate virtual server. When *server* is not specified,
  the setting of LogLevel does not apply, the LogLevel is dictated by
  an httpd compile-time default, usually ``warn``.

  If you have a reference to a request object available, consider using
  :meth:`request.log_error` instead, it will prepend request-specific
  information such as the source IP of the request to the log entry.

.. function:: import_module(module_name[, autoreload=1, log=0, path=None])

   ZZZ This needs thorough review

   This function can be used to import modules taking advantage of
   mod_python's internal mechanism which reloads modules automatically
   if they have changed since last import.

   *module_name* is a string containing the module name (it can
   contain dots, e.g. ``mypackage.mymodule``); *autoreload* indicates
   whether the module should be reloaded if it has changed since last
   import; when *log* is true, a message will be written to the
   logs when a module is reloaded; *path* allows restricting
   modules to specific paths.

   Example::

      from mod_python import apache
      module = apache.import_module('module_name')

   The ``apache.import_module()`` function is not just a wrapper for
   the standard Python module import mechanism. The purpose of the
   function and the mod_python module importer in general, is to
   provide a means of being able to import modules based on their
   exact location, with modules being distinguished based on their
   location rather than just the name of the module. Distinguishing
   modules in this way, rather than by name alone, means that the same
   module name can be used for handlers and other code in multiple
   directories and they will not interfere with each other.

   A secondary feature of the module importer is to implement a means
   of having modules automatically reloaded when the corresponding
   code file has been changed on disk. Having modules be able to be
   reloaded in this way means that it is possible to change the code
   for a web application without having to restart the whole Apache
   web server. Although this was always the intent of the module
   importer, prior to mod_python 3.3, its effectiveness was
   limited. With mod_python 3.3 however, the module reloading feature
   is much more robust and will correctly reload parent modules even
   when it was only a child module what was changed.

   When the ``apache.import_module()`` function is called with just
   the name of the module, as opposed to a path to the actual code
   file for the module, a search has to be made for the module. The
   first set of directories that will be checked are those specified
   by the *path* argument if supplied.
  
    Where the function is called from another module which had
    previously been imported by the mod_python importer, the next
    directory which will be checked will be the same directory as the
    parent module is located.  Where that same parent module contains
    a global data variable called ``__mp_path__`` containing a list
    of directories, those directories will also be searched.

   Finally, the mod_python module importer will search directories
   specified by the ``PythonOption`` called
   ``mod_python.importer.path``.

   For example::

      PythonOption mod_python.importer.path "['/some/path']"


   The argument to the option must be in the form of a Python
   list. The enclosing quotes are to ensure that Apache interprets the
   argument as a single value. The list must be self contained and
   cannot reference any prior value of the option. The list MUST NOT
   reference ``sys.path`` nor should any directory which also
   appears in ``sys.path`` be listed in the mod_python module
   importer search path.

   When searching for the module, a check is made for any code file
   with the name specified and having a '.py' extension. Because only
   modules implemented as a single file will be found, packages will
   not be found nor modules contained within a package.

   In any case where a module cannot be found, control is handed off
   to the standard Python module importer which will attempt to find
   the module or package by searching ``sys.path``.

   Note that only modules found by the mod_python module importer are
   candidates for automatic module reloading. That is, where the
   mod_python module importer could not find a module and handed the
   search off to the standard Python module importer, those modules or
   packages will not be able to be reloaded.

   Although true Python packages are not candidates for reloading and
   must be located in a directory listed in ``sys.path``, another
   form of packaging up modules such that they can be maintained
   within their own namespace is supported. When this mechanism is
   used, these modules will be candidates for reloading when found by
   the mod_python module importer.

   In this scheme for maintaining a pseudo package, individual modules
   are still placed into a directory, but the ``__init__.py`` file
   in the directory has no special meaning and will not be
   automatically imported as is the case with true Python
   packages. Instead, any module within the directory must always be
   explicitly identified when performing an import.
  
   To import a named module contained within these pseudo packages,
   rather than using a '.' to distinguish a sub module from the
   parent, a '/' is used instead. For example::

      from mod_python import apache
      module = apache.import_module('dirname/module_name')

   If an ``__init__.py`` file is present and it was necessary to
   import it to achieve the same result as importing the root of a
   true Python package, then ``__init__`` can be used as the module
   name.  For example::

      from mod_python import apache
      module = apache.import_module('dirname/__init__')
 
   As a true Python package is not being used, if a module in the
   directory needs to refer to another module in the same directory,
   it should use just its name, it should not use any form of dotted
   path name via the root of the package as would be the case for true
   Python packages.  Modules in subdirectories can be imported by
   using a '/' separated path where the first part of the path is the
   name of the subdirectory.

   As a new feature in mod_python 3.3, when using the standard Python
   'import' statement to import a module, if the import is being done
   from a module which was previously imported by the mod_python
   module importer, it is equivalent to having called
   ``apache.import_module()`` directly.

   For example::

      import name

   is equivalent to::

      from mod_python import apache
      name = apache.import_module('name')

   It is also possible to use constructs such as::

      import name as module

   and::

     from name import value

   Although the 'import' statement is used, that it maps through to
   the ``apache.import_module()`` function ensures that
   parent/child relationships are maintained correctly and reloading
   of a parent will still work when only the child has been
   changed. It also ensures that one will not end up with modules
   which were separately imported by the mod_python module importer
   and the standard Python module importer.

   With the reimplementation of the module importer in mod_python 3.3,
   the *module_name* argument may also now be an absolute path
   name of an actual Python module contained in a single file. On
   Windows, a drive letter can be supplied if necessary. For example::

      from mod_python import apache
      name = apache.import_module('/some/path/name.py')

   or::

      from mod_python import apache
      import os
      here = os.path.dirname(__file__)
      path = os.path.join(here, 'module.py')
      module = apache.import_module(path)

   Where the file has an extension, that extension must be
   supplied. Although it is recommended that code files still make use
   of the '.py' extension, it is not actually a requirement and an
   alternate extension can be used.  For example::

      from mod_python import apache
      import os
      here = os.path.dirname(__file__)
      path = os.path.join(here, 'servlet.mps')
      servlet = apache.import_module(path)

   To avoid the need to use hard coded absolute path names to modules,
   a few shortcuts are provided. The first of these allow for the use
   of relative path names with respect to the directory the module
   performing the import is located within.

   For example::

      from mod_python import apache

       parent = apache.import_module('../module.py')
       subdir = apache.import_module('./subdir/module.py')

   Forward slashes must always be used for the prefixes './' and
   '../', even on Windows hosts where native pathname use a
   backslash. This convention of using forward slashes is used as that
   is what Apache normalizes all paths to internally. If you are using
   Windows and have been using backward slashes with ``Directory``
   directives etc, you are using Apache contrary to what is the
   accepted norm.

   A further shortcut allows paths to be declared relative to what is
   regarded as the handler root directory. The handler root directory
   is the directory context in which the active ``Python*Handler``
   directive was specified. If the directive was specified within a
   ``Location`` or ``VirtualHost`` directive, or at global server
   scope, the handler root will be the relevant document root for the
   server.
  
   To express paths relative to the handler root, the '~' prefix
   should be used. A forward slash must again always be used, even on
   Windows.

   For example::

      from mod_python import apache

      parent = apache.import_module('~/../module.py')
      subdir = apache.import_module('~/subdir/module.py')

   In all cases where a path to the actual code file for a module is
   given, the *path* argument is redundant as there is no need to
   search through a list of directories to find the module. In these
   situations, the *path* is instead taken to be a list of directories
   to use as the initial value of the ``__mp_path__`` variable
   contained in the imported modules instead of an empty path.

   This feature can be used to attach a more restrictive search path
   to a set of modules rather than using the ``PythonOption`` to set a
   global search path. To do this, the modules should always be
   imported through a specific parent module. That module should then
   always import submodules using paths and supply ``__mp_path__`` as
   the *path* argument to subsequent calls to
   ``apache.import_module()`` within that module. For example::

      from mod_python import apache

      module1 = apache.import_module('./module1.py', path=__mp_path__)
      module2 = apache.import_module('./module2.py', path=__mp_path__)

   with the module being imported as::

      from mod_python import apache

      parent = apache.import_module('~/modules/parent.py', path=['/some/path'])

   The parent module may if required extend the value of
   ``__mp_path__`` prior to using it. Any such directories will be
   added to those inherited via the *path* argument. For example::

      from mod_python import apache
      import os

      here = os.path.dirname(__file__)
      subdir = os.path.join(here, 'subdir')
      __mp_path__.append(subdir)

      module1 = apache.import_module('./module1.py', path=__mp_path__)
      module2 = apache.import_module('./module2.py', path=__mp_path__)

   In all cases where a search path is being specified which is
   specific to the mod_python module importer, whether it be specified
   using the ``PythonOption`` called ``mod_python.importer.path``,
   using the *path* argument to the ``apache.import_module()``
   function or in the ``__mp_path__`` attribute, the prefix '~' can be
   used in a path and that path will be taken as being relative to
   handler root. For example::

      PythonOption mod_python.importer.path "['~/modules']"

   If wishing to refer to the handler root directory itself, then '~'
   can be used and the trailing slash left off. For example::

      PythonOption mod_python.importer.path "['~']"

   Note that with the new module importer, as directories associated
   with ``Python*Handler`` directives are no longer being added
   automatically to ``sys.path`` and they are instead used directly by
   the module importer only when required, some existing code which
   expected to be able to import modules in the handler root directory
   from a module in a subdirectory may no longer work. In these
   situations it will be necessary to set the mod_python module
   importer path to include '~' or list '~' in the
   `__mp_path__` attribute of the module performing the import.

   This trick of listing '~' in the module importer path
   will not however help in the case where Python packages were
   previously being placed into the handler root directory. In this
   case, the Python package should either be moved out of the document
   tree and the directory where it is located listed against the
   `PythonPath` directive, or the package converted into the
   pseudo packages that mod_python supports and change the module
   imports used to access the package.

   Only modules which could be imported by the mod_python module
   importer will be candidates for automatic reloading when changes
   are made to the code file on disk. Any modules or packages which
   were located in a directory listed in `sys.path` and which
   were imported using the standard Python module importer will not be
   candidates for reloading.

   Even where modules are candidates for module reloading, unless a
   true value was explicitly supplied as the *autoreload* option
   to the ``apache.import_module()`` function they will only be
   reloaded if the ``PythonAutoReload`` directive is ``On``. The
   default value when the directive is not specified will be
   ``On``, so the directive need only be used when wishing to set
   it to ``Off`` to disable automatic reloading, such as in a
   production system.

   Where possible, the ``PythonAutoReload`` directive should only be
   specified in one place and in the root context for a specific
   Python interpreter instance. If the ``PythonAutoReload`` directive
   is used in multiple places with different values, or doesn't cover
   all directories pertaining to a specific Python interpreter
   instance, then problems can result. This is because requests
   against some URLs may result in modules being reloaded whereas
   others may not, even when through each URL the same module may be
   imported from a common location.

   If absolute certainty is required that module reloading is disabled
   and that it isn't being enabled through some subset of URLs, the
   ``PythonImport`` directive should be used to import a special
   module whenever an Apache child process is being created. This
   module should include a call to the ``apache.freeze_modules()``
   function. This will have the effect of permanently disabling module
   reloading for the complete life of that Apache child process,
   irrespective of what value the ``PythonAutoReload`` directive is
   set to.

   Using the new ability within mod_python 3.3 to have
   ``PythonImport`` call a specific function within a module after
   it has been imported, one could actually dispense with creating a
   module and instead call the function directory out of the
   ``mod_python.apache`` module.  For example::

      PythonImport mod_python.apache::freeze_modules interpreter_name

   Where module reloading is being undertaken, unlike the core module
   importer in versions of mod_python prior to 3.3, they are not
   reloaded on top of existing modules, but into a completely new
   module instance. This means that any code that previously relied on
   state information or data caches to be preserved across reloads
   will no longer work.

   If it is necessary to transfer such information from an old module
   to the new module, it is necessary to provide a hook function
   within modules to transfer across the data that must be
   preserved. The name of this hook function is
   ``__mp_clone__()``. The argument given to the hook function will
   be an empty module into which the new module will subsequently be
   loaded.

   When called, the hook function should copy any data from the old
   module to the new module. In doing this, the code performing the
   copying should be cognizant of the fact that within a multithreaded
   Apache MPM that other request handlers could still be trying to
   access and update the data to be copied. As such, the hook function
   should ensure that it uses any thread locking mechanisms within the
   module as appropriate when copying the data. Further, it should
   copy the actual data locks themselves across to the new module to
   ensure a clean transition.
  
   Because copying integral values will result in the data then being
   separate, it may be necessary to always store data within a
   dictionary so as to provide a level of indirection which will allow
   the data to be usable from both module instances while they still
   exist.

   For example::

      import threading, time

     if not globals().has_key('_lock'):
       # Initial import of this module.
       _lock = threading.Lock()
       _data1 = { 'value1' : 0, 'value2': 0 }
       _data2 = {}

     def __mp_clone__(module):
       _lock.acquire()
       module._lock = _lock
       module._data1 = _data1
       module._data2 = _data2
       _lock.release()

   Because the old module is about to be discarded, the data which is
   transferred should not consist of data objects which are dependent
   on code within the old module. Data being copied across to the new
   module should consist of standard Python data types, or be
   instances of classes contained within modules which themselves are
   not candidates for reloading. Otherwise, data should be migrated by
   transforming it into some neutral intermediate state, with the new
   module transforming it back when its code executes at the time of
   being imported.

   If these guidelines aren't heeded and data is dependent on code
   objects within the old module, it will prevent those code objects
   from being unloaded and if this continues across multiple reloads,
   then process size may increase over time due to old code objects
   being retained.

   In any case, if for some reason the hook function fails and an
   exception is raised then both the old and new modules will be
   discarded. As a last opportunity to release any resources when this
   occurs, an extra hook function called ``__mp_purge__()`` can be
   supplied. This function will be called with no arguments.


.. function:: allow_methods([*args])

   A convenience function to set values in :meth:`request.allowed`.
   :meth:`request.allowed` is a bitmask that is used to construct the
   ``'Allow:'`` header. It should be set before returning a
   :const:`HTTP_NOT_IMPLEMENTED` error.

   Arguments can be one or more of the following::

      M_GET
      M_PUT
      M_POST
      M_DELETE
      M_CONNECT
      M_OPTIONS
      M_TRACE
      M_PATCH
      M_PROPFIND
      M_PROPPATCH
      M_MKCOL
      M_COPY
      M_MOVE
      M_LOCK
      M_UNLOCK
      M_VERSION_CONTROL
      M_CHECKOUT
      M_UNCHECKOUT
      M_CHECKIN
      M_UPDATE
      M_LABEL
      M_REPORT
      M_MKWORKSPACE
      M_MKACTIVITY
      M_BASELINE_CONTROL
      M_MERGE
      M_INVALID

.. function:: exists_config(name)

   This function returns True if the Apache server was launched with
   the definition with the given *name*. This means that you can
   test whether Apache was launched with the ``-DFOOBAR`` parameter
   by calling ``apache.exists_config_define('FOOBAR')``.

.. function:: stat(fname, wanted)

   This function returns an instance of an ``mp_finfo`` object
   describing information related to the file with name ``fname``.
   The ``wanted`` argument describes the minimum attributes which
   should be filled out. The resultant object can be assigned to the
   :attr:`request.finfo` attribute.

.. function:: register_cleanup(callable[, data])

   Registers a cleanup that will be performed at child shutdown
   time. Equivalent to :func:`server.register_cleanup`, except
   that a request object is not required. *Warning:* do not pass
   directly or indirectly a request object in the data
   parameter. Since the callable will be called at server shutdown
   time, the request object won't exist anymore and any manipulation
   of it in the handler will give undefined behaviour.

.. function:: config_tree()

   Returns the server-level configuration tree. This tree does not
   include directives from .htaccess files. This is a *copy* of the
   tree, modifying it has no effect on the actual configuration.

.. function:: server_root()

   Returns the value of ServerRoot.

.. function:: make_table()

   This function is obsolete and is an alias to :class:`table` (see below).

.. function:: mpm_query(code)

   Allows querying of the MPM for various parameters such as numbers of
   processes and threads. The return value is one of three constants::

      AP_MPMQ_NOT_SUPPORTED      = 0  # This value specifies whether 
                                      # an MPM is capable of         
                                      # threading or forking.        
      AP_MPMQ_STATIC             = 1  # This value specifies whether 
                                      # an MPM is using a static # of
                                      # threads or daemons.          
      AP_MPMQ_DYNAMIC            = 2  # This value specifies whether 
                                      # an MPM is using a dynamic # of
                                      # threads or daemons.          

   The *code* argument must be one of the following::

      AP_MPMQ_MAX_DAEMON_USED    = 1  # Max # of daemons used so far 
      AP_MPMQ_IS_THREADED        = 2  # MPM can do threading         
      AP_MPMQ_IS_FORKED          = 3  # MPM can do forking           
      AP_MPMQ_HARD_LIMIT_DAEMONS = 4  # The compiled max # daemons   
      AP_MPMQ_HARD_LIMIT_THREADS = 5  # The compiled max # threads   
      AP_MPMQ_MAX_THREADS        = 6  # # of threads/child by config 
      AP_MPMQ_MIN_SPARE_DAEMONS  = 7  # Min # of spare daemons       
      AP_MPMQ_MIN_SPARE_THREADS  = 8  # Min # of spare threads       
      AP_MPMQ_MAX_SPARE_DAEMONS  = 9  # Max # of spare daemons       
      AP_MPMQ_MAX_SPARE_THREADS  = 10 # Max # of spare threads       
      AP_MPMQ_MAX_REQUESTS_DAEMON= 11 # Max # of requests per daemon 
      AP_MPMQ_MAX_DAEMONS        = 12 # Max # of daemons by config   

   Example::

      if apache.mpm_query(apache.AP_MPMQ_IS_THREADED):
          # do something
      else:
          # do something else

.. _pyapi-apmem:

Attributes
----------

.. attribute:: interpreter

   String. The name of the subinterpreter under which we're running.
   *(Read-Only)*

.. attribute:: main_server

  A ``server`` object for the main server.
  *(Read-Only)*

.. attribute:: MODULE_MAGIC_NUMBER_MAJOR

   Integer. An internal to Apache version number useful to determine whether
   certain features should be available. See :attr:`MODULE_MAGIC_NUMBER_MINOR`.

   Major API changes that could cause compatibility problems for older
   modules such as structure size changes.  No binary compatibility is
   possible across a change in the major version.

   *(Read-Only)*


.. attribute:: MODULE_MAGIC_NUMBER_MINOR

   Integer. An internal to Apache version number useful to determine whether
   certain features should be available. See :attr:`MODULE_MAGIC_NUMBER_MAJOR`.

   Minor API changes that do not cause binary compatibility problems.

   *(Read-Only)*


.. _pyapi-mptable:

Table Object (mp_table)
-----------------------
.. index::
   singe: table

.. class:: table([mapping-or-sequence])

   Returns a new empty object of type ``mp_table``. See Section
   :ref:`pyapi-mptable` for description of the table object. The
   *mapping-or-sequence* will be used to provide initial values for
   the table.

   The table object is a wrapper around the Apache APR table. The
   table object behaves very much like a dictionary (including the
   Python 2.2 features such as support of the ``in`` operator, etc.),
   with the following differences:

   * Both keys and values must be strings.
   * Key lookups are case-insensitive.
   * Duplicate keys are allowed (see :meth:`table.add()` below). When there is
     more than one value for a key, a subscript operation returns a list.

   Much of the information that Apache uses is stored in tables. For
   example, :meth:`request.headers_in` and :meth:`request.headers_out`.

   All the tables that mod_python provides inside the request object
   are actual mappings to the Apache structures, so changing the
   Python table also changes the underlying Apache table.

   In addition to normal dictionary-like behavior, the table object
   also has the following method:

   .. method:: add(key, val)

      Allows for creating duplicate keys, which is useful 
      when multiple headers, such as `Set-Cookie:` are required.

.. _pyapi-mprequest:

Request Object
--------------

.. index::
   single: req
   single: request
   single: request_rec

The request object is a Python mapping to the Apache `request_rec`
structure. When a handler is invoked, it is always passed a single
argument - the request object. For brevity, we oftern refer to it here
and throughout the code as ``req``.

You can dynamically assign attributes to it as a way to communicate
between handlers. 

.. _pyapi-mprequest-meth:

Request Methods
^^^^^^^^^^^^^^^

.. method:: request.add_cgi_vars()

   Calls Apache function ``ap_add_common_vars()`` followed some code
   very similar to Apache ``ap_add_cgi_vars()`` with the exception of
   calculating ``PATH_TRANSLATED`` value, thereby avoiding
   sub-requests and filesystem access used in the ``ap_add_cgi_vars()``
   implementation.

.. method:: request.add_common_vars()

   Use of this method is discouraged, use
   :meth:`request.add_cgi_vars()` instead.

   Calls the Apache ``ap_add_common_vars()`` function. After a call to
   this method, :attr:`request.subprocess_env` will contain *some* CGI
   information.

.. method:: request.add_handler(htype, handler[, dir])

   Allows dynamic handler registration. *htype* is a string
   containing the name of any of the apache request (but not filter or
   connection) handler directives,
   e.g. ``'PythonHandler'``. *handler* is a string containing the
   name of the module and the handler function.  Optional *dir* is
   a string containing the name of the directory to be added to the
   pythonpath. If no directory is specified, then, if there is already
   a handler of the same type specified, its directory is inherited,
   otherwise the directory of the presently executing handler is
   used. If there is a ``'PythonPath'`` directive in effect, then
   ``sys.path`` will be set exactly according to it (no directories
   added, the *dir* argument is ignored).
  
   A handler added this way only persists throughout the life of the
   request. It is possible to register more handlers while inside the
   handler of the same type. One has to be careful as to not to create
   an infinite loop this way.

   Dynamic handler registration is a useful technique that allows the
   code to dynamically decide what will happen next. A typical example
   might be a ``PythonAuthenHandler`` that will assign different
   ``PythonHandlers`` based on the authorization level, something
   like::

      if manager:
         req.add_handler("PythonHandler", "menu::admin")
      else:
         req.add_handler("PythonHandler", "menu::basic")

   .. note::

      If you pass this function an invalid handler, an exception will be
      generated at the time an attempt is made to find the handler. 


.. method:: request.add_input_filter(filter_name)

   Adds the named filter into the input filter chain for the current
   request.  The filter should be added before the first attempt to
   read any data from the request.


.. method:: reques.add_output_filter(filter_name)

   Adds the named filter into the output filter chain for the current
   request.  The filter should be added before the first attempt to
   write any data for the response.

   Provided that all data written is being buffered and not flushed,
   this could be used to add the "CONTENT_LENGTH" filter into the
   chain of output filters. The purpose of the "CONTENT_LENGTH" filter
   is to add a ``Content-Length:`` header to the response.::


      req.add_output_filter("CONTENT_LENGTH")
      req.write("content",0)

.. method:: request.allow_methods(methods[, reset])

   Adds methods to the :meth:`request.allowed_methods` list. This list
   will be passed in `Allowed:` header if
   :const:`HTTP_METHOD_NOT_ALLOWED` or :const:`HTTP_NOT_IMPLEMENTED`
   is returned to the client. Note that Apache doesn't do anything to
   restrict the methods, this list is only used to construct the
   header. The actual method-restricting logic has to be provided in
   the handler code.

   *methods* is a sequence of strings. If *reset* is 1, then
   the list of methods is first cleared.


.. method:: request.auth_name()

   Returns AuthName setting.


.. method:: request.auth_type()

   Returns AuthType setting.


.. method:: request.construct_url(uri)

   This function returns a fully qualified URI string from the path
   specified by uri, using the information stored in the request to
   determine the scheme, server name and port. The port number is not
   included in the string if it is the same as the default port 80.

   For example, imagine that the current request is directed to the
   virtual server www.modpython.org at port 80. Then supplying
   ``'/index.html'`` will yield the string
   ``'http://www.modpython.org/index.html'``.


.. method:: request.discard_request_body()

   Tests for and reads any message body in the request, simply discarding
   whatever it receives.


.. method:: request.document_root()

   Returns DocumentRoot setting.


.. method:: request.get_basic_auth_pw()

   Returns a string containing the password when Basic authentication is
   used.


.. method:: request.get_config()

   Returns a reference to the table object containing the mod_python
   configuration in effect for this request except for
   ``Python*Handler`` and ``PythonOption`` (The latter can be obtained
   via :meth:`request.get_options()`. The table has directives as keys,
   and their values, if any, as values.


.. method:: request.get_remote_host([type[, str_is_ip]])

   This method is used to determine remote client's DNS name or IP
   number. The first call to this function may entail a DNS look up,
   but subsequent calls will use the cached result from the first
   call.

   The optional *type* argument can specify the following: 

   * :const:`apache.REMOTE_HOST` Look up the DNS name. Return None if Apache
     directive ``HostNameLookups`` is ``Off`` or the hostname cannot
     be determined.

   * :const:`apache.REMOTE_NAME` *(Default)* Return the DNS name if
     possible, or the IP (as a string in dotted decimal notation)
     otherwise.

   * :const:`apache.REMOTE_NOLOOKUP` Don't perform a DNS lookup, return an
     IP. Note: if a lookup was performed prior to this call, then the
     cached host name is returned.

   * :const:`apache.REMOTE_DOUBLE_REV` Force a double-reverse lookup. On 
     failure, return None.

   If *str_is_ip* is ``None`` or unspecified, then the return
   value is a string representing the DNS name or IP address.

   If the optional *str_is_ip* argument is not ``None``, then
   the return value is an ``(address, str_is_ip)`` tuple, where
   ``str_is_ip`` is non-zero if ``address`` is an IP address
   string.

   On failure, ``None`` is returned.


.. method:: request.get_options()

   Returns a reference to the table object containing the options set by
   the ``PythonOption`` directives.


.. method:: request.internal_redirect(new_uri)

   Internally redirects the request to the *new_uri*. *new_uri*
   must be a string.

   The httpd server handles internal redirection by creating a new
   request object and processing all request phases. Within an
   internal redirect, :meth:`request.prev` will contain a reference to a
   request object from which it was redirected.


.. method:: request.is_https()

   Returns non-zero if the connection is using SSL/TLS. Will always return
   zero if the mod_ssl Apache module is not loaded.

   You can use this method during any request phase, unlike looking
   for the ``HTTPS`` variable in the :attr:`request.subprocess_env` member
   dictionary.  This makes it possible to write an authentication or
   access handler that makes decisions based upon whether SSL is being
   used.

   Note that this method will not determine the quality of the
   encryption being used.  For that you should call the
   `ssl_var_lookup` method to get one of the `SSL_CIPHER*` variables.


.. method:: request.log_error(message[, level])

   An interface to the Apache `ap_log_rerror` function. *message* is a
   string with the error message, *level* is one of the following
   flags constants::


      APLOG_EMERG
      APLOG_ALERT
      APLOG_CRIT
      APLOG_ERR
      APLOG_WARNING
      APLOG_NOTICE
      APLOG_INFO
      APLOG_DEBUG
      APLOG_NOERRNO

   If you need to write to log and do not have a reference to a request object,
   use the :func:`apache.log_error` function.


.. method:: request.meets_conditions()

   Calls the Apache ``ap_meets_conditions()`` function which returns a
   status code. If *status* is :const:`apache.OK`, generate the
   content of the response normally. If not, simply return *status*.
   Note that *mtime* (and possibly the ETag header) should be set as
   appropriate prior to calling this function. The same goes for
   :meth:`request.status` if the status differs from :const:`apache.OK`.

   Example::

      # ...
      r.headers_out['ETag'] = '"1130794f-3774-4584-a4ea-0ab19e684268"'
      r.headers_out['Expires'] = 'Mon, 18 Apr 2005 17:30:00 GMT'
      r.update_mtime(1000000000)
      r.set_last_modified()

      status = r.meets_conditions()
      if status != apache.OK:
         return status

      # ... do expensive generation of the response content ... 


.. method:: request.requires()

   Returns a tuple of strings of arguments to ``require`` directive.
  
   For example, with the following apache configuration::

      AuthType Basic
      require user joe
      require valid-user

   :meth:`request.requires()` would return ``('user joe', 'valid-user')``.


.. method:: request.read([len])

   Reads at most *len* bytes directly from the client, returning a
   string with the data read. If the *len* argument is negative or
   omitted, reads all data given by the client.

   This function is affected by the ``Timeout`` Apache
   configuration directive. The read will be aborted and an
   :exc:`IOError` raised if the :exc:`Timeout` is reached while
   reading client data.

   This function relies on the client providing the ``Content-length``
   header. Absence of the ``Content-length`` header will be treated as
   if ``Content-length: 0`` was supplied.

   Incorrect ``Content-length`` may cause the function to try to read
   more data than available, which will make the function block until
   a ``Timeout`` is reached.


.. method:: request.readline([len])

   Like :meth:`request.read()` but reads until end of line. 

   .. note::
  
      In accordance with the HTTP specification, most clients will be
      terminating lines with ``'\r\n'`` rather than simply
      ``'\n'``.


.. method:: request.readlines([sizehint])

   Reads all lines using :meth:`request.readline()` and returns a list of
   the lines read.  If the optional *sizehint* parameter is given in,
   the method will read at least *sizehint* bytes of data, up to the
   completion of the line in which the *sizehint* bytes limit is
   reached.


.. method:: request.register_cleanup(callable[, data])

   Registers a cleanup. Argument *callable* can be any callable
   object, the optional argument *data* can be any object (default is
   ``None``). At the very end of the request, just before the actual
   request record is destroyed by Apache, *callable* will be
   called with one argument, *data*.

   It is OK to pass the request object as data, but keep in mind that
   when the cleanup is executed, the request processing is already
   complete, so doing things like writing to the client is completely
   pointless.

   If errors are encountered during cleanup processing, they should be
   in error log, but otherwise will not affect request processing in
   any way, which makes cleanup bugs sometimes hard to spot.

   If the server is shut down before the cleanup had a chance to run,
   it's possible that it will not be executed.


.. method:: request.register_input_filter(filter_name, filter[, dir])

   Allows dynamic registration of mod_python input
   filters. *filter_name* is a string which would then subsequently be
   used to identify the filter.  *filter* is a string containing
   the name of the module and the filter function.  Optional *dir*
   is a string containing the name of the directory to be added to the
   pythonpath. If there is a ``PythonPath`` directive in effect,
   then ``sys.path`` will be set exactly according to it (no
   directories added, the *dir* argument is ignored).

   The registration of the filter this way only persists for the life
   of the request. To actually add the filter into the chain of input
   filters for the current request ``request.add_input_filter()`` would be
   used.


.. method:: request.register_output_filter(filter_name, filter[, dir])

   Allows dynamic registration of mod_python output
   filters. *filter_name* is a string which would then subsequently be
   used to identify the filter.  *filter* is a string containing the
   name of the module and the filter function. Optional *dir* is a
   string containing the name of the directory to be added to the
   pythonpath. If there is a ``PythonPath`` directive in effect, then
   ``sys.path`` will be set exactly according to it (no directories
   added, the *dir* argument is ignored).

   The registration of the filter this way only persists for the life
   of the request. To actually add the filter into the chain of output
   filters for the current request :meth:`request.add_output_filter()`
   would be used.


.. method:: request.sendfile(path[, offset, len])

   Sends *len* bytes of file *path* directly to the client, starting
   at offset *offset* using the server's internal API. *offset*}
   defaults to 0, and *len* defaults to -1 (send the entire file).

   Returns the number of bytes sent, or raises an IOError exception on
   failure.

   This function provides the most efficient way to send a file to the
   client.


.. method:: request.set_etag()

   Sets the outgoing ``'ETag'`` header.


.. method:: request.set_last_modified()

   Sets the outgoing \samp{Last-Modified} header based on value of
   ``mtime`` attribute.


.. method:: request.ssl_var_lookup(var_name)

   Looks up the value of the named SSL variable.  This method queries
   the mod_ssl Apache module directly, and may therefore be used in
   early request phases (unlike using the :attr:`request.subprocess_env`
   member.

   If the mod_ssl Apache module is not loaded or the variable is not
   found then ``None`` is returned.

   If you just want to know if a SSL or TLS connection is being used,
   you may consider calling the ``is_https`` method instead.

   It is unfortunately not possible to get a list of all available
   variables with the current mod_ssl implementation, so you must know
   the name of the variable you want.  Some of the potentially useful
   ssl variables are listed below.  For a complete list of variables
   and a description of their values see the mod_ssl documentation.::


      SSL_CIPHER
      SSL_CLIENT_CERT
      SSL_CLIENT_VERIFY
      SSL_PROTOCOL
      SSL_SESSION_ID

   .. note::

      Not all SSL variables are defined or have useful values in every
      request phase.  Also use caution when relying on these values
      for security purposes, as SSL or TLS protocol parameters can
      often be renegotiated at any time during a request.


.. method:: request.update_mtime(dependency_mtime)

   If *ependency_mtime* is later than the value in the ``mtime``
   attribute, sets the attribute to the new value.


.. method:: request.write(string[, flush=1])

   Writes *string* directly to the client, then flushes the buffer,
   unless flush is 0.


.. method:: request.flush()

   Flushes the output buffer.


.. method:: request.set_content_length(len)

   Sets the value of :attr:`request.clength` and the ``'Content-Length'``
   header to len. Note that after the headers have been sent out
   (which happens just before the first byte of the body is written,
   i.e. first call to :meth:`request.write`), calling the method is
   meaningless.

.. _pyapi-mprequest-mem:

Request Members
^^^^^^^^^^^^^^^

.. attribute:: request.connection

   A ``connection`` object associated with this request. See
   :ref:`pyapi-mpconn` Object for more details.
   *(Read-Only)*


.. attribute:: request.server

   A server object associated with this request. See 
   :ref:`pyapi-mpserver` for more details.
   *(Read-Only)*


.. attribute:: request.next

   If this is an internal redirect, the request object we redirect to. 
   *(Read-Only)*


.. attribute:: request.prev

   If this is an internal redirect, the request object we redirect from.
   *(Read-Only)*


.. attribute:: request.main

   If this is a sub-request, pointer to the main request. 
   *(Read-Only)*


.. attribute:: request.the_request

   String containing the first line of the request.
   *(Read-Only)*


.. attribute:: request.assbackwards

   Indicates an HTTP/0.9 "simple" request. This means that the
   response will contain no headers, only the body. Although this
   exists for backwards compatibility with obsolescent browsers, some
   people have figred out that setting assbackwards to 1 can be a
   useful technique when including part of the response from an
   internal redirect to avoid headers being sent.


.. attribute:: request.proxyreq

   A proxy request: one of :const:`apache.PROXYREQ_*` values.


.. attribute:: request.header_only

   A boolean value indicating HEAD request, as opposed to GET. 
   *(Read-Only)*


.. attribute:: request.protocol

   Protocol, as given by the client, or ``'HTTP/0.9'``. Same as CGI :envvar:`SERVER_PROTOCOL`.
   *(Read-Only)*


.. attribute:: request.proto_num

   Integer. Number version of protocol; 1.1 = 1001 *(Read-Only)*


.. attribute:: request.hostname

   String. Host, as set by full URI or Host: header.  *(Read-Only)*


.. attribute:: request.request_time

   A long integer. When request started.  *(Read-Only)*


.. attribute:: request.status_line

   Status line. E.g. ``'200 OK'``.  *(Read-Only)*


.. attribute:: request.status

   Status. One of :const:`apache.HTTP_*` values.


.. attribute:: request.method

   A string containing the method - ``'GET'``, ``'HEAD'``, ``'POST'``, etc.  Same
   as CGI :envvar:`REQUEST_METHOD`.  *(Read-Only)*


.. attribute:: request.method_number

   Integer containing the method number.  *(Read-Only)*


.. attribute:: request.allowed

   Integer. A bitvector of the allowed methods. Used to construct the
   Allowed: header when responding with
   :const:`HTTP_METHOD_NOT_ALLOWED` or
   :const:`HTTP_NOT_IMPLEMENTED`. This field is for Apache's
   internal use, to set the ``Allowed:`` methods use
   :meth:`request.allow_methods` method, described in section
   :ref:`pyapi-mprequest-meth`. *(Read-Only)*


.. attribute:: request.allowed_xmethods

   Tuple. Allowed extension methods.  *(Read-Only)*


.. attribute:: request.allowed_methods

   Tuple. List of allowed methods. Used in relation with
   :const:`METHOD_NOT_ALLOWED`. This member can be modified via
   :meth:`request.allow_methods` described in section
   :ref:`pyapi-mprequest-meth`. *(Read-Only)*


.. attribute:: request.sent_bodyct

   Integer. Byte count in stream is for body. (?)  *(Read-Only)*


.. attribute:: request.bytes_sent

   Long integer. Number of bytes sent.  *(Read-Only)*


.. attribute:: request.mtime

   Long integer. Time the resource was last modified.  *(Read-Only)*


.. attribute:: request.chunked

   Boolean value indicating when sending chunked transfer-coding.
   *(Read-Only)*


.. attribute:: request.range

   String. The ``Range:`` header.  *(Read-Only)*


.. attribute:: request.clength

   Long integer. The "real" content length.  *(Read-Only)*


.. attribute:: request.remaining

   Long integer. Bytes left to read. (Only makes sense inside a read
   operation.)  *(Read-Only)*


.. attribute:: request.read_length

   Long integer. Number of bytes read. *(Read-Only)*


.. attribute:: request.read_body

   Integer. How the request body should be read. *(Read-Only)*


.. attribute:: request.read_chunked

   Boolean. Read chunked transfer coding.  *(Read-Only)*


.. attribute:: request.expecting_100

   Boolean. Is client waiting for a 100 (:const:`HTTP_CONTINUE`)
   response.  *(Read-Only)*


.. attribute:: request.headers_in

   A :class:`table` object containing headers sent by the client.


.. attribute:: request.headers_out

   A :class:`table` object representing the headers to be sent to the
   client.


.. attribute:: request.err_headers_out

   These headers get send with the error response, instead of
   headers_out.


.. attribute:: request.subprocess_env

   A :class:`table` object containing environment information
   typically usable for CGI.  You may have to call
   :meth:`request.add_common_vars` and :meth:`request.add_cgi_vars`
   first to fill in the information you need.


.. attribute:: request.notes

   A :class:`table` object that could be used to store miscellaneous
   general purpose info that lives for as long as the request
   lives. If you need to pass data between handlers, it's better to
   simply add members to the request object than to use
   :attr:`request.notes`.


.. attribute:: request.phase

   The phase currently being being processed,
   e.g. ``'PythonHandler'``.  *(Read-Only)*


.. attribute:: request.interpreter

   The name of the subinterpreter under which we're running.
   *(Read-Only)*


.. attribute:: request.content_type

   String. The content type. Mod_python maintains an internal flag
   (:attr:`request._content_type_set`) to keep track of whether
   :attr:`request.content_type` was set manually from within
   Python. The publisher handler uses this flag in the following way:
   when :attr:`request.content_type` isn't explicitly set, it attempts
   to guess the content type by examining the first few bytes of the
   output.


.. attribute:: request.content_languages

   Tuple. List of strings representing the content languages. 


.. attribute:: request.handler

   The symbolic name of the content handler (as in module, not
   mod_python handler) that will service the request during the
   response phase. When the SetHandler/AddHandler directives are used
   to trigger mod_python, this will be set to ``'mod_python'`` by
   mod_mime. A mod_python handler executing prior to the response
   phase may also set this to ``'mod_python'`` along with calling
   :meth:`request.add_handler` to register a mod_python handler for
   the response phase::

      def typehandler(req):
         if os.path.splitext(req.filename)[1] == ".py":
            req.handler = "mod_python"
           req.add_handler("PythonHandler", "mod_python.publisher")
           return apache.OK
         return apache.DECLINED


.. attribute:: request.content_encoding

   String. Content encoding.  *(Read-Only)*


.. attribute:: request.vlist_validator

   Integer. Variant list validator (if negotiated).  *(Read-Only)*


.. attribute:: request.user

   If an authentication check is made, this will hold the user
   name. Same as CGI :envvar:`REMOTE_USER`.

   .. note::

      :meth:`request.get_basic_auth_pw` must be called prior to using this value.


.. attribute:: request.ap_auth_type

   Authentication type. Same as CGI :envvar:`AUTH_TYPE`.


.. attribute:: request.no_cache

   Boolean. This response cannot be cached.


.. attribute:: request.no_local_copy

   Boolean. No local copy exists.


.. attribute:: request.unparsed_uri

   The URI without any parsing performed.  *(Read-Only)*


.. attribute:: request.uri

   The path portion of the URI.


.. attribute:: request.filename

   String. File name being requested.


.. attribute:: request.canonical_filename

   String. The true filename (:attr:`request.filename` is
   canonicalized if they don't match).


.. attribute:: request.path_info

   String. What follows after the file name, but is before query args,
   if anything. Same as CGI :envvar:`PATH_INFO`.


.. attribute:: request.args

   String. Same as CGI :envvar:`QUERY_ARGS`.


.. attribute:: request.finfo

   A file information object with type ``mp_finfo``, analogous to the
   result of the POSIX stat function, describing the file pointed to
   by the URI. The object provides the attributes ``fname``,
   ``filetype``, ``valid``, ``protection``, ``user``, ``group``, ``size``,
   ``inode``, ``device``, ``nlink``, ``atime``, ``mtime``, ``ctime`` and
   ``name``.

   The attribute may be assigned to using the result of
   :func:`apache.stat`.  For example::

      if req.finfo.filetype == apache.APR_DIR:
        req.filename = posixpath.join(req.filename, 'index.html')
        req.finfo = apache.stat(req.filename, apache.APR_FINFO_MIN)

   For backward compatability, the object can also be accessed as if
   it were a tuple. The ``apache`` module defines a set of
   :const:`FINFO_*` constants that should be used to access elements
   of this tuple.::

      user = req.finfo[apache.FINFO_USER]


.. attribute:: request.parsed_uri

   Tuple. The URI broken down into pieces. ``(scheme, hostinfo, user, password, hostname, port, path, query, fragment)``.
   The :mod:`apache` module defines a set of :const:`URI_*` constants that
   should be used to access elements of this tuple. Example::

      fname = req.parsed_uri[apache.URI_PATH]

   *(Read-Only)*


.. attribute:: request.used_path_info

   Flag to accept or reject path_info on current request.


.. attribute:: request.eos_sent

   Boolean. EOS bucket sent.  *(Read-Only)*


.. attribute:: request.useragent_addr

   *Apache 2.4 only*

   The (address, port) tuple for the user agent.

   This attribute should reflect the address of the user agent and
   not necessarily the other end of the TCP connection, for which
   there is :attr:`connection.client_addr`.
   *(Read-Only)*


.. attribute:: request.useragent_ip

   *Apache 2.4 only*

   String with the IP of the user agent. Same as CGI :envvar:`REMOTE_ADDR`.

   This attribute should reflect the address of the user agent and
   not necessarily the other end of the TCP connection, for which
   there is :attr:`connection.client_ip`.
   *(Read-Only)*


.. _pyapi-mpconn:

Connection Object (mp_conn)
---------------------------

.. index::
   singe: mp_conn

The connection object is a Python mapping to the Apache
:c:type:`conn_rec` structure.

.. _pyapi-mpconn-meth:

Connection Methods
^^^^^^^^^^^^^^^^^^

.. method:: connection.log_error(message[, level])

   An interface to the Apache ``ap_log_cerror`` function. *message* is
   a string with the error message, *level* is one of the following
   flags constants::

      APLOG_EMERG
      APLOG_ALERT
      APLOG_CRIT
      APLOG_ERR
      APLOG_WARNING
      APLOG_NOTICE
      APLOG_INFO
      APLOG_DEBUG
      APLOG_NOERRNO

    If you need to write to log and do not have a reference to a connection or
    request object, use the :func:`apache.log_error` function.


.. method:: connection.read([length])

   Reads at most *length* bytes from the client. The read blocks
   indefinitely until there is at least one byte to read. If length is
   -1, keep reading until the socket is closed from the other end
   (This is known as ``EXHAUSTIVE`` mode in the http server code).

   This method should only be used inside *Connection Handlers*.

   .. note::

      The behaviour of this method has changed since version 3.0.3. In
      3.0.3 and prior, this method would block until \var{length} bytes
      was read.


.. method:: connection.readline([length])

   Reads a line from the connection or up to *length* bytes.

   This method should only be used inside *Connection Handlers*.


.. method:: connection.write(string)

   Writes *string* to the client.

   This method should only be used inside *Connection Handlers*.


.. _pyapi-mpconn-mem:

Connection Members
^^^^^^^^^^^^^^^^^^

.. attribute:: connection.base_server

   A ``server`` object for the physical vhost that this connection came
   in through.  *(Read-Only)*


.. attribute:: connection.local_addr

   The (address, port) tuple for the server.  *(Read-Only)*


.. attribute:: connection.remote_addr

   *Deprecated in Apache 2.4, use client_addr. (Aliased to client_addr for backward compatibility)*

   The (address, port) tuple for the client.  *(Read-Only)*


.. attribute:: connection.client_addr

   *Apache 2.4 only*

   The (address, port) tuple for the client.

   This attribute reflects the other end of the TCP connection, which
   may not always be the address of the user agent. A more accurate
   source of the user agent address is :attr:`request.useragent_addr`.
   *(Read-Only)*


.. attribute:: connection.remote_ip

   *Deprecated in Apache 2.4, use client_ip. (Aliased to client_ip for backward compatibility)*

   String with the IP of the client. In Apache 2.2 same as CGI :envvar:`REMOTE_ADDR`.
   *(Read-Only)*


.. attribute:: connection.client_ip

   *Apache 2.4 only*

   String with the IP of the client.

   This attribute reflects the other end of the TCP connection, which
   may not always be the address of the user agent. A more accurate
   source of the user agent address is :attr:`request.useragent_ip`.

   *(Read-Only)*


.. attribute:: connection.remote_host

   String. The DNS name of the remote client. None if DNS has not been
   checked, ``''`` (empty string) if no name found. Same as CGI
   :envvar:`REMOTE_HOST`.  *(Read-Only)*


.. attribute:: connection.remote_logname

   Remote name if using RFC1413 (ident). Same as CGI
   :envvar:`REMOTE_IDENT`.  *(Read-Only)*


.. attribute:: connection.aborted

   Boolean. True is the connection is aborted. *(Read-Only)*


.. attribute:: connection.keepalive

   Integer. 1 means the connection will be kept for the next request,
   0 means "undecided", -1 means "fatal error".  *(Read-Only)*


.. attribute:: connection.double_reverse

   Integer. 1 means double reverse DNS lookup has been performed, 0
   means not yet, -1 means yes and it failed.  *(Read-Only)*


.. attribute:: connection.keepalives

   The number of times this connection has been used. (?)
   *(Read-Only)*


.. attribute:: connection.local_ip

   String with the IP of the server. *(Read-Only)*


.. attribute:: connection.local_host

   DNS name of the server. *(Read-Only)*


.. attribute:: connection.id

   Long. A unique connection id. *(Read-Only)*


.. attribute:: connection.notes

   A :class:`table` object containing miscellaneous general purpose
   info that lives for as long as the connection lives.


.. _pyapi-mpfilt:

Filter Object (mp_filter)
-------------------------

.. index::
   singe: mp_filter

A filter object is passed to mod_python input and output filters. It
is used to obtain filter information, as well as get and pass
information to adjacent filters in the filter stack.

.. _pyapi-mpfilt-meth:

Filter Methods
^^^^^^^^^^^^^^

.. method:: filter.pass_on()

   Passes all data through the filter without any processing.


.. method:: filter.read([length])

   Reads at most *len* bytes from the next filter, returning a
   string with the data read or None if End Of Stream (EOS) has been
   reached. A filter *must* be closed once the EOS has been
   encountered.

   If the *length* argument is negative or omitted, reads all data
   currently available.


.. method:: filter.readline([length])

   Reads a line from the next filter or up to *length* bytes.


.. method:: filter.write(string)

   Writes *string* to the next filter.


.. method:: filte.flush()

   Flushes the output by sending a FLUSH bucket.


.. method:: filter.close()

   Closes the filter and sends an EOS bucket. Any further IO
   operations on this filter will throw an exception.


.. method:: filter.disable()

   Tells mod_python to ignore the provided handler and just pass the
   data on. Used internally by mod_python to print traceback from
   exceptions encountered in filter handlers to avoid an infinite
   loop.


.. _pyapi-mpfilt-mem:

Filter Members
^^^^^^^^^^^^^^

.. attribute:: filter.closed

   A boolean value indicating whether a filter is closed.
   *(Read-Only)*


.. attribute:: filter.name

   String. The name under which this filter is registered.
   *(Read-Only)*


.. attribute:: filter.req

   A reference to the request object.  *(Read-Only)*


.. attribute:: filter.is_input

   Boolean. True if this is an input filter.  *(Read-Only)*


.. attribute:: filter.handler

   String. The name of the Python handler for this filter as specified
   in the configuration.  *(Read-Only)*


.. _pyapi-mpserver:

Server Object (mp_server)
^^^^^^^^^^^^^^^^^^^^^^^^^

.. index::
   single: mp_server


The request object is a Python mapping to the Apache
``request_rec`` structure. The server structure describes the
server (possibly virtual server) serving the request.

.. _pyapi-mpsrv-meth:

Server Methods
^^^^^^^^^^^^^^

.. method:: server.get_config()

   Similar to :meth:`request.get_config()`, but returns a table object
   holding only the mod_python configuration defined at global scope
   within the Apache configuration. That is, outside of the context of
   any VirtualHost, Location, Directory or Files directives.


.. method:: server.get_options()

   Similar to :meth:`request.get_options()`, but returns a table
   object holding only the mod_python options defined at global scope
   within the Apache configuration. That is, outside of the context of
   any VirtualHost, Location, Directory or Files directives.


.. method:: server.log_error(message[level])

   An interface to the Apache ``ap_log_error`` function. *message* is
   a string with the error message, *level* is one of the following
   flags constants::

      APLOG_EMERG
      APLOG_ALERT
      APLOG_CRIT
      APLOG_ERR
      APLOG_WARNING
      APLOG_NOTICE
      APLOG_INFO
      APLOG_DEBUG
      APLOG_NOERRNO

   If you need to write to log and do not have a reference to a server or
   request object, use the :func:`apache.log_error` function.


.. method:: server.register_cleanup(request, callable[, data])

   Registers a cleanup. Very similar to :meth:`req.register_cleanup`,
   except this cleanup will be executed at child termination
   time. This function requires the request object be supplied to
   infer the interpreter name.  If you don't have any request object
   at hand, then you must use the :func:`apache.register_cleanup`
   variant.

   .. note::

      *Warning:* do not pass directly or indirectly a request object in
      the data parameter. Since the callable will be called at server
      shutdown time, the request object won't exist anymore and any
      manipulation of it in the callable will give undefined behaviour.

.. _pyapi-mpsrv-mem:

Server Members
^^^^^^^^^^^^^^

.. attribute:: server.defn_name

   String. The name of the configuration file where the server
   definition was found.  *(Read-Only)*


.. attribute:: server.defn_line_number

   Integer. Line number in the config file where the server definition
   is found.  *(Read-Only)*


.. attribute:: server.server_admin

   Value of the ``ServerAdmin`` directive.  *(Read-Only)*


.. attribute:: server.server_hostname

   Value of the ``ServerName`` directive. Same as CGI
   :envvar:`SERVER_NAME`. *(Read-Only)*


.. attribute:: server.names

   Tuple. List of normal server names specified in the ``ServerAlias``
   directive.  This list does not include wildcarded names, which are
   listed separately in ``wild_names``. *(Read-Only)*


.. attribute:: server.wild_names

   Tuple. List of wildcarded server names specified in the ``ServerAlias``
   directive. *(Read-Only)*


.. attribute:: server.port

   Integer. TCP/IP port number. Same as CGI :envvar:`SERVER_PORT`.
   *This member appears to be 0 on Apache 2.0, look at
   req.connection.local_addr instead* *(Read-Only)*


.. attribute:: server.error_fname

   The name of the error log file for this server, if any.
   *(Read-Only)*


.. attribute:: server.loglevel

   Integer. Logging level. *(Read-Only)*


.. attribute:: server.is_virtual

   Boolean. True if this is a virtual server. *(Read-Only)*


.. attribute:: server.timeout

   Integer. Value of the ``Timeout`` directive.  *(Read-Only)*


.. attribute:: server.keep_alive_timeout

   Integer. Keepalive timeout.  *(Read-Only)*


.. attribute:: server.keep_alive_max

   Maximum number of requests per keepalive.  *(Read-Only)*


.. attribute:: server.keep_alive

   Use persistent connections?  *(Read-Only)*


.. attribute:: server.path

   String. Path for ``ServerPath`` *(Read-Only)*


.. attribute:: server.pathlen

   Integer. Path length. *(Read-Only)*


.. attribute:: server.limit_req_line

   Integer. Limit on size of the HTTP request line. *(Read-Only)*


.. attribute:: server.limit_req_fieldsize

   Integer. Limit on size of any request header field.  *(Read-Only)*


.. attribute:: server.limit_req_fields

   Integer. Limit on number of request header fields.  *(Read-Only)*


.. _pyapi-util:

:mod:`util` -- Miscellaneous Utilities
======================================

.. module:: util
   :synopsis: Miscellaneous Utilities.
.. moduleauthor:: Gregory Trubetskoy grisha@modpython.org

The :mod:`util` module provides a number of utilities handy to a web
application developer similar to those in the standard library
:mod:`cgi` module. The implementations in the :mod:`util` module are
much more efficient because they call directly into Apache API's as
opposed to using CGI which relies on the environment to pass
information.

The recommended way of using this module is::

   from mod_python import util


.. seealso::

   `Common Gateway Interface RFC Draft <http://ken.coar.org/cgi/draft-coar-cgi-v11-03.txt>`_
      for detailed information on the CGI specification

.. _pyapi-util-fstor:


FieldStorage class
------------------

Access to form data is provided via the \class{FieldStorage}
class. This class is similar to the standard library module
\module{cgi} \class{FieldStorage}.

.. class:: FieldStorage(req[, keep_blank_values[, strict_parsing[, file_callback[, field_callback]]]])

   This class provides uniform access to HTML form data submitted by
   the client.  *req* is an instance of the mod_python
   :class:`request` object.

   The optional argument *keep_blank_values* is a flag indicating
   whether blank values in URL encoded form data should be treated as
   blank strings. The default is false, which means that blank values
   are ignored as if they were not included.

   The optional argument *strict_parsing* is not yet implemented.

   The optional argument *file_callback* allows the application to
   override both file creation/deletion semantics and location. See
   :ref:`pyapi-util-fstor-examples` for
   additional information. *New in version 3.2*

   The optional argument *field_callback* allows the application to
   override both the creation/deletion semantics and behaviour. *New
   in version 3.2*

   During initialization, :class:`FieldStorage` class reads all of the
   data provided by the client. Since all data provided by the client
   is consumed at this point, there should be no more than one
   :class:`FieldStorage` class instantiated per single request, nor
   should you make any attempts to read client data before or after
   instantiating a :class:`FieldStorage`. A suggested strategy for
   dealing with this is that any handler should first check for the
   existance of a ``form`` attribute within the request object. If
   this exists, it should be taken to be an existing instance of the
   :class:`FieldStorage` class and that should be used. If the
   attribute does not exist and needs to be created, it should be
   cached as the ``form`` attribute of the request object so later
   handler code can use it.

   When the :class:`FieldStorage` class instance is created, the data
   read from the client is then parsed into separate fields and
   packaged in :class:`Field` objects, one per field. For HTML form
   inputs of type ``file``, a temporary file is created that can later
   be accessed via the :attr:`Field.file` attribute of a
   :class:`Field` object.

   The :class:`FieldStorage` class has a mapping object interface,
   i.e. it can be treated like a dictionary in most instances, but is
   not strictly compatible as is it missing some methods provided by
   dictionaries and some methods don't behave entirely like their
   counterparts, especially when there is more than one value
   associated with a form field. When used as a mapping, the keys are
   form input names, and the returned dictionary value can be:

   * An instance of :class:`StringField`, containing the form input
     value. This is only when there is a single value corresponding to
     the input name. :class:`StringField` is a subclass of
     :class:`str` which provides the additional
     :attr:`StringField.value` attribute for compatibility with
     standard library :mod:`cgi` module.

   * An instance of a :class:`Field` class, if the input is a file
     upload.

   * A list of :class:`StringField` and/or :class:`Field`
     objects. This is when multiple values exist, such as for a
     ``<select>`` HTML form element.


   .. note::

      Unlike the standard library :mod:`cgi` module
      :class:`FieldStorage` class, a :class:`Field` object is returned
      *only* when it is a file upload. In all other cases the return
      is an instance of :class:`StringField`. This means that you do
      not need to use the :attr:`StringFile.value` attribute to access
      values of fields in most cases.


   In addition to standard mapping object methods,
   :class:`FieldStorage` objects have the following attributes:

   .. attribute:: list

      This is a list of :class:`Field` objects, one for each
      input. Multiple inputs with the same name will have multiple
      elements in this list.

   .. _pyapi-util-fstor-meth:

:class:`FieldStorage` methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

   .. method:: add_field(name, value)

      Adds an additional form field with *name* and *value*.  If a
      form field already exists with *name*, the *value* will be added
      to the list of existing values for the form field.  This method
      should be used for adding additional fields in preference to
      adding new fields direct to the list of fields.

      If the value associated with a field should be replaced when it
      already exists, rather than an additional value being associated
      with the field, the dictionary like subscript operator should be
      used to set the value, or the existing field deleted altogether
      first using the ``del`` operator.


   .. method:: clear()

      Removes all form fields. Individual form fields can be deleted
      using the ``del`` operator.


   .. method:: get(name, default)

     If there is only one value associated with form field *name*,
     that single value will be returned. If there are multiple values,
     a list is returned holding all values. If no such form field or
     value exists then the method returns the value specified by the
     parameter *default*.  A subscript operator is also available
     which yields the same result except that an exception will be
     raised where the form field *name* does not exist.


   .. method:: getfirst(name[, default])

      Always returns only one value associated with form field
      *name*. If no such form field or value exists then the method
      returns the value specified by the optional parameter
      *default*. This parameter defaults to ``None`` if not specified.


   .. method:: getlist(name)

      This method always returns a list of values associated with form
      field *name*. The method returns an empty list if no such form
      field or value exists for *name*. It returns a list consisting
      of one item if only one such value exists.


   .. method:: has_key(name)

      Returns ``True`` if *name* is a valid form field. The ``in``
      operator is also supported and will call this method.


   .. method:: items()

      Returns a list consisting of tuples for each combination of form
      field name and value.


   .. method:: keys()

      This method returns the names of the form fields. The ``len``
      operator is also supported and will return the number of names
      which would be returned by this method.


.. _pyapi-util-fstor-examples:

FieldStorage Examples
---------------------

   The following examples demonstrate how to use the *file_callback*
   parameter of the :class:`FieldStorage` constructor to control file
   object creation. The :class:`Storage` classes created in both
   examples derive from FileType, thereby providing extended file
   functionality.

   These examples are provided for demonstration purposes only. The
   issue of temporary file location and security must be considered
   when providing such overrides with mod_python in production use.


Simple file control using class constructor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

      This example uses the :class:`FieldStorage` class constructor to
      create the file object, allowing simple control. It is not
      advisable to add class variables to this if serving multiple
      sites from apache. In that case use the factory method instead::

         class Storage(file):

            def __init__(self, advisory_filename):
                self.advisory_filename = advisory_filename
                self.delete_on_close = True
                self.already_deleted = False
                self.real_filename = '/someTempDir/thingy-unique-thingy'
                super(Storage, self).__init__(self.real_filename, 'w+b')

            def close(self):
                if self.already_deleted:
                    return
                super(Storage, self).close()
                if self.delete_on_close:
                    self.already_deleted = True
                    os.remove(self.real_filename)

            request_data = util.FieldStorage(request, keep_blank_values=True, file_callback=Storage)


Advanced file control using object factory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

      Using a object factory can provide greater control over the
      constructor parameters::

         import os

         class Storage(file):

             def __init__(self, directory, advisory_filename):
                 self.advisory_filename = advisory_filename
                 self.delete_on_close = True
                 self.already_deleted = False
                 self.real_filename = directory + '/thingy-unique-thingy'
                 super(Storage, self).__init__(self.real_filename, 'w+b')

             def close(self):
                 if self.already_deleted:
                     return
                 super(Storage, self).close()
                 if self.delete_on_close:
                     self.already_deleted = True
                     os.remove(self.real_filename)

         class StorageFactory:

             def __init__(self, directory):
                 self.dir = directory

             def create(self, advisory_filename):
                 return Storage(self.dir, advisory_filename)

         file_factory = StorageFactory(someDirectory)
         # [...sometime later...]
         request_data = util.FieldStorage(request, keep_blank_values=True,
                                          file_callback=file_factory.create)

.. _pyapi-util-fstor-fld:

Field class
-----------

.. class:: Field()

   This class is used internally by :class:`FieldStorage` and is not
   meant to be instantiated by the user. Each instance of a
   :class:`Field` class represents an HTML Form input.

   :class:`Field` instances have the following attributes:

   .. attribute:: name

      The input name.

   .. attribute:: value

      The input value. This attribute can be used to read data from a
      file upload as well, but one has to exercise caution when
      dealing with large files since when accessed via :attr:`value`,
      the whole file is read into memory.

   .. attribute:: file

      This is a file-like object. For file uploads it points to a
      :class:`TemporaryFile` instance. (For more information see the
      TemporaryFile class in the standard python `tempfile module
      <http://docs.python.org/lib/module-tempfile.html>`_.

      For simple values, it is a :class:`StringIO` object, so you can read
      simple string values via this attribute instead of using the :attr:`value`
      attribute as well.

   .. attribute:: filename

      The name of the file as provided by the client.

   .. attribute:: type

      The content-type for this input as provided by the client.

   .. attribute:: type_options

      This is what follows the actual content type in the ``content-type``
      header provided by the client, if anything. This is a dictionary.

   .. attribute:: disposition

      The value of the first part of the ``content-disposition`` header.

   .. attribute:: disposition_options

      The second part (if any) of the ``content-disposition`` header in
      the form of a dictionary.

   .. seealso::

      :rfc:`1867`
         Form-based File Upload in HTML}{for a description of form-based file uploads


.. _pyapi-util-funcs:

Other functions
---------------

.. function:: parse_qs(qs[, keep_blank_values[, strict_parsing]])

   This function is functionally equivalent to the standard library
   :func:`cgi.parse_qs`, except that it is written in C and is
   much faster.

    Parse a query string given as a string argument (data of type
    ``application/x-www-form-urlencoded``).  Data are returned as a
    dictionary.  The dictionary keys are the unique query variable
    names and the values are lists of values for each name.

    The optional argument *keep_blank_values* is a flag indicating
    whether blank values in URL encoded queries should be treated as
    blank strings.  A true value indicates that blanks should be
    retained as blank strings.  The default false value indicates that
    blank values are to be ignored and treated as if they were not
    included.

    .. note::

       The *strict_parsing* argument is not yet implemented.


.. function:: parse_qsl(qs[, keep_blank_values[, strict_parsing]])

   This function is functionally equivalent to the standard library
   :func:`cgi.parse_qsl`, except that it is written in C and is much
   faster.

    Parse a query string given as a string argument (data of type
    ``application/x-www-form-urlencoded``).  Data are returned as a
    list of name, value pairs.

    The optional argument *keep_blank_values* is a flag indicating
    whether blank values in URL encoded queries should be treated as
    blank strings.  A true value indicates that blanks should be
    retained as blank strings.  The default false value indicates that
    blank values are to be ignored and treated as if they were not
    included.

    .. note::

       The *strict_parsing* argument is not yet implemented.


.. function:: redirect(req, location[, permanent=0[, text=None]])

   This is a convenience function to redirect the browser to another
   location. When *permanent* is true, :const:`MOVED_PERMANENTLY`
   status is sent to the client, otherwise it is
   :const:`MOVED_TEMPORARILY`. A short text is sent to the browser
   informing that the document has moved (for those rare browsers that
   do not support redirection); this text can be overridden by
   supplying a *text* string.

    If this function is called after the headers have already been sent,
    an :exc:`IOError` is raised.

    This function raises :exc:`apache.SERVER_RETURN` exception with a
    value of :const:`apache.DONE` to ensuring that any later phases or
    stacked handlers do not run. If you do not want this, you can wrap
    the call to :func:`redirect` in a try/except block catching the
    :exc:`apache.SERVER_RETURN`.


.. _pyapi-cookie:

:mod:`Cookie` -- HTTP State Management
======================================

.. module:: Cookie
   :synopsis: HTTP State Management
.. moduleauthor:: Gregory Trubetskoy grisha@modpython.org

The :mod:`Cookie` module provides convenient ways for creating,
parsing, sending and receiving HTTP Cookies, as defined in the
specification published by Netscape.

.. note::

   Even though there are official IETF RFC's describing HTTP State
   Management Mechanism using cookies, the de facto standard supported
   by most browsers is the original Netscape specification.
   Furthermore, true compliance with IETF standards is actually
   incompatible with many popular browsers, even those that claim to
   be RFC-compliant. Therefore, this module supports the current
   common practice, and is not fully RFC compliant.
  
   More specifically, the biggest difference between Netscape and RFC
   cookies is that RFC cookies are sent from the browser to the server
   along with their attributes (like Path or Domain). The
   \module{Cookie} module ignore those incoming attributes, so all
   incoming cookies end up as Netscape-style cookies, without any of
   their attributes defined.


.. seealso::

   `Persistent Client State - HTTP Cookies <http://web.archive.org/web/20070202195439/http://wp.netscape.com/newsref/std/cookie_spec.html>`_
      for the original Netscape specification.

   :rfc:`2109`
      HTTP State Management Mechanism}{for the first RFC on Cookies.

   :rfc:`2694`
      Use of HTTP State Management}{for guidelines on using Cookies.

   :rfc:`2965`
      HTTP State Management Mechanism}{for the latest IETF standard.

   `HTTP Cookies: Standards, Privacy, and Politics <http://arxiv.org/abs/cs.SE/0105018>`_
      by David M. Kristol for an excellent overview of the issues surrounding standardization of Cookies.


.. _pyapi-cookie-classes:


Classes
-------

.. class:: Cookie(name, value[, attributes])

   This class is used to construct a single cookie named *name* and
   having *value* as the value. Additionally, any of the attributes
   defined in the Netscape specification and RFC2109 can by supplied
   as keyword arguments.

   The attributes of the class represent cookie attributes, and their
   string representations become part of the string representation of
   the cookie. The :class:`Cookie` class restricts attribute names to
   only valid values, specifically, only the following attributes are
   allowed: ``name, value, version, path, domain, secure, comment, expires, max_age, commentURL, discard, port, httponly, __data__``.

   The ``__data__`` attribute is a general-purpose dictionary that can
   be used for storing arbitrary values, when necessary (This is
   useful when subclassing :class:`Cookie`).

   The :attr:`expires` attribute is a property whose value is checked
   upon setting to be in format ``'Wdy, DD-Mon-YYYY HH:MM:SS GMT'``
   (as dictated per Netscape cookie specification), or a numeric value
   representing time in seconds since beginning of epoch (which will
   be automatically correctly converted to GMT time string). An
   invalid ``expires`` value will raise :exc:`ValueError`.

   When converted to a string, a :class:`Cookie` will be in correct
   format usable as value in a \samp{Cookie} or ``'Set-Cookie'``
   header.

   .. note::

      Unlike the Python Standard Library Cookie classes, this class
      represents a single cookie (referred to as :dfn:`Morsel` in
      Python Standard Library).


   .. method:: Cookie.parse(string)

      This is a class method that can be used to create a
      :class:`Cookie` instance from a cookie string *string* as
      passed in a header value. During parsing, attribute names are
      converted to lower case.

      Because this is a class method, it must be called explicitly
      specifying the class.

      This method returns a dictionary of :class:`Cookie` instances,
      not a single :class:`Cookie` instance.

      Here is an example of getting a single :class:`Cookie` instance::

         mycookies = Cookie.parse("spam=eggs; expires=Sat, 14-Jun-2003 02:42:36 GMT")
         spamcookie = mycookies["spam"]

      .. note::

         Because this method uses a dictionary, it is not possible to
         have duplicate cookies. If you would like to have more than
         one value in a single cookie, consider using a
         :class:`MarshalCookie`.


.. class:: SignedCookie(name, value, secret[, attributes])

   This is a subclass of :class:`Cookie`. This class creates cookies
   whose name and value are automatically signed using HMAC (md5) with
   a provided secret *secret*, which must be a non-empty string.

   .. method:: SignedCookie.parse(string, secret)

      This method acts the same way as :class:`Cookie.parse()`, but
      also verifies that the cookie is correctly signed. If the
      signature cannot be verified, the object returned will be of
      class :class:`Cookie`::

      ..  note::

         Always check the types of objects returned by
         :meth:SignedCookie.parse(). If it is an instance of
         :class:`Cookie` (as opposed to :class:`SignedCookie`), the
         signature verification has failed::

            # assume spam is supposed to be a signed cookie
            if type(spam) is not Cookie.SignedCookie:
               # do something that indicates cookie isn't signed correctly

.. class:: MarshalCookie(name, value, secret[, attributes])

   This is a subclass of :class:`SignedCookie`. It allows for *value*
   to be any marshallable objects. Core Python types such as string,
   integer, list, etc. are all marshallable object. For a complete
   list see `marchal <http://www.python.org/doc/current/lib/module-marshal.html>`_
   module documentation.

   When parsing, the signature is checked first, so incorrectly signed
   cookies will not be unmarshalled.

.. _pyapi-cookie-func:

Functions
^^^^^^^^^

.. function:: add_cookie(req, cookie[, value, attributes])

   This is a convenience function for setting a cookie in request
   headers. *req* is a mod_python :class:`Request` object.  If
   *cookie* is an instance of :class:`Cookie` (or subclass thereof),
   then the cookie is set, otherwise, *cookie* must be a string, in
   which case a :class:`Cookie} is constructed using *cookie* as
   name, *value* as the value, along with any valid :class:`Cookie`
   attributes specified as keyword arguments.

   This function will also set ``'Cache-Control: no-cache="set-cookie"'``
   header to inform caches that the cookie value should not be cached.

   Here is one way to use this function::

      c = Cookie.Cookie('spam', 'eggs', expires=time.time()+300)
      Cookie.add_cookie(req, c)

   Here is another:

      Cookie.add_cookie(req, 'spam', 'eggs', expires=time.time()+300)

.. function:: get_cookies(req[, Class[, data]])

   This is a convenience function for retrieving cookies from incoming
   headers. *req* is a mod_python :class:`Request` object. *Class*
   is a class whose :meth:`parse` method will be used to parse the
   cookies, it defaults to ``Cookie``. *data* can be any number of
   keyword arguments which, will be passed to :meth:`parse` (This
   is useful for :class:`signedCookie` and :class:`MarshalCookie`
   which require ``secret`` as an additional argument to
   :meth:`parse`). The set of cookies found is returned as a
   dictionary.

.. function:: get_cookie(req, name [, Class[, data]])

   This is a convenience function for retrieving a single named cookie
   from incoming headers. *req* is a mod_python :class:`Request`
   object. *name* is the name of the cookie. *Class* is a class
   whose :meth:`parse()` method will be used to parse the cookies, it
   defaults to ``Cookie``. *Data* can be any number of keyword
   arguments which, will be passed to :meth:`parse` (This is useful
   for :class:`signedCookie` and :class:`MarshalCookie` which require
   ``secret`` as an additional argument to :meth:`parse`). The cookie
   if found is returned, otherwise ``None`` is returned.

.. _pyapi-cookie-example:

Examples
--------

This example sets a simple cookie which expires in 300 seconds::

   from mod_python import Cookie, apache
   import time

   def handler(req):

       cookie = Cookie.Cookie('eggs', 'spam')
       cookie.expires = time.time() + 300
       Cookie.add_cookie(req, cookie)

       req.write('This response contains a cookie!\n')
       return apache.OK


This example checks for incoming marshal cookie and displays it to the
client. If no incoming cookie is present a new marshal cookie is set.
This example uses ``'secret007'`` as the secret for HMAC signature::

   from mod_python import apache, Cookie

   def handler(req):
    
       cookies = Cookie.get_cookies(req, Cookie.MarshalCookie,
                                       secret='secret007')
       if cookies.has_key('spam'):
           spamcookie = cookies['spam']

           req.write('Great, a spam cookie was found: %s\n' \
                                         % str(spamcookie))
           if type(spamcookie) is Cookie.MarshalCookie:
               req.write('Here is what it looks like decoded: %s=%s\n'
                         % (spamcookie.name, spamcookie.value))
           else:
               req.write('WARNING: The cookie found is not a \
                          MarshalCookie, it may have been tapered with!')

       else:

           # MarshaCookie allows value to be any marshallable object
           value = {'egg_count': 32, 'color': 'white'}
           Cookie.add_cookie(req, Cookie.MarshalCookie('spam', value, \
                          'secret007'))
           req.write('Spam cookie not found, but we just set one!\n')

       return apache.OK

.. _pyapi-sess:

:mod:`Session` -- Session Management
====================================

.. module:: Session
   :synopsis: Session Management
.. moduleauthor:: Gregory Trubetskoy grisha@modpython.org

The :mod:`Session` module provides objects for maintaining persistent
sessions across requests.

The module contains a :class:`BaseSession` class, which is not meant
to be used directly (it provides no means of storing a session),
:class:`DbmSession` class, which uses a dbm to store sessions, and
:class:`FileSession` class, which uses individual files to store
sessions.

The :class:`BaseSession` class also provides session locking, both
across processes and threads. For locking it uses APR global_mutexes
(a number of them is pre-created at startup) The mutex number is
computed by using modulus of the session id :func:`hash()`. (Therefore
it's possible that different session id's will have the same hash, but
the only implication is that those two sessions cannot be locked at
the same time resulting in a slight delay.)

.. _pyapi-sess-classes:

Classes
-------

.. function:: Session(req[, sid[, secret[, timeout[, lock]]]])

   :func:`Session()` takes the same arguments as :class:`BaseSession`.

   This function returns a instance of the default session class. The
   session class to be used can be specified using ``PythonOption mod_python.session.session_type value``, 
   where *value* is one of
   :class:`DbmSession`, :class:`MemorySession` or
   :class:`FileSession`.  Specifying custom session classes using
   ``PythonOption`` session is not yet supported.

   If session type option is not found, the function queries the MPM
   and based on that returns either a new instance of
   :class:`DbmSession` or
   :class:`MemorySession`. :class:`MemorySession` will be used if the
   MPM is threaded and not forked (such is the case on Windows), or if
   it threaded, forked, but only one process is allowed (the worker
   MPM can be configured to run this way). In all other cases
   :class:`DbmSession` is used.

   Note that on Windows if you are using multiple Python interpreter
   instances and you need sessions to be shared between applications
   running within the context of the distinct Python interpreter
   instances, you must specifically indicate that :class:`DbmSession`
   should be used, as :class:`MemorySession` will only allow a session
   to be valid within the context of the same Python interpreter
   instance.

   Also note that the option name ``mod_python.session.session_type``
   only started to be used from mod_python 3.3 onwards. If you need to
   retain compatability with older versions of mod_python, you should
   use the now obsolete ``session`` option instead.


.. class:: BaseSession(req[, sid[, secret[, timeout[, lock]]]])

   This class is meant to be used as a base class for other classes
   that implement a session storage mechanism. *req* is a required
   reference to a mod_python request object.

   :class:`BaseSession` is a subclass of :class:`dict`. Data can be
   stored and retrieved from the session by using it as a dictionary.

   *sid* is an optional session id; if provided, such a session must
   already exist, otherwise it is ignored and a new session with a new
   sid is created. If *sid* is not provided, the object will attempt
   to look at cookies for session id. If a sid is found in cookies,
   but it is not previously known or the session has expired, then a
   new sid is created. Whether a session is "new" can be determined
   by calling the :meth:`is_new()` method.

   Cookies generated by sessions will have a path attribute which is
   calculated by comparing the server ``DocumentRoot`` and the
   directory in which the ``PythonHandler`` directive currently in
   effect was specified. E.g. if document root is :file:`/a/b/c` and
   the directory ``PythonHandler`` was specified was :file:`/a/b/c/d/e`,
   the path will be set to :file:`/d/e`.
  
   The deduction of the path in this way will only work though where
   the ``Directory`` directive is used and the directory is actually
   within the document root. If the ``Location`` directive is used or
   the directory is outside of the document root, the path will be set
   to :file:`/`. You can force a specific path by setting the
   ``mod_python.session.application_path`` option 
   (``'PythonOption mod_python.session.application_path /my/path'`` in server
   configuration).

   Note that prior to mod_python 3.3, the option was
   ``ApplicationPath``.  If your system needs to be compatible with
   older versions of mod_python, you should continue to use the now
   obsolete option name.

   The domain of a cookie is by default not set for a session and as
   such the session is only valid for the host which generated it. In
   order to have a session which spans across common sub domains, you
   can specify the parent domain using the
   ``mod_python.session.application_domain`` option 
   (``'PythonOption mod_python.session.application_domain mod_python.org'`` in server
   configuration).

   When a *secret* is provided, :class:`BaseSession` will use
   :class:`SignedCookie` when generating cookies thereby making the
   session id almost impossible to fake. The default is to use plain
   :class:`Cookie` (though even if not signed, the session id is
   generated to be very difficult to guess).

   A session will timeout if it has not been accessed and a save
   performed, within the *timeout* period. Upon a save occuring the
   time of last access is updated and the period until the session
   will timeout be reset.  The default *timeout* period is 30
   minutes. An attempt to load an expired session will result in a
   "new" session.

   The *lock* argument (defaults to 1) indicates whether locking
   should be used. When locking is on, only one session object with a
   particular session id can be instantiated at a time.

   A session is in "new" state when the session id was just generated,
   as opposed to being passed in via cookies or the *sid* argument.

   .. method:: BaseSession.is_new()

      Returns 1 if this session is new. A session will also be "new"
      after an attempt to instantiate an expired or non-existent
      session. It is important to use this method to test whether an
      attempt to instantiate a session has succeeded, e.g.::


         sess = Session(req)
         if sess.is_new():
             # redirect to login
             util.redirect(req, 'http://www.mysite.com/login')


   .. method:: BaseSession.id()

      Returns the session id.


   .. method:: BaseSession.created()

      Returns the session creation time in seconds since beginning of
      epoch.

   .. method:: BaseSession.last_accessed()

      Returns last access time in seconds since beginning of epoch.


   .. method:: BaseSession.timeout()

      Returns session timeout interval in seconds.


   .. method:: BaseSession.set_timeout(secs)

      Set timeout to *secs*.


   .. method:: BaseSession.invalidate()

      This method will remove the session from the persistent store
      and also place a header in outgoing headers to invalidate the
      session id cookie.


   .. method:: BaseSession.load()

      Load the session values from storage.


   .. method:: BaseSession.save()

      This method writes session values to storage.


   .. method:: BaseSession.delete()

      Remove the session from storage.


   .. method:: BaseSession.init_lock()

      This method initializes the session lock. There is no need to
      ever call this method, it is intended for subclasses that wish
      to use an alternative locking mechanism.


   .. method:: BaseSession.lock()

     Locks this session. If the session is already locked by another
     thread/process, wait until that lock is released. There is no
     need to call this method if locking is handled automatically
     (default).

     This method registeres a cleanup which always unlocks the session
     at the end of the request processing.


   .. method:: BaseSession.unlock()

     Unlocks this session. (Same as :meth:`lock` - when locking is
     handled automatically (default), there is no need to call this
     method).


   .. method:: BaseSession.cleanup()

      This method is for subclasses to implement session storage
      cleaning mechanism (i.e. deleting expired sessions, etc.). It
      will be called at random, the chance of it being called is
      controlled by :const:`CLEANUP_CHANCE` :mod:`Session` module
      variable (default 1000). This means that cleanups will be
      ordered at random and there is 1 in 1000 chance of it
      happening. Subclasses implementing this method should not
      perform the (potentially time consuming) cleanup operation in
      this method, but should instead use
      :meth:req.register_cleanup` to register a cleanup which will
      be executed after the request has been processed.



.. class:: DbmSession(req[, dbm[, sid[, secret[, dbmtype[, timeout[, lock]]]]]])

   This class provides session storage using a dbm file. Generally,
   dbm access is very fast, and most dbm implementations memory-map
   files for faster access, which makes their performance nearly as
   fast as direct shared memory access.

   *dbm* is the name of the dbm file (the file must be writable by the
   httpd process). This file is not deleted when the server process is
   stopped (a nice side benefit of this is that sessions can survive
   server restarts). By default the session information is stored in a
   dbmfile named :file:`mp_sess.dbm` and stored in a temporary
   directory returned by ``tempfile.gettempdir()`` standard library
   function. An alternative directory can be specified using
   ``PythonOption mod_python.dbm_session.database_directory /path/to/directory``. 
   The path and filename can can be overridden by
   setting ``PythonOption mod_python.dbm_session.database_filename filename``.

   Note that the above names for the ``PythonOption`` settings were
   changed to these values in mod_python 3.3. If you need to retain
   compatability with older versions of mod_python, you should
   continue to use the now obsolete ``session_directory`` and
   ``session_dbm`` options.

   The implementation uses Python :mod:`anydbm` module, which will
   default to :mod:`dbhash` on most systems. If you need to use a
   specific dbm implementation (e.g. :mod:`gdbm`), you can pass that
   module as *dbmtype*.

   Note that using this class directly is not cross-platform. For best
   compatibility across platforms, always use the :func:`Session()`
   function to create sessions.


.. class:: FileSession(req[, sid[, secret[, timeout[, lock[, fast_cleanup[, verify_cleanup]]]]]])

   New in version 3.2.0.

   This class provides session storage using a separate file for each
   session. It is a subclass of :mod:`BaseSession`.

   Session data is stored in a separate file for each session. These
   files are not deleted when the server process is stopped, so
   sessions are persistent across server restarts.  The session files
   are saved in a directory named mp_sess in the temporary directory
   returned by the ``tempfile.gettempdir()`` standard library
   function. An alternate path can be set using 
   ``PythonOption mod_python.file_session.database_directory /path/to/directory``.
   This directory must exist and be readable and writeable by the apache process.

   Note that the above name for the ``PythonOption`` setting was
   changed to these values in mod_python 3.3. If you need to retain
   compatability with older versions of mod_python, you should
   continue to use the now obsolete ``session_directory`` option.

   Expired session files are periodically removed by the cleanup mechanism.
   The behaviour of the cleanup can be controlled using the
   *fast_cleanup* and *verify_cleanup* parameters, as well as
   ``PythonOption mod_python.file_session.cleanup_time_limit`` and
   ``PythonOption mod_python.file_session.cleanup_grace_period``.


   * *fast_cleanup*

      A boolean value used to turn on FileSession cleanup
      optimization.  Default is *True* and will result in reduced
      cleanup time when there are a large number of session files.
  
      When *fast_cleanup* is True, the modification time for the
      session file is used to determine if it is a candidate for
      deletion.  If ``(current_time - file_modification_time) > (timeout + grace_period)``, 
      the file will be a candidate for
      deletion. If *verify_cleanup* is False, no futher checks will be
      made and the file will be deleted.
    
     If *fast_cleanup* is False, the session file will unpickled and
     it's timeout value used to determine if the session is a
     candidate for deletion. *fast_cleanup* = ``False`` implies
     *verify_cleanup* = ``True``.

     The timeout used in the fast_cleanup calculation is same as the
     timeout for the session in the current request running the
     filesession_cleanup. If your session objects are not using the
     same timeout, or you are manually setting the timeout for a
     particular session with ``set_timeout()``, you will need to set
     *verify_cleanup* = ``True``.

     The value of *fast_cleanup* can also be set using
     ``PythonOption mod_python.file_session.enable_fast_cleanup``.
    
   * *verify_cleanup*

      Boolean value used to optimize the FileSession cleanup process.
      Default is ``True``.
    
      If *verify_cleanup* is True, the session file which is being 
      considered for deletion will be unpickled and its timeout value
      will be used to decide if the file should be deleted. 
    
      When *verify_cleanup* is False, the timeout value for the
      current session will be used in to determine if the session has
      expired. In this case, the session data will not be read from
      disk, which can lead to a substantial performance improvement
      when there are a large number of session files, or where each
      session is saving a large amount of data. However this may
      result in valid sessions being deleted if all the sessions are
      not using a the same timeout value.
    
      The value of *verify_cleanup* can also be set using
      ``PythonOption mod_python.file_session.verify_session_timeout``.
    
   * ``PythonOption mod_python.file_session.cleanup_time_limit [value]``
      Integer value in seconds. Default is 2 seconds.

     Session cleanup could potentially take a long time and be both
     cpu and disk intensive, depending on the number of session files
     and if each file needs to be read to verify the timeout value. To
     avoid overloading the server, each time filesession_cleanup is
     called it will run for a maximum of *session_cleanup_time_limit*
     seconds.  Each cleanup call will resume from where the previous
     call left off so all session files will eventually be checked.

     Setting *session_cleanup_time_limit* to 0 will disable this
     feature and filesession_cleanup will run to completion each time
     it is called.

   * ``PythonOption mod_python.file_session.cleanup_grace_period [value]``
     Integer value in seconds. Default is 240 seconds. This value is added
     to the session timeout in determining if a session file should be 
     deleted.
 
     There is a small chance that a the cleanup for a given session
     file may occur at the exact time that the session is being
     accessed by another request. It is possible under certain
     circumstances for that session file to be saved in the other
     request only to be immediately deleted by the cleanup. To avoid
     this race condition, a session is allowed a *grace_period* before
     it is considered for deletion by the cleanup.  As long as the
     grace_period is longer that the time it takes to complete the
     request (which should normally be less than 1 second), the
     session will not be mistakenly deleted by the cleanup.

     The default value should be sufficient for most applications.


.. class:: MemorySession(req[, sid[, secret[, timeout[, lock]]]])

   This class provides session storage using a global dictionary. This
   class provides by far the best performance, but cannot be used in a
   multi-process configuration, and also consumes memory for every
   active session. It also cannot be used where multiple Python
   interpreters are used within the one Apache process and it is
   necessary to share sessions between applications running in the
   distinct interpreters.

   Note that using this class directly is not cross-platform. For best
   compatibility across platforms, always use the :func:`Session()`
   function to create sessions.


.. _pyapi-sess-example:


Examples
--------

The following example demonstrates a simple hit counter.::

   from mod_python import Session

   def handler(req):
       session = Session.Session(req)

       try:
           session['hits'] += 1
       except:
           session['hits'] = 1

       session.save()

       req.content_type = 'text/plain'
       req.write('Hits: %d\n' % session['hits'])
       return apache.OK 


.. _pyapi-psp:

:mod:`psp` -- Python Server Pager
=================================

.. module:: psp
   :synopsis: Python Server Pages
.. moduleauthor:: Gregory Trubetskoy grisha@modpython.org


The :mod:`psp` module provides a way to convert text documents
(including, but not limited to HTML documents) containing Python code
embedded in special brackets into pure Python code suitable for
execution within a mod_python handler, thereby providing a versatile
mechanism for delivering dynamic content in a style similar to ASP,
JSP and others.

The parser used by :mod:`psp` is written in C (generated using flex)
and is therefore very fast.

See :ref:`hand-psp` for additional PSP information.

Inside the document, Python :dfn:`code` needs to be surrounded by
``'<%'`` and ``'%>'``. Python :dfn:`expressions` are enclosed in
``'<%='`` and ``'%>'``. A :dfn:`directive` can be enclosed in
``'<%@'`` and ``'%>'``. A comment (which will never be part of
the resulting code) can be enclosed in ``'<%--'`` and ``'--%>'``

Here is a primitive PSP page that demonstrated use of both code and
expression embedded in an HTML document::

   <html>
   <%
   import time
   %>
   Hello world, the time is: <%=time.strftime("%Y-%m-%d, %H:%M:%S")%>
   </html>


Internally, the PSP parser would translate the above page into the
following Python code::

   req.write("""<html>
   """)
   import time
   req.write("""
   Hello world, the time is: """); req.write(str(time.strftime("%Y-%m-%d, %H:%M:%S"))); req.write("""
   </html>
   """)

This code, when executed inside a handler would result in a page
displaying words ``'Hello world, the time is: '`` followed by current time.

Python code can be used to output parts of the page conditionally or
in loops. Blocks are denoted from within Python code by
indentation. The last indentation in Python code (even if it is a
comment) will persist through the document until either end of
document or more Python code.

Here is an example::

   <html>
   <%
   for n in range(3):
       # This indent will persist
   %>
   <p>This paragraph will be 
   repeated 3 times.</p>
   <%
   # This line will cause the block to end
   %>
   This line will only be shown once.<br>
   </html>

The above will be internally translated to the following Python code::

   req.write("""<html>
   """)
   for n in range(3):
       # This indent will persist
       req.write("""
   <p>This paragraph will be
   repeated 3 times.</p>
   """)
   # This line will cause the block to end
   req.write("""
   This line will only be shown once.<br>
   </html>
   """)

The parser is also smart enough to figure out the indent if the last
line of Python ends with ``':'`` (colon). Considering this, and that the
indent is reset when a newline is encountered inside ``'<% %>'``, the
above page can be written as::

   <html>
   <%
   for n in range(3):
   %>
   <p>This paragraph will be 
   repeated 3 times.</p>
   <%
   %>
   This line will only be shown once.<br>
   </html>

However, the above code can be confusing, thus having descriptive
comments denoting blocks is highly recommended as a good practice.

The only directive supported at this time is ``include``, here is
how it can be used::

   <%@ include file="/file/to/include"%>

If the :func:`parse` function was called with the *dir* argument, then
the file can be specified as a relative path, otherwise it has to be
absolute::

.. class:: PSP(req[, filename[, string[, vars]]])

   This class represents a PSP object.

   *req* is a request object; *filename* and *string* are optional
   keyword arguments which indicate the source of the PSP code. Only
   one of these can be specified. If neither is specified,
   ``req.filename`` is used as *filename*.

   *vars* is a dictionary of global variables. Vars passed in the
   :meth:`run` method will override vars passed in here.

   This class is used internally by the PSP handler, but can also be
   used as a general purpose templating tool.

   When a file is used as the source, the code object resulting from
   the specified file is stored in a memory cache keyed on file name
   and file modification time. The cache is global to the Python
   interpreter. Therefore, unless the file modification time changes,
   the file is parsed and resulting code is compiled only once per
   interpreter.

   The cache is limited to 512 pages, which depending on the size of
   the pages could potentially occupy a significant amount of
   memory. If memory is of concern, then you can switch to dbm file
   caching. Our simple tests showed only 20% slower performance using
   bsd db. You will need to check which implementation :mod:`anydbm`
   defaults to on your system as some dbm libraries impose a limit on
   the size of the entry making them unsuitable. Dbm caching can be
   enabled via ``mod_python.psp.cache_database_filename`` Python
   option, e.g.::

      PythonOption mod_python.psp.cache_database_filename "/tmp/pspcache.dbm"

   Note that the dbm cache file is not deleted when the server
   restarts.

   Unlike with files, the code objects resulting from a string are
   cached in memory only. There is no option to cache in a dbm file at
   this time.

   Note that the above name for the option setting was only changed to
   this value in mod_python 3.3. If you need to retain backward
   compatability with older versions of mod_python use the
   ``PSPDbmCache`` option instead.

   .. method:: PSP.run([vars[, flush]])

      This method will execute the code (produced at object
      initialization time by parsing and compiling the PSP
      source). Optional argument *vars* is a dictionary keyed by
      strings that will be passed in as global variables. Optional
      argument *flush* is a boolean flag indicating whether output
      should be flushed. The default is not to flush output.

      Additionally, the PSP code will be given global variables
      ``req``, ``psp``, ``session`` and ``form``. A session will be
      created and assigned to ``session`` variable only if ``session``
      is referenced in the code (the PSP handler examines ``co_names``
      of the code object to make that determination). Remember that a
      mere mention of ``session`` will generate cookies and turn on
      session locking, which may or may not be what you
      want. Similarly, a mod_python :class:`FieldStorage` object will
      be instantiated if ``form`` is referenced in the code.

      The object passed in ``psp`` is an instance of
      :class:`PSPInterface`.


   .. method:: PSP.display_code()

      Returns an HTML-formatted string representing a side-by-side
      listing of the original PSP code and resulting Python code
      produced by the PSP parser. 

      Here is an example of how :class:`PSP` can be used as a templating
      mechanism:
  
      The template file::

         <html>
           <!-- This is a simple psp template called template.html -->
           <h1>Hello, <%=what%>!</h1>
         </html>

      The handler code::

         from mod_python import apache, psp

         def handler(req):
             template = psp.PSP(req, filename='template.html')
             template.run({'what':'world'})
             return apache.OK

.. class:: PSPInterface()

   An object of this class is passed as a global variable ``psp`` to
   the PSP code. Objects of this class are instantiated internally and
   the interface to :meth:`__init__` is purposely undocumented.

   .. method:: set_error_page(filename)

      Used to set a psp page to be processed when an exception
      occurs. If the path is absolute, it will be appended to document
      root, otherwise the file is assumed to exist in the same directory
      as the current page. The error page will receive one additional
      variable, ``exception``, which is a 3-tuple returned by
      ``sys.exc_info()``.

   .. method:: apply_data(object[, **kw])

      This method will call the callable object *object*, passing form
      data as keyword arguments, and return the result.

   .. method:: redirect(location[, permanent=0])

      This method will redirect the browser to location
      *location*. If *permanent* is true, then
      :const:`MOVED_PERMANENTLY` will be sent (as opposed to
      :const:`MOVED_TEMPORARILY`).

      .. note::

         Redirection can only happen before any data is sent to the
         client, therefore the Python code block calling this method must
         be at the very beginning of the page. Otherwise an
         :exc:`IOError` exception will be raised.

      Example::

         <%

         # note that the '<' above is the first byte of the page!
         psp.redirect('http://www.modpython.org')
         %>

Additionally, the :mod:`psp` module provides the following low level
functions:

.. function:: parse(filename[, dir])

   This function will open file named *filename*, read and parse its
   content and return a string of resulting Python code.

   If *dir* is specified, then the ultimate filename to be parsed is
   constructed by concatenating *dir* and *filename*, and the argument
   to ``include`` directive can be specified as a relative path. (Note
   that this is a simple concatenation, no path separator will be
   inserted if *dir* does not end with one).

.. function:: parsestring(string)

   This function will parse contents of *string* and return a string
   of resulting Python code.





