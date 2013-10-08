
.. _handlers:

*****************
Standard Handlers
*****************

.. _hand-pub:

Publisher Handler
=================

.. index::
   pair: publisher; handler

The ``publisher`` handler is a good way to avoid writing your own
handlers and focus on rapid application development. It was inspired
by `Zope <http://www.zope.org/>`_ ZPublisher.

.. _hand-pub-intro:

Introduction
------------

To use the handler, you need the following lines in your configuration:::

   <Directory /some/path>
     SetHandler mod_python
     PythonHandler mod_python.publisher
   </Directory>


This handler allows access to functions and variables within a module
via URL's. For example, if you have the following module, called
:file:`hello.py`:::

   """ Publisher example """

   def say(req, what="NOTHING"):
      return "I am saying %s" % what


A URL ``http://www.mysite.com/hello.py/say`` would return
``'I am saying NOTHING``. A URL
``http://www.mysite.com/hello.py/say?what=hello`` would
return ``'I am saying hello``.


.. _hand-pub-alg:

The Publishing Algorithm
------------------------

The Publisher handler maps a URI directly to a Python variable or
callable object, then, respectively, returns it's string
representation or calls it returning the string representation of the
return value.

.. index::
   pair: publisher; traversal

.. _hand-pub-alg-trav:

Traversal
^^^^^^^^^

The Publisher handler locates and imports the module specified in the
URI. The module location is determined from the :attr:`request.filename`
attribute. Before importing, the file extension, if any, is
discarded.

If :attr:`request.filename` is empty, the module name defaults to
``'index'``.

Once module is imported, the remaining part of the URI up to the
beginning of any query data (a.k.a. :const:`PATH_INFO`) is used to find an
object within the module. The Publisher handler *traverses* the
path, one element at a time from left to right, mapping the elements
to Python object within the module.

If no ``path_info`` was given in the URL, the Publisher handler will use
the default value of ``'index'``. If the last element is an object inside
a module, and the one immediately preceding it is a directory
(i.e. no module name is given), then the module name will also default
to ``'index'``.

The traversal will stop and :const:`HTTP_NOT_FOUND` will be returned to
the client if:


* Any of the traversed object's names begin with an underscore
  (``'_'``). Use underscores to protect objects that should not be
  accessible from the web.

* A module is encountered. Published objects cannot be modules for
  security reasons.


If an object in the path could not be found, :const:`HTTP_NOT_FOUND`
is returned to the client.

For example, given the following configuration:::

   DocumentRoot /some/dir

   <Directory /some/dir>
     SetHandler mod_python
     PythonHandler mod_python.publisher
   </Directory>

And the following :file:`/some/dir/index.py` file:::

   def index(req):
      return "We are in index()"

   def hello(req):
      return "We are in hello()"


Then:

* http://www.somehost/index/index will return ``'We are in index()'``

* http://www.somehost/index/ will return ``'We are in index()'``

* http://www.somehost/index/hello will return ``'We are in hello()'``

* http://www.somehost/hello will return ``'We are in hello()'``

* http://www.somehost/spam will return ``'404 Not Found'``


.. _hand-pub-alg-args:


Argument Matching and Invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the destination object is found, if it is callable and not a
class, the Publisher handler will get a list of arguments that the
object expects. This list is compared with names of fields from HTML
form data submitted by the client via ``POST`` or
``GET``. Values of fields whose names match the names of callable
object arguments will be passed as strings. Any fields whose names do
not match the names of callable argument objects will be silently dropped,
unless the destination callable object has a ``**kwargs`` style
argument, in which case fields with unmatched names will be passed in the
``**kwargs`` argument.

If the destination is not callable or is a class, then its string
representation is returned to the client.


.. index::
   pair: publisher; authentication

.. _hand-pub-alg-auth:

Authentication
^^^^^^^^^^^^^^

The publisher handler provides simple ways to control access to
modules and functions.

At every traversal step, the Publisher handler checks for presence of
``__auth__`` and ``__access__`` attributes (in this order), as
well as ``__auth_realm__`` attribute.

If ``__auth__`` is found and it is callable, it will be called
with three arguments: the ``request`` object, a string containing
the user name and a string containing the password. If the return
value of
``__auth__`` is false, then :const:`HTTP_UNAUTHORIZED` is
returned to the client (which will usually cause a password dialog box
to appear).

If :meth:`__auth__` is a dictionary, then the user name will be
matched against the key and the password against the value associated
with this key. If the key and password do not match,
:const:`HTTP_UNAUTHORIZED` is returned. Note that this requires
storing passwords as clear text in source code, which is not very secure.

``__auth__`` can also be a constant. In this case, if it is false
(i.e. ``None``, ``0``, ``""``, etc.), then
:const:`HTTP_UNAUTHORIZED` is returned.

If there exists an ``__auth_realm__`` string, it will be sent
to the client as Authorization Realm (this is the text that usually
appears at the top of the password dialog box).

If ``__access__`` is found and it is callable, it will be called
with two arguments: the ``request`` object and a string containing
the user name. If the return value of ``__access__`` is false, then
:const:`HTTP_FORBIDDEN` is returned to the client.

If ``__access__`` is a list, then the user name will be matched
against the list elements. If the user name is not in the list,
:const:`HTTP_FORBIDDEN` is returned.

Similarly to ``__auth__``, ``__access__`` can be a constant.

In the example below, only user ``'eggs'`` with password ``'spam'``
can access the ``hello`` function:::

   __auth_realm__ = "Members only"

   def __auth__(req, user, passwd):

      if user == "eggs" and passwd == "spam" or \
         user == "joe" and passwd == "eoj":
         return 1
      else:
         return 0

   def __access__(req, user):
      if user == "eggs":
         return 1
      else:
          return 0

   def hello(req):
      return "hello"

Here is the same functionality, but using an alternative technique:::

   __auth_realm__ = "Members only"
   __auth__ = {"eggs":"spam", "joe":"eoj"}
   __access__ = ["eggs"]

   def hello(req):
      return "hello"


Since functions cannot be assigned attributes, to protect a function,
an ``__auth__`` or ``__access__`` function can be defined within
the function, e.g.:::

   def sensitive(req):

      def __auth__(req, user, password):
         if user == 'spam' and password == 'eggs':
            # let them in
            return 1
         else:
            # no access
            return 0

      # something involving sensitive information
      return 'sensitive information`

Note that this technique will also work if ``__auth__`` or
``__access__`` is a constant, but will not work is they are
a dictionary or a list.

The ``__auth__`` and ``__access__`` mechanisms exist
independently of the standard
:ref:`dir-handlers-auh`. It
is possible to use, for example, the handler to authenticate, then the
``__access__`` list to verify that the authenticated user is
allowed to a particular function.

.. note::

   In order for mod_python to access ``__auth__``, the module
   containing it must first be imported. Therefore, any module-level
   code will get executed during the import even if
   ``__auth__`` is false.  To truly protect a module from being
   accessed, use other authentication mechanisms, e.g. the Apache
   ``mod_auth`` or with a mod_python :ref:`dir-handlers-auh`.


.. _hand-pub-form:

Form Data
---------

In the process of matching arguments, the Publisher handler creates an
instance of :ref:`pyapi-util-fstor`.
A reference to this instance is stored in an attribute \member{form}
of the ``request`` object.

Since a ``FieldStorage`` can only be instantiated once per
request, one must not attempt to instantiate ``FieldStorage`` when
using the Publisher handler and should use
:attr:`request.form` instead.


.. _hand-wsgi:

WSGI Handler
============

.. index::
   pair: WSGI; handler

WSGI handler can run WSGI applications as described in :pep:`333`.

Assuming there exists the following minimal WSGI app residing in a file named
``mysite/wsgi.py`` in directory ``/path/to/mysite`` (so that the full
path to ``wsgi.py`` is ``/path/to/mysite/mysite/wsgi.py``)::

  def application(environ, start_response):
     status = '200 OK'
     output = 'Hello World!'

     response_headers = [('Content-type', 'text/plain'),
                         ('Content-Length', str(len(output)))]
     start_response(status, response_headers)

     return [output]

It can be executed using the WSGI handler by adding the following to the
Apache configuration::

   PythonHandler mod_python.wsgi
   PythonOption mod_python.wsgi.application mysite.wsgi
   PythonPath "sys.path+['/path/to/mysite']"

The above configuration will import a module named ``mysite.wsgi`` and
will look for an ``application`` callable in the module.

An alternative name for the callable can be specified by appending it
to the module name separated by ``'::'``, e.g.::

  PythonOption mod_python.wsgi.application mysite.wsgi::my_application

If you would like your application to appear under a base URI, it can
be specified by wrapping your configuration in a ``<Location>``
block. It can also be specified via the ``mod_python.wsgi.base_uri``
option, but the ``<Location>`` method is recommended, also because it
has a side-benefit of informing mod_python to skip the map-to-storage
processing phase and thereby improving performance.

For example, if you would like the above application to appear under
``'/wsgiapps'``, you could specify::

   <Location /wsgiapps>
      PythonHandler mod_python.wsgi
      PythonOption mod_python.wsgi.application mysite.wsgi
      PythonPath "sys.path+['/path/to/mysite']"
   </Location>

With the above configuration, content formerly under
``http://example.com/hello`` becomes available under
``http://example.com/wsgiapps/hello``.

If both ``<Location>`` and ``mod_python.wsgi.base_uri`` exist, then
``mod_python.wsgi.base_uri`` takes precedence.
``mod_python.wsgi.base_uri`` cannot be ``'/'`` or end with a
``'/'``. "Root" (or no base_uri) is a blank string, which is the
default. (Note that it is allowed for ``<Location>`` path to be
``"/"`` or have a trailing slash, it will automatically be removed by
mod_python before computing ``PATH_INFO``).


..  index::
   pair: WSGI; SCRIPT_NAME
   pair: WSGI; PATH_INFO

.. note::

   :pep:`333` describes ``SCRIPT_NAME`` and ``PATH_INFO`` environment
   variables which are core to the specification. Most WSGI-supporting
   frameworks currently in existence use the value of ``PATH_INFO`` as the
   request URI.

   The two variable's name and function originate in CGI
   (:rfc:`3875`), which describes an environment wherein a script (or
   any executable's) output could be passed on by the web server as
   content. A typical CGI script resides somewhere on the filesystem
   to which the request URI maps. As part of serving the request the
   server traverses the URI mapping each element to an element of the
   filesystem path to locate the script. Once the script is found, the
   portion of the URI used thus far is assigned to the ``SCRIPT_NAME``
   variable, while the remainder of the URI gets assigned to
   ``PATH_INFO``.

   Because the relationship between Python modules and files on disk
   is largely tangential, it is not very clear what exactly
   ``PATH_INFO`` and ``SCRIPT_NAME`` ought to be. Even though Python
   modules are most often files on disk located somewhere in the
   Python path, they don't have to be (they could be code objects
   constructed on-the-fly), and their location in the filesystem has
   no relationship to the URL structure at all.

   The mismatch between CGI and WSGI results in an ambiguity which
   requires that the split between the two variables be explicitely
   specified, which is why ``mod_python.wsgi.base_uri`` exists. In essence
   ``mod_python.wsgi.base_uri`` (or the path in surrounding
   ``<Location>``) is the ``SCRIPT_NAME`` portion of the URI and
   defaults to ``''``.

   An important detail is that ``SCRIPT_NAME`` + ``PATH_INFO`` should
   result in the original URI (encoding issues aside). Since
   ``SCRIPT_NAME`` (in its original CGI definition) referrs to an
   actual file, its name never ends with a slash. The slash, if any,
   always ends up in ``PATH_INFO``. E.g. ``/path/to/myscrip/foo/bar``
   splits into ``/path/to/myscript`` and ``/foo/bar``. If the whole
   site is served by an app or a script, then ``SCRIPT_NAME`` is a
   blank string ``''``, not a ``'/'``.


.. _hand-psp:

PSP Handler
===========

..  index::
   pair: PSP; handler

PSP handler is a handler that processes documents using the
``PSP`` class in ``mod_python.psp`` module.

To use it, simply add this to your httpd configuration::

   AddHandler mod_python .psp
   PythonHandler mod_python.psp

For more details on the PSP syntax, see Section :ref:`pyapi-psp`.

If ``PythonDebug`` server configuration is ``On``, then by
appending an underscore (``'_'``) to the end of the url you can get a
nice side-by-side listing of original PSP code and resulting Python
code generated by the ``psp} module``. This is very useful for
debugging. You'll need to adjust your httpd configuration:::

   AddHandler mod_python .psp .psp_
   PythonHandler mod_python.psp
   PythonDebug On

.. note::

   Leaving debug on in a production environment will allow remote users
   to display source code of your PSP pages!

.. _hand-cgi:

CGI Handler
===========

.. index::
   pair: CGI; handler


CGI handler is a handler that emulates the CGI environment under mod_python.

Note that this is not a ``'true'`` CGI environment in that it is
emulated at the Python level. ``stdin`` and ``stdout`` are
provided by substituting ``sys.stdin`` and ``sys.stdout``, and
the environment is replaced by a dictionary. The implication is that
any outside programs called from within this environment via
``os.system``, etc. will not see the environment available to the
Python program, nor will they be able to read/write from standard
input/output with the results expected in a ``'true'`` CGI environment.

The handler is provided as a stepping stone for the migration of
legacy code away from CGI. It is not recommended that you settle on
using this handler as the preferred way to use mod_python for the long
term. This is because the CGI environment was not intended for
execution within threads (e.g. requires changing of current directory
with is inherently not thread-safe, so to overcome this cgihandler
maintains a thread lock which forces it to process one request at a
time in a multi-threaded server) and therefore can only be implemented
in a way that defeats many of the advantages of using mod_python in
the first place.

To use it, simply add this to your :file:`.htaccess` file:::

   SetHandler mod_python
   PythonHandler mod_python.cgihandler

As of version 2.7, the cgihandler will properly reload even indirectly
imported module. This is done by saving a list of loaded modules
(sys.modules) prior to executing a CGI script, and then comparing it
with a list of imported modules after the CGI script is done.  Modules
(except for whose whose __file__ attribute points to the standard
Python library location) will be deleted from sys.modules thereby
forcing Python to load them again next time the CGI script imports
them.

If you do not want the above behavior, edit the :file:`cgihandler.py`
file and comment out the code delimited by ###.

Tests show the cgihandler leaking some memory when processing a lot of
file uploads. It is still not clear what causes this. The way to work
around this is to set the Apache ``MaxRequestsPerChild`` to a non-zero
value.


