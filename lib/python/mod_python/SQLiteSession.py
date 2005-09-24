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
 # $Id: Session.py 231126 2005-08-09 22:26:38Z jgallacher $   
from Session import *
from time import time

ISOLATION_LEVEL = None

# TODO : solve the problem with an exception being raised when
# the database file is locked and wee try to read/write to it. This
# could be solved by carefully selecting an ISOLATION_LEVEL.

try:
    # If this code is included into Session.py,
    # we don't want to add a dependency to SQLite
    from pysqlite2 import dbapi2 as sqlite
except:
    pass
else:
    class SQLiteSession(BaseSession):
        """ A session implementation using SQLite to store session data.
            pysqlite2 is required, see http://pysqlite.org/
        """
    
        def __init__(self, req, filename=None, sid=0, secret=None, timeout=0, lock=1):
            # if no filename is given, get it from PythonOption
            if not filename:
                opts = req.get_options()
                if opts.has_key("session_filename"):
                    filename = opts["session_filename"]
                else:
                    # or build a session file in a temporary directory
                    filename = os.path.join(
                        opts.get('session_directory', tempdir),
                        'mp_sess.sqlite'
                    )
    
            self.filename = filename
    
            # check whether the sessions table exists, and create it if not
            db = sqlite.connect(self.filename, isolation_level=ISOLATION_LEVEL)
            try:
                try:
                    cur = db.cursor()
                    cur.execute("""
                        select name from sqlite_master
                        where name='sessions' and type='table'
                    """)
                    if cur.fetchone() is None:
                        cur.execute("""
                            create table sessions
                            (id text,data blob,timeout real)
                        """)
                        cur.execute("""
                            create unique index idx_session on sessions (id)
                        """)
                        db.commit()
                finally:
                    cur.close()
            finally:
                db.close()

            BaseSession.__init__(self, req, sid=sid, secret=secret,
                                 timeout=timeout, lock=lock)

        def count(self):
            db = sqlite.connect(self.filename, isolation_level=ISOLATION_LEVEL)
            try:
                try:
                    cur = db.cursor()
                    cur.execute("select count(*) from sessions")
                    return cur.fetchone()[0]
                finally:
                    cur.close()
            finally:
                db.close()

        def do_cleanup(self):
            db = sqlite.connect(self.filename, isolation_level=ISOLATION_LEVEL)
            try:
                try:
                    cur = db.cursor()
                    cur.execute(
                        "delete from sessions where timeout<?",
                        (time(),)
                    )
                    db.commit()
                finally:
                    cur.close()
            finally:
                db.close()
    
        def do_load(self):
            db = sqlite.connect(self.filename, isolation_level=ISOLATION_LEVEL)
            try:
                try:
                    cur = db.cursor()
                    cur.execute(
                        "select data from sessions where id=?",
                        (self._sid,)
                    )
                    row = cur.fetchone()
                    if row is None:
                        return None
                    else:
                        return cPickle.loads(str(row[0]))
                finally:
                    cur.close()
            finally:
                db.close()
    
        def do_save(self, dict):
            db = sqlite.connect(self.filename, isolation_level=ISOLATION_LEVEL)
            try:
                try:
                    cur = db.cursor()
                    data = buffer(cPickle.dumps(dict,2))
                    timeout = self._accessed+self._timeout
                    cur.execute("""
                        insert or replace into sessions (id,data,timeout)
                        values (?,?,?)
                    """,(self._sid,data,timeout))
                    db.commit()
                finally:
                    cur.close()
            finally:
                db.close()
    
        def do_delete(self):
            db = sqlite.connect(self.filename, isolation_level=ISOLATION_LEVEL)
            try:
                try:
                    cur = db.cursor()
                    cur.execute(
                        "delete from sessions where id=?",
                        (self._sid,)
                    )
                finally:
                    cur.close()
            finally:
                db.close()
