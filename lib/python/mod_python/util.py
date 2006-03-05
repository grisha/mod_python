
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

import _apache
import apache
import cStringIO
import tempfile
import re

from types import *
from exceptions import *

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
   def __init__(self, name, file, ctype, type_options,
                disp, disp_options, headers = {}):
       self.name = name
       self.file = file
       self.type = ctype
       self.type_options = type_options
       self.disposition = disp
       self.disposition_options = disp_options
       if disp_options.has_key("filename"):
           self.filename = disp_options["filename"]
       else:
           self.filename = None
       self.headers = headers

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

   def __init__(self, req, keep_blank_values=0, strict_parsing=0, file_callback=None, field_callback=None):
       #
       # Whenever readline is called ALWAYS use the max size EVEN when not expecting a long line.
       # - this helps protect against malformed content from exhausting memory.
       #

       self.list = []

       # always process GET-style parameters
       if req.args:
           pairs = parse_qsl(req.args, keep_blank_values)
           for pair in pairs:
               file = cStringIO.StringIO(pair[1])
               self.list.append(Field(pair[0], file, "text/plain", {}, None, {}))

       if req.method != "POST":
           return

       try:
           clen = int(req.headers_in["content-length"])
       except (KeyError, ValueError):
           # absent content-length is not acceptable
           raise apache.SERVER_RETURN, apache.HTTP_LENGTH_REQUIRED

       if not req.headers_in.has_key("content-type"):
           ctype = "application/x-www-form-urlencoded"
       else:
           ctype = req.headers_in["content-type"]

       if ctype.startswith("application/x-www-form-urlencoded"):
           pairs = parse_qsl(req.read(clen), keep_blank_values)
           for pair in pairs:
               # TODO : isn't this a bit heavyweight just for form fields ?
               file = cStringIO.StringIO(pair[1])
               self.list.append(Field(pair[0], file, "text/plain", {}, None, {}))
           return

       if not ctype.startswith("multipart/"):
           # we don't understand this content-type
           raise apache.SERVER_RETURN, apache.HTTP_NOT_IMPLEMENTED

       # figure out boundary
       try:
           i = ctype.lower().rindex("boundary=")
           boundary = ctype[i+9:]
           if len(boundary) >= 2 and boundary[0] == boundary[-1] == '"':
               boundary = boundary[1:-1]
           boundary = re.compile("--" + re.escape(boundary) + "(--)?\r?\n") 

       except ValueError:
           raise apache.SERVER_RETURN, apache.HTTP_BAD_REQUEST

       # read until boundary
       self.read_to_boundary(req, boundary, None)

       end_of_stream = False
       while not end_of_stream:
           ## parse headers

           ctype, type_options = "text/plain", {}
           disp, disp_options = None, {}
           headers = apache.make_table()

           line = req.readline(readBlockSize)
           match = boundary.match(line)
           if (not line) or match:
              # we stop if we reached the end of the stream or a stop boundary
              # (which means '--' after the boundary)
              # we continue to the next part if we reached a simple boundary
              # in either case this would mean the entity is malformed, but we're
              # tolerating it anyway.
              end_of_stream = (not line) or (match.group(1) is not None)
              continue
        
           skip_this_part = False
           while line not in ('\r','\r\n'):
               # we read the headers until we reach an empty line
               # NOTE : a single \n would mean the entity is malformed, but
               # we're tolerating it anyway
               h, v = line.split(":", 1)
               headers.add(h, v)
               h = h.lower()
               if h == "content-disposition":
                   disp, disp_options = parse_header(v)
               elif h == "content-type":
                   ctype, type_options = parse_header(v)
                   #
                   # NOTE: FIX up binary rubbish sent as content type
                   # from Microsoft IE 6.0 when sending a file which
                   # does not have a suffix.
                   #
                   if ctype.find('/') == -1:
                       ctype = 'application/octet-stream'
            
               line = req.readline(readBlockSize)
               match = boundary.match(line)
               if (not line) or match:
                  # we stop if we reached the end of the stream or a stop boundary
                  # (which means '--' after the boundary)
                  # we continue to the next part if we reached a simple boundary
                  # in either case this would mean the entity is malformed, but we're
                  # tolerating it anyway.
                  skip_this_part = True
                  end_of_stream = (not line) or (match.group(1) is not None)
                  break
           
           if skip_this_part:
               continue
           
           if disp_options.has_key("name"):
               name = disp_options["name"]
           else:
               name = None

           # is this a file?
           if disp_options.has_key("filename"):
               if file_callback and callable(file_callback):
                   file = file_callback(disp_options["filename"])
               else:
                   file = self.make_file()
           else:
               if field_callback and callable(field_callback):
                   file = field_callback()
               else:
                   file = self.make_field()

           # read it in
           end_of_stream = self.read_to_boundary(req, boundary, file)
           file.seek(0)

           # make a Field
           field = Field(name, file, ctype, type_options, disp, disp_options, headers)

           self.list.append(field)

   def make_file(self):
       return tempfile.TemporaryFile("w+b")

   def make_field(self):
       return cStringIO.StringIO()

   def read_to_boundary(self, req, boundary, file):
        previous_delimiter = None
        while True:
            line = req.readline(readBlockSize)
            
            if not line:
                # end of stream
                if file is not None and previous_delimiter is not None:
                    file.write(previous_delimiter)
                return True                
            
            match = boundary.match(line)
            if match:
                # the line is the boundary, so we bail out
                # if the two last chars are '--' it is the end of the entity
                return match.group(1) is not None

            if line[-2:] == '\r\n':
                # the line ends with a \r\n, which COULD be part
                # of the next boundary. We write the previous line delimiter
                # then we write the line without \r\n and save it for the next
                # iteration if it was not part of the boundary
                if file is not None:
                    if previous_delimiter is not None: file.write(previous_delimiter)
                    file.write(line[:-2])
                previous_delimiter = '\r\n'
    
            elif line[-1:] == '\r':
                # the line ends with \r, which is only possible if
                # readBlockSize bytes have been read. In that case the
                # \r COULD be part of the next boundary, so we save it for the next
                # iteration
                assert len(line) == readBlockSize
                if file is not None:
                    if previous_delimiter is not None: file.write(previous_delimiter)
                    file.write(line[:-1])
                previous_delimiter = '\r'
    
            elif line == '\n' and previous_delimiter == '\r':
                # the line us a single \n and we were in the middle of a \r\n,
                # so we complete the delimiter
                previous_delimiter = '\r\n'
    
            else:
                if file is not None:
                    if previous_delimiter is not None: file.write(previous_delimiter)
                    file.write(line)
                previous_delimiter = None

   def __getitem__(self, key):
       """Dictionary style indexing."""
       if self.list is None:
           raise TypeError, "not indexable"
       found = []
       for item in self.list:
           if item.name == key:
               if isinstance(item.file, FileType) or \
                      isinstance(getattr(item.file, 'file', None), FileType):
                   found.append(item)
               else:
                   found.append(StringField(item.value))
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

   def getfirst(self, key, default=None):
       """ return the first value received """
       for item in self.list:
           if item.name == key:
               if isinstance(item.file, FileType) or \
                      isinstance(getattr(item.file, 'file', None), FileType):
                   return item
               else:
                   return StringField(item.value)
       return default

   def getlist(self, key):
       """ return a list of received values """
       if self.list is None:
           raise TypeError, "not indexable"
       found = []
       for item in self.list:
           if item.name == key:
               if isinstance(item.file, FileType) or \
                      isinstance(getattr(item.file, 'file', None), FileType):
                   found.append(item)
               else:
                   found.append(StringField(item.value))
       return found

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

   # we need to weed out unexpected keyword arguments
   # and for that we need to get a list of them. There
   # are a few options for callable objects here:

   fc = None
   expected = []
   if hasattr(object, "func_code"):
       # function
       fc = object.func_code
       expected = fc.co_varnames[0:fc.co_argcount]
   elif hasattr(object, 'im_func'):
       # method
       fc = object.im_func.func_code
       expected = fc.co_varnames[1:fc.co_argcount]
   elif type(object) in (TypeType,ClassType):
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

   # remove unexpected args unless co_flags & 0x08,
   # meaning function accepts **kw syntax
   if fc is None:
       args = {}
   elif not (fc.co_flags & 0x08):
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

   raise apache.SERVER_RETURN, apache.DONE
