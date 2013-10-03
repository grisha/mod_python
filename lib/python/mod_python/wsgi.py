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

def handler(req):

    # using a closure is faster than an object-based implementation
    def start_response(status, headers, exc_info=None):

        if exc_info:
            try:
                raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                exc_info = None

        # avoid str2int conversion for frequently used ones
        if status == '200':
            req.status = 200
        elif status == '301':
            req.status = 301
        elif status == '302':
            req.status = 302
        else:
            req.status = int(status[:3])

        # There is no need to req.set_content_length() or set
        # req.content_type because it will be in the headers anyhow.
        for k,v in headers: 
            req.headers_out.add(k,v)
        
        return req.write

    options = req.get_options()

    ## Find the application callable

    app = None
    app_str = options['mod_python.wsgi.application']
    if app_str:
        if '::' in app_str:
            mod_str, callable_str = app_str.split('::', 1)
        else:
            mod_str, callable_str = app_str, 'application'
        config = req.get_config()
        autoreload, log = True, False
        if "PythonAutoReload" in config:
            autoreload = config["PythonAutoReload"] == "1"
        if "PythonDebug" in config:
            log = config["PythonDebug"] == "1"
        module = apache.import_module(mod_str, autoreload=autoreload, log=log)

        try:
            app = module.__dict__[callable_str]
        except KeyError: pass

    if not app:
        req.log_error(
            'WSGI handler: mod_python.wsgi.application (%s) not found, declining.'
            % `app_str`, apache.APLOG_WARNING)
        return apache.DECLINED

    ## Build env

    env = req.build_wsgi_env()
    if env is None:
        base_uri = options.get('mod_python.wsgi.base_uri')
        req.log_error(
            "WSGI handler: req.uri (%s) does not start with mod_python.wsgi.base_uri (%s), declining."
            % (`req.uri`, `base_uri`), apache.APLOG_WARNING)
        return apache.DECLINED

    ## Run the app

    response = None
    try:
        response = app(env, start_response)
        [req.write(token) for token in response]
    finally:
        # call close() if there is one
        if type(response) not in (list, tuple):
            getattr(response, 'close', lambda: None)()

    return apache.OK


