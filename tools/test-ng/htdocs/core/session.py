#
# Copyright 2006 Apache Software Foundation 
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
# $Id$
#

"""mod_python.Session tests"""

from mod_python import apache

def Session_Session(req):

    from mod_python import Session, Cookie

    s = Session.Session(req)
    if s.is_new():
        s.save()
        
    cookies = Cookie.get_cookies(req)
    if cookies.has_key(Session.COOKIE_NAME) and s.is_new():
        req.write(str(cookies[Session.COOKIE_NAME]))
    else:
        req.write("test ok")

    return apache.OK


