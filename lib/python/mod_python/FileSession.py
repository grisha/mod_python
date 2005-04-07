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

from mod_python import Session

tempdir = tempfile.gettempdir()

# Credits : this was initially contributed by dharana <dharana@dharana.net>
class FileSession(Session.BaseSession):
    def __init__(self, req, sid=0, secret=None, timeout=0, lock=1):
        Session.BaseSession.__init__(self, req, sid=sid, secret=secret,
            timeout=timeout, lock=lock)

    def do_cleanup(self):
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
            except Exception:
                # TODO : emit a warning to the Apache Log
                pass

    def do_load(self):
        try:
            # again, is there a more pythonic way of doing this check?
            fp = file('%s/mp_sess_%s' % (tempdir, self._sid))
            try:
                data = cPickle.load(fp)
                return data
            finally:
                fp.close()
        except:
            return None

    def do_save(self, dict):
        fp = file('%s/mp_sess_%s' % (tempdir, self._sid), 'w+')
        try:
            cPickle.dump(dict, fp)
        finally:
            fp.close()

    def do_delete(self):
        try:
            os.unlink('%s/mp_sess_%s' % (tempdir, self._sid))
        except Exception:
            pass
