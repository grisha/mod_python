
.. _tutorial:

********
Tutorial
********

*So how can I make this work?*

This is a quick guide to getting started with mod_python programming
once you have it installed. This is not an installation manual.

It is also highly recommended to read (at least the top part of)
the section :ref:`pythonapi` after completing this tutorial.

.. _tut-pub:

A Quick Start with the Publisher Handler
========================================

This section provides a quick overview of the Publisher handler for
those who would like to get started without getting into too much
detail. A more thorough explanation of how mod_python handlers work
and what a handler actually is follows on in the later sections of the
tutorial.

The :ref:`hand-pub` is provided as one of the standard
mod_python handlers. To get the publisher handler working, you will
need the following lines in your config::

   AddHandler mod_python .py
   PythonHandler mod_python.publisher
   PythonDebug On

The following example demonstrates a simple feedback form. The form
asks for a name, e-mail address and a comment which are then used to
construct and send a message to the webmaster.  This simple
application consists of two files: :file:`form.html` - the form to
collect the data, and :file:`form.py` - the target of the form's
action.

Here is the html for the form::

   <html>
      Please provide feedback below:
   <p>                           
   <form action="form.py/email" method="POST">

      Name:    <input type="text" name="name"><br>
      Email:   <input type="text" name="email"><br>
      Comment: <textarea name="comment" rows=4 cols=20></textarea><br>
      <input type="submit">

   </form>
   </html>  

The ``action`` element of the ``<form>`` tag points to
``form.py/email``. We are going to create a file called
:file:`form.py`, like this::

   import smtplib

   WEBMASTER = "webmaster"   # webmaster e-mail
   SMTP_SERVER = "localhost" # your SMTP server

   def email(req, name, email, comment):

       # make sure the user provided all the parameters
       if not (name and email and comment):
           return "A required parameter is missing, \
                  please go back and correct the error"

       # create the message text
       msg = """\
   From: %s                                                                                                                                           
   Subject: feedback
   To: %s

   I have the following comment:

   %s

   Thank You,

   %s

   """ % (email, WEBMASTER, comment, name)

       # send it out
       conn = smtplib.SMTP(SMTP_SERVER)
       conn.sendmail(email, [WEBMASTER], msg)
       conn.quit()

       # provide feedback to the user
       s = """\
   <html>

   Dear %s,<br>                                                                                                                                       
   Thank You for your kind comments, we
   will get back to you shortly.

   </html>""" % name

       return s

When the user clicks the Submit button, the publisher handler will
load the :func:`email` function in the :mod:`form` module,
passing it the form fields as keyword arguments. It will also pass the
request object as ``req``.

You do not have to have ``req`` as one of the arguments if you do not
need it. The publisher handler is smart enough to pass your function
only those arguments that it will accept.

The data is sent back to the browser via the return value of the
function.

Even though the Publisher handler simplifies mod_python programming a
great deal, all the power of mod_python is still available to this
program, since it has access to the request object. You can do all the
same things you can do with a "native" mod_python handler, e.g. set
custom headers via ``req.headers_out``, return errors by raising
:exc:`apache.SERVER_ERROR` exceptions, write or read directly to
and from the client via :meth:`req.write()` and :meth:`req.read()`,
etc.

Read Section :ref:`hand-pub` for more information on the publisher
handler.

.. _tut-overview:

Quick Overview of how Apache Handles Requests
=============================================

Apache processes requests in :dfn:`phases`. For example, the first
phase may be to authenticate the user, the next phase to verify
whether that user is allowed to see a particular file, then (next
phase) read the file and send it to the client. A typical static file
request involves three phases: (1) translate the requested URI to a
file location (2) read the file and send it to the client, then (3)
log the request. Exactly which phases are processed and how varies
greatly and depends on the configuration.

A :dfn:`handler` is a function that processes one phase. There may be
more than one handler available to process a particular phase, in
which case they are called by Apache in sequence. For each of the
phases, there is a default Apache handler (most of which by default
perform only very basic functions or do nothing), and then there are
additional handlers provided by Apache modules, such as mod_python.

Mod_python provides every possible handler to Apache. Mod_python
handlers by default do not perform any function, unless specifically
told so by a configuration directive. These directives begin with
``'Python'`` and end with ``'Handler'``
(e.g. ``PythonAuthenHandler``) and associate a phase with a Python
function. So the main function of mod_python is to act as a dispatcher
between Apache handlers and Python functions written by a developer
like you.

The most commonly used handler is ``PythonHandler``. It handles the
phase of the request during which the actual content is
provided. Because it has no name, it is sometimes referred to as as
:dfn:`generic` handler. The default Apache action for this handler is
to read the file and send it to the client. Most applications you will
write will provide this one handler. To see all the possible
handlers, refer to Section :ref:`directives`.

.. _tut-what-it-do:

So what Exactly does Mod-python do?
===================================

Let's pretend we have the following configuration::

   <Directory /mywebdir>
       AddHandler mod_python .py
       PythonHandler myscript
       PythonDebug On
   </Directory>

Note: ``/mywebdir`` is an absolute physical path in this case.

And let's say that we have a python program (Windows users: substitute
forward slashes for backslashes) :file:`/mywedir/myscript.py` that looks like
this::

   from mod_python import apache

   def handler(req):

       req.content_type = "text/plain"
       req.write("Hello World!")

       return apache.OK

Here is what's going to happen: The ``AddHandler`` directive tells
Apache that any request for any file ending with :file:`.py` in the
:file:`/mywebdir` directory or a subdirectory thereof needs to be
processed by mod_python. The ``'PythonHandler myscript'`` directive
tells mod_python to process the generic handler using the
`myscript` script. The ``'PythonDebug On'`` directive instructs
mod_python in case of an Python error to send error output to the
client (in addition to the logs), very useful during development.

When a request comes in, Apache starts stepping through its request
processing phases calling handlers in mod_python. The mod_python
handlers check whether a directive for that handler was specified in
the configuration. (Remember, it acts as a dispatcher.)  In our
example, no action will be taken by mod_python for all handlers except
for the generic handler. When we get to the generic handler,
mod_python will notice ``'PythonHandler myscript'`` directive and do
the following:

* If not already done, prepend the directory in which the
  ``PythonHandler`` directive was found to ``sys.path``.

* Attempt to import a module by name ``myscript``. (Note that if
  ``myscript`` was in a subdirectory of the directory where
  ``PythonHandler`` was specified, then the import would not work
  because said subdirectory would not be in the ``sys.path``. One
  way around this is to use package notation, e.g. 
  ``'PythonHandler subdir.myscript'``.)

* Look for a function called ``handler`` in module ``myscript``.

* Call the function, passing it a request object. (More on what a
  request object is later).

* At this point we're inside the script, let's examine it line-by-line: 

  * ::

       from mod_python import apache

    This imports the apache module which provides the interface to
    Apache. With a few rare exceptions, every mod_python program will have
    this line.

  .. index::
     single: handler

  * ::

       def handler(req):

    This is our :dfn:`handler` function declaration. It
    is called ``'handler'`` because mod_python takes the name of the
    directive, converts it to lower case and removes the word
    ``'python'``. Thus ``'PythonHandler'`` becomes
    ``'handler'``. You could name it something else, and specify it
    explicitly in the directive using ``'::'``. For example, if the
    handler function was called ``'spam'``, then the directive would
    be ``'PythonHandler myscript::spam'``.

    Note that a handler must take one argument - the :ref:`pyapi-mprequest`.
    The request object is an object that provides all of the
    information about this particular request - such as the IP of
    client, the headers, the URI, etc. The communication back to the
    client is also done via the request object, i.e. there is no
    "response" object.

  * ::

       req.content_type = "text/plain"

    This sets the content type to ``'text/plain'``. The default is
    usually ``'text/html'``, but because our handler does not produce
    any html, ``'text/plain'`` is more appropriate.  You should always
    make sure this is set *before* any call to ``'req.write'``. When
    you first call ``'req.write'``, the response HTTP header is sent
    to the client and all subsequent changes to the content type (or
    other HTTP headers) have no effect.

  * ::

       req.write("Hello World!")

    This writes the ``'Hello World!'`` string to the client.

  * ::

       return apache.OK

    This tells Apache that everything went OK and that the request has
    been processed. If things did not go OK, this line could return
    :const:`apache.HTTP_INTERNAL_SERVER_ERROR` or
    :const:`apache.HTTP_FORBIDDEN`. When things do not go OK, Apache
    logs the error and generates an error message for the client.

.. note::

  It is important to understand that in order for the handler code to
  be executed, the URL needs not refer specficially to
  :file:`myscript.py`. The only requirement is that it refers to a
  :file:`.py` file. This is because the ``AddHandler mod_python .py``
  directive assignes mod_python to be a handler for a file *type*
  (based on extention ``.py``), not a specific file. Therefore the
  name in the URL does not matter, in fact the file referred to in the
  URL doesn't event have to exist. Given the above configuration,
  ``'http://myserver/mywebdir/myscript.py'`` and
  ``'http://myserver/mywebdir/montypython.py'`` would yield the exact
  same result.


.. _tut-more-complicated:

Now something More Complicated - Authentication
===============================================

Now that you know how to write a basic handler, let's try
something more complicated.

Let's say we want to password-protect this directory. We want the
login to be ``'spam'``, and the password to be ``'eggs'``.

First, we need to tell Apache to call our *authentication*
handler when authentication is needed. We do this by adding the
``PythonAuthenHandler``. So now our config looks like this::

   <Directory /mywebdir>
       AddHandler mod_python .py
       PythonHandler myscript
       PythonAuthenHandler myscript
       PythonDebug On
   </Directory>

Notice that the same script is specified for two different
handlers. This is fine, because if you remember, mod_python will look
for different functions within that script for the different handlers.

Next, we need to tell Apache that we are using Basic HTTP
authentication, and only valid users are allowed (this is fairly basic
Apache stuff, so we're not going to go into details here). Our config
looks like this now::

   <Directory /mywebdir>
      AddHandler mod_python .py
      PythonHandler myscript
      PythonAuthenHandler myscript
      PythonDebug On
      AuthType Basic
      AuthName "Restricted Area"
      require valid-user
   </Directory>

Note that depending on which version of Apache is being used, you may need
to set either the \code{AuthAuthoritative} or ``AuthBasicAuthoritative``
directive to ``Off`` to tell Apache that you want allow the task of
performing basic authentication to fall through to your handler.

Now we need to write an authentication handler function in
:file:`myscript.py`. A basic authentication handler would look like
this::

   from mod_python import apache

   def authenhandler(req):

       pw = req.get_basic_auth_pw()
       user = req.user

       if user == "spam" and pw == "eggs":
          return apache.OK
       else:
          return apache.HTTP_UNAUTHORIZED

Let's look at this line by line:

* ::

     def authenhandler(req):

  This is the handler function declaration. This one is called
  ``authenhandler`` because, as we already described above,
  mod_python takes the name of the directive
  (``PythonAuthenHandler``), drops the word ``'Python'`` and converts
  it lower case.

* ::

     pw = req.get_basic_auth_pw()
  
  This is how we obtain the password. The basic HTTP authentication
  transmits the password in base64 encoded form to make it a little
  bit less obvious. This function decodes the password and returns it
  as a string. Note that we have to call this function before obtaining
  the user name.

* ::

     user = req.user
  
  This is how you obtain the username that the user entered. 

* ::

     if user == "spam" and pw == "eggs":
         return apache.OK


  We compare the values provided by the user, and if they are what we
  were expecting, we tell Apache to go ahead and proceed by returning
  :const:`apache.OK`. Apache will then consider this phase of the
  request complete, and proceed to the next phase. (Which in this case
  would be :func:`handler()` if it's a ``'.py'`` file).

* ::

     else:
         return apache.HTTP_UNAUTHORIZED 

  Else, we tell Apache to return :const:`HTTP_UNAUTHORIZED` to the
  client, which usually causes the browser to pop a dialog box asking
  for username and password.

.. _tut-404-handler:

Your Own 404 Handler
====================

In some cases, you may wish to return a 404 (:const:`HTTP_NOT_FOUND`) or
other non-200 result from your handler.  There is a trick here.  if you
return :const:`HTTP_NOT_FOUND` from your handler, Apache will handle
rendering an error page.  This can be problematic if you wish your handler
to render it's own error page.

In this case, you need to set ``req.status = apache.HTTP_NOT_FOUND``,
render your page, and then ``return(apache.OK)``::

   from mod_python import apache

   def handler(req):
      if req.filename[-17:] == 'apache-error.html':
         #  make Apache report an error and render the error page
         return(apache.HTTP_NOT_FOUND)
      if req.filename[-18:] == 'handler-error.html':
         #  use our own error page
         req.status = apache.HTTP_NOT_FOUND
         pagebuffer = 'Page not here.  Page left, not know where gone.'
      else:
         #  use the contents of a file
         pagebuffer = open(req.filename, 'r').read()

      #  fall through from the latter two above
      req.write(pagebuffer)
      return(apache.OK)

Note that if wishing to returning an error page from a handler phase other
than the response handler, the value ``apache.DONE`` must be returned
instead of ``apache.OK``. If this is not done, subsequent handler phases
will still be run. The value of ``apache.DONE`` indicates that processing
of the request should be stopped immediately. If using stacked response
handlers, then ``apache.DONE`` should also be returned in that situation
to prevent subsequent handlers registered for that phase being run if
appropriate.
