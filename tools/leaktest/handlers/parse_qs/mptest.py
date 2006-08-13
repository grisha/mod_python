from mod_python import apache, util

def handler(req):
    req.content_type = 'text/plain'
    if req.args:
        query = util.parse_qs(req.args, 0)
    else:
        query = 'empty query string'
    req.write('ok parse_qs:\n')
    req.write(str(query))
    return apache.OK
