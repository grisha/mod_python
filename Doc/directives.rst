
.. |br| raw:: html

   <br />

.. _directives:

*******************************
Apache Configuration Directives
*******************************

.. _dir-handlers:

Request Handlers
================

.. _dir-handlers-syn:

Python*Handler Directive Syntax
-------------------------------

.. index::
   single: Python*Handler Syntax


All request handler directives have the following syntax:

``Python*Handler handler [handler ...] [ | .ext [.ext ...] ]``

Where *handler* is a callable object that accepts a single argument -
request object, and *.ext* is an optional file extension.

Multiple handlers can be specified on a single line, in which case
they will be called sequentially, from left to right. Same handler
directives can be specified multiple times as well, with the same
result - all handlers listed will be executed sequentially, from first
to last.

If any handler in the sequence returns a value other than
``apache.OK`` or ``apache.DECLINED``, then execution of all subsequent
handlers for that phase is aborted. What happens when either
``apache.OK`` or ``apache.DECLINED`` is returned is dependent on which
phase is executing.

Note that prior to mod_python 3.3, if any handler in the sequence, no
matter which phase was executing, returned a value other than
``apache.OK``, then execution of all subsequent handlers for that phase
was aborted.

The list of handlers can optionally be followed by a ``|`` followed
by one or more file extensions. This would restrict the execution of
the handler to those file extensions only. This feature only works for
handlers executed after the trans phase.

A *handler* has the following syntax:

``module[::object]``

Where *module* can be a full module name (package dot notation is
accepted) or an actual path to a module code file. The module is loaded
using the mod_python module importer as implemented by the
``apache.import_module()`` function. Reference should be made to
the documentation of that function for further details of how module
importing is managed.

The optional *object* is the name of an object inside the module.
Object can also contain dots, in which case it will be resolved from
left to right. During resolution, if mod_python encounters an object
of type ``<class>``, it will try instantiating it passing it a single
argument, a request object.

If no object is specified, then it will default to the directive of
the handler, all lower case, with the word ``'python'``
removed. E.g. the default object for PythonAuthenHandler would be
authenhandler.

Example::

   PythonAuthzHandler mypackage.mymodule::checkallowed

For more information on handlers, see :ref:`pyapi-handler`.

.. note:: The ``'::'`` was chosen for performance reasons. In order
   for Python to use objects inside modules, the modules first need to
   be imported. Having the separator as simply a ``'.'``, would
   considerably complicate process of sequentially evaluating every
   word to determine whether it is a package, module, class etc. Using
   the (admittedly un-Python-like) ``'::'`` removes the time-consuming
   work of figuring out where the module part ends and the object
   inside of it begins, resulting in a modest performance gain.

.. index::
   pair: phase; order

The handlers in this document are listed in order in which phases are
processed by Apache.

.. _dir-handlers-pp:

Python*Handlers and Python path
-------------------------------

.. index::
   pair: pythonpath, Python*Handler

If a ``Python*Handler`` directive is specified in a *directory section*
(i.e. inside a ``<Directory></Directory>`` or
``<DirectoryMatch></DirectoryMatch>`` or in an ``.htaccess`` file),
then this directory is automatically prepended to the Python path
(``sys.path``) *unless* Python path is specified explicitely with the
``PythonPath`` directive.

If a ``Python*Handler`` directive is specified in a *location section*
(i.e. inside ``<Location></Location>`` or
``<LocationMatch></LocationMatch>``), then no path modification is done
automatically and in most cases a ``PythonPath`` directive is required
to augment the path so that the handler module can be imported.

Also for ``Python*Handlers`` inside a location section mod_python
disables the phase of the request that maps the URI to a file on the
filesystem (``ap_hook_map_to_storage``). This is because there is
usually no link between path specified in ``<Location>`` and the
filesystem, while attempting to map to a filesystem location results
in unnecessary and expensive filesystem calls. Note that an important
side-effect of this is that once a request URI has been matched to a
``<Location>`` containing a mod_python handler, all ``<Directory>``
and ``<DirectoryMatch>`` directives and their contents are ignored for
this request.

.. _dir-handlers-prrh:

PythonPostReadRequestHandler
----------------------------

.. index::
   single: PythonPostReadRequestHandler

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This handler is called after the request has been read but before any
other phases have been processed. This is useful to make decisions
based upon the input header fields.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.OK`` or ``apache.DECLINED``, then
execution of all subsequent handlers for this phase is aborted.

.. note::

   When this phase of the request is processed, the URI has not yet
   been translated into a path name, therefore this directive could
   never be executed by Apache if it could specified within
   ``<Directory>``, ``<Location>``, ``<File>`` directives or in an
   :file:`.htaccess` file. The only place this directive is allowed is
   the main configuration file, and the code for it will execute in
   the main interpreter. And because this phase happens before any
   identification of the type of content being requested is done
   (i.e. is this a python program or a gif?), the python routine
   specified with this handler will be called for *ALL* requests on
   this server (not just python programs), which is an important
   consideration if performance is a priority.



.. _dir-handlers-th:

PythonTransHandler
------------------

.. index::
   single: PythonTransHandler



`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|

This handler allows for an opportunity to translate the URI into
an actual filename, before the server's default rules (Alias
directives and the like) are followed.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.DECLINED``, then execution of all
subsequent handlers for this phase is aborted.

.. note::

   At the time when this phase of the request is being processed, the
   URI has not been translated into a path name, therefore this
   directive will never be executed by Apache if specified within
   ``<Directory>``, ``<Location>``, ``<File>`` directives or in an
   :file:`.htaccess` file. The only place this can be specified is the
   main configuration file, and the code for it will execute in the
   main interpreter.


.. _dir-handlers-hph:

PythonHeaderParserHandler
-------------------------

.. index::
   single: PythonHeaderParserHandler

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This handler is called to give the module a chance to look at the
request headers and take any appropriate specific actions early in the
processing sequence.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.OK`` or ``apache.DECLINED``, then
execution of all subsequent handlers for this phase is aborted.


.. _dir-handlers-pih:

PythonInitHandler
------------------

.. index::
   single: PythonInitHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This handler is the first handler called in the request processing
phases that is allowed both inside and outside :file`.htaccess` and
directory.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.OK`` or ``apache.DECLINED``, then
execution of all subsequent handlers for this phase is aborted.

This handler is actually an alias to two different handlers. When
specified in the main config file outside any directory tags, it is an
alias to ``PostReadRequestHandler``. When specified inside directory
(where ``PostReadRequestHandler`` is not allowed), it aliases to
``PythonHeaderParserHandler``.

\*(This idea was borrowed from mod_perl)


.. _dir-handlers-ach:

PythonAccessHandler
-------------------

.. index::
   single: PythonAccessHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This routine is called to check for any module-specific restrictions
placed upon the requested resource.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.OK`` or ``apache.DECLINED``, then
execution of all subsequent handlers for this phase is aborted.

For example, this can be used to restrict access by IP number. To do
so, you would return ``HTTP_FORBIDDEN`` or some such to indicate
that access is not allowed.

.. _dir-handlers-auh:

PythonAuthenHandler
-------------------

.. index::
   single: PythonAuthenHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This routine is called to check the authentication information sent
with the request (such as looking up the user in a database and
verifying that the [encrypted] password sent matches the one in the
database).

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.DECLINED``, then execution of all
subsequent handlers for this phase is aborted.

To obtain the username, use ``req.user``. To obtain the password
entered by the user, use the :meth:`request.get_basic_auth_pw` function.

A return of ``apache.OK`` means the authentication succeeded. A return
of ``apache.HTTP_UNAUTHORIZED`` with most browser will bring up the
password dialog box again. A return of ``apache.HTTP_FORBIDDEN`` will
usually show the error on the browser and not bring up the password
dialog ``again. HTTP_FORBIDDEN`` should be used when authentication
succeeded, but the user is not permitted to access a particular URL.

An example authentication handler might look like this::

   def authenhandler(req):

       pw = req.get_basic_auth_pw()
       user = req.user
       if user == "spam" and pw == "eggs":
           return apache.OK
       else:
           return apache.HTTP_UNAUTHORIZED

.. note::

   :meth:`request.get_basic_auth_pw` must be called prior to using the
   :attr:`request.user` value. Apache makes no attempt to decode the
   authentication information unless :meth:`request.get_basic_auth_pw` is called.


.. _dir-handlers-auzh:

PythonAuthzHandler
-------------------

.. index::
   single: PythonAuthzHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This handler runs after AuthenHandler and is intended for checking
whether a user is allowed to access a particular resource. But more
often than not it is done right in the AuthenHandler.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.DECLINED``, then execution of all
subsequent handlers for this phase is aborted.

.. _dir-handlers-tph:

PythonTypeHandler
-------------------

.. index::
   single: PythonTypeHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This routine is called to determine and/or set the various document
type information bits, like Content-type (via ``r->content_type``),
language, et cetera.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.DECLINED``, then execution of all
subsequent handlers for this phase is aborted.


.. _dir-handlers-fuh:

PythonFixupHandler
-------------------

.. index::
   single: PythonFixupHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This routine is called to perform any module-specific fixing of header
fields, et cetera. It is invoked just before any content-handler.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.OK`` or ``apache.DECLINED``, then
execution of all subsequent handlers for this phase is aborted.

.. _dir-handlers-ph:

PythonHandler
-------------

.. index::
   single: PythonHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This is the main request handler. Many applications will only provide
this one handler.

Where multiple handlers are specified, if any handler in the sequence
returns a status value other than ``apache.OK`` or
``apache.DECLINED``, then execution of subsequent handlers for the phase
are skipped and the return status becomes that for the whole content
handler phase. If all handlers are run, the return status of the final
handler is what becomes the return status of the whole content handler
phase. Where that final status is ``apache.DECLINED``, Apache will fall
back to using the ``default-handler`` and attempt to serve up the target
as a static file.

.. _dir-handlers-plh:

PythonLogHandler
----------------

.. index::
   single: PythonLogHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This routine is called to perform any module-specific logging
activities.

Where multiple handlers are specified, if any handler in the sequence
returns a value other than ``apache.OK`` or ``apache.DECLINED``, then
execution of all subsequent handlers for this phase is aborted.

.. _dir-handlers-pch:

PythonCleanupHandler
--------------------

.. index::
   single: PythonCleanupHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ *Python\*Handler Syntax* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


This is the very last handler, called just before the request object
is destroyed by Apache.

Unlike all the other handlers, the return value of this handler is
ignored. Any errors will be logged to the error log, but will not be
sent to the client, even if PythonDebug is On.

This handler is not a valid argument to the ``rec.add_handler()``
function. For dynamic clean up registration, use
``req.register_cleanup()``.

Once cleanups have started, it is not possible to register more of
them. Therefore, ``req.register_cleanup()`` has no effect within this
handler.

Cleanups registered with this directive will execute *after* cleanups
registered with ``req.register_cleanup()``.

.. _dir-filter:

Filters
=======

.. _dir-filter-if:

PythonInputFilter
-----------------

.. index::
   single: PythonInputFilter


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonInputFilter handler name |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Registers an input filter *handler* under name *name*. *Handler* is a
module name optionally followed ``::`` and a callable object name. If
callable object name is omitted, it will default to
``'inputfilter'``. *Name* is the name under which the filter is
registered, by convention filter names are usually in all caps.

The *module* referred to by the handler can be a full module name
(package dot notation is accepted) or an actual path to a module code file.
The module is loaded using the mod_python module importer as implemented by
the :func:`apache.import_module` function. Reference should be made to the
documentation of that function for further details of how module importing
is managed.

To activate the filter, use the ``AddInputFilter`` directive.

.. _dir-filter-of:

PythonOutputFilter
------------------

.. index::
   single: PythonOutputFilter


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonOutputFilter handler name |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Registers an output filter *handler* under name *name*. *handler* is a
module name optionally followed ``::`` and a callable object name. If
callable object name is omitted, it will default to
``'outputfilter'``. *name* is the name under which the filter is
registered, by convention filter names are usually in all caps.

The *module* referred to by the handler can be a full module name
(package dot notation is accepted) or an actual path to a module code file.
The module is loaded using the mod_python module importer as implemented by
the :func:`apache.import_module` function. Reference should be made to the
documentation of that function for further details of how module importing
is managed.

To activate the filter, use the ``AddOutputFilter`` directive.

.. _dir-conn:

Connection Handler
==================

.. _dir-conn-ch:

PythonConnectionHandler
-----------------------

.. index::
   single: PythonConnectionHandler


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonConnectionHandler handler |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Specifies that the connection should be handled with *handler*
connection handler. *handler* will be passed a single argument -
the connection object.

*Handler* is a module name optionally followed ``::`` and a
callable object name. If callable object name is omitted, it will
default to ``'connectionhandler'``.

The *module* can be a full module name (package dot notation is
accepted) or an absolute path to a module code file. The module is loaded
using the mod_python module importer as implemented by the
:func:`apache.import_module` function. Reference should be made to the
documentation of that function for further details of how module importing
is managed.

.. _dir-other:

Other Directives
==================

.. _dir-other-epd:

PythonEnablePdb
---------------

.. index::
   single: PythonEnablePdb


`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonEnablePdb {On, Off} |br|
`Default: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Default>`_ PythonEnablePdb Off |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


When On, mod_python will execute the handler functions within the
Python debugger pdb using the :func:`pdb.runcall` function.

Because pdb is an interactive tool, start httpd from the command line
with the ``-DONE_PROCESS`` option when using this directive. As soon as
your handler code is entered, you will see a Pdb prompt allowing you
to step through the code and examine variables.

.. _dir-other-pd:

PythonDebug
-----------

.. index::
   single: PythonDebug

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonDebug {On, Off} |br|
`Default: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Default>`_ PythonDebug Off |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Normally, the traceback output resulting from uncaught Python errors
is sent to the error log. With PythonDebug On directive specified, the
output will be sent to the client (as well as the log), except when
the error is :exc:`IOError` while writing, in which case it will go
to the error log.

This directive is very useful during the development process. It is
recommended that you do not use it production environment as it may
reveal to the client unintended, possibly sensitive security
information.

.. _dir-other-pimp:

PythonImport
------------

.. index::
   single: PythonImport

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonImport *module* *interpreter_name* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Tells the server to import the Python module module at process startup
under the specified interpreter name. The import takes place at child
process initialization, so the module will actually be imported once for
every child process spawned.

The *module* can be a full module name (package dot notation is
accepted) or an absolute path to a module code file. The module is loaded
using the mod_python module importer as implemented by the
:func:`apache.import_module` function. Reference should be made to
the documentation of that function for further details of how module
importing is managed.

The ``PythonImport`` directive is useful for initialization tasks that
could be time consuming and should not be done at the time of processing a
request, e.g. initializing a database connection. Where such initialization
code could fail and cause the importing of the module to fail, it should be
placed in its own function and the alternate syntax used:

``PythonImport *module::function* *interpreter_name*``

The named function will be called only after the module has been imported
successfully. The function will be called with no arguments.

.. note::

   At the time when the import takes place, the configuration is not
   completely read yet, so all other directives, including
   PythonInterpreter have no effect on the behavior of modules
   imported by this directive. Because of this limitation, the
   interpreter must be specified explicitly, and must match the name
   under which subsequent requests relying on this operation will
   execute. If you are not sure under what interpreter name a request
   is running, examine the :attr:`request.interpreter` member of the request
   object.

See also Multiple Interpreters.

.. _dir-other-ipd:

PythonInterpPerDirectory
------------------------

.. index::
   single: PythonInterpPerDirectory

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonInterpPerDirectory {On, Off} |br|
`Default: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Default>`_ PythonInterpPerDirectory Off |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Instructs mod_python to name subinterpreters using the directory of
the file in the request (``req.filename``) rather than the the
server name. This means that scripts in different directories will
execute in different subinterpreters as opposed to the default policy
where scripts in the same virtual server execute in the same
subinterpreter, even if they are in different directories.

For example, assume there is a
:file:`/directory/subdirectory`. :file:`/directory` has an
``.htaccess`` file with a ``PythonHandler`` directive.
:file:`/directory/subdirectory` doesn't have an ``.htaccess``. By
default, scripts in :file:`/directory` and
:file:`/directory/subdirectory` would execute in the same interpreter
assuming both directories are accessed via the same virtual
server. With ``PythonInterpPerDirectory``, there would be two
different interpreters, one for each directory.

.. note::

   In early phases of the request prior to the URI translation
   (PostReadRequestHandler and TransHandler) the path is not yet known
   because the URI has not been translated. During those phases and
   with PythonInterpPerDirectory on, all python code gets executed in
   the main interpreter. This may not be exactly what you want, but
   unfortunately there is no way around this.


.. seealso::

   :ref:`pyapi-interps`
       for more information


.. _dir-other-ipdv:

PythonInterpPerDirective
------------------------

.. index::
   single: PythonInterpPerDirective

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonInterpPerDirective {On, Off} |br|
`Default: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Default>`_ PythonInterpPerDirective Off |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Instructs mod_python to name subinterpreters using the directory in
which the Python*Handler directive currently in effect was
encountered.

For example, assume there is a
:file:`/directory/subdirectory`. :file:`/directory` has an ``.htaccess``
file with a ``PythonHandler`` directive.  :file:`/directory/subdirectory`
has another :file:`.htaccess` file with another ``PythonHandler``. By
default, scripts in :file:`/directory` and
:file:`/directory/subdirectory` would execute in the same interpreter
assuming both directories are in the same virtual server. With
``PythonInterpPerDirective``, there would be two different interpreters,
one for each directive.

.. seealso::

   :ref:`pyapi-interps`
       for more information

.. _dir-other-pi:

PythonInterpreter
-----------------

.. index::
   single: PythonInterpreter

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonInterpreter *name* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Forces mod_python to use interpreter named *name*, overriding the
default behaviour or behaviour dictated by a :ref:`dir-other-ipd` or
:ref:`dir-other-ipdv` direcive.

This directive can be used to force execution that would normally
occur in different subinterpreters to run in the same one. When
specified in the DocumentRoot, it forces the whole server to run in one
subinterpreter.

.. seealso::

   :ref:`pyapi-interps`
       for more information

.. _dir-other-phm:

PythonHandlerModule
-------------------

.. index::
   single: PythonHandlerModule

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonHandlerModule *module* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


PythonHandlerModule can be used an alternative to Python*Handler
directives. The module specified in this handler will be searched for
existence of functions matching the default handler function names,
and if a function is found, it will be executed.

For example, instead of::

   PythonAuthenHandler mymodule
   PythonHandler mymodule
   PythonLogHandler mymodule


one can simply use::

   PythonHandlerModule mymodule


.. _dir-other-par:

PythonAutoReload
----------------

.. index::
   single: PythonAutoReload

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonAutoReload {On, Off} |br|
`Default: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Default>`_ PythonAutoReload On |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


If set to Off, instructs mod_python not to check the modification date
of the module file.

By default, mod_python checks the time-stamp of the file and reloads
the module if the module's file modification date is later than the
last import or reload. This way changed modules get automatically
reimported, eliminating the need to restart the server for every
change.

Disabling autoreload is useful in production environment where the
modules do not change; it will save some processing time and give a
small performance gain.

.. _dir-other-pomz:

PythonOptimize
--------------

.. index::
   single: PythonOptimize

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonOptimize {On, Off} |br|
`Default: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Default>`_ PythonOptimize Off |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Enables Python optimization. Same as the Python ``-O`` option.

.. _dir-other-po:

PythonOption
------------

.. index::
   single: PythonOption

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonOption key [value] |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


Assigns a key value pair to a table that can be later retrieved by the
:meth:`request.get_options` function. This is useful to pass information
between the apache configuration files (:file:`httpd.conf`,
:file:`.htaccess`, etc) and the Python programs. If the value is omitted or empty (``""``),
then the key is removed from the local configuration.

Reserved PythonOption Keywords
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some ``PythonOption`` keywords are used for configuring various aspects of
mod_python. Any keyword starting with mod_python.\* should be considered
as reserved for internal mod_python use.

Users are encouraged to use their own namespace qualifiers when creating
add-on modules, and not pollute the global namespace.

The following PythonOption keys are currently used by mod_python.

| mod_python.mutex_directory
| mod_python.mutex_locks
| mod_python.psp.cache_database_filename
| mod_python.session.session_type
| mod_python.session.cookie_name
| mod_python.session.application_domain
| mod_python.session.application_path
| mod_python.session.database_directory
| mod_python.dbm_session.database_filename
| mod_python.dbm_session.database_directory
| mod_python.file_session.enable_fast_cleanup
| mod_python.file_session.verify_session_timeout
| mod_python.file_session.cleanup_grace_period
| mod_python.file_session.cleanup_time_limit
| mod_python.file_session.database_directory
| mod_python.wsgi.application
| mod_python.wsgi.base_url

| session *Deprecated in 3.3, use mod_python.session.session_type*
| ApplicationPath *Deprecated in 3.3, use mod_python.session.application_path*
| session_cookie_name *Deprecated in 3.3, use mod_python.session.cookie_name*
| session_directory *Deprecated in 3.3, use mod_python.session.database_directory*
| session_dbm *Deprecated in 3.3, use mod_python.dbm_session.database_filename*
| session_cleanup_time_limit *Deprecated in 3.3, use mod_python.file_session.cleanup_time_limit*
| session_fast_cleanup *Deprecated in 3.3, use mod_python.file_session.enable_fast_cleanup*
| session_grace_period *Deprecated in 3.3, use mod_python.file_session.cleanup_grace_period*
| session_verify_cleanup *Deprecated in 3.3, use mod_python.file_session.cleanup_session_timeout*
| PSPDbmCache *Deprecated in 3.3, use mod_python.psp.cache_database_filename*


.. _dir-other-pp:

PythonPath
----------

.. index::
   single: PythonPath

`Syntax: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Syntax>`_ PythonPath *path* |br|
`Context: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Context>`_ server config, virtual host, directory, htaccess |br|
`Override: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Override>`_ not None |br|
`Module: <http://httpd.apache.org/docs-2.4/mod/directive-dict.html#Module>`_ mod_python.c |br|


PythonPath directive sets the PythonPath. The path must be specified
in Python list notation, e.g.::

   PythonPath "['/usr/local/lib/python2.0', '/usr/local/lib/site_python', '/some/other/place']"

The path specified in this directive will replace the path, not add to
it. However, because the value of the directive is evaled, to append a
directory to the path, one can specify something like::

   PythonPath "sys.path+['/mydir']"

Mod_python tries to minimize the number of evals associated with the
PythonPath directive because evals are slow and can negatively impact
performance, especially when the directive is specified in an
:file:`.htaccess` file which gets parsed at every hit. Mod_python will
remember the arguments to the PythonPath directive in the un-evaled
form, and before evaling the value it will compare it to the
remembered value. If the value is the same, no action is
taken. Because of this, you should not rely on the directive as a way
to restore the pythonpath to some value if your code changes it.

When multiple PythonPath directives are specified, the effect is not
cumulative, last directive will override all previous ones.

.. note::

   This directive should not be used as a security measure since the
   Python path is easily manipulated from within the scripts.









