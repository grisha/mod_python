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
 # $Id$
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
        self.args = list(args)
        self.indent = 0
    
    def append(self, value):
        self.args.append(value)

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

class AddHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class AddOutputFilter(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class AddType(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class AuthBasicAuthoritative(Directive):
    # New in Apache 2.2
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class AuthBasicProvider(Directive):
    # New in Apache 2.2
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

class DirectoryIndex(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class DocumentRoot(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class ErrorLog(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class IfModule(ContainerTag):
    def __init__(self, dir, *args):
        ContainerTag.__init__(self, self.__class__.__name__, dir, args)

class KeepAliveTimeout(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

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

class LockFile(Directive):
    def __init__(self, val):
        import sys
        if sys.platform!='win32':
            Directive.__init__(self, self.__class__.__name__, val)
        else:
            Directive.__init__(self, '#'+self.__class__.__name__, val)

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

class Options(Directive):
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

class PythonAccessHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonPostReadRequestHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonTransHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonFixupHandler(Directive):
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

class Require(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class SetHandler(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class ServerAdmin(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class ServerName(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

class ServerPath(Directive):
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

class PythonInterpPerDirectory(Directive):
    def __init__(self, val='Off'):
        Directive.__init__(self, self.__class__.__name__, val)

class PythonInterpPerDirective(Directive):
    def __init__(self, val='Off'):
        Directive.__init__(self, self.__class__.__name__, val)

class VirtualHost(ContainerTag):
    def __init__(self, addr, *args):
        ContainerTag.__init__(self, self.__class__.__name__, addr, args)



    
             
    
