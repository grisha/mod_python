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
 # $Id: httpdconf.py,v 1.3 2002/10/12 05:41:31 grisha Exp $
 #
 # Config maker, a la HTMLGen. This could grow into something useful.
 #

class Directive:

    def __init__(self, name, val, flipslash=1):
        self.name = name
        self.val = val
        self.indent = 0
        self.flipslash = flipslash

    def __str__(self):

        i = " " * self.indent
        s = i + '%s %s\n' % (self.name, self.val)
        if self.flipslash:
            s = s.replace("\\", "/")
        return s

class Container:
    
    def __init__(self, *args):
        self.args = args
        self.indent = 0

    def __str__(self):

        i = " " * self.indent
        s = "\n"
        for arg in self.args:
            s += i + "%s" % str(arg)

        return s

class ContainerTag:

    def __init__(self, tag, attr, args, flipslash=1):
        self.tag = tag
        self.attr = attr
        self.args = args
        self.indent = 0
        self.flipslash = flipslash

    def __str__(self):

        i = " " * self.indent

        s = i + "<%s %s>\n" % (self.tag, self.attr)
        if self.flipslash:
            s = s.replace("\\", "/")
        for arg in self.args:
            arg.indent = self.indent + 2
            s += i + "%s" % str(arg)
        s += i + "</%s>\n" % self.tag

        return s

class AddOutputFilter(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class AuthType(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class AuthName(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class CustomLog(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class Directory(ContainerTag):
    def __init__(self, dir, *args):
        ContainerTag.__init__(self, self.__class__.__name__, dir, args)

class DocumentRoot(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class ErrorLog(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class IfModule(ContainerTag):
    def __init__(self, dir, *args):
        ContainerTag.__init__(self, self.__class__.__name__, dir, args)

class Listen(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class LoadModule(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class LogLevel(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class LogFormat(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val, flipslash=0)

class MaxClients(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class MaxRequestsPerChild(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class MaxSpareServers(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class MaxSpareThreads(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class MaxThreadsPerChild(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class MinSpareThreads(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class NumServers(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PidFile(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonAuthenHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonConnectionHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonDebug(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonImport(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonPath(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val, flipslash=0)

class PythonOutputFilter(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonOption(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class require(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class SetHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class ServerName(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class ServerRoot(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class StartServers(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class StartThreads(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class ThreadsPerChild(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class Timeout(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class TypesConfig(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class VirtualHost(ContainerTag):
    def __init__(self, addr, *args):
        ContainerTag.__init__(self, self.__class__.__name__, addr, args)



    
             
    
