 #
 # Copyright (C) 2000, 2001, 2013, 2024 Gregory Trubetskoy
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

__all__ = ["apache", "cgihandler", "psp",
           "publisher", "util", "python22", "version"]

# This is used by mod_python.c to make sure the version of C
# code matches the Python code.
from . import version
mp_version = version.version

try:
    # it's possible for mod_python to be imported outside httpd, e.g. to use
    # httpdconf, so we fail silently
    from . import apache
except: pass
