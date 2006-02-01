 #
 # Copyright 2004 Apache Software Foundation 
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
 # $Id$

# Loads Python 2.2 compatibility module
from python22 import *

"""

This module is a mod_python handler that can be used to test the configuration.

"""

from mod_python import apache, util
import sys, os

class bounded_buffer(object):
    """
        This class implements a bounded buffer, i.e. a list that keeps the last
        n lines. It doesn't use pop(0), which is costly.
    
    """
    def __init__(self,size):
        self.max_size = size
        self.list = []
        self.pos = 0
    
    def append(self,value):
        if len(self.list)<self.max_size:
            self.list.append(value)
        else:
            self.list[self.pos]=value
        self.pos = (self.pos+1)%self.max_size
    
    def items(self):
        return self.list[self.pos:]+self.list[:self.pos]

    def __iter__(self):
        return iter(self.items())

def write_table(req,table):
    req.write('<table border="1">')
    req.write('<tr><th>Key</th><th>Value</th></tr>\n')
    for key in table:
        req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
            key,
            table[key]
        ))
    req.write('</table>')

def write_tree(req,tree,level):
    for entry in tree:
        if isinstance(entry,list):
            write_tree(req,entry,level+1)
        else:
            req.write('    '*level)
            req.write(' '.join(entry))
            req.write('\n')

def handler(req):
    req.form = util.FieldStorage(req)
    
    if req.form.getfirst('view_log'):
        log = file(os.path.join(apache.server_root(),req.server.error_fname),'rb')
        lines = bounded_buffer(100)
        for line in log:
            lines.append(line)
        log.close()
        req.content_type='text/plain'
        for line in lines:
            req.write(line)
        return apache.OK        

    req.add_common_vars()
    req.content_type = 'text/html'
    req.write('<html><head><title>mod_python test page</title></head><body>\n')
    
    req.write('<h3>General information</h3>\n')
    req.write('<table border="1">\n')
    req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
        'Apache version',
        req.subprocess_env.get('SERVER_SOFTWARE')
    ))
    req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
        'Apache threaded MPM',
        (
            apache.mpm_query(apache.AP_MPMQ_IS_THREADED) and
            'Yes, maximum %i threads / process'%
            apache.mpm_query(apache.AP_MPMQ_MAX_THREADS)
        ) or 'No (single thread MPM)'
    ))
    req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
        'Apache forked MPM',
        (
            apache.mpm_query(apache.AP_MPMQ_IS_FORKED) and
            'Yes, maximum %i processes'%
            apache.mpm_query(apache.AP_MPMQ_MAX_DAEMONS)
        ) or 'No (single process MPM)'
    ))
    req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
        'Apache server root',
        apache.server_root()
    ))
    req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
        'Apache document root',
        req.document_root()
    ))
    if req.server.error_fname:
        req.write('<tr><td><code>%s</code></td><td><code>%s</code> (<a href="?view_log=1" target="_new">view last 100 lines</a>)</td></tr>\n'%(
            'Apache error log',
            os.path.join(apache.server_root(),req.server.error_fname)
        ))
    else:
        req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
            'Apache error log',
            'None'
        ))
    req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
        'Python sys.version',
        sys.version
    ))
    req.write('<tr><td><code>%s</code></td><td><pre>%s</pre></td></tr>\n'%(
        'Python sys.path',
        '\n'.join(sys.path)
    ))
    req.write('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>\n'%(
        'Python interpreter name',
        req.interpreter
    ))
    req.write('<tr><td><code>mod_python.publisher available</code></td><td><code>')
    try:
        from mod_python import publisher
        req.write('Yes')
    except:
        req.write('No')
    req.write('</code></td></tr>\n')
    req.write('<tr><td><code>mod_python.psp available</code></td><td><code>')
    try:
        from mod_python import psp
        req.write('Yes')
    except:
        req.write('No')
    req.write('</code></td></tr>\n')
    req.write('</table>\n')

    req.write('<h3>Request input headers</h3>\n')
    write_table(req,req.headers_in)    

    req.write('<h3>Request environment</h3>\n')
    write_table(req,req.subprocess_env)    

    req.write('<h3>Request configuration</h3>\n')
    write_table(req,req.get_config())    

    req.write('<h3>Request options</h3>\n')
    write_table(req,req.get_options())    

    req.write('<h3>Request notes</h3>\n')
    write_table(req,req.notes)

    req.write('<h3>Server configuration</h3>\n')
    write_table(req,req.server.get_config())

    req.write('<h3>Server configuration tree</h3>\n<pre>')
    write_tree(req,apache.config_tree(),0)
    req.write('</pre>\n')

    req.write('</body></html>')
    return apache.OK
