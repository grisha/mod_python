from mod_python import apache

def handler(req):
    req.content_type = 'text/plain'
    t = apache.make_table()
    t2 = apache.make_table()
    t3 = apache.table()

    req.write('ok table:')
    return apache.OK
