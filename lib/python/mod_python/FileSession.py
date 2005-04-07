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
import os
import apache, _apache
import cStringIO
import traceback

from mod_python import Session

tempdir = tempfile.gettempdir()

# Credits : this was initially contributed by dharana <dharana@dharana.net>
class FileSession(Session.BaseSession):
    def __init__(self, req, sid=0, secret=None, timeout=0, lock=1):
        Session.BaseSession.__init__(self, req, sid=sid, secret=secret,
            timeout=timeout, lock=lock)

    def do_cleanup(self):
        self._req.log_error('Sessions cleanup...',apache.APLOG_NOTICE)

        # is there any faster way of doing this?
        for f in os.listdir(tempdir):
            if not f.startswith('mp_sess_'):
                continue

            try:
                fp = file('%s/%s' % (tempdir, f))
                try:
                    dict = cPickle.load(fp)
                    if (time() - dict['_accessed']) > dict['_timeout']:
                        os.unlink('%s%s' % (tempdir, f))
                finally:
                    fp.close()
            except:
                s = cStringIO.StringIO()
                traceback.print_exc(file=s)
                s = s.getvalue()
                self._req.log_error('Error while cleaning up the sessions : %s'%s)

    def do_load(self):
        _apache._global_lock(self._req.server, self._sid)
        try:
            try:
                # again, is there a more pythonic way of doing this check?
                # TODO : why does this load fails sometimes with an EOFError ?
                fp = file('%s/mp_sess_%s' % (tempdir, self._sid))
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
            _apache._global_unlock(self._req.server, self._sid)

    def do_save(self, dict):
        _apache._global_lock(self._req.server, self._sid)
        try:
            try:
                fp = file('%s/mp_sess_%s' % (tempdir, self._sid), 'w+')
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
            _apache._global_unlock(self._req.server, self._sid)

    def do_delete(self):
        _apache._global_lock(self._req.server, self._sid)
        try:
            try:
                os.unlink('%s/mp_sess_%s' % (tempdir, self._sid))
            except Exception:
                pass
        finally:
            _apache._global_unlock(self._req.server, self._sid)
