from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    req.write('ok allow_methods:')
    # this should raise an exception and cause a leak
    try:
        req.allow_methods([0])
    except TypeError:
        req.write(' EXCEPTION pass')
        pass
    
    return apache.OK
