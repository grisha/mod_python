 # ====================================================================
 # The Apache Software License, Version 1.1
 #
 # Copyright (c) 2000-2002 The Apache Software Foundation.  All rights
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
 # This file originally written by Sterling Hughes
 #
 # $Id: psp.py,v 1.10 2003/08/01 01:53:13 grisha Exp $

# this trick lets us be used outside apache
try:
    from mod_python import apache
    import _apache
except:
    from mod_python import apache
    apache.OK = 0

try:
    import Session
except: pass

import _psp

import sys
import os
import marshal
import new
from cgi import escape
import anydbm, whichdb
import tempfile

# dbm typees for cache
dbm_types = {}

tempdir = tempfile.gettempdir()

def parse(filename):

    return _psp.parse(filename)

def parsestring(str):

    return _psp.parsestring(str)

def code2str(c):

    ctuple = (c.co_argcount, c.co_nlocals, c.co_stacksize, c.co_flags,
              c.co_code, c.co_consts, c.co_names, c.co_varnames, c.co_filename,
              c.co_name, c.co_firstlineno, c.co_lnotab)
    
    return marshal.dumps(ctuple)

def str2code(s):

    return apply(new.code, marshal.loads(s))

def load_file(filename, dbmcache=None, srv=None):

    """ In addition to dbmcache, this function will check for
    existence of a file with same name, but ending with c and load it
    instead. The c file contains already compiled code (see code2str
    above). My crude tests showed that mileage varies greatly as to
    what the actual speedup would be, but on average for files that
    are mostly strings and not a lot of Python it was 1.5 - 3
    times. The good news is that this means that the PSP lexer and the
    Python parser are *very* fast, so compiling PSP pages is only
    necessary in extreme cases. """

    smtime = 0
    cmtime = 0

    if os.path.isfile(filename):
        smtime = os.path.getmtime(filename)

    if dbmcache:
        cached = cache_get(srv, dbmcache, filename, smtime)
        if cached:
            return str2code(cached)

    name, ext = os.path.splitext(filename)

    cext = ext[:-1] + "c"
    cname = name + cext
    
    if os.path.isfile(name + cext):
        cmtime = os.path.getmtime(cname)

        if cmtime > smtime:
            # we've got a code file!
            code = str2code(open(name + cext).read())

            return code
                
    source = _psp.parse(filename)
    code = compile(source, filename, "exec")

    if dbmcache:
        cache_store(srv, dbmcache, filename, smtime, code2str(code))

    return code

def display_code(req):
    """
    Display a niceliy HTML-formatted side-by-side of
    what PSP generated next to orinial code
    """

    source = open(req.filename[:-1]).read().splitlines()
    pycode = _psp.parse(req.filename[:-1]).splitlines()

    source = [s.rstrip() for s in source]
    pycode = [s.rstrip() for s in pycode]

    req.write("<table>\n<tr>")
    for s in ("", "&nbsp;PSP-produced Python Code:",
              "&nbsp;%s:" % req.filename[:-1]):
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

    return apache.OK

def run_psp(req):

    dbmcache = None
    opts = req.get_options()
    if opts.has_key("PSPDbmCache"):
        dbmcache = opts["PSPDbmCache"]

    code = load_file(req.filename, dbmcache, srv=req.server)

    session = None
    if "session" in code.co_names:

        if opts.has_key("PSPSessionDbm"):
            fname = opts["PSPSessionDbm"]
        else:
            fname = os.path.join(tempdir, "psp_sess.dbm")
        
        session = Session.Session(req, fname)

    try:

        # give it it's own locals
        exec code in globals(), {"req":req, "session":session}

        # the mere instantiation of a session changes it
        # (access time), so it *always* has to be saved
        if session:
            session.save()
    finally:
        if session:
            session.unlock()
    
    return apache.OK

def handler(req):

    config = req.get_config()
    debug = config.has_key("PythonDebug")
    
    req.content_type = "text/html"

    if debug and req.filename[-1] == "_":
        return display_code(req)
    else:
        return run_psp(req)

def cache_type(dbmfile):

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

def cache_store(srv, dbmfile, filename, mtime, val):
    dbm_type = cache_type(dbmfile)
    _apache._global_lock(srv, "pspcache")
    try:
        dbm = dbm_type.open(dbmfile, 'c')
        dbm[filename] = "%d %s" % (mtime, val)
    finally:
        try: dbm.close()
        except: pass
        _apache._global_unlock(srv, "pspcache")

def cache_get(srv, dbmfile, filename, mtime):
    dbm_type = cache_type(dbmfile)
#    _apache._global_lock(srv, "pspcache")
    try:
        dbm = dbm_type.open(dbmfile, 'c')
        try:
            entry = dbm[filename]
            t, val = entry.split(" ", 1)
            if long(t) == mtime:
                return val
        except KeyError:
            return None
    finally:
        try: dbm.close()
        except: pass
#        _apache._global_unlock(srv, "pspcache")
