from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    r = req.requires()
    req.write('ok requires:\n')
    req.write(str(r))
    return apache.OK
