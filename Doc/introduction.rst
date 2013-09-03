.. _introduction:

************
Introduction
************

.. _performance:

Performance
===========

One of the main advantages of mod_python is the increase in
performance over traditional CGI. Below are results of a very crude
test. The test was done on a 1.2GHz Pentium machine running Red Hat
Linux 7.3. `Ab <http://httpd.apache.org/docs-2.0/programs/ab.html>`_
was used to poll 4 kinds of scripts, all of which imported the
standard cgi module (because this is how a typical Python cgi script
begins), then output a single word ``'Hello!'``. The results are
based on 10000 requests with concurrency of 1::

   Standard CGI:               23 requests/s
   Mod_python cgihandler:     385 requests/s
   Mod_python publisher:      476 requests/s
   Mod_python handler:       1203 requests/s


.. _apache_api:

Apache HTTP Server API
======================

Apache processes requests in *phases* (i.e. read the request, parse
headers, check access, etc.). Phases are implemented by
functions called *handlers*. Traditionally, handlers are written in C
and compiled into Apache modules. Mod_python provides a way to extend
Apache functionality by writing Apache handlers in Python. For a
detailed description of the Apache request processing process, see the
`Apache Developer Documentation <http://httpd.apache.org/docs/2.4/developer/>`_, as well as the
`Mod_python - Integrating Python with Apache <http://www.modpython.org/python10/>`_
paper.

Currently only a subset of the Apache HTTP Server API is accessible
via mod_python. It was never the goal of the project to provide a 100%
coverage of the API. Rather, mod_python is focused on the most useful
parts of the API and on providing the most "Pythonic" ways of using
it.

.. _intro_other:

Other Features
==============

Mod_python also provides a number features that fall in the category
of web development, e.g. a parser for embedding Python in HTML
(:ref:`pyapi-psp`), a handler that maps URL space into modules and
functions (:ref:`hand-pub`), support for session (:ref:`pyapi-sess`)
and cookie (:ref:`pyapi-cookie`) handling.

.. seealso::

   `Apache HTTP Server Developer Documentation <http://httpd.apache.org/docs/2.4/developer/>`_
      for HTTP developer information

   `Mod_python - Integrating Python with Apache <http://www.modpython.org/python10/>`_
      for details on how mod_python interfaces with Apache HTTP Server
