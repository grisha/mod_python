from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    count = 0
    while(1):
        line = req.readline()
        if not line:
            break
        count += 1

    req.write('ok readline: %d lines read' % count)
    return apache.OK
