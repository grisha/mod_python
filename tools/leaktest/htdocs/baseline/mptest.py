from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    req.write('ok baseline:')
    return apache.OK
