from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    req.write('ok get_config:\n')
    req.write(str(req.get_config()))
    return apache.OK
