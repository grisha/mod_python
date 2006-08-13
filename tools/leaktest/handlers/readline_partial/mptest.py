from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    count = 0
    for i in range(0, 20):
        line = req.readline()
        count += 1

    req.write('ok readline_partial: %d lines read' % count)
    return apache.OK
