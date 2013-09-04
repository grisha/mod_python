.. _installation:

************
Installation
************

.. note::

  By far the best place to get help with installation and other issues
  is the mod_python mailing list. Please take a moment to join the
  mod_python mailing list by sending an e-mail with the word
  "subscribe" in the subject to mod_python-request@modpython.org or visit the 
  `mod_python mailing list page <http://mailman.modpython.org/mailman/listinfo/mod_python>`_


.. _inst-prerequisites:

Prerequisites
=============

In the ideal case your Operating System provides a pre-packaged
version of mod_python. If not, you will need to compile it
yourself. This version of mod_python requires:

* Python 2.6 or 2.7. (earlier versions might work too).
* Apache 2.2 or later. Apache 2.4 is highly recommended over 2.2.

In order to compile mod_python you will need to have the include files
for both Apache and Python, as well as the Python library installed on
your system.  If you installed Python and Apache from source, then you
already have everything needed. However, if you are using pre-packaged
software then you may need to install the "development" packages
which contain the include files and libraries necessary to compile
mod_python. Please check your OS documentation for specifics. (Hint:
look for packages named python-devel or python-dev and apache-devel or
apache-dev or httpd-dev, etc.).

.. _inst-compiling:

Compiling
=========

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
  program is part of the standard Apache distribution, and is required
  for compilation.

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
  :option:`with-python` option, e.g.::

     $ ./configure --with-python=/usr/local/bin/python2.3

.. index::
   pair: ./configure; --with-mutex-dir

* Sets the directory for the apache mutex locks (if the mutex
  mechanism chosen by APR requires one).

  Note: mutex locks are used only by :ref:`mod_python Sessions <pyapi-sess>` and
  :ref:`PSP <hand-psp>` (which maintains a Session implicitly). If you're
  not using mod_python Sessions or PSP, then this setting should not
  matter.

  Default is :file:`/tmp`. The directory must exist and be
  writable by the owner of the apache process.

  Use :option:`with-mutex-dir` option, e.g::

     $ ./configure --with-mutex-dir=/var/run/mod_python

  The mutex directory can also be specified at run time using 
  :ref:`dir-other-po` ``mod_python.mutex_directory``.
  See :ref:`inst-apacheconfig`.

  *New in version 3.3.0*

.. index::
   pair: ./configure; --with-max-locks

* Sets the maximum number of mutex locks reserved by mod_python.

  Note: mutex locks are used only by :ref:`mod_python Sessions <pyapi-sess>` and
  :ref:`PSP <hand-psp>` (which maintains a Session implicitly). If you're
  not using mod_python Sessions or PSP, then this setting should not
  matter.

  The mutexes used for locking are a limited resource on some
  systems. Increasing the maximum number of locks may increase performance
  when using session locking.  The default is 8. A reasonable number for 
  higher performance would be 32.
  Use :option:`with-max-locks` option, e.g::

     $ ./configure --with-max-locks=32

  The number of locks can also be specified at run time using
  :ref:`dir-other-po` ``mod_python.mutex_locks``. 
  See :ref:`inst-apacheconfig`.

  *New in version 3.2.0*

.. index::
   single: flex
   pair: ./configure; --with-flex

* Attempts to locate :program:`flex` and determine its version. 
  If :program:`flex` cannot be found in your :envvar:`PATH` :program:`configure`
  will fail.  If the wrong version is found :program:`configure` will generate a warning.
  You can generally ignore this warning unless you need to re-create
  :file:`src/psp_parser.c`.
 
  The parser used by psp (See :ref:`pyapi-psp`) is written in C
  generated using :program:`flex`. (This requires a reentrant version
  of :program:`flex`, 2.5.31 or later).
 
  If the first flex binary in the path is not suitable or not the one desired
  you can specify an alternative location with the option:with-flex:
  option, e.g::
 
     $ ./configure --with-flex=/usr/local/bin/flex

  *New in version 3.2.0*

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

.. _inst-makeinstall:

.. index::
   pair: make; install

Running :file:`make install`

* This part of the installation in most cases needs to be done as root::

      $ sudo make install

  * This will copy the mod_python library (:file:`mod_python.so`) into your Apache
    :file:`libexec` or :file:`modules` directory, where all the other modules are.

  * Lastly, it will install the Python libraries in
    :file:`site-packages` and compile them.

.. index::
   pair: make targets; install_py_lib
   pair: make targets; install_dso

.. note::

  If you wish to selectively install just the Python libraries
  or the DSO (mod_python.so) (which may not always require superuser
  privileges), you can use the following :program:`make` targets:
  :option:`install_py_lib` and :option:`install_dso`.

.. _inst-apacheconfig:

Configuring Apache
==================

.. index::
   pair: LoadModule; apache configuration
   single: mod_python.so

* *LoadModule*

  You need to configure Apache to load the module by adding the
  following line in the Apache configuration file, usually called
  :file:`httpd.conf` or :file:`apache.conf`::

     LoadModule python_module libexec/mod_python.so

  The actual path to :program:`mod_python.so` may vary, but :program:`make install`
  should report at the very end exactly where :program:`mod_python.so`
  was placed and how the ``LoadModule`` directive should appear.

* See :ref:`inst-testing` below for more basic configuration parameters.


.. _inst-testing:

Testing
=======

#. Make a directory that would be visible on your web site, e.g. ``htdocs/test``.

#. Add the following configuration directives to the main server config file::

     <Directory /some/directory/htdocs/test> 
         AddHandler mod_python .py
         PythonHandler mptest 
         PythonDebug On 
     </Directory>

   (Substitute ``/some/directory`` above for something applicable to
   your system, usually your Apache ServerRoot)

   This configuration can also be specified in an :file:`.htaccess`
   file.  Note that :file:`.htaccess` configuration is typically
   disabled by default, to enable it in a directory specify
   ``AllowOverride`` with at least ``FileInfo``.

#. This causes all requests for URLs ending in ``.py`` to be processed
   by mod_python. Upon being handed a request, mod_python looks for
   the appropriate *python handler* to handle it. Here, there is a
   single ``PythonHandler`` directive defining module ``mptest`` as
   the python handler to use. We'll see next how this python handler
   is defined.

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
   point your browser to *any* URL ending in .py in the test
   directory.  Therefore pointing your browser to
   :file:`/test/foobar.py` will be handled exactly the same way by
   :file:`mptest.py`. This is because the code in the ``handler``
   function does not bother examining the URL and always acts the same
   way no matter what the URL is.

#. If everything worked well, move on to Chapter :ref:`tutorial`.


.. _inst-trouble:

Troubleshooting
===============

There are a few things you can try to identify the problem: 

* Carefully study the error output, if any. 

* Check the server error log file, it may contain useful clues. 

* Try running Apache from the command line in single process mode::

     ./httpd -X

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

* Ask on the `mod_python list <http://mailman.modpython.org/mailman/listinfo/mod_python>`_. 
  Please make sure to provide specifics such as:

  * mod_python version.
  * Your operating system type, name and version.
  * Your Python version, and any unusual compilation options.
  * Your Apache version.
  * Relevant parts of the Apache config, .htaccess.
  * Relevant parts of the Python code.


