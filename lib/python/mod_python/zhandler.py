"""
 (C) Gregory Trubetskoy, 1998 <grisha@ispol.com>

  $Id: zhandler.py,v 1.3 2000/05/11 22:54:39 grisha Exp $

"""

import apache
import os
import sys

# this will save memory
os.environ = {}

try:
    import ZPublisher
except ImportError:
    import cgi_module_publisher
    ZPublisher = cgi_module_publisher

def handler(req):

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
    finally:
        apache.restore_nocgi(env, si, so)

    return apache.OK








