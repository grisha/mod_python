"""
 (C) Gregory Trubetskoy, 1998 <grisha@ispol.com>

 XXX This handler leaks memory whith scripts processing large
 POST operations with cgi.py.
 

"""

import apache
import imp
import os

# the next statement  deserves some explaining.
# it seems that the standard os.environ object looses
# memory if the environment is manipulated frequently. Since for
# CGI you have to rebuild it for every request, your httpd will
# grow rather fast. I am not exactly sure why it happens and if there
# is a more sensible remedy, but this seems to work OK.
os.environ = {}

def handler(req):

    # get the filename of the script
    if req.subprocess_env.has_key("script_filename"):
        dir, file = os.path.split(req.subprocess_env["script_filename"])
    else:
        dir, file = os.path.split(req.filename)
    module_name, ext = os.path.splitext(file)

    # we must chdir, because mod_python will cd into
    # directory where the handler directive was last
    # encountered, which is not always the same as
    # where the file is....
    os.chdir(dir)

    try:

        # simulate cgi environment
        env, si, so = apache.setup_cgi(req)

        try:
            # we do not search the pythonpath (security reasons)
            fd, path, desc = imp.find_module(module_name, [dir])
        except ImportError:
            raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

        # this executes the module
        imp.load_module(module_name, fd, path, desc)

        return apache.OK

    finally:
        # unsimulate the cgi environment
        apache.restore_nocgi(env, si, so)
        try:
            fd.close()
        except: pass


