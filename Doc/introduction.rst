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
begins), then output a single word \samp{Hello!}. The results are
based on 10000 requests with concurrency of 1::

   Standard CGI:               23 requests/s
   Mod_python cgihandler:     385 requests/s
   Mod_python publisher:      476 requests/s
   Mod_python handler:       1203 requests/s


.. _flexibility:

Flexibility
===========

Apache processes requests in phases (e.g. read the request, parse
headers, check access, etc.). These phases can be implemented by
functions called handlers. Traditionally, handlers are written in C
and compiled into Apache modules. Mod_python provides a way to extend
Apache functionality by writing Apache handlers in Python. For a
detailed description of the Apache request processing process, see the
`Apache API Notes <http://dev.apache.org/API.html>`_, as well as the
`Mod_python - Integrating Python with Apache <http://www.modpython.org/python10/>`_
paper.

To ease migration from CGI, a standard mod_python handler is provided
that simulates the CGI environment allowing a user to run legacy
scripts under mod_python with no changes to the code (in most cases).

.. seealso::

   `Apache HTTP Server Developer Resources <http://httpd.apache.org/dev>`_
      for HTTP developer information

   `Mod_python - Integrating Python with Apache <http://www.modpython.org/python10/>`_
      for details on how mod_python interfaces with Apache HTTP Server
