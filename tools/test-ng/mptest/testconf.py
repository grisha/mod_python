#
# Copyright 2006 Apache Software Foundation 
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
# $Id$
#

"""Test base classes derived from unittest.TestCase.

Mod_python unittests should subclass these classes rather than
directly subclassing TestCase.
"""


from cStringIO import StringIO
import httplib
import os
import random
import sys
import time
import unittest

readBlockSize = 65368


def make_server_name(obj):
    return  '%s.%s' % (obj.__module__.split('.',1)[1], obj.__class__.__name__)

def make_handler_name(obj):
    return  '%s::handler_%s' % (obj.__module__.split('.')[-1], obj.__class__.__name__)
    
def make_handler_filename(obj):
    return  '%s.py' % (obj.__module__.split('.')[2])

def make_document_root_name(obj):
    return  '%s/%s' % (obj.httpd.document_root, obj.__module__.split('.')[1])


class MpTestBase(object):
    def markLogStart(self):
        self.log_start = 0
        if os.path.exists(self.httpd.error_log):
            self.httpd.log_start = os.stat(self.httpd.error_log).st_size 

    def archiveConfigFile(self):
        self.config_archive = open(self.httpd.config_file, 'r').read()

    def archiveLogFile(self):
        f = open(self.httpd.error_log)
        f.seek(self.log_start)
        self.log_archive = f.read()
        f.close()

    def scanLog(search_str):
        raise NotImplementedError



class PerInstanceTestBase(unittest.TestCase, MpTestBase):
    """PerInstanceTestBase subclasses will get a clean 
    apache config file and an httpd restart
    """

    priority = 0

    # All tests are enabled by default
    # If disable == True, the test will be skipped
    # You can force the test to run with the -f option
    # eg.
    # $ python test.py -f some.test.name
    disable = False

    def __init__(self, httpd=None, document_root=None):
        super(PerInstanceTestBase, self).__init__()
        self.httpd = httpd

        if document_root:
            self.document_root = document_root
 
        if not hasattr(self, 'document_root'):
            self.document_root = make_document_root_name(self)
        if not hasattr(self, 'server_name'):
            self.server_name = make_server_name(self)
        if not hasattr(self, 'handler'):
            self.handler = make_handler_name(self)
        if not hasattr(self, 'handler_file'):
            self.handler_file = make_handler_filename(self)
        
       
 
    def setUp(self):
        self.markLogStart()
        self.httpd.start()

    def tearDown(self):
        if self.httpd.httpd_running:
            self.httpd.stop()
        self.archiveConfigFile()
        self.archiveLogFile()

    def config(self):
        return ''


class PerRequestTestBase(unittest.TestCase, MpTestBase):
    priority = 0

    # All tests are enabled by default
    # If disable == True, the test will be skipped
    # You can force the test to run with the -f option
    # eg.
    # $ python test.py -f some.test.name
    disable = False


    def __init__(self, httpd=None, document_root=None):
        super(PerRequestTestBase, self).__init__()
        self.httpd = httpd

        if document_root:
            self.document_root = document_root

        if not hasattr(self, 'document_root'):
            self.document_root = make_document_root_name(self)
        if not hasattr(self, 'server_name'):
            self.server_name = make_server_name(self)
        if not hasattr(self, 'handler'):
            self.handler = make_handler_name(self)
        if not hasattr(self, 'handler_file'):
            self.handler_file = make_handler_filename(self)
        

    def setUp(self):
        self.markLogStart()
        if not self.httpd.httpd_running:
            self.httpd.start()

    def tearDown(self):
        self.archiveConfigFile()
        self.archiveLogFile()

    def config(self):
        return ''

    def vhost_get(self, vhost, path=None):
        # allows to specify a custom host: header
        if path is None:
            if hasattr(self, 'handler_file'):
                path = '/%s' % self.handler_file
            else:
                path = '/tests.py'

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        conn.putrequest("GET", path, skip_host=1)
        conn.putheader("Host", "%s:%s" % (vhost, self.httpd.port))
        conn.endheaders()
        response = conn.getresponse()
        rsp = response.read()
        conn.close()

        return rsp


    def vhost_post_multipart_form_data(self, vhost, path=None,variables={}, files={}):
        # variables is a { name : value } dict
        # files is a { name : (filename, content) } dict


        if path is None:
            if hasattr(self, 'handler_file'):
                path = '/%s' % self.handler_file
            else:
                path = '/tests.py'

        # build the POST entity
        entity = StringIO()
        # This is the MIME boundary
        boundary = "============="+''.join( [ random.choice('0123456789') for x in range(10) ] )+'=='
        # A part for each variable
        for name, value in variables.iteritems():
            entity.write('--')
            entity.write(boundary)
            entity.write('\r\n')
            entity.write('Content-Type: text/plain\r\n')
            entity.write('Content-Disposition: form-data; name="%s"\r\n'%name)
            entity.write('\r\n')
            entity.write(str(value))
            entity.write('\r\n')

        # A part for each file
        for name, filespec in files.iteritems():
            filename, content = filespec
            # if content is readable, read it
            try:
                content = content.read()
            except:
                pass

            entity.write('--')
            entity.write(boundary)
            entity.write('\r\n')

            entity.write('Content-Type: application/octet-stream\r\n')
            entity.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'%(name,filename))
            entity.write('\r\n')
            entity.write(content)
            entity.write('\r\n')

        # The final boundary
        entity.write('--')
        entity.write(boundary)
        entity.write('--\r\n')
        
        entity = entity.getvalue()

        conn = httplib.HTTPConnection("127.0.0.1:%s" % self.httpd.port)
        # conn.set_debuglevel(1000)
        conn.putrequest("POST", path, skip_host=1)
        conn.putheader("Host", "%s:%s" % (vhost, self.httpd.port))
        conn.putheader("Content-Type", 'multipart/form-data; boundary="%s"'%boundary)
        conn.putheader("Content-Length", '%s'%(len(entity)))
        conn.endheaders()

        start = time.time()
        conn.send(entity)
        response = conn.getresponse()
        rsp = response.read()
        conn.close()
        print '    --> Send + process + receive took %.3f s'%(time.time()-start)

        return rsp

