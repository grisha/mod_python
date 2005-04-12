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
                timeout=0, lock=1,
                fast_cleanup=True, verify_cleanup=False):
        
        opts = req.get_options()
        self._sessdir = opts.get('FileSessionDir',tempdir)
        
        self._fast_cleanup = fast_cleanup
        self._verify_cleanup = verify_cleanup
        if timeout:
            self._fast_timeout = timeout
        else:
            self._fast_timeout = Session.DFT_TIMEOUT
        
        Session.BaseSession.__init__(self, req, sid=sid, secret=secret,
            timeout=timeout, lock=lock)

    def do_cleanup(self):
        # WARNING - this method does no file locking.
        # Problems may lurk here.
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
            
                # FIXME - What happens if another process saved it's
                # session data to filename after the above test but
                # before we have a chance to deleted the file below?
                # WARNING - We may be deleting a completely valid session file.
                # Oops. Sorry.
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
        self.lock_file()
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
            self.unlock_file()

    def do_save(self, dict):
        self.lock_file()
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
            self.unlock_file()

    def do_delete(self):
        self.lock_file()
        try:
            try:
                os.unlink(os.path.join(self._sessdir, 'mp_sess_%s' % self._sid))
            except Exception:
                pass
        finally:
            self.unlock_file()

    def lock_file(self):
        # self._lock = 1 indicates that session locking is turned on,
        # so let BaseSession handle it.
        # Otherwise, explicitly acquire a lock for the file manipulation.
        if not self._locked:
            _apache._global_lock(self._req.server, self._sid)
            self._locked = 1

    def unlock_file(self):
        if self._locked and not self._lock:
            _apache._global_unlock(self._req.server, self._sid)
            self._locked = 0
