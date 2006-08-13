from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    req.write('ok get_options:\n')
    req.write(str(req.get_options()))
    return apache.OK
