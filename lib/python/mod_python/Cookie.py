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

"""

This module contains classes to support HTTP State Management
Mechanism, also known as Cookies. The classes provide simple
ways for creating, parsing and digitally signing cookies, as
well as the ability to store simple Python objects in Cookies
(using marshalling).

The behaviour of the classes is designed to be most useful
within mod_python applications.

The current state of HTTP State Management standardization is
rather unclear. It appears that the de-facto standard is the
original Netscape specification, even though already two RFC's
have been put out (RFC2109 (1997) and RFC2965 (2000)). The
RFC's add a couple of useful features (e.g. using Max-Age instead
of Expires, but my limited tests show that Max-Age is ignored
by the two browsers tested (IE and Safari). As a result of this,
perhaps trying to be RFC-compliant (by automatically providing
Max-Age and Version) could be a waste of cookie space...

"""

import time
import re
import hmac
import marshal
import base64

# import apache

class CookieError(Exception):
    pass

class metaCookie(type):

    def __new__(cls, clsname, bases, clsdict):

        _valid_attr = (
            "version", "path", "domain", "secure",
            "comment", "expires", "max_age",
            # RFC 2965
            "commentURL", "discard", "port",
            # Microsoft Extension
            "httponly" )

        # _valid_attr + property values
        # (note __slots__ is a new Python feature, it
        # prevents any other attribute from being set)
        __slots__ = _valid_attr + ("name", "value", "_value",
                                   "_expires", "__data__")

        clsdict["_valid_attr"] = _valid_attr
        clsdict["__slots__"] = __slots__

        def set_expires(self, value):

            if type(value) == type(""):
                # if it's a string, it should be
                # valid format as per Netscape spec
                try:
                    t = time.strptime(value, "%a, %d-%b-%Y %H:%M:%S GMT")
                except ValueError:
                    raise ValueError, "Invalid expires time: %s" % value
                t = time.mktime(t)
            else:
                # otherwise assume it's a number
                # representing time as from time.time()
                t = value
                value = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT",
                                      time.gmtime(t))

            self._expires = "%s" % value

        def get_expires(self):
            return self._expires

        clsdict["expires"] = property(fget=get_expires, fset=set_expires)

        return type.__new__(cls, clsname, bases, clsdict)

class Cookie(object):
    """
    This class implements the basic Cookie functionality. Note that
    unlike the Python Standard Library Cookie class, this class represents
    a single cookie (not a list of Morsels).
    """

    __metaclass__ = metaCookie

    def parse(Class, str):
        """
        Parse a Cookie or Set-Cookie header value, and return
        a dict of Cookies. Note: the string should NOT include the
        header name, only the value.
        """

        dict = _parse_cookie(str, Class)
        return dict

    parse = classmethod(parse)

    def __init__(self, name, value, **kw):

        """
        This constructor takes at least a name and value as the
        arguments, as well as optionally any of allowed cookie attributes
        as defined in the existing cookie standards. 
        """
        self.name, self.value = name, value

        for k in kw:
            setattr(self, k.lower(), kw[k])

        # subclasses can use this for internal stuff
        self.__data__ = {}


    def __str__(self):

        """
        Provides the string representation of the Cookie suitable for
        sending to the browser. Note that the actual header name will
        not be part of the string.

        This method makes no attempt to automatically double-quote
        strings that contain special characters, even though the RFC's
        dictate this. This is because doing so seems to confuse most
        browsers out there.
        """
        
        result = ["%s=%s" % (self.name, self.value)]
        for name in self._valid_attr:
            if hasattr(self, name):
                if name in ("secure", "discard", "httponly"):
                    result.append(name)
                else:
                    result.append("%s=%s" % (name, getattr(self, name)))
        return "; ".join(result)
    
    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__,
                                str(self))
    

class SignedCookie(Cookie):
    """
    This is a variation of Cookie that provides automatic
    cryptographic signing of cookies and verification. It uses
    the HMAC support in the Python standard library. This ensures
    that the cookie has not been tamprered with on the client side.

    Note that this class does not encrypt cookie data, thus it
    is still plainly visible as part of the cookie.
    """

    def parse(Class, s, secret):

        dict = _parse_cookie(s, Class)

        for k in dict:
            c = dict[k]
            try:
                c.unsign(secret)
            except CookieError:
                # downgrade to Cookie
                dict[k] = Cookie.parse(Cookie.__str__(c))[k]
        
        return dict

    parse = classmethod(parse)

    def __init__(self, name, value, secret=None, **kw):
        Cookie.__init__(self, name, value, **kw)

        self.__data__["secret"] = secret

    def hexdigest(self, str):
        if not self.__data__["secret"]:
            raise CookieError, "Cannot sign without a secret"
        _hmac = hmac.new(self.__data__["secret"], self.name)
        _hmac.update(str)
        return _hmac.hexdigest()

    def __str__(self):
        
        result = ["%s=%s%s" % (self.name, self.hexdigest(self.value),
                               self.value)]
        for name in self._valid_attr:
            if hasattr(self, name):
                if name in ("secure", "discard", "httponly"):
                    result.append(name)
                else:
                    result.append("%s=%s" % (name, getattr(self, name)))
        return "; ".join(result)

    def unsign(self, secret):

        sig, val = self.value[:32], self.value[32:]

        mac = hmac.new(secret, self.name)
        mac.update(val)

        if mac.hexdigest() == sig:
            self.value = val
            self.__data__["secret"] = secret
        else:
            raise CookieError, "Incorrectly Signed Cookie: %s=%s" % (self.name, self.value)


class MarshalCookie(SignedCookie):

    """
    This is a variation of SignedCookie that can store more than
    just strings. It will automatically marshal the cookie value,
    therefore any marshallable object can be used as value.

    The standard library Cookie module provides the ability to pickle
    data, which is a major security problem. It is believed that unmarshalling
    (as opposed to unpickling) is safe, yet we still err on the side of caution
    which is why this class is a subclass of SignedCooke making sure what
    we are about to unmarshal passes the digital signature test.

    Here is a link to a sugesstion that marshalling is safer than unpickling
    http://groups.google.com/groups?hl=en&lr=&ie=UTF-8&selm=7xn0hcugmy.fsf%40ruckus.brouhaha.com
    """

    def parse(Class, s, secret):

        dict = _parse_cookie(s, Class)

        for k in dict:
            c = dict[k]
            try:
                c.unmarshal(secret)
            except (CookieError, ValueError):
                # downgrade to Cookie
                dict[k] = Cookie.parse(Cookie.__str__(c))[k]

        return dict

    parse = classmethod(parse)

    def __str__(self):
        
        m = base64.encodestring(marshal.dumps(self.value))
        # on long cookies, the base64 encoding can contain multiple lines
        # separated by \n or \r\n
        m = ''.join(m.split())

        result = ["%s=%s%s" % (self.name, self.hexdigest(m), m)]
        for name in self._valid_attr:
            if hasattr(self, name):
                if name in ("secure", "discard", "httponly"):
                    result.append(name)
                else:
                    result.append("%s=%s" % (name, getattr(self, name)))
        return "; ".join(result)

    def unmarshal(self, secret):

        self.unsign(secret)
        self.value = marshal.loads(base64.decodestring(self.value))



# This is a simplified and in some places corrected
# (at least I think it is) pattern from standard lib Cookie.py

_cookiePattern = re.compile(
    r"(?x)"                       # Verbose pattern
    r"[,\ ]*"                        # space/comma (RFC2616 4.2) before attr-val is eaten
    r"(?P<key>"                   # Start of group 'key'
    r"[^;\ =]+"                     # anything but ';', ' ' or '='
    r")"                          # End of group 'key'
    r"\ *(=\ *)?"                 # a space, then may be "=", more space
    r"(?P<val>"                   # Start of group 'val'
    r'"(?:[^\\"]|\\.)*"'            # a doublequoted string
    r"|"                            # or
    r"[^;]*"                        # any word or empty string
    r")"                          # End of group 'val'
    r"\s*;?"                      # probably ending in a semi-colon
    )

def _parse_cookie(str, Class):
    # XXX problem is we should allow duplicate
    # strings
    result = {}

    matchIter = _cookiePattern.finditer(str)

    for match in matchIter:
        key, val = match.group("key"), match.group("val")

        # We just ditch the cookies names which start with a dollar sign since
        # those are in fact RFC2965 cookies attributes. See bug [#MODPYTHON-3].
        if key[0]!='$':
            result[key] = Class(key, val)

    return result

def add_cookie(req, cookie, value="", **kw):
    """
    Sets a cookie in outgoing headers and adds a cache
    directive so that caches don't cache the cookie.
    """

    # is this a cookie?
    if not isinstance(cookie, Cookie):

        # make a cookie
        cookie = Cookie(cookie, value, **kw)
        
    if not req.headers_out.has_key("Set-Cookie"):
        req.headers_out.add("Cache-Control", 'no-cache="set-cookie"')

    req.headers_out.add("Set-Cookie", str(cookie))

def get_cookies(req, Class=Cookie, **kw):
    """
    A shorthand for retrieveing and parsing cookies given
    a Cookie class. The class must be one of the classes from
    this module.
    """
    
    if not req.headers_in.has_key("cookie"):
        return {}

    cookies = req.headers_in["cookie"]
    if type(cookies) == type([]):
        cookies = '; '.join(cookies)

    return Class.parse(cookies, **kw)

