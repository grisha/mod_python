"""This is not a leaktest. It is used to get the mod_python version string"""
from mod_python import apache, version

def handler(req):
    req.content_type = 'text/plain'
    req.write(version)
    return apache.OK
