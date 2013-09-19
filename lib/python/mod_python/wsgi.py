 #
 # Copyright (C) 2000, 2001, 2013 Gregory Trubetskoy
 # Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007 Apache Software Foundation
 #
 # Licensed under the Apache License, Version 2.0 (the "License"); you
 # may not use this file except in compliance with the License.  You
 # may obtain a copy of the License at
 #
 #      http://www.apache.org/licenses/LICENSE-2.0
 #
 # Unless required by applicable law or agreed to in writing, software
 # distributed under the License is distributed on an "AS IS" BASIS,
 # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 # implied.  See the License for the specific language governing
 # permissions and limitations under the License.
 #
 # Originally developed by Gregory Trubetskoy.
 #

import sys
from mod_python import apache

class WSGIContainer(object):
    
    def __init__(self, req):
        self.req = req
    
    def start_response(self, status, headers, exc_info=None):

        if exc_info:
            try:
                raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                exc_info = None
        
        self.req.status = int(status[:3])

        # There is no need to req.set_content_length() or set
        # req.content_type because it will be in the headers anyhow.
        for k,v in headers: 
            self.req.headers_out.add(k,v)
        
        return self.req.write
    
    def run(self, application, env):
        response = None
        try:
            response = application(env, self.start_response)
            map(self.req.write, response)
        finally:
            # call close() if there is one
            getattr(response, 'close', lambda: None)()

def handler(req):

    options = req.get_options()

    ## Process wsgi.base_uri

    base_uri = options.get('wsgi.base_uri', '')

    if base_uri == '/' or base_uri.endswith('/'):
        req.log_error(
            "WSGI handler: wsgi.base_uri (%s) must not be '/' or end with '/', declining."
            % `base_uri`, apache.APLOG_WARNING)
        return apache.DECLINED

    if req.uri.startswith(base_uri):
        req.path_info = req.uri[len(base_uri):]
    else:
        req.log_error(
            "WSGI handler: req.uri (%s) does not start with wsgi.base_uri (%s), declining."
            % (`req.uri`, `base_uri`), apache.APLOG_WARNING)
        return apache.DECLINED

    ## Find the application callable

    app = None
    app_str = options.get('wsgi.application')
    if app_str:
        mod_str, callable_str = (app_str.split('::', 1) + [None])[0:2]
        module = apache.import_module(mod_str, log=True)
        app = getattr(module, callable_str or 'application')

    if not app:
        req.log_error(
            'WSGI handler: wsgi.application (%s) not found, declining.'
            % `app_str`, apache.APLOG_WARNING)
        return apache.DECLINED

    ## Build env

    req.add_cgi_vars()
    env = dict(req.subprocess_env)

    if req.headers_in.has_key("authorization"):
        env["HTTP_AUTHORIZATION"] = req.headers_in["authorization"]

    env['wsgi.input'] = req
    env['wsgi.errors'] = sys.stderr
    env['wsgi.version'] = (1, 0)
    env['wsgi.multithread']  = apache.mpm_query(apache.AP_MPMQ_IS_THREADED)
    env['wsgi.multiprocess'] = apache.mpm_query(apache.AP_MPMQ_IS_FORKED)
    if env.get('HTTPS', 'off') == 'off':
        env['wsgi.url_scheme'] = 'http'
    else:
        env['wsgi.url_scheme'] = 'https'

    ## Run the app

    WSGIContainer(req).run(app, env)

    return apache.OK

