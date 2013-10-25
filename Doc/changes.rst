
.. _changes:

*******
Changes
*******

.. _changes_from_3_4_1:

Changes from version 3.4.1
==========================

New Features
------------

* Support for Python 3.3

Improvements
------------

* Simpler, faster and up-to-date with latest Python code for creating/maintaining interpreter and thread state.
* A much faster WSGI implementation (start_response now implemented in C)

.. _changes_from_3_3_1:

Changes from version 3.3.1
==========================

New Features
------------

* Create the mod_python command-line tool to report version, manage Apache configuration and instances.
* Make httpdconf directives render themselves as Python, add the only_if conditional and comments.
* Expose and document httpdconf, make mod_python importable outside of Apache.
* Provide a WSGI handler.
* Change the Copyright to reflect the new status.
* Add support for Apache HTTP Server 2.4.
* Add support for Python 2.7.

Improvements
------------

* Improve WSGI and Python path documentation.
* Change WSGI handler to use Location path as SCRIPT_NAME.
* Add is_location to hlist object, skip the map_to_storage for Location-wrapped Python*Handlers.
* Some optimizations to Python code to make it run faster.
* Add Mutex to Apache 2.4 tests.
* Provide and internal add_cgi_vars() implementation which does not use sub-requests.
* Many documentation clarifications and improvements.
* Add a test to ensure that req.write() and req.flush() do not leak memory (2.4 only).
* Many new tests and test framework improvements.
* Added a curl hint to the tests for easier stagin/debugging.
* Get rid of the ancient memberlist and PyMember_Get/Set calls.
* Add support for the c.remote_ip/addr to c.client_ip/addr change in 2.4. Add req.useragent_addr (also new in 2.4).
* Always check C version against Py version and warn.
* Remove APLOG_NOERRNO references.
* A more unified and cleaned up method of keeping version information.
* Convert documentation to the new reStructuredText format.
* Revert to using the old importer from 3.2.
* Replace README with README.md
* (`MODPYTHON-238 <http://issues.apache.org/jira/browse/MODPYTHON-238>`_) Make req.chunked and req.connection.keepalive writable. Being able to set these allows chunking to be turned off when HTTP/1.1 is used but no content length supplied in response.
* (`MODPYTHON-226 <http://issues.apache.org/jira/browse/MODPYTHON-226>`_) Make req.status_line writable.

Bug Fixes
---------

* Make PythonCleanupHandler run again.
* Use PCapsule API instead of PyCObject for Python 2.7+.
* Fix SCRIPT_NAME and PATH_INFO inconsistencies so that the WSGI handler behaves correctly.
* Remove with-python-src configure option as it is no longer used to build the docs.
* (`MODPYTHON-243 <http://issues.apache.org/jira/browse/MODPYTHON-243>`_) Fixed format string error.
* (`MODPYTHON-250 <http://issues.apache.org/jira/browse/MODPYTHON-250>`_) Fixed MacOS X (10.5) Leopard 64 bit architecture problems.
* (`MODPYTHON-249 <http://issues.apache.org/jira/browse/MODPYTHON-249>`_) Fixed incorrect use of APR bucket brigades shown up by APR 1.3.2.
* (`MODPYTHON-245 <http://issues.apache.org/jira/browse/MODPYTHON-245>`_) Fix prototype of optional exported function mp_release_interpreter().
* (`MODPYTHON-220 <http://issues.apache.org/jira/browse/MODPYTHON-220>`_) Fix 'import' from same directory as PSP file.

.. _changes_from_3_2_10:

Changes from version 3.2.10
===========================

New Features
------------

* (`MODPYTHON-103 <http://issues.apache.org/jira/browse/MODPYTHON-103>`_) New req.add_output_filter(), req.add_input_filter(), req.register_output_fiter(), req.register_input_filter() methods. These allows the dynamic registration of filters and the attaching of filters to the current request.
* (`MODPYTHON-104 <http://issues.apache.org/jira/browse/MODPYTHON-104>`_) Support added for using Python in content being passed through "INCLUDES" output filter, or as more commonly referred to server side include (SSI) mechanism.
* (`MODPYTHON-108 <http://issues.apache.org/jira/browse/MODPYTHON-108>`_) Added support to cookies for httponly attribute, an extension originally created by Microsoft, but now getting more widespread use in the battle against cross site-scripting attacks.
* (`MODPYTHON-118 <http://issues.apache.org/jira/browse/MODPYTHON-118>`_) Now possible using the PythonImport directive to specify the name of a function contained in the module to be called once the designated module has been imported.
* (`MODPYTHON-124 <http://issues.apache.org/jira/browse/MODPYTHON-124>`_) New req.auth_name() and req.auth_type() methods. These return the values associated with the AuthName and AuthType directives respectively. The req.ap_auth_type has now also been made writable so that it can be set by an authentication handler.
* (`MODPYTHON-130 <http://issues.apache.org/jira/browse/MODPYTHON-130>`_) Added req.set_etag(), req.set_last_modified() and req.update_mtime() functions as wrappers for similar functions provided by Apache C API. These are required to effectively use the req.meets_condition() function. The documentation for req.meets_condition() has also been updated as what it previously described probably wouldn't actually work.
* (`MODPYTHON-132 <http://issues.apache.org/jira/browse/MODPYTHON-132>`_) New req.construct_url() method. Used to construct a fully qualified URI string incorporating correct scheme, server and port.
* (`MODPYTHON-144 <http://issues.apache.org/jira/browse/MODPYTHON-144>`_) The "apache.interpreter" and "apache.main_server" attributes have been made publically available. These were previously private and not part of the public API.
* (`MODPYTHON-149 <http://issues.apache.org/jira/browse/MODPYTHON-149>`_) Added support for session objects that span domains.
* (`MODPYTHON-153 <http://issues.apache.org/jira/browse/MODPYTHON-153>`_) Added req.discard_request_body() function as wrapper for similar function provided by Apache C API. The function tests for and reads any message body in the request, simply discarding whatever it receives.
* (`MODPYTHON-164 <http://issues.apache.org/jira/browse/MODPYTHON-164>`_) The req.add_handler(), req.register_input_filter() and req.register_output_filter() methods can now take a direct reference to a callable object as well a string which refers to a module or module::function combination by name.
* (`MODPYTHON-165 <http://issues.apache.org/jira/browse/MODPYTHON-165>`_) Exported functions from mod_python module to be used in other third party modules for Apache. The purpose of these functions is to allow those other modules to access the mechanics of how mod_python creates interpreters, thereby allowing other modules to also embed Python and for there not to be a conflict with mod_python.
* (`MODPYTHON-170 <http://issues.apache.org/jira/browse/MODPYTHON-170>`_) Added req._request_rec, server._server_rec and conn._conn_rec semi private members for getting accessing to underlying Apache struct as a Python CObject. These can be used for use in implementing SWIG bindings for lower level APIs of Apache. These members should be regarded as experimental and there are no guarantees that they will remain present in this specific form in the future.
* (`MODPYTHON-193 <http://issues.apache.org/jira/browse/MODPYTHON-193>`_) Added new attribute available as req.hlist.location. For a handler executed directly as the result of a handler directive within a Location directive, this will be set to the value of the Location directive. If LocationMatch, or wildcards or regular expressions are used with Location, the value will be the matched value in the URL and not the pattern.

Improvements
------------

* (`MODPYTHON-27 <http://issues.apache.org/jira/browse/MODPYTHON-27>`_) When using mod_python.publisher, the __auth__() and __access__() functions and the __auth_realm__ string can now be nested within a class method as a well a normal function.
* (`MODPYTHON-90 <http://issues.apache.org/jira/browse/MODPYTHON-90>`_) The PythonEnablePdb configuration option will now be ignored if Apache hasn't been started up in single process mode.
* (`MODPYTHON-91 <http://issues.apache.org/jira/browse/MODPYTHON-91>`_) If running Apache in single process mode with PDB enabled and the "quit" command is used to exit that debug session, an exception indicating that the PDB session has been aborted is raised rather than None being returned with a subsequent error complaining about the handler returning an invalid value.
* (`MODPYTHON-93 <http://issues.apache.org/jira/browse/MODPYTHON-93>`_) Improved util.FieldStorage efficiency and made the interface more dictionary like.
* (`MODPYTHON-101 <http://issues.apache.org/jira/browse/MODPYTHON-101>`_) Force an exception when handler evaluates to something other than None but is otherwise not callable. Previously an exception would not be generated if the handler evaluated to False.
* (`MODPYTHON-107 <http://issues.apache.org/jira/browse/MODPYTHON-107>`_) Neither mod_python.publisher nor mod_python.psp explicitly flush output after writing the content of the response back to the request object. By not flushing output it is now possible to use the "CONTENT_LENGTH" output filter to add a "Content-Length" header.
* (`MODPYTHON-111 <http://issues.apache.org/jira/browse/MODPYTHON-111>`_) Note made in session documentation that a save is required to avoid session timeouts.
* (`MODPYTHON-125 <http://issues.apache.org/jira/browse/MODPYTHON-125>`_) The req.handler attribute is now writable. This allows a handler executing in a phase prior to the response phase to specify which Apache module will be responsible for generating the content.
* (`MODPYTHON-128 <http://issues.apache.org/jira/browse/MODPYTHON-128>`_) Made the req.canonical_filename attribute writable. Changed the req.finfo attribute from being a tuple to an actual object. For backwards compatibility the attributes of the object can still be accessed as if they were a tuple. New code however should access the attributes as member data. The req.finfo attribute is also now writable and can be assigned to using the result of calling the new function apache.stat(). This function is a wrapper for apr_stat().
* (`MODPYTHON-129 <http://issues.apache.org/jira/browse/MODPYTHON-129>`_) When specifying multiple handlers for a phase, the status returned by each handler is now treated the same as how Apache would treat the status if the handler was registered using the low level C API. What this means is that whereas stacked handlers of any phase would in turn previously be executed as long as they returned apache.OK, this is no longer the case and what happens is dependent on the phase. Specifically, a handler returning apache.DECLINED no longer causes the execution of subsequent handlers for the phase to be skipped. Instead, it will move to the next of the stacked handlers. In the case of PythonTransHandler, PythonAuthenHandler, PythonAuthzHandler and PythonTypeHandler, as soon as apache.OK is returned, subsequent handlers for the phase will be skipped, as the result indicates that any processing pertinent to that phase has been completed. For other phases, stacked handlers will continue to be executed if apache.OK is returned as well as when apache.DECLINED is returned. This new interpretation of the status returned also applies to stacked content handlers listed against the PythonHandler directive even though Apache notionally only ever calls at most one content handler. Where all stacked content handlers in that phase run, the status returned from the last handler becomes the overall status from the content phase.
* (`MODPYTHON-141 <http://issues.apache.org/jira/browse/MODPYTHON-141>`_) The req.proxyreq and req.uri attributes are now writable. This allows a handler to setup these values and trigger proxying of the current request to a remote server.
* (`MODPYTHON-142 <http://issues.apache.org/jira/browse/MODPYTHON-142>`_) The req.no_cache and req.no_local_copy attributes are now writable.
* (`MODPYTHON-143 <http://issues.apache.org/jira/browse/MODPYTHON-143>`_) Completely reimplemented the module importer. This is now used whenever modules are imported corresponding to any of the Python*Handler, Python*Filter and PythonImport directives. The module importer is still able to be used directly using the apache.import_module() function. The new module importer no longer supports automatic reloading of packages/modules that appear on the standard Python module search path as defined by the PythonPath directive or within an application by direct changes to sys.path. Automatic module reloading is however still performed on file based modules (not packages) which are located within the document tree where handlers are located. Locations within the document tree are however no longer added to the standard Python module search path automatically as they are maintained within a distinct importer search path. The PythonPath directive MUST not be used to point at directories within the document tree. To have additional directories be searched by the module importer, they should be listed in the mod_python.importer.path option using the PythonOption directive. This is a path similar to how PythonPath argument is supplied, but MUST not reference sys.path nor contain any directories also listed in the standard Python module search path. If an application does not appear to work under the module importer, the old module importer can be reenabled by setting the mod_python.legacy.importer option using the PythonOption directive to the value '*'. This option must be set in the global Apache configuration.
* (`MODPYTHON-152 <http://issues.apache.org/jira/browse/MODPYTHON-152>`_) When in a sub request, when a request is the result of an internal redirect, or when when returning from such a request, the req.main, req.prev and req.next members now correctly return a reference to the original Python request object wrapper first created for the specific request_rec instance rather than creating a new distinct Python request object. This means that any data added explicitly to a request object can be passed between such requests.
* (`MODPYTHON-178 <http://issues.apache.org/jira/browse/MODPYTHON-178>`_) When using mod_python.psp, if the PSP file which is the target of the request doesn't actually exist, an apache.HTTP_NOT_FOUND server error is now returned to the client rather than raising a ValueError exception which results in a 500 internal server error. Note that if using SetHandler and the request is against the directory and no DirectoryIndex directive is specified which lists a valid PSP index file, then the same apache.HTTP_NOT_FOUND server error is returned to the client.
* (`MODPYTHON-196 <http://issues.apache.org/jira/browse/MODPYTHON-196>`_) For completeness, added req.server.log_error() and req.connection.log_error(). The latter wraps ap_log_cerror() (when available), allowing client information to be logged along with message from a connection handler.
* (`MODPYTHON-206 <http://issues.apache.org/jira/browse/MODPYTHON-206>`_) The attribute req.used_path_info is now modifiable and can be set from within handlers. This is equivalent to having used the AcceptPathInfo directive.
* (`MODPYTHON-207 <http://issues.apache.org/jira/browse/MODPYTHON-207>`_) The attribute req.args is now modifiable and can be set from within handlers.

Bug Fixes
---------

* (`MODPYTHON-38 <http://issues.apache.org/jira/browse/MODPYTHON-38>`_) Fixed issue when using PSP pages in conjunction with publisher handler or where a PSP error page was being triggered, that form parameters coming from content of a POST request weren't available or only available using a workaround. Specifically, the PSP page will now use any FieldStorage object instance cached as req.form left there by preceding code.
* (`MODPYTHON-43 <http://issues.apache.org/jira/browse/MODPYTHON-43>`_) Nested __auth__() functions in mod_python.publisher now execute in context of globals from the file the function is in and not that of mod_python.publisher itself.
* (`MODPYTHON-47 <http://issues.apache.org/jira/browse/MODPYTHON-47>`_) Fixed mod_python.publisher so it will not return a HTTP Bad Request response when mod_auth is being used to provide Digest authentication.
* (`MODPYTHON-63 <http://issues.apache.org/jira/browse/MODPYTHON-63>`_) When handler directives are used within Directory or DirectoryMatch directives where wildcards or regular expressions are used, the handler directory will be set to the shortest directory matched by the directory pattern. Handler directives can now also be used within Files and FilesMatch directives and the handler directory will correctly resolve to the directory corresponding to the enclosing Directory or DirectoryMatch directive, or the directory the .htaccess file is contained in.
* (`MODPYTHON-76 <http://issues.apache.org/jira/browse/MODPYTHON-76>`_) The FilterDispatch callback should not flush the filter if it has already been closed.
* (`MODPYTHON-84 <http://issues.apache.org/jira/browse/MODPYTHON-84>`_) The original change to fix the symlink issue for req.sendfile() was causing problems on Win32, plus code needed to be changed to work with APR 1.2.7.
* (`MODPYTHON-100 <http://issues.apache.org/jira/browse/MODPYTHON-100>`_) When using stacked handlers and a SERVER_RETURN exception was used to return an OK status for that handler, any following handlers weren't being run if appropriate for the phase.
* (`MODPYTHON-109 <http://issues.apache.org/jira/browse/MODPYTHON-109>`_) The Py_Finalize() function was being called on child process shutdown. This was being done though from within the context of a signal handler, which is generally unsafe and would cause the process to lock up. This function is no longer called on child process shutdown.
* (`MODPYTHON-112 <http://issues.apache.org/jira/browse/MODPYTHON-112>`_) The req.phase attribute is no longer overwritten by an input or output filter. The filter.is_input member should be used to determine if a filter is an input or output filter.
* (`MODPYTHON-113 <http://issues.apache.org/jira/browse/MODPYTHON-113>`_) The PythonImport directive now uses the apache.import_module() function to import modules to avoid reloading problems when same module is imported from a handler.
* (`MODPYTHON-114 <http://issues.apache.org/jira/browse/MODPYTHON-114>`_) Fixed race conditions on setting sys.path when the PythonPath directive is being used as well as problems with infinite extension of path.
* (`MODPYTHON-120 <http://issues.apache.org/jira/browse/MODPYTHON-120>`_) (`MODPYTHON-121 <http://issues.apache.org/jira/browse/MODPYTHON-121>`_) Fixes to test suite so it will work on virtual hosting environments where localhost doesn't resolve to 127.0.0.1 but the actual IP address of the host.
* (`MODPYTHON-126 <http://issues.apache.org/jira/browse/MODPYTHON-126>`_) When Python*Handler or Python*Filter directive is used inside of a Files directive container, the handler/filter directory value will now correctly resolve to the directory corresponding to any parent Directory directive or the location of the .htaccess file the Files directive is contained in.
* (`MODPYTHON-133 <http://issues.apache.org/jira/browse/MODPYTHON-133>`_) The table object returned by req.server.get_config() was not being populated correctly to be the state of directives set at global scope for the server.
* (`MODPYTHON-134 <http://issues.apache.org/jira/browse/MODPYTHON-134>`_) Setting PythonDebug to Off, wasn't overriding On setting in parent scope.
* (`MODPYTHON-140 <http://issues.apache.org/jira/browse/MODPYTHON-140>`_) The util.redirect() function should be returning server status of apache.DONE and not apache.OK otherwise it will not give desired result if used in non content handler phase or where there are stacked content handlers.
* (`MODPYTHON-147 <http://issues.apache.org/jira/browse/MODPYTHON-147>`_) Stopped directories being added to sys.path multiple times when PythonImport and PythonPath directive used.
* (`MODPYTHON-148 <http://issues.apache.org/jira/browse/MODPYTHON-148>`_) Added missing Apache contants apache.PROXYREQ_RESPONSE and apache.HTTP_UPGRADE_REQUIRED. Also added new constants for Apache magic mime types and values for interpreting the req.connection.keepalive and req.read_body members.
* (`MODPYTHON-150 <http://issues.apache.org/jira/browse/MODPYTHON-150>`_) In a multithread MPM, the apache.init() function could be called more than once for a specific interpreter instance whereas it should only be called once.
* (`MODPYTHON-151 <http://issues.apache.org/jira/browse/MODPYTHON-151>`_) Debug error page returned to client when an exception in a handler occurred wasn't escaping special HTML characters in the traceback or the details of the exception.
* (`MODPYTHON-157 <http://issues.apache.org/jira/browse/MODPYTHON-157>`_) Wrong interpreter name used for fixup handler phase and earlier, when PythonInterpPerDirectory was enabled and request was against a directory but client didn't provide the trailing slash.
* (`MODPYTHON-159 <http://issues.apache.org/jira/browse/MODPYTHON-159>`_) Fix FieldStorage class so that it can handle multiline headers.
* (`MODPYTHON-160 <http://issues.apache.org/jira/browse/MODPYTHON-160>`_) Using PythonInterpPerDirective when setting content handler to run dynamically with req.add_handler() would cause Apache to crash.
* (`MODPYTHON-161 <http://issues.apache.org/jira/browse/MODPYTHON-161>`_) Directory argument supplied to req.add_handler() is canonicalized and a trailing slash added automatically. This is needed to ensure that the directory is always in POSIX path style as used by Apache and that convention where directories associated with directives always have trailing slash is adhered to. If this is not done, a different interpreter can be chosen to that expected when the PythonInterpPerDirective is used.
* (`MODPYTHON-166 <http://issues.apache.org/jira/browse/MODPYTHON-166>`_) PythonHandlerModule was not setting up registration of the PythonFixupHandler or PythonAuthenHandler. For the latter this meant that using Require directive with PythonHandlerModule would cause a 500 error and complaint in error log about "No groups file".
* (`MODPYTHON-167 <http://issues.apache.org/jira/browse/MODPYTHON-167>`_) When PythonDebug was On and and exception occurred, the response to the client had a status of 200 when it really should have been a 500 error status indicating that an internal error occurred. A 500 error status was correctly being returned when PythonDebug was Off.
* (`MODPYTHON-168 <http://issues.apache.org/jira/browse/MODPYTHON-168>`_) Fixed psp_parser error when CR is used as a line terminator in psp code. This may occur with some older editors such as GoLive on Mac OS X.
* (`MODPYTHON-175 <http://issues.apache.org/jira/browse/MODPYTHON-175>`_) Fixed problem whereby a main PSP page and an error page triggered from that page both accessing the session object would cause a deadlock.
* (`MODPYTHON-176 <http://issues.apache.org/jira/browse/MODPYTHON-176>`_) Fixed issue whereby PSP code would unlock session object which it had inherited from the caller meaning caller could no longer use it safely. PSP code will now only unlock session if it created it in the first place.
* (`MODPYTHON-179 <http://issues.apache.org/jira/browse/MODPYTHON-179>`_) Fixed the behaviour of req.readlines() when a size hint was provided. Previously, it would always return a single line when a size hint was provided.
* (`MODPYTHON-180 <http://issues.apache.org/jira/browse/MODPYTHON-180>`_) Publisher would wrongly output a warning about nothing to publish if req.write() or req.sendfile() used and data not flushed, and then published function returned None.
* (`MODPYTHON-181 <http://issues.apache.org/jira/browse/MODPYTHON-181>`_) Fixed memory leak when mod_python handlers are defined for more than one phase at the same time.
* (`MODPYTHON-182 <http://issues.apache.org/jira/browse/MODPYTHON-182>`_) Fixed memory leak in req.readline().
* (`MODPYTHON-184 <http://issues.apache.org/jira/browse/MODPYTHON-184>`_) Fix memory leak in apache.make_table(). This was used by util.FieldStorage class so affected all code using forms.
* (`MODPYTHON-185 <http://issues.apache.org/jira/browse/MODPYTHON-185>`_) Fixed segfault in psp.parsestring(src_string) when src_string is empty.
* (`MODPYTHON-187 <http://issues.apache.org/jira/browse/MODPYTHON-187>`_) Table objects could crash in various ways when the value of an item was NULL. This could occur for SCRIPT_FILENAME when the req.subprocess_env table was accessed in the post read request handler phase.
* (`MODPYTHON-189 <http://issues.apache.org/jira/browse/MODPYTHON-189>`_) Fixed representation returned by calling repr() on a table object.
* (`MODPYTHON-191 <http://issues.apache.org/jira/browse/MODPYTHON-191>`_) Session class will no longer accept a normal cookie if a signed cookie was expected.
* (`MODPYTHON-194 <http://issues.apache.org/jira/browse/MODPYTHON-194>`_) Fixed potential memory leak due to not clearing the state of thread state objects before deleting them.
* (`MODPYTHON-195 <http://issues.apache.org/jira/browse/MODPYTHON-195>`_) Fix potential Win32 resource leaks in parent Apache process when process restarts occur.
* (`MODPYTHON-198 <http://issues.apache.org/jira/browse/MODPYTHON-198>`_) Python 2.5 broke nested __auth__/__access__/__auth_realm__ in mod_python.publisher.
* (`MODPYTHON-200 <http://issues.apache.org/jira/browse/MODPYTHON-200>`_) Fixed problem whereby signed and marshalled cookies could not be used at the same time. When expecting marshalled cookie, any signed, but not marshalled cookies will be returned as normal cookies.


.. _changes_from_3_2_8:

Changes from version 3.2.8
==========================

New Features
------------

* (`MODPYTHON-78 <http://issues.apache.org/jira/browse/MODPYTHON-78>`_) Added support for Apache 2.2.
* (`MODPYTHON-94 <http://issues.apache.org/jira/browse/MODPYTHON-94>`_) New req.is_https() and req.ssl_var_lookup() methods. These communicate direct with the Apache mod_ssl module, allowing it to be determined if the connection is using SSL/TLS and what the values of internal ssl variables are.
* (`MODPYTHON-131 <http://issues.apache.org/jira/browse/MODPYTHON-131>`_) The directory used for mutex locks can now be specified at at compile time using ./configure --with-mutex-dir value or at run time with PythonOption mod_python.mutex_directory value.
* (`MODPYTHON-137 <http://issues.apache.org/jira/browse/MODPYTHON-137>`_) New req.server.get_options() method. This returns the subset of Python options set at global scope within the Apache configuration. That is, outside of the context of any VirtualHost, Location, Directory or Files directives.
* (`MODPYTHON-145 <http://issues.apache.org/jira/browse/MODPYTHON-145>`_) The number of mutex locks can now be specified at run time with PythonOption mod_python.mutex_locks value.
* (`MODPYTHON-172 <http://issues.apache.org/jira/browse/MODPYTHON-172>`_) Fixed three memory leaks that were found in _apachemodule.parse_qsl, req.readlines and util.cfgtree_walk.

Improvements
------------

* (`MODPYTHON-77 <http://issues.apache.org/jira/browse/MODPYTHON-77>`_) Third party C modules that use the simplified API for the Global Interpreter Lock (GIL), as described in PEP 311, can now be used. The only requirement is that such modules can only be used in the context of the "main_interpreter".
* (`MODPYTHON-119 <http://issues.apache.org/jira/browse/MODPYTHON-119>`_) DbmSession unit test no longer uses the default directory for the dbm file, so the test will not interfer with the user's current apache instance.
* (`MODPYTHON-158 <http://issues.apache.org/jira/browse/MODPYTHON-158>`_) Added additional debugging and logging output for where mod_python cannot initialise itself properly due to Python or mod_python version mismatches or missing Python module code files.

Bug Fixes
---------

* (`MODPYTHON-84 <http://issues.apache.org/jira/browse/MODPYTHON-84>`_) Fixed request.sendfile() bug for symlinked files on Win32.
* (`MODPYTHON-122 <http://issues.apache.org/jira/browse/MODPYTHON-122>`_) Fixed configure problem when using bash 3.1.x.
* (`MODPYTHON-173 <http://issues.apache.org/jira/browse/MODPYTHON-173>`_) Fixed DbmSession to create db file with mode 0640.


.. _changes_from_3_2_7:

Changes from version 3.2.7
==========================

Security Fix
------------

* (`MODPYTHON-135 <http://issues.apache.org/jira/browse/MODPYTHON-135>`_) Fixed possible directory traversal attack in FileSession. The session id is now checked to ensure it only contains valid characters. This check is performed for all sessions derived from the BaseSession class.

.. _changes_from_3_1_4:

Changes from version 3.1.4
==========================

New Features
------------

* New apache.register_cleanup() method.
* New apache.exists_config_define() method.
* New file-based session manager class.
* Session cookie name can be specified.
* The maximum number of mutexes mod_python uses for session locking can now be specifed at compile time using configure --with-max-locks.
* New a version attribute in mod_python module.
* New test handler testhandler.py has been added.

Improvements
------------

* Autoreload of a module using apache.import_module() now works if modification time for the module is different from the file. Previously, the module was only reloaded if the the modification time of the file was more recent. This allows for a more graceful reload if a file with an older modification time needs to be restored from backup.
* Fixed the publisher traversal security issue
* Objects hierarchy a la CherryPy can now be published.
* mod_python.c now logs reason for a 500 error
* Calls to PyErr_Print in mod_python.c are now followed by fflush()
* Using an empty value with PythonOption will unset a PythonOption key.
* req.path_info is now a read/write member.
* Improvements to FieldStorage allow uploading of large files. Uploaded files are now streamed to disk, not to memory.
* Path to flex is now discovered at configuration time or can be specifed using configure --with-flex=/path/to/flex.
* sys.argv is now initialized to ["mod_python"] so that modules like numarray and pychart can work properly.

Bug Fixes
---------

* Fixed memory leak which resulted from circular references starting from the request object.
* Fixed memory leak resulting from multiple PythonOption directives.
* Fixed Multiple/redundant interpreter creation problem.
* Cookie attributes with attribute names prefixed with $ are now ignored. See Section 4.7 for more information.
* Bug in setting up of config_dir from Handler directives fixed.
* mod_python.publisher will now support modules with the same name but in different directories
* Fixed continual reloading of modules problem
* Fixed big marshalled cookies error.
* Fixed mod_python.publisher extension handling
* mod_python.publisher default index file traversal
* mod_python.publisher loading wrong module and giving no warning/error
* apply_fs_data() now works with "new style" objects
* File descriptor fd closed after ap_send_fd() in req_sendfile()
* Bug in mem_cleanup in MemorySession fixed.
* Fixed bug in _apache._global_lock() which could cause a segfault if the lock index parameter is greater number of mutexes created at mod_python startup.
* Fixed bug where local_ip and local_host in connection object were returning remote_ip and remote_host instead
* Fixed install_dso Makefile rule so it only installs the dso, not the python files
* Potential deadlock in psp cache handling fixed
* Fixed bug where sessions are used outside <Directory> directive.
* Fixed compile problem on IRIX. ln -s requires both TARGET and LINK_NAME on IRIX. ie. ln -s TARGET LINK_NAME
* Fixed ./configure problem on SuSE Linux 9.2 (x86-64). Python libraries are in lib64/ for this platform.
* Fixed req.sendfile() problem where sendfile(filename) sends the incorrect number of bytes when filename is a symlink.
* Fixed problem where util.FieldStorage was not correctly checking the mime types of POSTed entities
* Fixed conn.local_addr and conn.remote_addr for a better IPv6 support.
* Fixed psp_parser.l to properly escape backslash-n, backslash-t and backslash-r character sequences.
* Fixed segfault bug when accessing some request object members (allowed_methods, allowed_xmethods, content_languages) and some server object members (names, wild_names).
* Fixed request.add_handler() segfault bug when adding a handler to an empty handler list.
* Fixed PythonAutoReload directive so that AutoReload can be turned off.
* Fixed connection object read() bug on FreeBSD.
* Fixed potential buffer corruption bug in connection object read().

.. _changes_from_2_x:

Changes from version 2.x
========================

* Mod_python 3.0 no longer works with Apache 1.3, only Apache 2.x is supported.
* Mod_python no longer works with Python versions less than 2.2.1
* Mod_python now supports Apache filters.
* Mod_python now supports Apache connection handlers.
* Request object supports internal_redirect().
* Connection object has read(), readline() and write().
* Server object has get_config().
* Httpdapi handler has been deprecated.
* Zpublisher handler has been deprecated.
* Username is now in req.user instead of req.connection.user
