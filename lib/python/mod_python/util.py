 # vim: set sw=4 expandtab :
 #
 # Copyright (C) 2000, 2001, 2013 Gregory Trubetskoy
 # Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007 Apache Software Foundation
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

import _apache

import sys
PY2 = sys.version[0] == '2'
if PY2:
    import apache
    from exceptions import *
else:
    from . import apache

from io import BytesIO
import tempfile
import re

from types import *
import collections

MethodWrapper = type(object.__call__)

parse_qs = _apache.parse_qs
parse_qsl = _apache.parse_qsl

# Maximum line length for reading. (64KB)
# Fixes memory error when upload large files such as 700+MB ISOs.
readBlockSize = 65368

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
    def __init__(self, name, *args, **kwargs):
        self.name = name

        # Some third party packages such as Trac create
        # instances of the Field object and insert it
        # directly into the list of form fields. To
        # maintain backward compatibility check for
        # where more than just a field name is supplied
        # and invoke an additional initialisation step
        # to process the arguments. Ideally, third party
        # code should use the add_field() method of the
        # form, but if they need to maintain backward
        # compatibility with older versions of mod_python
        # they will not have a choice but to use old
        # way of doing things and thus we need this code
        # for the forseeable future to cope with that.

        if args or kwargs:
            self.__bc_init__(*args, **kwargs)

    def __bc_init__(self, file, ctype, type_options,
                    disp, disp_options, headers = {}):
       self.file = file
       self.type = ctype
       self.type_options = type_options
       self.disposition = disp
       self.disposition_options = disp_options
       if "filename" in disp_options:
           self.filename = disp_options["filename"]
       else:
           self.filename = None
       self.headers = headers

    def __repr__(self):
        """Return printable representation."""
        return "Field(%s, %s)" % (repr(self.name), repr(self.value))

    def __getattr__(self, name):
        if name != 'value':
            raise AttributeError(name)
        if self.file:
            self.file.seek(0)
            value = self.file.read()
            if not isinstance(value, bytes):
                raise TypeError("value must be bytes, is file opened in binary mode?")
            self.file.seek(0)
        else:
            value = None
        return value

    def __del__(self):
        self.file.close()

if PY2:
    class StringField(str):
        """ This class is basically a string with
        added attributes for compatibility with std lib cgi.py. Basically, this
        works the opposite of Field, as it stores its data in a string, but creates
        a file on demand. Field creates a value on demand and stores data in a file.
        """
        filename = None
        headers = {}
        ctype = "text/plain"
        type_options = {}
        disposition = None
        disp_options = None

        # I wanted __init__(name, value) but that does not work (apparently, you
        # cannot subclass str with a constructor that takes >1 argument)
        def __init__(self, value):
            '''Create StringField instance. You'll have to set name yourself.'''
            str.__init__(self, value)
            self.value = value

        def __getattr__(self, name):
            if name != 'file':
                raise AttributeError(name)
            self.file = BytesIO(self.value)
            return self.file

        def __repr__(self):
            """Return printable representation (to pass unit tests)."""
            return "Field(%s, %s)" % (repr(self.name), repr(self.value))
else:
    class StringField(bytes):
        """ This class is basically a string with
        added attributes for compatibility with std lib cgi.py. Basically, this
        works the opposite of Field, as it stores its data in a string, but creates
        a file on demand. Field creates a value on demand and stores data in a file.
        """
        filename = None
        headers = {}
        ctype = "text/plain"
        type_options = {}
        disposition = None
        disp_options = None

        def __new__(self, value):
            if PY2:
                return bytes.__new__(self, value)
            else:
                str_value = value.decode("utf-8") if isinstance(value, bytes) else value
                return bytes.__new__(self, str(str_value), encoding="utf-8")

        def __init__(self, value):
            self.value = value

        def __getattr__(self, name):
            if name != 'file':
                raise AttributeError(name)
            self.file = BytesIO(self.value)
            return self.file

        def __repr__(self):
            """Return printable representation (to pass unit tests)."""
            return "Field(%s, %s)" % (repr(self.name), repr(self.value))

class FieldList(list):

    def __init__(self):
        self.__table = None
        list.__init__(self)

    def table(self):
        if self.__table is None:
            self.__table = {}
            for item in self:
                if item.name in self.__table:
                    self.__table[item.name].append(item)
                else:
                    self.__table[item.name] = [item]
        return self.__table

    def __delitem__(self, *args):
        self.__table = None
        return list.__delitem__(self, *args)

    def __delslice__(self, *args):
        self.__table = None
        return list.__delslice__(self, *args)

    def __iadd__(self, *args):
        self.__table = None
        return list.__iadd__(self, *args)

    def __imul__(self, *args):
        self.__table = None
        return list.__imul__(self, *args)

    def __setitem__(self, *args):
        self.__table = None
        return list.__setitem__(self, *args)

    def __setslice__(self, *args):
        self.__table = None
        return list.__setslice__(self, *args)

    def append(self, *args):
        self.__table = None
        return list.append(self, *args)

    def extend(self, *args):
        self.__table = None
        return list.extend(self, *args)

    def insert(self, *args):
        self.__table = None
        return list.insert(self, *args)

    def pop(self, *args):
        self.__table = None
        return list.pop(self, *args)

    def remove(self, *args):
        self.__table = None
        return list.remove(self, *args)


class FieldStorage:

    def __init__(self, req, keep_blank_values=0, strict_parsing=0, file_callback=None, field_callback=None):
        #
        # Whenever readline is called ALWAYS use the max size EVEN when
        # not expecting a long line. - this helps protect against
        # malformed content from exhausting memory.
        #

        self.list = FieldList()

        # always process GET-style parameters
        if req.args:
            pairs = self.parse_qsl_safely(req.args, keep_blank_values)
            for pair in pairs:
                self.add_field(pair[0], pair[1])

        if req.method != "POST":
            return

        try:
            clen = int(req.headers_in["content-length"])
        except (KeyError, ValueError):
            # absent content-length is not acceptable
            raise apache.SERVER_RETURN(apache.HTTP_LENGTH_REQUIRED)

        if "content-type" not in req.headers_in:
            ctype = b"application/x-www-form-urlencoded"
        else:
            ctype = req.headers_in["content-type"].encode("latin1")

        if not isinstance(ctype, bytes):
            raise TypeError("ctype must be of type bytes")

        if ctype.startswith(b"application/x-www-form-urlencoded"):
            v = req.read(clen)
            if not isinstance(v, bytes):
                raise TypeError("req.read() must return bytes")
            pairs = self.parse_qsl_safely(v, keep_blank_values)
            for pair in pairs:
                self.add_field(pair[0], pair[1])
            return

        if not ctype.startswith(b"multipart/"):
            # we don't understand this content-type
            raise apache.SERVER_RETURN(apache.HTTP_NOT_IMPLEMENTED)

        # figure out boundary
        try:
            i = ctype.lower().rindex(b"boundary=")
            boundary = ctype[i+9:]
            if len(boundary) >= 2 and boundary[:1] == boundary[-1:] == b'"':
                boundary = boundary[1:-1]
            boundary = re.compile(b"--" + re.escape(boundary) + b"(--)?\r?\n")

        except ValueError:
            raise apache.SERVER_RETURN(apache.HTTP_BAD_REQUEST)

        # read until boundary
        self.read_to_boundary(req, boundary, None)

        end_of_stream = False
        while not end_of_stream:
            ## parse headers

            ctype, type_options = b"text/plain", {}
            disp, disp_options = None, {}
            headers = apache.make_table()

            line = req.readline(readBlockSize)
            if not isinstance(line, bytes):
                raise TypeError("req.readline() must return bytes")
            match = boundary.match(line)
            if (not line) or match:
                # we stop if we reached the end of the stream or a stop
                # boundary (which means '--' after the boundary) we
                # continue to the next part if we reached a simple
                # boundary in either case this would mean the entity is
                # malformed, but we're tolerating it anyway.
                end_of_stream = (not line) or (match.group(1) is not None)
                continue

            skip_this_part = False
            while line not in (b'\r',b'\r\n'):
                nextline = req.readline(readBlockSize)
                while nextline and nextline[:1] in [ b' ', b'\t']:
                    line = line + nextline
                    nextline = req.readline(readBlockSize)
                # we read the headers until we reach an empty line
                # NOTE : a single \n would mean the entity is malformed, but
                # we're tolerating it anyway
                h, v = line.split(b":", 1)
                headers.add(h, v)  # mp_table accepts bytes, but always returns str
                h = h.lower()
                if h == b"content-disposition":
                    disp, disp_options = parse_header(v)
                elif h == b"content-type":
                    ctype, type_options = parse_header(v)
                    #
                    # NOTE: FIX up binary rubbish sent as content type
                    # from Microsoft IE 6.0 when sending a file which
                    # does not have a suffix.
                    #
                    if ctype.find(b'/') == -1:
                        ctype = b'application/octet-stream'

                line = nextline
                match = boundary.match(line)
                if (not line) or match:
                    # we stop if we reached the end of the stream or a
                    # stop boundary (which means '--' after the
                    # boundary) we continue to the next part if we
                    # reached a simple boundary in either case this
                    # would mean the entity is malformed, but we're
                    # tolerating it anyway.
                    skip_this_part = True
                    end_of_stream = (not line) or (match.group(1) is not None)
                    break

            if skip_this_part:
                continue

            if b"name" in disp_options:
                name = disp_options[b"name"]
            else:
                name = None

            # create a file object
            # is this a file?
            filename = None
            if b"filename" in disp_options:
                filename = disp_options[b"filename"]
                if file_callback and isinstance(file_callback, collections.abc.Callable):
                    file = file_callback(filename)
                else:
                    file = tempfile.TemporaryFile("w+b")
            else:
                if field_callback and isinstance(field_callback, collections.abc.Callable):
                    file = field_callback()
                else:
                    file = BytesIO()

            # read it in
            self.read_to_boundary(req, boundary, file)
            file.seek(0)

            # make a Field
            if filename:
                field = Field(name)
                field.filename = filename
            else:
                field = StringField(file.read())
                field.name = name
            field.file = file
            field.type = PY2 and ctype or ctype.decode('latin1')
            field.type_options = type_options
            field.disposition = PY2 and disp or disp.decode('latin1')
            field.disposition_options = disp_options
            field.headers = headers
            self.list.append(field)

    def parse_qsl_safely(self, query_string, keep_blank_values):
        """
        This script calls urllib.parse.parse_qsl if there is exception in processing parse_qsl function

        :param query_string: The query string which needs to be parsed
        :type query_string: string
        :param keep_blank_values: keep_blank_values is a flag indicating whether blank values in percent-encoded queries should be treated as blank strings.
        :type keep_blank_values: int/boolean
        """
        try:
            pairs = parse_qsl(query_string, keep_blank_values)
        except SystemError as er:
            import urllib.parse
            pairs = urllib.parse.parse_qsl(query_string, keep_blank_values)
        return pairs

    def add_field(self, key, value):
        """Insert a field as key/value pair"""
        item = StringField(value)
        item.name = key
        self.list.append(item)

    def __setitem__(self, key, value):
        if not isinstance(value, bytes):
            raise TypeError("Field value must be bytes")
        if not isinstance(key, bytes):
            raise TypeError("Field key must be bytes")
        table = self.list.table()
        if key in table:
            items = table[key]
            for item in items:
                self.list.remove(item)
        item = StringField(value)
        item.name = key
        self.list.append(item)

    def read_to_boundary(self, req, boundary, file):
        previous_delimiter = None
        while True:
            line = req.readline(readBlockSize)
            if not isinstance(line, bytes):
                raise TypeError("req.readline() must return bytes")

            if not line:
                # end of stream
                if file is not None and previous_delimiter is not None:
                    file.write(previous_delimiter)
                return True

            match = boundary.match(line)
            if match:
                # the line is the boundary, so we bail out
                # if the two last bytes are '--' it is the end of the entity
                return match.group(1) is not None

            if line[-2:] == b'\r\n':
                # the line ends with a \r\n, which COULD be part
                # of the next boundary. We write the previous line delimiter
                # then we write the line without \r\n and save it for the next
                # iteration if it was not part of the boundary
                if file is not None:
                    if previous_delimiter is not None: file.write(previous_delimiter)
                    file.write(line[:-2])
                previous_delimiter = b'\r\n'

            elif line[-1:] == b'\r':
                # the line ends with \r, which is only possible if
                # readBlockSize bytes have been read. In that case the
                # \r COULD be part of the next boundary, so we save it
                # for the next iteration
                assert len(line) == readBlockSize
                if file is not None:
                    if previous_delimiter is not None: file.write(previous_delimiter)
                    file.write(line[:-1])
                previous_delimiter = b'\r'

            elif line == b'\n' and previous_delimiter == b'\r':
                # the line us a single \n and we were in the middle of a \r\n,
                # so we complete the delimiter
                previous_delimiter = b'\r\n'

            else:
                if file is not None:
                    if previous_delimiter is not None: file.write(previous_delimiter)
                    file.write(line)
                previous_delimiter = None

    def __getitem__(self, key):
        """Dictionary style indexing."""
        found = self.list.table()[key]
        if len(found) == 1:
            return found[0]
        else:
            return found

    def get(self, key, default):
        try:
            return self.__getitem__(key)
        except (TypeError, KeyError):
            return default

    def keys(self):
        """Dictionary style keys() method."""
        return list(self.list.table().keys())

    def __iter__(self):
        return iter(list(self.keys()))

    def __repr__(self):
        return repr(self.list.table())

    def has_key(self, key):
        """Dictionary style has_key() method."""
        return (key in self.list.table())

    __contains__ = has_key

    def __len__(self):
        """Dictionary style len(x) support."""
        return len(self.list.table())

    def getfirst(self, key, default=None):
        """ return the first value received """
        try:
            return self.list.table()[key][0]
        except KeyError:
            return default

    def getlist(self, key):
        """ return a list of received values """
        try:
            return self.list.table()[key]
        except KeyError:
            return []

    def items(self):
        """Dictionary-style items(), except that items are returned in the same
        order as they were supplied in the form."""
        return [(item.name, item) for item in self.list]

    def __delitem__(self, key):
        table = self.list.table()
        values = table[key]
        for value in values:
            self.list.remove(value)

    def clear(self):
        self.list = FieldList()


def parse_header(line):
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    """

    if not isinstance(line, bytes):
        raise TypeError("parse_header() only accepts bytes")

    plist = [a.strip() for a in line.split(b';')]
    key = plist[0].lower()
    del plist[0]
    pdict = {}
    for p in plist:
        i = p.find(b'=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i+1:].strip()
            if len(value) >= 2 and value[:1] == value[-1:] == b'"':
                value = value[1:-1]
            pdict[name] = PY2 and value or value.decode('latin1')
    return key, pdict

def apply_fs_data(object, fs, **args):
    """
    Apply FieldStorage data to an object - the object must be
    callable. Examine the args, and match then with fs data,
    then call the object, return the result.
    """

    # we need to weed out unexpected keyword arguments
    # and for that we need to get a list of them. There
    # are a few options for callable objects here:

    fc = None
    expected = []

    if PY2:
        if hasattr(object, "func_code"):
            # function
            fc = object.func_code
            expected = fc.co_varnames[0:fc.co_argcount]
        elif hasattr(object, 'im_func'):
            # method
            fc = object.im_func.func_code
            expected = fc.co_varnames[1:fc.co_argcount]
        elif type(object) in (TypeType,ClassType) and hasattr(object, "__init__"):
            # class
            fc = object.__init__.im_func.func_code
            expected = fc.co_varnames[1:fc.co_argcount]
        elif type(object) is BuiltinFunctionType:
            # builtin
            fc = None
            expected = []
        elif hasattr(object, '__call__'):
            # callable object
            if type(object.__call__) is MethodType:
                fc = object.__call__.im_func.func_code
                expected = fc.co_varnames[1:fc.co_argcount]
            else:
                # abuse of objects to create hierarchy
                return apply_fs_data(object.__call__, fs, **args)
    else:
        if hasattr(object, '__code__'):
            # function
            fc = object.__code__
            expected = fc.co_varnames[0:fc.co_argcount]
        elif hasattr(object, '__func__'):
            # method
            fc = object.__func__.__code__
            expected = fc.co_varnames[1:fc.co_argcount]
        elif type(object) is type and hasattr(object, "__init__") and hasattr(object.__init__, "__code__"):
            # class
            fc = object.__init__.__code__
            expected = fc.co_varnames[1:fc.co_argcount]
        elif type(object) is [type, BuiltinFunctionType]:
            # builtin
            fc = None
            expected = []
        elif hasattr(object, '__call__'):
            # callable object
            if type(object.__call__) is MethodType:
                fc = object.__call__.__func__.__code__
                expected = fc.co_varnames[1:fc.co_argcount]
            elif type(object.__call__) != MethodWrapper:
                # abuse of objects to create hierarchy
                return apply_fs_data(object.__call__, fs, **args)

    # add form data to args
    for field in fs.list:
        if field.filename:
            val = field
        else:
            val = field.value
        args.setdefault(field.name, []).append(val)

    # replace lists with single values
    for arg in args:
        if ((type(args[arg]) is list) and
            (len(args[arg]) == 1)):
            args[arg] = args[arg][0]

    # remove unexpected args unless co_flags & 0x08,
    # meaning function accepts **kw syntax
    if fc is None:
        args = {}
    elif not (fc.co_flags & 0x08):
        for name in list(args.keys()):
            if name not in expected:
                del args[name]

    return object(**args)

def redirect(req, location, permanent=0, text=None):
    """
    A convenience function to provide redirection
    """

    if not isinstance(location, str):
        raise TypeError("location must be of type str")

    if req.sent_bodyct:
        raise IOError("Cannot redirect after headers have already been sent.")

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

    raise apache.SERVER_RETURN(apache.DONE)
