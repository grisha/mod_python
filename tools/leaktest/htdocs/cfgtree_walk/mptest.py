from mod_python import apache, util

def handler(req):
    req.content_type = 'text/plain'
    cfg = apache.config_tree()
    req.write('ok cfgtree_walk:\n')
    req.write(str(cfg))
    return apache.OK
