
"""

(C) 2003 Apache Software Foundation

$Id: Cookie.py,v 1.1 2003/06/14 03:03:37 grisha Exp $

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

parsing (note the result is a dict of cookies)

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
    This class reflects the sorry state that standardizaion of
    HTTP State Management is currently in. Even though RFC2109
    has been out since 1997, and was even upgraded by RFC2165 in
    2000, most browsers out there still support the buggy Netscape
    specification...
    Here we try to be RFC2109 compliant while making all necessary
    adjustments for those clients that only understand the NS spec.


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

        dict = _parseCookie(str, Class)

        return dict

    parse = classmethod(parse)

    def __init__(self, name, value, **kw):

        self.name, self.value = name, value

        for k in kw:
            setattr(self, k, kw[k])

        if not hasattr(self, "version"):
            self.version = "1"

    def __str__(self):

        # NOTE: quoting the value is up to the user!

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

        # if max-age not already set, make it
        # match expires.
        if not hasattr(self, "max_age"):
            self.max_age = int(max(0, t - time.time()))
        
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

    # It is wrong to assume that unmarshalling data is safe, though
    # here is a link to a sugesstion that it is at least safer than unpickling
    # http://groups.google.com/groups?hl=en&lr=&ie=UTF-8&selm=7xn0hcugmy.fsf%40ruckus.brouhaha.com
    #
    # This class unmarshals only signed cookies, so we're pretty safe
    #

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
    r"\ *"                        # space before attr-val is eaten
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

