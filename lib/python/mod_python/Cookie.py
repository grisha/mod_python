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
 # $Id: Cookie.py,v 1.3 2003/06/27 16:59:05 grisha Exp $

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


Sample usage:

A "Cookie" is a cookie, not a list of cookies as in std lib Cookie.py

* making a cookie:

>>> c = Cookie("spam", "eggs")
>>> print c
spam=eggs; version=1
>>> c.max_age = 3
>>> str(c)
'spam=eggs; version=1; expires=Sat, 14-Jun-2003 02:42:36 GMT; max_age=3'
>>>

* bogus attributes not allowed:

>>> c.eggs = 24
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
  AttributeError: 'Cookie' object has no attribute 'eggs'

* parsing (note the result is a dict of cookies)

>>> Cookie.parse(str(c))
{'spam': <Cookie: spam=eggs; version=1; expires=Sat, 14-Jun-2003 02:42:36 GMT; max_age=3>}
>>>

* signed cookies (uses hmac):

>>> sc = SignedCookie("spam", "eggs", "secret")
>>> print sc
spam=da1170b718dfbad95c392db649d24898eggs; version=1
>>>

* parsing signed cookies:

>>> SignedCookie.parse("secret", str(sc))
{'spam': <SignedCookie: spam=da1170b718dfbad95c392db649d24898eggs; version=1>}
>>>

>>> SignedCookie.parse("evil", str(sc))
   [snip]
        Cookie.CookieError: Incorrectly Signed Cookie: spam=da1170b718dfbad95c392db649d24898eggs
>>>

* marshal cookies (subclass of SignedCookie, so MUST be signed),
  also - this is marshal, not pickle (that would be too scary):

>>> mc = MarshalCookie("spam", {"eggs":24}, "secret")
>>> print mc
spam=a90f71893109ca246ab68860f552302ce3MEAAAAZWdnc2kYAAAAMA==; version=1
>>>

>>> newmc = MarshalCookie.parse("secret", str(mc))
>>> print newmc["spam"]
spam=a90f71893109ca246ab68860f552302ce3MEAAAAZWdnc2kYAAAAMA==; version=1
>>> newmc["spam"].value
{'eggs': 24}
>>>

NB: This module is named Cookie with a capital C so as to let people
have a variable called cookie without accidently overwriting the
module.

"""

import time
import re
import hmac
import marshal
import base64

class CookieError(Exception):
    pass

class Cookie(object):
    """
    This class implements the basic Cookie functionality. Note that
    unlike the Python Standard Library Cookie class, this class represents
    a single cookie (not a list of Morsels).
    """

    _valid_attr = (
        "version", "path", "domain", "secure",
        "comment", "expires", "max_age",
        # RFC 2965
        "commentURL", "discard", "port")

    # _valid_attr + property values
    # (note __slots__ is a new Python feature, it
    # prevents any other attribute from being set)
    __slots__ = _valid_attr + ("name", "value", "_value",
                               "_expires", "_max_age")

    def parse(Class, str):
        """
        Parse a Cookie or Set-Cookie header value, and return
        a dict of Cookies. Note: the string should NOT include the
        header name, only the value.
        """

        dict = _parseCookie(str, Class)
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
                if name in ("secure", "discard"):
                    result.append(name)
                else:
                    result.append("%s=%s" % (name, getattr(self, name)))
        return "; ".join(result)
    
    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__,
                                str(self))
    
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

    def set_max_age(self, value):

        self._max_age = int(value)

        # if expires not already set, make it
        # match max_age for those old browsers that
        # only understand the Netscape spec
        if not hasattr(self, "expires"):
            self._expires = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT",
                                          time.gmtime(time.time() +
                                                      self._max_age))

    def get_max_age(self):
        return self._max_age

    expires = property(fget=get_expires, fset=set_expires)
    max_age = property(fget=get_max_age, fset=set_max_age)

class SignedCookie(Cookie):
    """
    This is a variation of Cookie that provides automatic
    cryptographic signing of cookies and verification. It uses
    the HMAC support in the Python standard library. This ensures
    that the cookie has not been tamprered with on the client side.

    Note that this class does not encrypt cookie data, thus it
    is still plainly visible as part of the cookie.
    """

    def parse(Class, secret, str):

        dict = _parseCookie(str, Class)

        for k in dict:
            dict[k].unsign(secret)
        
        return dict

    parse = classmethod(parse)

    __slots__ = Cookie.__slots__ + ("_secret",)

    expires = property(fget=Cookie.get_expires, fset=Cookie.set_expires)
    max_age = property(fget=Cookie.get_max_age, fset=Cookie.set_max_age)

    def __init__(self, name, value, secret=None, **kw):

        self._secret = secret

        Cookie.__init__(self, name, value, **kw)

    def hexdigest(self, str):
        if not self._secret:
            raise CookieError, "Cannot sign without a secret"
        _hmac = hmac.new(self._secret, self.name)
        _hmac.update(str)
        return _hmac.hexdigest()

    def __str__(self):
        
        result = ["%s=%s%s" % (self.name, self.hexdigest(self.value),
                               self.value)]
        for name in self._valid_attr:
            if hasattr(self, name):
                if name in ("secure", "discard"):
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
            self._secret = secret
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
    __slots__ = SignedCookie.__slots__ 

    expires = property(fget=Cookie.get_expires, fset=Cookie.set_expires)
    max_age = property(fget=Cookie.get_max_age, fset=Cookie.set_max_age)

    def parse(Class, secret, str):

        dict = _parseCookie(str, Class)

        for k in dict:
            dict[k].unmarshal(secret)
        
        return dict

    parse = classmethod(parse)

    def __str__(self):
        
        m = base64.encodestring(marshal.dumps(self.value))[:-1]

        result = ["%s=%s%s" % (self.name, self.hexdigest(m), m)]
        for name in self._valid_attr:
            if hasattr(self, name):
                if name in ("secure", "discard"):
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
    r"[,\ ]*"                     # space/comma (RFC2616 4.2) before attr-val is eaten
    r"(?P<key>"                   # Start of group 'key'
    r"[^;\ =]+"                     # anything but ';', ' ' or '='
    r")"                          # End of group 'key'
    r"\ *(=\ *)?"                 # apace, then may be "=", more space
    r"(?P<val>"                   # Start of group 'val'
    r'"(?:[^\\"]|\\.)*"'            # a doublequoted string
    r"|"                            # or
    r"[^;]*"                        # any word or empty string
    r")"                          # End of group 'val'
    r"\s*;?"                      # probably ending in a semi-colon
    )

def _parseCookie(str, Class):

    # XXX problem is we should allow duplicate
    # strings
    result = {}

    # max-age is a problem because of the '-'
    # XXX there should be a more elegant way
    valid = Cookie._valid_attr + ("max-age",)

    c = None
    matchIter = _cookiePattern.finditer(str)

    for match in matchIter:

        key, val = match.group("key"), match.group("val")

        if not c:
            # new cookie
            c = Class(key, val)
            result[key] = c

        l_key = key.lower()
        
        if (l_key in valid or key[0] == '$'):
            
            # "internal" attribute, add to cookie

            if l_key == "max-age":
                l_key = "max_age"
            setattr(c, l_key, val)

        else:
            # start a new cookie
            c = Class(key, val)
            result[key] = c

    return result


def setCookie(req, cookie):
    """
    Sets a cookie in outgoing headers and adds a cache
    directive so that caches don't cache the cookie.
    """

    if not req.headers_out.has_key("Set-Cookie"):
        req.headers_out.add("Cache-Control", 'no-cache="set-cookie"')
        
    req.headers_out.add("Set-Cookie", str(cookie))

def getCookie(req, Class=Cookie, data=None):
    """
    A shorthand for retrieveing and parsing cookies given
    a Cookie class. The class must be one of the classes from
    this module.
    """

    if not req.headers_in.has_key("cookie"):
        return None

    cookies = req.headers_in["cookie"]
    if type(cookies) == type([]):
        cookies = '; '.join(cookies)

    if data:
        return Class.parse(data, cookies)
    else:
        return Class.parse(cookies)
