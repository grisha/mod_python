 # Copyright 2004 Apache Software Foundation
 #
 #  Licensed under the Apache License, Version 2.0 (the "License");
 #  you may not use this file except in compliance with the License.
 #  You may obtain a copy of the License at
 #
 #      http://www.apache.org/licenses/LICENSE-2.0
 #
 #  Unless required by applicable law or agreed to in writing, software
 #  distributed under the License is distributed on an "AS IS" BASIS,
 #  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 #  See the License for the specific language governing permissions and
 #  limitations under the License.
 #
 # Originally developed by Gregory Trubetskoy.
 #
 # $Id$
 #
 # this script runs at the end of windows install


import sys, os, shutil
import distutils.sysconfig

def getApacheDirOptions():
    """find potential apache directories in the registry..."""
    try:
        import win32api, win32con
        class nullregkey:
            """a registry key that doesn't exist..."""
            def childkey(self, subkeyname):
                return nullregkey()
            def subkeynames(self):
                return []
            def getvalue(self, valuename):
                raise AttributeError("Cannot access registry value %r: key does not exist" % (valuename))
        class regkey:
            """simple wrapper for registry functions that closes keys nicely..."""
            def __init__(self, parent, subkeyname):
               self.key = win32api.RegOpenKey(parent, subkeyname)
            def childkey(self, subkeyname):
               try:
                   return regkey(self.key, subkeyname)
               except win32api.error:
                   return nullregkey()
            def subkeynames(self):
               numsubkeys = win32api.RegQueryInfoKey(self.key)[0]
               return [win32api.RegEnumKey(self.key, index) for index in range(numsubkeys)]
            def getvalue(self, valuename):
               try:
                   return win32api.RegQueryValueEx(self.key, valuename)
               except win32api.error:
                   raise AttributeError("Cannot access registry value %r" % (valuename))
            def __del__(self):
               if hasattr(self, "key"):
                   win32api.RegCloseKey(self.key)
    except ImportError:
        return {}
    versions = {}
    hklm_key = regkey(win32con.HKEY_LOCAL_MACHINE, "Software").childkey("Apache Group").childkey("Apache")
    hkcu_key = regkey(win32con.HKEY_CURRENT_USER, "Software").childkey("Apache Group").childkey("Apache")
    for apachekey in (hklm_key, hkcu_key):
        for versionname in apachekey.subkeynames():
            try:
                serverroot = apachekey.childkey(versionname).getvalue("ServerRoot")
            except AttributeError:
                continue
            versions[versionname] = serverroot[0]
    return versions

def askForApacheDir(apachediroptions):
    # try to ask for Apache directory
    if len(apachediroptions) > 0:
        # get the most recent version...
        versionnames = apachediroptions.keys()
        versionnames.sort()
        initialdir = apachediroptions[versionnames[-1]]
    else:
        initialdir="C:/Program Files/Apache Group/Apache2"
    # TODO: let the user select the name from a list, or click browse to choose...
    try:
        from tkFileDialog import askdirectory
        from Tkinter import Tk
        root = Tk()
        root.withdraw()
        path = askdirectory(title="Where is Apache installed?",
                            initialdir=initialdir,
                            mustexist=1, master=root)
        root.quit()
        root.destroy()
        return path
    except ImportError:
        try:
            from win32com.shell import shell
            pidl, displayname, imagelist = shell.SHBrowseForFolder(0, None, "Where is Apache installed?")
            path = shell.SHGetPathFromIDList(pidl)
            return path
        except ImportError:
            return ""

# if we're called during removal, just exit
if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] != "-remove"):

    mp = os.path.join(distutils.sysconfig.get_python_lib(), "mod_python_so.pyd")

    apachediroptions = getApacheDirOptions()

    apachedir = askForApacheDir(apachediroptions)

    if apachedir:

        # put mod_python.so there
        shutil.copy2(mp, os.path.join(apachedir, "modules", "mod_python.so"))
        os.remove(mp)

        print """Important Note for Windows users, PLEASE READ!!!

        1. This script does not attempt to modify Apache configuration,
           you must do it manually:

           Edit %s,
           find where other LoadModule lines are and add this:
                LoadModule python_module modules/mod_python.so

        2. Now test your installation using the instructions at this link:
           http://www.modpython.org/live/current/doc-html/inst-testing.html

        """ % os.path.join(apachedir, "conf", "httpd.conf")

    else:

        print """Important Note for Windows users, PLEASE READ!!!

        1. It appears that you do not have Tkinter installed,
           which is required for a part of this installation.
           Therefore you must manually take
           "%s"
           and copy it to your Apache modules directory.

        2. This script does not attempt to modify Apache configuration,
           you must do it manually:

           Edit %s,
           find where other LoadModule lines and add this:
                LoadModule python_module modules/mod_python.so

        3. Now test your installation using the instructions at this link:
           http://www.modpython.org/live/current/doc-html/inst-testing.html

        """ % (mp, os.path.join(apachedir, "conf", "httpd.conf"))
