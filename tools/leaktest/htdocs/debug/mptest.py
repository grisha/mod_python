"""This handler is not part of any leaktest. It is only used to debug the 
leaktest client application.
"""

from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    req.write('ok debug:')
    return apache.OK
