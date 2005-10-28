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

import apache, Cookie
import _apache

import os
import stat
import time
import anydbm, whichdb
import random
import md5
import cPickle, cStringIO
import tempfile
import traceback

COOKIE_NAME="pysid"
DFT_TIMEOUT=30*60 # 30 min
DFT_LOCK = True
CLEANUP_CHANCE=1000 # cleanups have 1 in CLEANUP_CHANCE chance

tempdir = tempfile.gettempdir()

def _init_rnd():
    """ initialize random number generators
    this is key in multithreaded env, see
    python docs for random """

    # query max number of threads

    
    if _apache.mpm_query(apache.AP_MPMQ_IS_THREADED):
        gennum = _apache.mpm_query(apache.AP_MPMQ_MAX_SPARE_THREADS)
    else:
        gennum = 10

    # make generators
    # this bit is from Python lib reference
    g = random.Random(time.time())
    result = [g]
    for i in range(gennum - 1):
       laststate = g.getstate()
       g = random.Random()
       g.setstate(laststate)
       g.jumpahead(1000000)
       result.append(g)

    return result

rnd_gens = _init_rnd()
rnd_iter = iter(rnd_gens)

def _get_generator():
    # get rnd_iter.next(), or start over
    # if we reached the end of it
    global rnd_iter
    try:
        return rnd_iter.next()
    except StopIteration:
        # the small potential for two threads doing this
        # seems does not warrant use of a lock
        rnd_iter = iter(rnd_gens)
        return rnd_iter.next()

def _new_sid(req):
    # Make a number based on current time, pid, remote ip
    # and two random ints, then hash with md5. This should
    # be fairly unique and very difficult to guess.

    t = long(time.time()*10000)
    pid = os.getpid()
    g = _get_generator()
    rnd1 = g.randint(0, 999999999)
    rnd2 = g.randint(0, 999999999)
    ip = req.connection.remote_ip

    return md5.new("%d%d%d%d%s" % (t, pid, rnd1, rnd2, ip)).hexdigest()
    
class BaseSession(dict):

    def __init__(self, req, sid=None, secret=None, lock=1,
                 timeout=0):

        self._req, self._sid, self._secret = req, sid, secret
        self._lock = lock
        self._new = 1
        self._created = 0
        self._accessed = 0
        self._timeout = 0
        self._locked = 0
        self._invalid = 0
        
        dict.__init__(self)

        session_cookie_name = req.get_options().get("session_cookie_name",COOKIE_NAME)

        if not self._sid:
            # check to see if cookie exists
            if secret:  
                cookies = Cookie.get_cookies(req, Class=Cookie.SignedCookie,
                                             secret=self._secret)
            else:
                cookies = Cookie.get_cookies(req)

            if cookies.has_key(session_cookie_name):
                self._sid = cookies[session_cookie_name].value

        self.init_lock()

        if self._sid:
            # attempt to load ourselves
            self.lock()
            if self.load():
                self._new = 0

        if self._new:
            # make a new session
            if self._sid: self.unlock() # unlock old sid
            self._sid = _new_sid(self._req)
            self.lock()                 # lock new sid
            Cookie.add_cookie(self._req, self.make_cookie())
            self._created = time.time()
            if timeout:
                self._timeout = timeout
            else:
                self._timeout = DFT_TIMEOUT

        self._accessed = time.time()

        # need cleanup?
        if random.randint(1, CLEANUP_CHANCE) == 1:
            self.cleanup()

    def make_cookie(self):
        session_cookie_name = self._req.get_options().get("session_cookie_name",COOKIE_NAME)

        if self._secret:
            c = Cookie.SignedCookie(session_cookie_name, self._sid,
                                    secret=self._secret)
        else:
            c = Cookie.Cookie(session_cookie_name, self._sid)

        config = self._req.get_options()
        if config.has_key("ApplicationPath"):
            c.path = config["ApplicationPath"]
        else:
            # the path where *Handler directive was specified
            dirpath = self._req.hlist.directory 
            if dirpath:
                docroot = self._req.document_root()
                c.path = dirpath[len(docroot):]
            else:
                c.path = '/'

            # Sometimes there is no path, e.g. when Location
            # is used. When Alias or UserDir are used, then
            # the path wouldn't match the URI. In those cases
            # just default to '/'
            if not c.path or not self._req.uri.startswith(c.path):
                c.path = '/'

        return c

    def invalidate(self):
        c = self.make_cookie()
        c.expires = 0
        Cookie.add_cookie(self._req, c)
        self.delete()
        self._invalid = 1

    def load(self):
        dict = self.do_load()
        if dict == None:
            return 0

        if (time.time() - dict["_accessed"]) > dict["_timeout"]:
            return 0

        self._created  = dict["_created"]
        self._accessed = dict["_accessed"]
        self._timeout  = dict["_timeout"]
        self.update(dict["_data"])
        return 1

    def save(self):
        if not self._invalid:
            dict = {"_data"    : self.copy(), 
                    "_created" : self._created, 
                    "_accessed": self._accessed, 
                    "_timeout" : self._timeout}
            self.do_save(dict)

    def delete(self):
        self.do_delete()
        self.clear()

    def init_lock(self):
        pass
            
    def lock(self):
        if self._lock:
            _apache._global_lock(self._req.server, self._sid)
            self._locked = 1
            self._req.register_cleanup(unlock_session_cleanup, self)

    def unlock(self):
        if self._lock and self._locked:
            _apache._global_unlock(self._req.server, self._sid)
            self._locked = 0
            
    def is_new(self):
        return not not self._new

    def id(self):
        return self._sid

    def created(self):
        return self._created

    def last_accessed(self):
        return self._accessed

    def timeout(self):
        return self._timeout

    def set_timeout(self, secs):
        self._timeout = secs

    def cleanup(self):
        self.do_cleanup()

    def __del__(self):
        self.unlock()

def unlock_session_cleanup(sess):
    sess.unlock()

###########################################################################
## DbmSession

def dbm_cleanup(data):
    dbm, server = data
    _apache._global_lock(server, None, 0)
    db = anydbm.open(dbm, 'c')
    try:
        old = []
        s = db.first()
        while 1:
            key, val = s
            dict = cPickle.loads(val)
            try:
                if (time.time() - dict["_accessed"]) > dict["_timeout"]:
                    old.append(key)
            except KeyError:
                old.append(key)
            try:
                s = db.next()
            except KeyError: break

        for key in old:
            try:
                del db[key]
            except: pass
    finally:
        db.close()
        _apache._global_unlock(server, None, 0)

class DbmSession(BaseSession):

    def __init__(self, req, dbm=None, sid=0, secret=None, dbmtype=anydbm,
                 timeout=0, lock=1):

        if not dbm:
            opts = req.get_options()
            if opts.has_key("session_dbm"):
                dbm = opts["session_dbm"]
            else:
                dbm = os.path.join(opts.get('session_directory', tempdir), 'mp_sess.dbm')

        self._dbmfile = dbm
        self._dbmtype = dbmtype

        BaseSession.__init__(self, req, sid=sid, secret=secret,
                             timeout=timeout, lock=lock)

    def _set_dbm_type(self):
        module = whichdb.whichdb(self._dbmfile)
        if module:
            self._dbmtype = __import__(module)
        
    def _get_dbm(self):
        result = self._dbmtype.open(self._dbmfile, 'c')
        if self._dbmtype is anydbm:
            self._set_dbm_type()
        return result

    def do_cleanup(self):
        data = [self._dbmfile, self._req.server]
        self._req.register_cleanup(dbm_cleanup, data)
        self._req.log_error("DbmSession: registered database cleanup.",
                            apache.APLOG_NOTICE)

    def do_load(self):
        _apache._global_lock(self._req.server, None, 0)
        dbm = self._get_dbm()
        try:
            if dbm.has_key(self._sid):
                return cPickle.loads(dbm[self._sid])
            else:
                return None
        finally:
            dbm.close()
            _apache._global_unlock(self._req.server, None, 0)

    def do_save(self, dict):
        _apache._global_lock(self._req.server, None, 0)
        dbm = self._get_dbm()
        try:
            dbm[self._sid] = cPickle.dumps(dict)
        finally:
            dbm.close()
            _apache._global_unlock(self._req.server, None, 0)

    def do_delete(self):
        _apache._global_lock(self._req.server, None, 0)
        dbm = self._get_dbm()
        try:
            try:
                del dbm[self._sid]
            except KeyError: pass
        finally:
            dbm.close()
            _apache._global_unlock(self._req.server, None, 0)

###########################################################################
## FileSession

DFT_FAST_CLEANUP = True 
DFT_VERIFY_CLEANUP = True 
DFT_GRACE_PERIOD = 240
DFT_CLEANUP_TIME_LIMIT = 2

# Credits : this was initially contributed by dharana <dharana@dharana.net>
class FileSession(BaseSession):

    def __init__(self, req, sid=0, secret=None, timeout=0, lock=1,
                fast_cleanup=-1, verify_cleanup=-1):
        
        opts = req.get_options()

        if fast_cleanup == -1:
            self._fast_cleanup = true_or_false(opts.get('session_fast_cleanup', DFT_FAST_CLEANUP))
        else:
            self._fast_cleanup = fast_cleanup

        if verify_cleanup == -1:
            self._verify_cleanup = true_or_false(opts.get('session_verify_cleanup', DFT_VERIFY_CLEANUP))
        else:
            self._verify_cleanup = verify_cleanup
            
        self._grace_period = int(opts.get('session_grace_period', DFT_GRACE_PERIOD))
        self._cleanup_time_limit = int(opts.get('session_cleanup_time_limit',DFT_CLEANUP_TIME_LIMIT))
        self._sessdir = os.path.join(opts.get('session_directory', tempdir), 'mp_sess')

        # FIXME
        if timeout:
            self._cleanup_timeout = timeout
        else:
            self._cleanup_timeout = DFT_TIMEOUT
        
        BaseSession.__init__(self, req, sid=sid, secret=secret,
            timeout=timeout, lock=lock)

    def do_cleanup(self):
        data = {'req':self._req,
                'sessdir':self._sessdir,
                'fast_cleanup':self._fast_cleanup, 
                'verify_cleanup':self._verify_cleanup, 
                'timeout':self._cleanup_timeout,
                'grace_period':self._grace_period,
                'cleanup_time_limit': self._cleanup_time_limit,
               }

        self._req.register_cleanup(filesession_cleanup, data)
        self._req.log_error("FileSession: registered filesession cleanup.",
                            apache.APLOG_NOTICE)

    def do_load(self):
        self.lock_file()
        try:
            try:
                path = os.path.join(self._sessdir, self._sid[0:2])
                filename = os.path.join(path, self._sid)
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
                path = os.path.join(self._sessdir, self._sid[0:2])
                if not os.path.exists(path):
                    make_filesession_dirs(self._sessdir)
                filename = os.path.join(path, self._sid)
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
                path = os.path.join(self._sessdir, self._sid[0:2])
                filename = os.path.join(path, self._sid)
                os.unlink(filename)
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

FS_STAT_VERSION = 'MPFS_3.2'
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
    cleanup_time_limit = data['cleanup_time_limit']

    req.log_error('FileSession cleanup: (fast=%s, verify=%s) ...'
                    % (fast_cleanup,verify_cleanup),
                    apache.APLOG_NOTICE)

    lockfile = os.path.join(sessdir,'.mp_sess.lck')
    try:
        lockfp = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0660) 
    except:
        # check if it's a stale lockfile
        mtime = os.stat(lockfile).st_mtime
        if mtime < (time.time() - 3600):
            # lockfile is over an hour old so it's likely stale.
            # Even though there may not be another cleanup process running,
            # we are going to defer running the cleanup at this time.
            # Short circuiting this cleanup just makes the code a little cleaner.
            req.log_error('FileSession cleanup: stale lockfile found - deleting it',
                        apache.APLOG_NOTICE)
            # Remove the stale lockfile so the next call to filesession_cleanup
            # can proceed.
            os.remove(lockfile)
        else:
            req.log_error('FileSession cleanup: another process is already running',
                        apache.APLOG_NOTICE)
        return

    try:
        status_file = file(os.path.join(sessdir, 'fs_status.txt'), 'r')
        d = status_file.readline()
        status_file.close()

        if not d.startswith(FS_STAT_VERSION):
            raise Exception, 'wrong status file version'

        parts = d.split()
        
        stat_version = parts[0]
        next_i = int(parts[1])
        expired_file_count = int(parts[2])
        total_file_count = int(parts[3])
        total_time = float(parts[4])

    except:
        stat_version = FS_STAT_VERSION 
        next_i = 0
        expired_file_count = 0 
        total_file_count =  0
        total_time = 0.0 

    try:
        start_time = time.time()
        filelist =  os.listdir(sessdir)
        dir_index = range(0,256)[next_i:]
        for i in dir_index:
            path = '%s/%s' % (sessdir,'%02x' % i)
            if not os.path.exists(path):
                continue
        
            filelist = os.listdir(path)
            total_file_count += len(filelist)

            for f in filelist:
                try:
                    filename = os.path.join(path,f)
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
                        expired_file_count += 1
                except:
                    s = cStringIO.StringIO()
                    traceback.print_exc(file=s)
                    s = s.getvalue()
                    req.log_error('FileSession cleanup error: %s'
                                    % (s),
                                    apache.APLOG_NOTICE)

            next_i = (i + 1) % 256
            time_used = time.time() - start_time 
            if (cleanup_time_limit > 0) and (time_used > cleanup_time_limit):
                break

        total_time += time.time() - start_time
        if next_i == 0:
            # next_i can only be 0 when the full cleanup has run to completion
            req.log_error("FileSession cleanup: deleted %d of %d in %.4f seconds"
                            % (expired_file_count, total_file_count, total_time),
                            apache.APLOG_NOTICE)
            expired_file_count = 0
            total_file_count = 0
            total_time = 0.0
        else:
            req.log_error("FileSession cleanup incomplete: next cleanup will start at index %d (%02x)"
                        % (next_i,),
                        apache.APLOG_NOTICE)

        status_file = file(os.path.join(sessdir, 'fs_status.txt'), 'w')
        status_file.write('%s %d %d %d %f\n' % (stat_version, next_i, expired_file_count, total_file_count, total_time))
        status_file.close()
   
        try:
            os.unlink(lockfile)
        except:
            pass

    finally:
        os.close(lockfp)

def make_filesession_dirs(sess_dir):
    """Creates the directory structure used for storing session files"""
    for i in range(0,256):
        path = os.path.join(sess_dir, '%02x' % i)
        if not os.path.exists(path):
            os.makedirs(path,  stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)

###########################################################################
## MemorySession

def mem_cleanup(sdict):
    for sid in sdict.keys():
        try:
            session = sdict[sid]
            if (time.time() - session["_accessed"]) > session["_timeout"]:
                del sdict[sid]
        except:
            pass

class MemorySession(BaseSession):

    sdict = {}

    def __init__(self, req, sid=0, secret=None, timeout=0, lock=1):

        BaseSession.__init__(self, req, sid=sid, secret=secret,
                             timeout=timeout, lock=lock)

    def do_cleanup(self):
        self._req.register_cleanup(mem_cleanup, MemorySession.sdict)
        self._req.log_error("MemorySession: registered session cleanup.",
                            apache.APLOG_NOTICE)

    def do_load(self):
        if MemorySession.sdict.has_key(self._sid):
            return MemorySession.sdict[self._sid]
        return None

    def do_save(self, dict):
        MemorySession.sdict[self._sid] = dict

    def do_delete(self):
        try:
            del MemorySession.sdict[self._sid]
        except KeyError: pass

###########################################################################
## Session

def Session(req, sid=0, secret=None, timeout=0, lock=1):

    opts = req.get_options()
    if opts.has_key('session'):
        # Check the apache config for the type of session
        sess_type = opts['session']
    else:
        # no session class in config so get the default for the platform
        threaded = _apache.mpm_query(apache.AP_MPMQ_IS_THREADED)
        forked = _apache.mpm_query(apache.AP_MPMQ_IS_FORKED)
        daemons =  _apache.mpm_query(apache.AP_MPMQ_MAX_DAEMONS)

        if (threaded and ((not forked) or (daemons == 1))):
            sess_type = 'MemorySession'
        else:
            sess_type = 'DbmSession'

    if sess_type == 'FileSession':
        sess =  FileSession
    elif sess_type == 'DbmSession':
        sess = DbmSession
    elif sess_type == 'MemorySession':
        sess = MemorySession
    else:
        # TODO Add capability to load a user defined class
        # For now, just raise an exception.
        raise Exception, 'Unknown session type %s' % sess_type

    return sess(req, sid=sid, secret=secret,
                         timeout=timeout, lock=lock)


## helper functions
def true_or_false(item):
    """This function is used to assist in getting appropriate
    values set with the PythonOption directive
    """

    try:
        item = item.lower()
    except:
        pass
    if item in ['yes','true', '1', 1, True]:
        return True
    elif item in ['no', 'false', '0', 0, None, False]:
        return False
    else:
        raise Exception
