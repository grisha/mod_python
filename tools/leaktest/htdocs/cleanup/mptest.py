from mod_python import apache, util

def handler(req):
    req.content_type = 'text/plain'
    lines = req.readlines()
    req.write('ok register_cleanup: %d lines read' % len(lines))
    return apache.OK
