.. _installation:

************
Installation
************

.. note::

  ZZZ: Some support forum information goes here (mailing list?)


.. _inst-prerequisites:

Prerequisites
=============

* Python 2.3.4 or later. Python versions less than 2.3 will not work.
* Apache 2.0.54 or later. (ZZZ) (For Apache 1.3.x, use mod_python version 2.7.x).

In order to compile mod_python you will need to have the include files
for both Apache and Python, as well as the Python library installed on
your system.  If you installed Python and Apache from source, then you
already have everything needed. However, if you are using prepackaged
software (e.g. Red Hat Linux RPM, Debian, or Solaris packages from
sunsite, etc) then chances are, you have just the binaries and not the
sources on your system. Often, the Apache and Python include files and
libraries necessary to compile mod_python are part of separate
"development" package. If you are not sure whether you have all the
necessary files, either compile and install Python and Apache from
source, or refer to the documentation for your system on how to get
the development packages.


.. _inst-compiling:

Compiling
=========

There are two ways in which modules can be compiled and linked to
Apache - statically, or as a DSO (Dynamic Shared Object).

:dfn:`DSO` is a more popular approach nowadays and is the recommended
one for mod_python. The module gets compiled as a shared library which
is dynamically loaded by the server at run time.

The advantage of DSO is that a module can be installed without
recompiling Apache and used as needed.  A more detailed description of
the Apache DSO mechanism is available at `<http://httpd.apache.org/docs-2.4/dso.html>`_

*At this time only DSO is supported by mod_python.*

:dfn:`Static` linking is an older approach. With dynamic linking
available on most platforms it is used less and less. The main
drawback is that it entails recompiling Apache, which in many
instances is not a favorable option.


.. _inst-configure:

Running :file:`./configure`
---------------------------

The :file:`./configure` script will analyze your environment and
create custom Makefiles particular to your system. Aside from all the
standard autoconf stuff, :file:`./configure` does the following:

.. index::
   single: apxs
   pair: ./configure; --with-apxs

* Finds out whether a program called :program:`apxs` is available. This
  program is part of the standard Apache distribution, and is necessary
  for DSO compilation. If apxs cannot be found in your :envvar:`PATH` or in
  :file:`/usr/local/apache/bin`, DSO compilation will not be available.

  You can manually specify the location of apxs by using the
  :option:`with-apxs` option, e.g.::

     $ ./configure --with-apxs=/usr/local/apache/bin/apxs        

  It is recommended that you specify this option.

.. index::
   single: libpython.a
   pair: ./configure; --with-python

* Checks your Python version and attempts to figure out where
  :file:`libpython` is by looking at various parameters compiled into
  your Python binary. By default, it will use the :program:`python`
  program found in your :envvar:`PATH`.

  If the first Python binary in the path is not suitable or not the one
  desired for mod_python, you can specify an alternative location with the
  :option:`with-python` option, e.g::

     $ ./configure --with-python=/usr/local/bin/python2.3

.. index::
   pair: ./configure; --with-mutex-dir

* Sets the directory for the apache mutex locks. The default is
  :file:`/tmp`. The directory must exist and be writable by the
  owner of the apache process.

  Use :option:`with-mutex-dir` option, e.g::

     $ ./configure --with-mutex-dir=/var/run/mod_python

  The mutex directory can also be specified in using a 
  :ref:`PythonOption` ZZZ directive. 
  See :ref:`Configuring Apache` ZZZ.

  New in version 3.3.0

.. index::
   pair: ./configure; --with-max-locks

* Sets the maximum number of locks reserved by mod_python.

  The mutexes used for locking are a limited resource on some
  systems. Increasing the maximum number of locks may increase performance
  when using session locking.  The default is 8. A reasonable number for 
  higher performance would be 32.
  Use :option:`with-max-locks` option, e.g::

     $ ./configure --with-max-locks=32

  The number of locks can also be specified in using a 
  :ref:`PythonOption` ZZZ  directive. 
  See :ref:`Configuring Apache` ZZZ.

  New in version 3.2.0

.. index::
   single: flex
   pair: ./configure; --with-flex

* Attempts to locate :program:`flex` and determine its version. 
  If :program:`flex` cannot be found in your :envvar:`PATH` :program:`configure`
  will fail.  If the wrong version is found :program:`configure` will generate a warning.
  You can generally ignore this warning unless you need to re-create
  :file:`src/psp_parser.c`.
 
  The parser used by psp (See :ref:`pyapi-psp`) is written in C generated using 
  :program:`flex`. This requires a reentrant version of :program:`flex` which
  at this time is 2.5.31. Most platforms however ship with version 2.5.4
  which is not suitable, so a pre-generated copy of psp_parser.c is included
  with the source. If you do need to compile :file:`src/psp_parser.c` you 
  must get the correct :program:`flex` version.
 
  If the first flex binary in the path is not suitable or not the one desired
  you can specify an alternative location with the option:with-flex:
  option, e.g::
 
     $ ./configure --with-flex=/usr/local/bin/flex

  New in version 3.2.0

.. index::
   pair: ./configure; --with-python-src

* The python source is required to build the mod_python documentation.
  You can safely ignore this option unless you want to build the the
  documentation. If you want to build the documentation, specify the path
  to your python source with the :option:`with-python-src` option, eg.

     $ ./configure --with-python-src=/usr/src/python2.3

  New in version 3.2.0

.. _inst-make:

Running :file:`make`
--------------------

.. index::
   single: make

* To start the build process, simply run::

     $ make

.. _inst-installing:

Installing
==========

.. _inst-makeinstall

.. index::
   paris: make; install

Running :file:`make install`

* This part of the installation needs to be done as root:

      $ su
      # make install

  * This will simply copy the library into your Apache
    :file:`libexec` directory, where all the other modules are.

  * Lastly, it will install the Python libraries in
    file:`site-packages` and compile them.

.. index::
   pair: make targets; install_py_lib
   pair: make targets; install_dso

.. note::

  If you wish to selectively install just the Python libraries
  or the DSO (which may not always require superuser
  privileges), you can use the following :program:`make` targets:
  :option:`install_py_lib` and :option:`install_dso`
  :option:`install_static` and :option:`install_dso`

.. _inst-apacheconfig:

Configuring Apache
==================

.. index::
   pair: LoadModule; apache configuration
   single: mod_python.so

* **LoadModule**

  If you compiled mod_python as a DSO, you will need to tell Apache to
  load the module by adding the following line in the Apache
  configuration file, usually called \filenq{httpd.conf} or
  :file:`apache.conf`::

     LoadModule python_module libexec/mod_python.so

  The actual path to :program:`mod_python.so` may vary, but :program:`make install`
  should report at the very end exactly where :program:`mod_python.so`
  was placed and how the ``LoadModule`` directive should appear.

.. index::
   pair: mutex directory; apache configuration

* **Mutex Directory**

  The default directory for mutex lock files is :file:`/tmp`. The
  default value can be be specified at compile time using
  :ref:`./configure ----with-mutex-dir` ZZZ.

  Alternatively this value can be overriden at apache startup using 
  a :ref:`PythonOption`::

     PythonOption mod_python.mutex_directory "/tmp"

  This may only be used in the server configuration context.
  It will be ignored if used in a directory, virtual host,
  htaccess or location context. The most logical place for this 
  directive in your apache configuration file is immediately
  following the **LoadModule** directive.

  *New in version 3.3.0*

.. index::
   pair: apache configuration; mutex locks

* **Mutex Locks**
  
  Mutexes are used in mod_python for session locking. The default
  value is 8.

  On some systems the locking mechanism chosen uses valuable
  system resources. Notably on RH 8 sysv ipc is used, which 
  by default provides only 128 semaphores system-wide.
  On many other systems flock is used which may result in a relatively
  large number of open files.

  The optimal number of necessary locks is not clear. 
  Increasing the maximum number of locks may increase performance
  when using session locking.  A reasonable number for 
  higher performance might be 32.

  The maximum number of locks can be specified at compile time
  using :ref:`./configure ----with-max-locks` ZZZ.

  Alternatively this value can be overriden at apache startup using 
  a :ref:`PythonOption` ZZZ::

     PythonOption mod_python.mutex_locks 8 

  This may only be used in the server configuration context.  It will
  be ignored if used in a directory, virtual host, htaccess or
  location context. The most logical place for this directive in your
  apache configuration file is immediately following the
  **LoadModule** directive.

  *New in version 3.3.0*

.. _inst-testing:

Testing
=======

.. note::

   These instructions are meant to be followed if you are using
   mod_python 3.x or later. If you are using mod_python 2.7.x (namely,
   if you are using Apache 1.3.x), please refer to the proper
   documentation.

#. Make some directory that would be visible on your web site, for
   example, htdocs/test.

#. Add the following Apache directives, which can appear in either the
   main server configuration file, or :file:`.htaccess`.  If you are
   going to be using the :file:`.htaccess` file, you will not need
   the ``<Directory>`` tag below (the directory then becomes the
   one in which the :file:`.htaccess` file is located), and you will
   need to make sure the ``AllowOverride`` directive applicable to
   this directory has at least ``FileInfo`` specified. (The default
   is ``None``, which will not work.)

   ZZZ: the above has been verified to be still true for Apache 2.0::

     <Directory /some/directory/htdocs/test> 
         AddHandler mod_python .py
         PythonHandler mptest 
         PythonDebug On 
     </Directory>

   (Substitute :file:`/some/directory` above for something applicable to
   your system, usually your Apache ServerRoot)

#. This redirects all requests for URLs ending in :file:`.py} to the
   mod_python handler. mod_python receives those requests and looks
   for an appropriate PythonHandler to handle them. Here, there is a
   single PythonHandler directive defining mptest as the python
   handler to use. We'll see next how this python handler is defined.

#. At this time, if you made changes to the main configuration file,
   you will need to restart Apache in order for the changes to take
   effect.

#. Edit :file:`mptest.py` file in the :file:`htdocs/test` directory so
   that is has the following lines (be careful when cutting and
   pasting from your browser, you may end up with incorrect
   indentation and a syntax error)::

     from mod_python import apache

     def handler(req):
         req.content_type = 'text/plain'
         req.write("Hello World!")
         return apache.OK 

#. Point your browser to the URL referring to the :file:`mptest.py`;
   you should see ``'Hello World!'``. If you didn't - refer to the
   troubleshooting section next.

#. Note that according to the configuration written above, you can
   also point your browser to any URL ending in .py in the test
   directory.  You can for example point your browser to
   :file:`/test/foobar.py` and it will be handled by
   :file:`mptest.py`. That's because you explicitely set the handler
   to always be :file:`mptest`, whatever the requested file was.

#. If everything worked well, move on to Chapter :ref:`Tutorial` ZZZ.


.. _inst-trouble:

Troubleshooting
===============

There are a few things you can try to identify the problem: 

* Carefully study the error output, if any. 

* Check the server error log file, it may contain useful clues. 

* Try running Apache from the command line in single process mode::

     ./httpd -X ZZZ does this even work?

  This prevents it from backgrounding itself and may provide some useful
  information.

* Beginning with mod_python 3.2.0, you can use the mod_python.testhandler
  to diagnose your configuration. Add this to your :file:`httpd.conf` file::

     <Location /mpinfo>
       SetHandler mod_python
       PythonHandler mod_python.testhandler
     </Location>

  Now point your browser to the :file:`/mpinfo` URL
  (e.g. :file:`http://localhost/mpinfo`) and note down the information given.
  This will help you reporting your problem to the mod_python list.

* Ask on the mod_python list. Make sure to provide specifics such as: ZZZ what list?

  * Mod_python version.
  * Your operating system type, name and version.
  * Your Python version, and any unusual compilation options.
  * Your Apache version.
  * Relevant parts of the Apache config, .htaccess.
  * Relevant parts of the Python code.


