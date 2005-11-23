:version: $Id$

=============================================
Developer's Guide for mod_python Contributors
=============================================

Mod_Python is a subproject of the Apache `httpd server project`_.
As such we strive to conform to the practices recommended by the
`Apache Software Foundation`_.

.. _httpd server project: http://httpd.apache.org/
.. _Apache Software Foundation: http://www.apache.org/


Becoming a Developer
====================

A developer_ is a user who contributes to a project in the form of code or 
documentation. They take extra steps to participate in a project, are active
on the developer mailing list, participate in discussions, provide patches,
documentation, suggestions, and criticism. Developers are also known as 
contributors.

Contributions from developers are integrated into mod_python by committers_
at the committer's discretion.

*(Should we mention that everyone on python-dev gets a vote on releases? -jg)*

*(Should we mention that becoming a committer is by invitation only? -jg)*

See `ASF roles`_ for more information.

.. _developer: http://www.apache.org/foundation/how-it-works.html#developers
.. _committers: http://www.apache.org/foundation/how-it-works.html#committers

.. _ASF roles: http://www.apache.org/foundation/how-it-works.html#roles

Developer Mailing List
======================

Development issues such as patches, bug fixes, ideas, etc are discussed
on the python-dev mailing list. Subscribe to the python-dev@httpd.apache.org
list by mailing python-dev-subscribe@httpd.apache.org.  This is a advanced
topic list for people who are versed in C and Apache httpd internals. 

The mailing list archive is available from gmane.org. See
http://dir.gmane.org/gmane.comp.apache.mod-python.devel


*(I borrowed this bit from the website. I think we could re-phrase this to 
be a little less intimidating. People with good python skills but no knowledge
of apache internals or C can still make valuable contributions. -jg)*

Issue Tracking
==============

The mod_python project uses JIRA. The best way to ensure
your improvements, suggestions or bug reports are not lost in the noise of the
mailing list is to create a new issue in JIRA. Likewise, if you have a patch
you want to submit it is best to attach it to the appropriate JIRA issue rather
than sending it to directly to the mailing list. The python-dev mailing list
automatically receives a message when a JIRA issue is created or modified so
you can be assured your issue will get noticed.

See http://issues.apache.org/jira/browse/MODPYTHON.

.. _issue tracking: http://issues.apache.org/jira/browse/MODPYTHON

Subversion Code Repository
==========================

The mod_python project uses Subversion for version control. You can browse_
the repository online. For more help on using Subversion, consult the `Subversion website`_ or 
the `Subversion book`_. The web site provides a list of `clients and useful
links`_.

.. _browse: http://svn.apache.org/viewcvs.cgi/httpd/mod_python/

.. _Subversion website: http://subversion.tigris.org/
.. _Subversion book: http://svnbook.red-bean.com/
.. _clients and useful links: http://subversion.tigris.org/project_links.html

Anonymous Subversion Checkout
-----------------------------

To access the Subversion repositories anonymously, you will need a Subversion
client.

Choose the branch you would like to work on and check it out. For example, 
to get the current development branch (trunk), use::

  svn co http://svn.apache.org/repos/asf/httpd/mod_python/trunk mod_python

Subversion Commit Notifications
-------------------------------

Subversion commit notifications are available on the  python-cvs mailing list.
Subscribe to the python-cvs@httpd.apache.org mailing list by mailing
python-cvs-subscribe@httpd.apache.org.


Writing Code
============

You should develop your code using the working copy of mod_python you checked
out with Subversion.

Coding Style
------------

Python
......

Indent your code with 4 spaces.

*(Let's expand this section with some good general recommendations. -jg)*


C Language
..........

For C-language coding style, follow the `Apache Developers' C Language Style
Guide`_.

.. _Apache Developers' C Language Style Guide: http://www.apache.org/dev/styleguide.html


Comments
........

As per the Apache style guide, use only C-style comments in your C-code. 
Do not use C++ style comments.

Use the Doxygen format for comments.

*(I'll add a quick and dirty guide to doxygen. -jg)*


Unit Tests
==========

We like unit tests. Get in the habit of running the tests when you modify some
code. Likewise it's very helpful if you can write unit tests for your new code.

*(Maybe stick a simple example explaining how to write a unit test here? -jg)*


Documentation
=============

Ideally you'll provide documentation for your code as a patch to the current
docs.  However, if you don't feel comfortable writing LaTex code feel
free to write in plain text. Heck, we'll accept good documentation in just
about any format.

Preparing Your Code For Submission
==================================

The preferred form for submitted code is as a patch created as a diff against
the current development branch. The diffs should be in the unified diff
format. Luckily, Subversion makes this easy. To create a patch for 
changes made to src/util.c use svn diff::

  svn diff src/util.c > jg-20051114.diff

Choose a reasonable name for your patch. Files attached to a JIRA issue
are sorted alphabetically and listed at the top of the JIRA page for that
issue. It'll make it easier to understand what has been uploaded if you
adopt a consistent naming scheme.

*(Perhaps we can agree on a naming scheme that contributors would be 
urged to adopt. Take a look at `MODPYTHON-77`_ to see why this is desirable.)*

.. _MODPYTHON-77: http://issues.apache.org/jira/browse/MODPYTHON-77

License
=======

As with all Apache Software Foundation projects, mod_python is licensed under
the current `Apache Software License (ASL)`_, `Version 2.0`_.

.. _Apache Software License (ASL): http://www.apache.org/licenses
.. _Version 2.0: http://www.apache.org/licenses/LICENSE-2.0.html
