from mod_python import apache, util

def handler(req):
    req.content_type = 'text/plain'
    fs = util.FieldStorage(req)
    req.write('ok fieldstorage:\n')
    keys = fs.keys()
    keys.sort()
    for k in keys:
        req.write('\n%s: ' % k)
        req.write(str(fs.getlist(k)))
    
    return apache.OK
