"""
 (C) Gregory Trubetskoy, 1998 <grisha@ispol.com>

 This file is part of Httpdapy.
 
 This module allows one to use the Z Object Publisher (formerly Bobo) with
 Httpdapy. This gives you the power of Zope object publishing along with the
 speed of Httpdapy. It doesn't get any better than this!

 WHAT IS THIS ZPublisher?????

 ZPublisher is a component of Zope. While I don't profess at Zope itself as it
 seems to be designed for different type of users than me, I do think that the
 ZPublisher provides an ingenously simple way of writing WWW applications in
 Python.

 Take a look at the zpublisher_hello.py file. Notice how it has one method
 defined in it. Through ZPublisher, that method can be invoked through the web
 via a URL similar to this: 

 http://www.domain.tld/site/zpublisher_hello/sayHello and
 http://www.domain.tld/site/zpublisher_hello/sayHello?name=Joe

 If the above didn't "click" for you, go read the ZPublisher documentation at
 http://classic.zope.org:8080/Documentation/Reference/ObjectPublishingIntro
 for a more in-depth explanation.

 QUICK START

 1. Download and install Zope. 
 2. Don't start it. You're only interested in ZPublisher, and in order for
    it to work, Zope doesn't need to be running.
 3. Pick a www directory where you want to use ZPublisher. For our purposes
    let's imagine it is accessible via http://www.domain.tld/site. 
 4. Make sure that the FollowSymLinks option is on for this directory 
    in httpd.conf.
 5. Make a symlink in this directory to the ZPublisher directory:
    cd site
    ln -s /usr/local/src/Zope-2.1.0-src/lib/python/ZPublisher .
 5. Verify that it is correct:
    ls -l
    lrwxr-xr-x  1 uid group    53 Dec 13 12:15 ZPublisher -> /usr/local/src/Zope-2.1.0-src/lib/python/ZPublisher
 6. Create an .htaccess file with this in it:
      SetHandler python-program
      PythonOption handler httpdapi_publisher
      PythonOption debug 1
 7. Look at http://www.domain.tld/site/zpublisher_hello/sayHello?name=Joe

 Noteworthy:
 
 This module automatically reloads modules just like httpdapy does with
 autoreload on. But modules that are imported by your code will not get
 reloaded. There are ways around having to restart the server for script
 changes to take effect. For example, let's say you have a module called
 mycustomlib.py and you have a module that imports it. If you make a changes
 to mycustomlib.py, you can force the changes to take effect by requesting
 http://www.domain.tld/site/mycustomlib/.  You will get a server error, but
 mycustomelib should get reloaded.
 
 P.S.: Previous versions of this file contained references on how to get Zope
 (not just Zpublisher, but the whole shabang) work. Don't bother with it - it
 won't work with httpdapy. This is because of locking issues. Older versions
 of Zope had no locking, so different children of apache would corrupt the
 database by trying to access it at the same time. Starting with version 2
 Zope does have locking, however, it seems that the first child locks the
 database without ever releasing it and after that no other process can acess
 it.

"""

import apache
import os
import sys

try:
    import ZPublisher
except ImportError:
    import cgi_module_publisher
    ZPublisher = cgi_module_publisher

def publish(req):

    conf = req.get_config()

    # get module name to be published
    dir, file = os.path.split(req.filename)
    module_name, ext = os.path.splitext(file)

    # if autoreload is on, we will check dates
    # and reload the module if the source is newer
    apache.import_module(module_name, req)

    # setup CGI environment
    env, si, so = apache.setup_cgi(req)

    try:
        ZPublisher.publish_module(module_name, stdin=sys.stdin,
                                  stdout=sys.stdout, stderr=sys.stderr,
                                  environ=os.environ)
        s = `req.headers_out`
        f = open("/tmp/XXX", "w")
        f.write(s)
        f.close()
    finally:
        apache.restore_nocgi(env, si, so)

    return apache.OK








