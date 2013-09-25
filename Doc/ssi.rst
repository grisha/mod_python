.. _ssi:

********************
Server Side Includes
********************

.. _ssi-overview:

Overview of SSI
===============

SSI (Server Side Includes) are directives that are placed in HTML pages,
and evaluated on the server while the pages are being served. They let you
add dynamically generated content to an existing HTML page, without having
to serve the entire page via a CGI program, or other dynamic technology
such as a mod_python handler.

SSI directives have the following syntax:::

   <!--#element attribute=value attribute=value ... -->


It is formatted like an HTML comment, so if you don't have SSI correctly
enabled, the browser will ignore it, but it will still be visible in the
HTML source. If you have SSI correctly configured, the directive will be
replaced with its results.

For a more thorough description of the SSI mechanism and how to enable it,
see the `SSI tutorial <http://httpd.apache.org/docs/2.0/howto/ssi.html>`_
provided with the Apache documentation.

Version 3.3 of mod_python introduces support for using Python code within
SSI files. Note that mod_python honours the intent of the Apache
``IncludesNOEXEC`` option to the ``Options`` directive. That is, if
``IncludesNOEXEC`` is enabled, then Python code within a SSI file will
not be executed.


.. _ssi-python-code:

Using Python Code
=================

The extensions to mod_python to allow Python code to be used in conjunction
with SSI introduces the new SSI directive called ``'python'``. This directive
can be used in two forms, these being ``'eval'`` and ``'exec'`` modes. In the case
of ``'eval'``, a Python expression is used and it is the result of that
expression which is substituted in place into the page.::

   <!--#python eval="10*'HELLO '" -->
   <!--#python eval="len('HELLO')" -->


Where the result of the expression is not a string, the value will be
automatically converted to a string by applying ``'str()'`` to the value.

In the case of ``'exec'`` a block of Python code may be included. For any
output from this code to appear in the page, it must be written back
explicitly as being part of the response. As SSI are processed by an Apache
output filter, this is done by using an instance of the mod_python
``filter`` object which is pushed into the global data set available to
the code.::

   <!--#python exec="
   filter.write(10*'HELLO ')
   filter.write(str(len('HELLO')))
   " -->

Any Python code within the ``'exec'`` block must have a zero first level
indent. You cannot start the code block with an arbitrary level of indent
such that it lines up with any indenting used for surrounding HTML
elements.

Although the mod_python ``filter`` object is not a true file object, that
it provides the ``write()`` method is sufficient to allow the ``print``
statement to be used on it directly. This will avoid the need to explicitly
convert non string objects to a string before being output.::

   <!--#python exec="
   print >> filter, len('HELLO')
   " -->


.. _ssi-data-scope:

Scope of Global Data
====================

Multiple instances of ``'eval'`` or ``'exec'`` code blocks may be used within the
one page. Any changes to or creation of global data which is performed
within one code block will be reflected in any following code blocks.
Global data constitutes variables as well as module imports, function and
class definitions.::

   <!--#python exec="
   import cgi, time, os
   def _escape(object):
       return cgi.escape(str(object))
   now = time.time() 
   " -->
   <html>
   <body>
   <pre>
   <!--#python eval="_escape(time.asctime(time.localtime(now)))"-->

   <!--#python exec="
   keys = os.environ.keys()
   keys.sort()
   for key in keys:
       print >> filter, _escape(key),
       print >> filter, '=',
       print >> filter, _escape(repr(os.environ.get(key)))
   " -->
   </pre>
   </body>
   </html>


The lifetime of any global data is for the current request only. If data
must persist between requests, it must reside in external modules and as
necessary be protected against multithreaded access in the event that a
multithreaded Apache MPM is used.


.. _ssi-globals:

Pre-populating Globals
======================

Any Python code which appears within the page has to be compiled each time
the page is accessed before it is executed. In other words, the compiled
code is not cached between requests. To limit such recompilation and to
avoid duplication of common code amongst many pages, it is preferable to
pre-populate the global data from within a mod_python handler prior to the
page being processed.

In most cases, a fixup handler would be used for this purpose. For this to
work, first need to configure Apache so that it knows to call the fixup
handler.::

   PythonFixupHandler _handlers


The implementation of the fixup handler contained in ``_handlers.py``
then needs to create an instance of a Python dictionary, store that in the
mod_python request object as ``ssi_globals`` and then populate that
dictionary with any data to be available to the Python code executing
within the page.::

   from mod_python import apache

   import cgi, time

   def _escape(object):
      return cgi.escape(str(object))

   def _header(filter):
      print >> filter, '...'

   def _footer(filter):
      print >> filter, '...'

   def fixuphandler(req):
      req.ssi_globals = {}
      req.ssi_globals['time'] = time
      req.ssi_globals['_escape'] = _escape
      req.ssi_globals['_header'] = _header
      req.ssi_globals['_footer'] = _footer
      return apache.OK


This is most useful where it is necessary to insert common information such
as headers, footers or menu panes which are dynamically generated into many
pages.::

   <!--#python exec="
   now = time.time()
   " -->
   <html>
   <body>
   <!--#python exec="_header(filter)" -->
   <pre>
   <!--#python eval="_escape(time.asctime(time.localtime(now)))"-->
   </pre>
   <!--#python exec="_footer(filter)" -->
   </body>
   </html>

.. _ssi-conditionals:

Conditional Expressions
=======================

SSI allows for some programmability in its own right through the use of
conditional expressions. The structure of this conditional construct is:::

   <!--#if expr="test_condition" -->
   <!--#elif expr="test_condition" -->
   <!--#else -->
   <!--#endif -->


A test condition can be any sort of logical comparison, either comparing
values to one another, or testing the 'truth' of a particular value.

The source of variables used in conditional expressions is distinct from
the set of global data used by the Python code executed within a page.
Instead, the variables are sourced from the ``subprocess_env`` table
object contained within the request object. The values of these variables
can be set from within a page using the SSI ``'set'`` directive, or by a range
of other Apache directives within the Apache configuration files such as
``BrowserMatchNoCase`` and ``SetEnvIf``.

To set these variables from within a mod_python handler, the
``subprocess_env`` table object would be manipulated directly through
the request object.::

   from mod_python import apache

   def fixuphandler(req):
      debug = req.get_config().get('PythonDebug', '0')
      req.subprocess_env['DEBUG'] = debug
      return apache.OK


If being done from within Python code contained within the page itself, the
request object would first have to be accessed via the filter object.::

   <!--#python exec="
   debug = filter.req.get_config().get('PythonDebug', '0')
   filter.req.subprocess_env['DEBUG'] = debug
   " -->
   <html>
   <body>
   <!--#if expr="${DEBUG} != 0" -->
   DEBUG ENABLED
   <!--#else -->
   DEBUG DISABLED
   <!--#endif -->
   </body>
   </html>


.. _ssi-output-filter:

Enabling INCLUDES Filter
========================

SSI is traditionally enabled using the ``AddOutputFilter`` directive in
the Apache configuration files. Normally this would be where the request
mapped to a static file.::

   AddOutputFilter INCLUDES .shtml

When mod_python is being used, the ability to dynamically enable output
filters for the current request can instead be used. This could be done
just for where the request maps to a static file, but may just as easily be
carried out where the content of a response is generated dynamically. In
either case, to enable SSI for the current request, the
:meth:`request.add_output_filter` method of the mod_python request object would be
used.::

   from mod_python import apache

   def fixuphandler(req):
      req.add_output_filter('INCLUDES')
      return apache.OK

