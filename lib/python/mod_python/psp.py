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
 # This file originally written by Sterling Hughes
 #
 # $Id$

import apache, Session, util, _psp
import _apache

import sys
import os
import marshal
import new
from cgi import escape
import anydbm, whichdb
import tempfile

# dbm types for cache
dbm_types = {}

tempdir = tempfile.gettempdir()

def path_split(filename):

    dir, fname = os.path.split(filename)
    if sys.platform.startswith("win"):
        dir += "\\"
    else:
        dir += "/"

    return dir, fname

def code2str(c):

    ctuple = (c.co_argcount, c.co_nlocals, c.co_stacksize, c.co_flags,
              c.co_code, c.co_consts, c.co_names, c.co_varnames, c.co_filename,
              c.co_name, c.co_firstlineno, c.co_lnotab)
    
    return marshal.dumps(ctuple)

def str2code(s):

    return new.code(*marshal.loads(s))

class PSPInterface:

    def __init__(self, req, filename, form):
        self.req = req
        self.filename = filename
        self.error_page = None
        self.form = form

    def set_error_page(self, page):
        if page and page[0] == '/':
            # relative to document root
            self.error_page = PSP(self.req, self.req.document_root() + page)
        else:
            # relative to same dir we're in
            dir = path_split(self.filename)[0]
            self.error_page = PSP(self.req, dir + page)

    def apply_data(self, object):

        if not self.form:
            self.form = util.FieldStorage(self.req, keep_blank_values=1)

        return util.apply_fs_data(object, self.form, req=self.req)

    def redirect(self, location, permanent=0):

        util.redirect(self.req, location, permanent)

class PSP:

    code = None
    dbmcache = None

    def __init__(self, req, filename=None, string=None, vars={}):

        if (string and filename):
            raise ValueError, "Must specify either filename or string"

        self.req, self.vars = req, vars

        if not filename and not string:
            filename = req.filename

        self.filename, self.string = filename, string

        if filename:

            # if filename is not absolute, default to our guess
            # of current directory
            if not os.path.isabs(filename):
                base = os.path.split(req.filename)[0]
                self.filename = os.path.join(base, filename)

            self.load_from_file()
        else:

            cached = strcache.get(string)
            if cached:
                self.code = cached
            else:
                self.code = _psp.parsestring(string)
                strcache.store(string)

    def cache_get(self, filename, mtime):

        opts = self.req.get_options()
        if opts.has_key("PSPDbmCache"):
            self.dbmcache = opts["PSPDbmCache"]

        if self.dbmcache:
            cached = dbm_cache_get(self.req.server, self.dbmcache,
                                   filename, mtime)
            if cached:
                return cached

        cached = mem_fcache.get(filename, mtime)
        if cached:
            return cached

    def cache_store(self, filename, mtime, code):

        if self.dbmcache:
            dbm_cache_store(self.req.server, self.dbmcache,
                            filename, mtime, code)
        else:
            mem_fcache.store(filename, mtime, code)

    def cfile_get(self, filename, mtime):

        # check for a file ending with 'c' (precompiled file)
        name, ext = os.path.splitext(filename)
        cname = name + ext[:-1] + 'c'

        if os.path.isfile(cname):
            cmtime = os.path.getmtime(cname)

            if cmtime >= mtime:
                return str2code(open(cname).read())

    def load_from_file(self):

        filename = self.filename

        if not os.path.isfile(filename):
            raise ValueError, "%s is not a file" % filename

        mtime = os.path.getmtime(filename)

        # check cache
        code = self.cache_get(filename, mtime)

        # check for precompiled file
        if not code:
            code = self.cfile_get(filename, mtime)

        # finally parse and compile
        if not code:
            dir, fname = path_split(self.filename)
            source = _psp.parse(fname, dir)
            code = compile(source, filename, "exec")

        # store in cache
        self.cache_store(filename, mtime, code)

        self.code = code

    def run(self, vars={}):

        code, req = self.code, self.req

        # does this code use session?
        session = None
        if "session" in code.co_names:
            session = Session.Session(req)

        # does this code use form?
        form = None
        if "form" in code.co_names:
            form = util.FieldStorage(req, keep_blank_values=1)

        # create psp interface object
        psp = PSPInterface(req, self.filename, form)

        try:
            global_scope = globals().copy()
            global_scope.update({"req":req, "session":session,
                                 "form":form, "psp":psp})
            global_scope.update(self.vars) # passed in __init__()
            global_scope.update(vars)      # passed in run()
            try:
                exec code in global_scope
                req.flush()
                
                # the mere instantiation of a session changes it
                # (access time), so it *always* has to be saved
                if session is not None:
                    session.save()
            except:
                et, ev, etb = sys.exc_info()
                if psp.error_page:
                    # run error page
                    psp.error_page.run({"exception": (et, ev, etb)})
                else:
                    raise et, ev, etb
        finally:
            if session is not None:
                    session.unlock()

    def __str__(self):
        self.req.content_type = 'text/html'
        self.run()
        return ""

    def display_code(self):
        """
        Display a niceliy HTML-formatted side-by-side of
        what PSP generated next to orinial code.
        """

        req, filename = self.req, self.filename

        # Because of caching, source code is most often not
        # available in this object, so we read it here
        # (instead of trying to get it in __init__ somewhere)

        dir, fname = path_split(filename)

        source = open(filename).read().splitlines()
        pycode = _psp.parse(fname, dir).splitlines()

        source = [s.rstrip() for s in source]
        pycode = [s.rstrip() for s in pycode]

        req.write("<table>\n<tr>")
        for s in ("", "&nbsp;PSP-produced Python Code:",
                  "&nbsp;%s:" % filename):
            req.write("<td><tt>%s</tt></td>" % s)
        req.write("</tr>\n")

        n = 1
        for line in pycode:
            req.write("<tr>")
            left = escape(line).replace("\t", " "*4).replace(" ", "&nbsp;")
            if len(source) < n:
                right = ""
            else:
                right = escape(source[n-1]).replace("\t", " "*4).replace(" ", "&nbsp;")
            for s in ("%d.&nbsp;" % n,
                      "<font color=blue>%s</font>" % left,
                      "&nbsp;<font color=green>%s</font>" % right):
                req.write("<td><tt>%s</tt></td>" % s)
            req.write("</tr>\n")

            n += 1
        req.write("</table>\n")


def parse(filename, dir=None):
    if dir:
        return _psp.parse(filename, dir)
    else:
        return _psp.parse(filename)

def parsestring(str):

    return _psp.parsestring(str)

def handler(req):

    req.content_type = "text/html"

    config = req.get_config()
    debug = debug = int(config.get("PythonDebug", 0))

    if debug and req.filename[-1] == "_":
        p = PSP(req, req.filename[:-1])
        p.display_code()
    else:
        p = PSP(req)
        p.run()

    return apache.OK

def dbm_cache_type(dbmfile):

    global dbm_types

    if dbm_types.has_key(dbmfile):
        return dbm_types[dbmfile]

    module = whichdb.whichdb(dbmfile)
    if module:
        dbm_type = __import__(module)
        dbm_types[dbmfile] = dbm_type
        return dbm_type
    else:
        # this is a new file
        return anydbm

def dbm_cache_store(srv, dbmfile, filename, mtime, val):
    
    dbm_type = dbm_cache_type(dbmfile)
    _apache._global_lock(srv, "pspcache")
    try:
        dbm = dbm_type.open(dbmfile, 'c')
        dbm[filename] = "%d %s" % (mtime, code2str(val))
    finally:
        try: dbm.close()
        except: pass
        _apache._global_unlock(srv, "pspcache")

def dbm_cache_get(srv, dbmfile, filename, mtime):

    dbm_type = dbm_cache_type(dbmfile)
    _apache._global_lock(srv, "pspcache")
    try:
        dbm = dbm_type.open(dbmfile, 'c')
        try:
            entry = dbm[filename]
            t, val = entry.split(" ", 1)
            if long(t) == mtime:
                return str2code(val)
        except KeyError:
            return None
    finally:
        try: dbm.close()
        except: pass
        _apache._global_unlock(srv, "pspcache")


class HitsCache:

    def __init__(self, size=512):
        self.cache = {}
        self.size = size

    def store(self, key, val):
        self.cache[key] = (1, val)
        if len(self.cache) > self.size:
            self.clean()

    def get(self, key):
        if self.cache.has_key(key):
            hist, val = self.cache[key]
            self.cache[key] = (hits+1, code)
            return val
        else:
            return None

    def clean(self):
        
        byhits = [(n[1], n[0]) for n in self.cache.items()]
        byhits.sort()

        # delete enough least hit entries to make cache 75% full
        for item in byhits[:len(self.cache)-int(self.size*.75)]:
            val, key = item
            del self.cache[key]

mem_scache = HitsCache()

class FileCache(HitsCache):

    def store(self, filename, mtime, code):
        self.cache[filename] = (1, mtime, code)
        if len(self.cache) > self.size:
            self.clean()

    def get(self, filename, mtime):
        try:
            hits, c_mtime, code = self.cache[filename]
            if mtime != c_mtime:
                del self.cache[filename]
                return None
            else:
                self.cache[filename] = (hits+1, mtime, code)
                return code
        except KeyError:
            return None

mem_fcache = FileCache()

