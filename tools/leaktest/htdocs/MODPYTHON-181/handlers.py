
from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    req.write('handler')
    return apache.OK

def fixuphandler(req):
    return apache.OK
