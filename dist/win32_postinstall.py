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
 # $Id: win32_postinstall.py,v 1.5 2004/02/16 19:47:27 grisha Exp $
 #
 # this script runs at the end of windows install


import sys, os, shutil


def askForApacheDir():
    # try to ask for Apache directory
    try:
        from tkFileDialog import askdirectory
        from Tkinter import Tk
        root = Tk()
        root.withdraw()
        path = askdirectory(title="Where is Apache installed?",
                            initialdir="C:/Program Files/Apache Group/Apache2",
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
if len(sys.argv) == 0 or sys.argv[1] != "-remove":

    mp = os.path.join(sys.prefix, "mod_python.so")

    apachedir = askForApacheDir()

    if apachedir:

        # put mod_python.so there
        shutil.copy2(mp, os.path.join(apachedir, "modules"))
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
