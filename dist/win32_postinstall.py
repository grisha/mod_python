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
 # $Id: win32_postinstall.py,v 1.4 2003/08/27 15:39:03 grisha Exp $
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
