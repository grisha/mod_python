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
 # $Id: psp.py,v 1.8 2003/06/13 02:36:23 sterling Exp $

# this trick lets us be used outside apache
try:
    from mod_python import apache
except:
    from mod_python import apache
    apache.OK = 0
    
import _psp

import sys
import os
import marshal
import new

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

def load_file(filename):

    """ This function will check for existence of a file with same
    name, but ending with c and load it instead. The c file contains
    already compiled code (see code2str above). My crude tests showed
    that mileage vaires greatly as to what the actual speedup would
    be, but on average for files that are mostly strings and not a lot
    of Python it was 1.5 - 3 times. The good news is that this means
    that the PSP lexer and the Python parser are *very* fast, so
    compiling PSP pages is only necessary in extreme cases. """

    smtime = 0
    cmtime = 0

    if os.path.isfile(filename):
        smtime = os.path.getmtime(filename)

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
    return compile(source, filename, "exec")


def handler(req):

    code = load_file(req.filename)

    req.content_type = "text/html"

    # give it it's own locals
    exec code in globals(), {"req":req}

    return apache.OK
