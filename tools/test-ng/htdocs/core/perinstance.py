from mod_python import apache
import time


def global_lock(req):

    import _apache

    _apache._global_lock(req.server, 1)
    time.sleep(1)
    _apache._global_unlock(req.server, 1)

    req.write("test ok")
    
    return apache.OK


def server_cleanup(data):
    # for srv_register_cleanup and apache_register_cleanup below

    apache.log_error(data)

def srv_register_cleanup(req):

    req.server.register_cleanup(req, server_cleanup, "srv_register_cleanup test ok")
    req.write("registered server cleanup that will write to log")

    return apache.OK


def apache_register_cleanup(req):

    apache.register_cleanup(server_cleanup, "apache_register_cleanup test ok")
    req.write("registered server cleanup that will write to log")

    return apache.OK


def apache_exists_config_define(req):
    if apache.exists_config_define('FOOBAR'):
        req.write('FOOBAR')
    else:
        req.write('NO_FOOBAR')
    return apache.OK


