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
 # Originally developed by Gregory Trubetskoy.
 #
 # $Id: util.py,v 1.18 2003/08/28 18:47:13 grisha Exp $

import _apache
import apache
import StringIO

from types import *
from exceptions import *

parse_qs = _apache.parse_qs
parse_qsl = _apache.parse_qsl

""" The classes below are a (almost) a drop-in replacement for the
    standard cgi.py FieldStorage class. They should have pretty much the
    same functionality.

    These classes differ in that unlike cgi.FieldStorage, they are not
    recursive. The class FieldStorage contains a list of instances of
    Field class. Field class is incapable of storing anything in it.

    These objects should be considerably faster than the ones in cgi.py
    because they do not expect CGI environment, and are
    optimized specifically for Apache and mod_python.
"""

class Field:

    filename = None
    headers = {}

    def __init__(self, name, file, ctype, type_options,
                 disp, disp_options):
        self.name = name
        self.file = file
        self.type = ctype
        self.type_options = type_options
        self.disposition = disp
        self.disposition_options = disp_options

    def __repr__(self):
        """Return printable representation."""
        return "Field(%s, %s)" % (`self.name`, `self.value`)

    def __getattr__(self, name):
        if name != 'value':
            raise AttributeError, name
        if self.file:
            self.file.seek(0)
            value = self.file.read()
            self.file.seek(0)
        else:
            value = None
        return value

    def __del__(self):
        self.file.close()

class StringField(str):
    """ This class is basically a string with
    a value attribute for compatibility with std lib cgi.py
    """
    
    def __init__(self, str=""):
        str.__init__(self, str)
        self.value = self.__str__()

class FieldStorage:

    def __init__(self, req, keep_blank_values=0, strict_parsing=0):

        self.list = []

        # always process GET-style parameters
        if req.args:
            pairs = parse_qsl(req.args, keep_blank_values)
            for pair in pairs:
                file = StringIO.StringIO(pair[1])
                self.list.append(Field(pair[0], file, "text/plain", {},
                                       None, {}))

        if req.method == "POST":

            try:
                clen = int(req.headers_in["content-length"])
            except (KeyError, ValueError):
                # absent content-length is not acceptable
                raise apache.SERVER_RETURN, apache.HTTP_LENGTH_REQUIRED

            if not req.headers_in.has_key("content-type"):
                ctype = "application/x-www-form-urlencoded"
            else:
                ctype = req.headers_in["content-type"]

            if ctype == "application/x-www-form-urlencoded":
                
                pairs = parse_qsl(req.read(clen), keep_blank_values)
                for pair in pairs:
                    file = StringIO.StringIO(pair[1])
                    self.list.append(Field(pair[0], file, "text/plain",
                                     {}, None, {}))

            elif ctype[:10] == "multipart/":

                # figure out boundary
                try:
                    i = ctype.lower().rindex("boundary=")
                    boundary = ctype[i+9:]
                    if len(boundary) >= 2 and boundary[0] == boundary[-1] == '"':
                        boundary = boundary[1:-1]
                    boundary = "--" + boundary
                except ValueError:
                    raise apache.SERVER_RETURN, apache.HTTP_BAD_REQUEST

                #read until boundary
                line = req.readline()
                sline = line.strip()
                while line and sline != boundary:
                    line = req.readline()
                    sline = line.strip()

                while 1:

                    ## parse headers
                    
                    ctype, type_options = "text/plain", {}
                    disp, disp_options = None, {}
                    headers = apache.make_table()

                    line = req.readline()
                    sline = line.strip()
                    if not line or sline == (boundary + "--"):
                        break
                    
                    while line and line not in ["\n", "\r\n"]:
                        h, v = line.split(":", 1)
                        headers.add(h, v)
                        h = h.lower()
                        if h == "content-disposition":
                            disp, disp_options = parse_header(v)
                        elif h == "content-type":
                            ctype, type_options = parse_header(v)
                        line = req.readline()
                        sline = line.strip()

                    if disp_options.has_key("name"):
                        name = disp_options["name"]
                    else:
                        name = None

                    # is this a file?
                    if disp_options.has_key("filename"):
                        file = self.make_file()
                    else:
                        file = StringIO.StringIO()

                    # read it in
                    self.read_to_boundary(req, boundary, file)
                    file.seek(0)

                    # make a Field
                    field = Field(name, file, ctype, type_options,
                                  disp, disp_options)
                    field.headers = headers
                    if disp_options.has_key("filename"):
                        field.filename = disp_options["filename"]

                    self.list.append(field)

            else:
                # we don't understand this content-type
                raise apache.SERVER_RETURN, apache.HTTP_NOT_IMPLEMENTED


    def make_file(self):
        import tempfile
        return tempfile.TemporaryFile("w+b")

    def skip_to_boundary(self, req, boundary):
        line = req.readline()
        sline = line.strip()
        last_bound = boundary + "--"
        while line and sline != boundary and sline != last_bound:
            line = req.readline()
            sline = line.strip()

    def read_to_boundary(self, req, boundary, file):
        delim = ""
        line = req.readline()
        sline = line.strip()
        last_bound = boundary + "--"
        while line and sline != boundary and sline != last_bound:
            odelim = delim
            if line[-2:] == "\r\n":
                delim = "\r\n"
                line = line[:-2]
            elif line[-1:] == "\n":
                delim = "\n"
                line = line[:-1]
            file.write(odelim + line)
            line = req.readline()
            sline = line.strip()

    def __getitem__(self, key):
        """Dictionary style indexing."""
        if self.list is None:
            raise TypeError, "not indexable"
        found = []
        for item in self.list:
            if item.name == key:
                if isinstance(item.file, StringIO.StringIO):
                    found.append(StringField(item.value))
                else:
                    found.append(item)
        if not found:
            raise KeyError, key
        if len(found) == 1:
            return found[0]
        else:
            return found

    def get(self, key, default):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def keys(self):
        """Dictionary style keys() method."""
        if self.list is None:
            raise TypeError, "not indexable"
        keys = []
        for item in self.list:
            if item.name not in keys: keys.append(item.name)
        return keys

    def has_key(self, key):
        """Dictionary style has_key() method."""
        if self.list is None:
            raise TypeError, "not indexable"
        for item in self.list:
            if item.name == key: return 1
        return 0

    __contains__ = has_key

    def __len__(self):
        """Dictionary style len(x) support."""
        return len(self.keys())

def parse_header(line):
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    """
    
    plist = map(lambda a: a.strip(), line.split(';'))
    key = plist[0].lower()
    del plist[0]
    pdict = {}
    for p in plist:
        i = p.find('=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i+1:].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
            pdict[name] = value
    return key, pdict

def apply_fs_data(object, fs, **args):
    """
    Apply FieldStorage data to an object - the object must be
    callable. Examine the args, and match then with fs data,
    then call the object, return the result.
    """

    # add form data to args
    for field in fs.list:
        if field.filename:
            val = field
        else:
            val = field.value
        args.setdefault(field.name, []).append(val)

    # replace lists with single values
    for arg in args:
        if ((type(args[arg]) is ListType) and
            (len(args[arg]) == 1)):
            args[arg] = args[arg][0]

    # we need to weed out unexpected keyword arguments
    # and for that we need to get a list of them. There
    # are a few options for callable objects here:

    if type(object) is InstanceType:
        # instances are callable when they have __call__()
        object = object.__call__

    expected = []
    if hasattr(object, "func_code"):
        # function
        fc = object.func_code
        expected = fc.co_varnames[0:fc.co_argcount]
    elif hasattr(object, 'im_func'):
        # method
        fc = object.im_func.func_code
        expected = fc.co_varnames[1:fc.co_argcount]
    elif type(object) is ClassType:
        # class
        fc = object.__init__.im_func.func_code
        expected = fc.co_varnames[1:fc.co_argcount]

    # remove unexpected args unless co_flags & 0x08,
    # meaning function accepts **kw syntax
    if not (fc.co_flags & 0x08):
        for name in args.keys():
            if name not in expected:
                del args[name]

    return object(**args)

def redirect(req, location, permanent=0, text=None):
    """
    A convenience function to provide redirection
    """

    if req.sent_bodyct:
        raise IOError, "Cannot redirect after headers have already been sent."

    req.err_headers_out["Location"] = location
    if permanent:
        req.status = apache.HTTP_MOVED_PERMANENTLY
    else:
        req.status = apache.HTTP_MOVED_TEMPORARILY

    if text is None:
        req.write('<p>The document has moved' 
                  ' <a href="%s">here</a></p>\n'
                  % location)
    else:
        req.write(text)

    raise apache.SERVER_RETURN, apache.OK

