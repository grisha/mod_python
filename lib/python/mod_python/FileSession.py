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

import cPickle
import tempfile
import os, os.path
import apache, _apache
import cStringIO
import time
import traceback

from mod_python import Session

tempdir = tempfile.gettempdir()

# Credits : this was initially contributed by dharana <dharana@dharana.net>
class FileSession(Session.BaseSession):
    def __init__(self, req, sid=0, secret=None,
                timeout=0, lock=0,
                fast_cleanup=True, verify_cleanup=False):
        
        opts = req.get_options()
        self._fast_cleanup = fast_cleanup
        self._verify_cleanup = verify_cleanup
        self._fast_timeout = timeout
        self._sessdir = opts.get('FileSessionDir',tempdir)
        Session.BaseSession.__init__(self, req, sid=sid, secret=secret,
            timeout=timeout, lock=lock)

    def do_cleanup(self):
        self._req.log_error('Sessions cleanup (fast=%s, verify=%s) ...' 
            % (self._fast_cleanup,self._verify_cleanup),
            apache.APLOG_NOTICE)

        for f in os.listdir(self._sessdir):
            if not f.startswith('mp_sess_'):
                continue
            
            try:
                filename = os.path.join(self._sessdir, f)
                if self._fast_cleanup:
                    mtime = os.stat(filename).st_mtime
                    if time.time() - mtime < self._fast_timeout:
                        continue

                if self._fast_cleanup and not self._verify_cleanup:        
                        os.unlink(filename)
                else:
                    try:
                        fp = file(filename)
                        dict = cPickle.load(fp)
                        if (time.time() - dict['_accessed']) > dict['_timeout']:
                            os.unlink(filename)
                    finally:
                        fp.close()
            except:
                s = cStringIO.StringIO()
                traceback.print_exc(file=s)
                s = s.getvalue()
                self._req.log_error('Error while cleaning up the sessions : %s'%s)

    def do_load(self):
        _apache._global_lock(self._req.server, 'fl_%s' % self._sid)
        try:
            try:
                # again, is there a more pythonic way of doing this check?
                # TODO : why does this load fails sometimes with an EOFError ?
                fp = file(os.path.join(self._sessdir, 'mp_sess_%s' % self._sid))
                try:
                    data = cPickle.load(fp)
                    return data
                finally:
                    fp.close()
            except:
                s = cStringIO.StringIO()
                traceback.print_exc(file=s)
                s = s.getvalue()
                self._req.log_error('Error while loading a session : %s'%s)
                return None
        finally:
            _apache._global_unlock(self._req.server, 'fl_%s' % self._sid)

    def do_save(self, dict):
        _apache._global_lock(self._req.server, 'fl_%s' % self._sid)
        try:
            try:
                fp = file(os.path.join(self._sessdir, 'mp_sess_%s' % self._sid), 'w+')
                try:
                    cPickle.dump(dict, fp, 2)
                finally:
                    fp.close()
            except:
                s = cStringIO.StringIO()
                traceback.print_exc(file=s)
                s = s.getvalue()
                self._req.log_error('Error while saving a session : %s'%s)
        finally:
            _apache._global_unlock(self._req.server, 'fl_%s' % self._sid)

    def do_delete(self):
        _apache._global_lock(self._req.server, 'fl_%s' % self._sid)
        try:
            try:
                os.unlink(os.path.join(self._sessdir, 'mp_sess_%s' % self._sid))
            except Exception:
                pass
        finally:
            _apache._global_unlock(self._req.server, 'fl_%s' % self._sid)

