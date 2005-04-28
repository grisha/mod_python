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

    def __init__(self, req, sid=0, secret=None, timeout=0, lock=1,
                fast_cleanup=True, verify_cleanup=False, grace_period=240):
        
        opts = req.get_options()
        self._sessdir = opts.get('FileSessionDir',tempdir)
        
        self._fast_cleanup = fast_cleanup
        self._verify_cleanup = verify_cleanup
        self._grace_period = grace_period
        if timeout:
            self._cleanup_timeout = timeout
        else:
            self._cleanup_timeout = Session.DFT_TIMEOUT
        
        Session.BaseSession.__init__(self, req, sid=sid, secret=secret,
            timeout=timeout, lock=lock)

    def do_cleanup(self):
        data = {'req':self._req,
                'sessdir':self._sessdir,
                'fast_cleanup':self._fast_cleanup, 
                'verify_cleanup':self._verify_cleanup, 
                'timeout':self._cleanup_timeout,
                'grace_period':self._grace_period}

        self._req.register_cleanup(filesession_cleanup, data)
        self._req.log_error("FileSession: registered filesession cleanup.",
                            apache.APLOG_NOTICE)

    def do_load(self):
        self.lock_file()
        try:
            try:
                filename = os.path.join(self._sessdir, 'mp_sess_%s' % self._sid)
                fp = file(filename,'rb')
                try:
                    data = cPickle.load(fp)
                    if (time.time() - data["_accessed"]) <= data["_timeout"]:
                        # Change the file access time to the current time so the 
                        # cleanup does not delete this file before the request
                        # can save it's session data
                        os.utime(filename,None)
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
                filename = os.path.join(self._sessdir, 'mp_sess_%s' % self._sid)
                fp = file(filename, 'wb')
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


def filesession_cleanup(data):
    # There is a small chance that a the cleanup for a given session file
    # may occur at the exact time that the session is being accessed by
    # another request. It is possible under certain circumstances for that
    # session file to be saved in another request only to immediately deleted
    # by the cleanup. To avoid this race condition, a session is allowed a 
    # grace_period before it is considered for deletion by the cleanup. 
    # As long as the grace_period is longer that the time it takes to complete
    # the request (which should normally be less than 1 second), the session will
    # not be mistakenly deleted by the cleanup. By doing this we also avoid the
    # need to lock individual sessions and bypass any potential deadlock
    # situations.
   
    req = data['req']
    sessdir = data['sessdir']
    fast_cleanup = data['fast_cleanup']
    verify_cleanup = data['verify_cleanup']
    timeout = data['timeout']
    grace_period = data['grace_period']

    req.log_error('Sessions cleanup (fast=%s, verify=%s) ...'
        % (fast_cleanup,verify_cleanup),
        apache.APLOG_NOTICE)

    lockfile = os.path.join(sessdir,'.mp_sess.lck')
    try:
        lockfp = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0660) 
    except:
        req.log_error('filesession_cleanup: another process is already running.') 
        return

    try:
        start_time = time.time()
        filelist =  os.listdir(sessdir)
        count = 0
        i = 0
        for f in filelist:
            if not f.startswith('mp_sess_'):
                continue
            try:
                filename = os.path.join(sessdir, f)
                if fast_cleanup:
                    accessed = os.stat(filename).st_mtime
                    if time.time() - accessed < (timeout + grace_period):
                        continue

                if fast_cleanup and not verify_cleanup:        
                    delete_session = True
                else:
                    try:
                        fp = file(filename)
                        dict = cPickle.load(fp)
                        if (time.time() - dict['_accessed']) > (dict['_timeout'] + grace_period):
                            delete_session = True
                        else:
                            delete_session = False
                    finally:
                        fp.close()
                if delete_session:
                    os.unlink(filename)
                    count += 1
            except:
                s = cStringIO.StringIO()
                traceback.print_exc(file=s)
                s = s.getvalue()
                req.log_error('Error while cleaning up the sessions : %s' % s)

        elapsed_time = time.time() - start_time
        req.log_error('filesession cleanup: %d of %d in %.4f seconds' % (count,len(filelist), elapsed_time))
   
        try:
            os.unlink(lockfile)
        except:
            pass

    finally:
        os.close(lockfp)
