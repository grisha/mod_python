 # ====================================================================
 # The Apache Software License, Version 1.1
 #
 # Copyright (c) 2000-2003 The Apache Software Foundation.  All rights
 # reserved.
 #
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions
 # are met:
 #
 # 1. Redistributions of source code must retain the above copyright
 #    notice, this list of conditions and the following disclaimer.
 #
 # 2. Redistributions in binary form must reproduce the above copyright
 #    notice, this list of conditions and the following disclaimer in
 #    the documentation and/or other materials provided with the
 #    distribution.
 #
 # 3. The end-user documentation included with the redistribution,
 #    if any, must include the following acknowledgment:
 #       "This product includes software developed by the
 #        Apache Software Foundation (http://www.apache.org/)."
 #    Alternately, this acknowledgment may appear in the software itself,
 #    if and wherever such third-party acknowledgments normally appear.
 #
 # 4. The names "Apache" and "Apache Software Foundation" must
 #    not be used to endorse or promote products derived from this
 #    software without prior written permission. For written
 #    permission, please contact apache@apache.org.
 #
 # 5. Products derived from this software may not be called "Apache",
 #    "mod_python", or "modpython", nor may these terms appear in their
 #    name, without prior written permission of the Apache Software
 #    Foundation.
 #
 # THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
 # WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 # OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 # DISCLAIMED.  IN NO EVENT SHALL THE APACHE SOFTWARE FOUNDATION OR
 # ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 # SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 # LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 # USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 # ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 # OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 # OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 # SUCH DAMAGE.
 # ====================================================================
 #
 # This software consists of voluntary contributions made by many
 # individuals on behalf of the Apache Software Foundation.  For more
 # information on the Apache Software Foundation, please see
 # <http://www.apache.org/>.
 #
 # Originally developed by Gregory Trubetskoy.
 #
 # $Id: Session.py,v 1.1 2003/08/01 01:53:13 grisha Exp $

from mod_python import apache, Cookie
import _apache

import os
import time
import anydbm, whichdb
import random
import md5
import cPickle

COOKIE_NAME="pysid"
DFT_TIMEOUT=30*60*60 # 30 min
CLEANUP_CHANCE=1000 # cleanups have 1 in CLEANUP_CHANCE chance

def _init_rnd():
    """ initialize random number generators
    this is key in multithreaded env, see
    python docs for random """

    # guess max number of threads
    config = apache.config_tree()
    dict = {}
    for line in config:
        if type(line) == type(()):
            if line[0].lower() in ("startthreads",
                                   "maxthreadsperchild",
                                   "threadsperchild"):
                dict[line[0].lower()] = int(line[1])

    # in order of preference
    if dict.has_key("threadsperchild"):
        gennum = dict["threadsperchild"]
    elif dict.has_key("maxthreadsperchild"):
        gennum = dict["maxthreadsperchild"]
    elif dict.has_key("startthreads"):
        gennum = dict["startthreads"]
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

    def __init__(self, req, sid=None, secret=None, lock=1, lockfile="",
                 timeout=0):

        if lock and not lockfile:
            raise ValueError, "lockfile is required when locking is on"

        self._req, self._sid, self._secret = req, sid, secret
        self._lock, self._lockfile = lock, lockfile
        self._new = 1
        self._created = 0
        self._accessed = 0
        self._timeout = 0
        self._locked = 0
        
        dict.__init__(self)

        if not self._sid:
            # check to see if cookie exists
            if secret:  
                cookies = Cookie.get_cookies(req, Class=Cookie.SignedCookie,
                                             secret=self._secret)
            else:
                cookies = Cookie.get_cookies(req)

            if cookies.has_key(COOKIE_NAME):
                self._sid = cookies[COOKIE_NAME].value

        self.init_lock()

        if self._sid:
            # attempt to load ourselves
            self.lock()
            if self.load():
                if (time.time() - self._accessed) > self._timeout:
                    # we expired
                    self.delete()
                else:
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

        if self._secret:
            c = Cookie.SignedCookie(COOKIE_NAME, self._sid,
                                    secret=self._secret)
        else:
            c = Cookie.Cookie(COOKIE_NAME, self._sid)

        config = self._req.get_options()
        if config.has_key("ApplicationPath"):
            c.path = config["ApplicationPath"]
        else:
            docroot = self._req.document_root()
            # the path where *Handler directive was specified
            dirpath = self._req.hlist.directory 
            c.path = dirpath[len(docroot):]
        
        return c

    def invalidate(self):
        c = self.make_cookie()
        c.expires = 0
        Cookie.add_cookie(self._req, c)

    def _load_internal(self):
        self._created = self["_created"]
        del self["_created"]
        self._accessed = self["_accessed"]
        del self["_accessed"]
        self._timeout = self["_timeout"]
        del self["_timeout"]

    def load(self):
        if self.do_load():
            self._load_internal()
            return 1
        else:
            return 0

    def _save_internal(self):
        self["_created"] = self._created
        self["_accessed"] = self._accessed
        self["_timeout"] = self._timeout

    def save(self):
        self._save_internal()
        self.do_save()

    def delete(self):
        self.do_delete()

    def init_lock(self):
        pass
            
    def lock(self, key=None):
        if key is None:
            if self._lock:
                _apache._global_lock(self._req.server, self._sid)
                self._locked = 1
        else:
            # just do what we're told
            _apache._global_lock(self._req.server, key)

    def unlock(self, key=None):
        if key is None: 
            if self._lock and self._locked:
                _apache._global_unlock(self._req.server, self._sid)
                self._locked = 0
        else:
            # just do what we're told
            _apache._global_unlock(self._req.server, key)
            
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

def dbm_cleanup(data):
    dbm, server = data
    _apache._global_lock(server, 1)
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
        _apache._global_unlock(server, 1)
    
class DbmSession(BaseSession):

    def __init__(self, req, dbm, sid=0, secret=None, dbmtype=anydbm,
                 timeout=0):

        self._dbmfile = dbm
        self._dbmtype = dbmtype

        BaseSession.__init__(self, req, sid=sid,
                             secret=secret, lockfile=dbm+".lck",
                             timeout=timeout)

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
#        self.lock(key=1)
        dbm = self._get_dbm()
        try:
            if dbm.has_key(self._sid):
                dict = cPickle.loads(dbm[self._sid])
                self.clear()
                self.update(dict)
                return 1
            return 0
        finally:
            dbm.close()
#            self.unlock(key=1)

    def do_save(self):
        self.lock(key=1)
        dbm = self._get_dbm()
        try:
            dbm[self._sid] = cPickle.dumps(self.copy())
        finally:
            dbm.close()
            self.unlock(key=1)

    def do_delete(self):
        self.lock(key=1)
        dbm = self._get_dbm()
        try:
            del self._dbm[self._sid]
        finally:
            dbm.close()
            self.unlock(key=1)

Session = DbmSession
    
