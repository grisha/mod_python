 #
 # Copyright (C) 2000, 2001, 2013 Gregory Trubetskoy
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
 #
 # Config maker, a la HTMLGen. This could grow into something useful.
 #

import sys
import os
import shutil

# this is so that it could be referred to in a Container only_if
import mod_python

class Directive:

    def __init__(self, name, val, flipslash=1):
        self.name = name
        self.val = val
        self.indent = 0
        self.flipslash = flipslash

    def __repr__(self):
        i = " " * self.indent
        s = i + '%s(%s)' % (self.name, `self.val`)
        if self.flipslash:
            s = s.replace("\\", "/")
        return s

    def __str__(self):
        i = " " * self.indent
        s = i + '%s %s\n' % (self.name, self.val)
        if self.flipslash:
            s = s.replace("\\", "/")
        return s

class Container:
    
    def __init__(self, *args, **kwargs):
        self.args = list(args)
        self.indent = 0
        self.only_if = kwargs.get('only_if')
    
    def append(self, value):
        if not (isinstance(value, Directive) or
                isinstance(value, Container) or
                isinstance(value, ContainerTag) or
                isinstance(value, Comment)):
            raise TypeError("appended value must be an instance of Directive, Container, ContainerTag or Comment")
        self.args.append(value)

    def __repr__(self):
        i = " " * self.indent
        s = i + 'Container('
        for arg in self.args:
            arg.indent = self.indent + 4
            s += "\n%s," % `arg`
        s += "\n" + i + (self.only_if and ('    only_if=%s)' % `self.only_if`) or ')')
        return s

    def __str__(self):
        if self.only_if and not eval(self.only_if):
            return ""
        s = ""
        for arg in self.args:
            arg.indent = self.indent
            s += "%s" % str(arg)

        return s

class ContainerTag:

    def __init__(self, tag, attr, args, flipslash=1):
        self.tag = tag
        self.attr = attr
        self.args = args
        self.indent = 0
        self.flipslash = flipslash

    def __repr__(self):
        i = " " * self.indent
        s = i + "%s(%s," % (self.tag, `self.attr`)
        if self.flipslash:
            s = s.replace("\\", "/")
        for arg in self.args:
            arg.indent = self.indent + 4
            s += "\n%s," % `arg`
        s += "\n" + i + ")"
        return s

    def __str__(self):
        i = " " * self.indent
        s = i + "<%s %s>\n" % (self.tag, self.attr)
        if self.flipslash:
            s = s.replace("\\", "/")
        for arg in self.args:
            arg.indent = self.indent + 2
            s += "%s" % str(arg)
        s += i + "</%s>\n" % self.tag
        return s

class Comment:

    def __init__(self, comment):
        self.comment = comment
        self.indent = 0

    def __repr__(self):
        i = " " * self.indent
        lines = self.comment.splitlines()
        s = i + "Comment(%s" % `lines[0]+"\n"`
        for line in lines[1:]:
            s += "\n        " + i + `line+"\n"`
        s += ")"
        return s

    def __str__(self):
        i = " " * self.indent
        s = ""
        for line in self.comment.splitlines():
            s += i + '# %s\n' % line
        return s

## directives

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

class Files(ContainerTag):
    def __init__(self, dir, *args):
        ContainerTag.__init__(self, self.__class__.__name__, dir, args)

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

class MaxConnectionsPerChild(Directive):
    def __init__(self, val):
        Directive.__init__(self, self.__class__.__name__, val)

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

class NameVirtualHost(Directive):
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

class PythonAuthzHandler(Directive):
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

## utility functions

def quote_if_space(s):

    # Windows doesn't like quotes when there are
    # no spaces, but needs them otherwise,
    # TODO: Is this still true?
    if s.find(" ") != -1:
        s = '"%s"' % s
    return s

def write_basic_config(server_root, listen='0.0.0.0:8888', conf="conf", logs="logs",
                        htdocs="public", pythonhandler="mod_python.publisher",
                        pythonpath=[], pythonoptions=[], mp_comments=[],
                        conf_name='httpd_conf.py', createdirs=True, replace_config=False):
    """This generates a sensible Apache configuration"""

    conf_path = os.path.join(server_root, conf, conf_name)
    if os.path.exists(conf_path) and not replace_config:
        print >> sys.stderr, 'Error: %s already exists, aborting.' % `conf_path`
        return

    if createdirs:
        for dirname in [server_root,
                        os.path.join(server_root, htdocs),
                        os.path.join(server_root, conf),
                        os.path.join(server_root, logs)]:
            if os.path.isdir(dirname):
                print >> sys.stderr, "Warning: directory %s already exists, continuing." % `dirname`
            else:
                print >> sys.stderr, "Creating directory %s." % `dirname`
                os.mkdir(dirname)

        # try to find mime.types
        mime_types_dest = os.path.join(server_root, conf, 'mime.types')
        if os.path.isfile(mime_types_dest):
            print >> sys.stderr, "Warning: file %s already exists, continuing." % `mime_types_dest`
        else:
            for mime_types_dir in [mod_python.version.SYSCONFDIR, '/etc']:
                mime_types_src = os.path.join(mime_types_dir, 'mime.types')
                if os.path.isfile(mime_types_src):
                    print >> sys.stderr, "Copying %s to %s" % (`mime_types_src`, `mime_types_dest`)
                    shutil.copy(mime_types_src, mime_types_dest)
                    break

    mime_types = os.path.join(conf, "mime.types")
    if not os.path.exists(os.path.join(server_root, mime_types)):
        print >> sys.stderr, "Warning: file %s does not exist." % `os.path.join(server_root, mime_types)`

    if not os.path.isdir(os.path.join(server_root, htdocs)):
        print >> sys.stderr, "Warning: %s does not exist or not a directory." % `os.path.join(server_root, htdocs)`

    modpath = mod_python.version.LIBEXECDIR

    modules = Container(Comment("\nLoad the necessary modules (this is the default httpd set):\n\n"))
    for module in [
        ['authn_file_module', 'mod_authn_file.so'],
        ['authn_core_module', 'mod_authn_core.so'],
        ['authz_host_module', 'mod_authz_host.so'],
        ['authz_groupfile_module', 'mod_authz_groupfile.so'],
        ['authz_user_module', 'mod_authz_user.so'],
        ['authz_core_module', 'mod_authz_core.so'],
        ['access_compat_module', 'mod_access_compat.so'],
        ['auth_basic_module', 'mod_auth_basic.so'],
        ['reqtimeout_module', 'mod_reqtimeout.so'],
        ['include_module', 'mod_include.so'],
        ['filter_module', 'mod_filter.so'],
        ['mime_module', 'mod_mime.so'],
        ['log_config_module', 'mod_log_config.so'],
        ['env_module', 'mod_env.so'],
        ['headers_module', 'mod_headers.so'],
        ['setenvif_module', 'mod_setenvif.so'],
        ['version_module', 'mod_version.so'],
        ['unixd_module', 'mod_unixd.so'],
        ['status_module', 'mod_status.so'],
        ['autoindex_module', 'mod_autoindex.so'],
        ['dir_module', 'mod_dir.so'],
        ['alias_module', 'mod_alias.so'],
        ]:
        modules.append(
            LoadModule("%s %s" % (module[0], quote_if_space(os.path.join(modpath, module[1]))))
            )

    main = Container(Comment("\nMain configuration options:\n\n"),

                     ServerRoot(server_root),

                     Container(MaxConnectionsPerChild('65536'),
                               only_if="mod_python.version.HTTPD_VERSION[0:3] == '2.4'"),
                     Container(MaxRequestsPerChild('65536'),
                               only_if="mod_python.version.HTTPD_VERSION[0:3] < '2.4'"),

                     LogFormat(r'"%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined'),
                     CustomLog("%s combined" % quote_if_space(os.path.join(logs, "access_log"))),
                     ErrorLog(quote_if_space(os.path.join(logs, "error_log"))),
                     LogLevel("warn"),

                     PidFile(quote_if_space(os.path.join(logs, "httpd.pid"))),

                     TypesConfig(quote_if_space(mime_types)),

                     # The only reason we need a ServerName is so that Apache does not
                     # generate a warning about being unable to determine its name.
                     ServerName("127.0.0.1"),
                     Listen(listen),
                     DocumentRoot(quote_if_space(os.path.join(server_root, htdocs))),

                     Container(LockFile(quote_if_space(os.path.join(logs, "accept.lock"))),
                               only_if="mod_python.version.HTTPD_VERSION[0:3] == '2.2'"),
                     )

    mp = Container(Comment("\nmod_python-specific options:\n\n"),
                   LoadModule("python_module %s" % quote_if_space(quote_if_space(os.path.join(modpath, 'mod_python.so')))),
                   SetHandler("mod_python"),
                   Comment("PythonDebug On"),
                   PythonHandler(pythonhandler),
                   )

    if pythonpath:
        pp = "sys.path+["
        for p in pythonpath:
            pp += `p`+","
        pp += "]"
        mp.append(PythonPath('"%s"' % pp))
    for po in pythonoptions:
        mp.append(PythonOption(po))
    for c in mp_comments:
        mp.append(Comment(c))

    config = Container()
    config.append(Comment(
            "\n"
            "This config was auto-generated, do not edit!\n"
            "\n"
            ))
    config.append(modules)
    config.append(main)
    config.append(mp)

    s = """#!%s

#
# This config was auto-generated, but you can edit it!
# It can be used to generate an Apache config by simply
# running it. We recommend you run it like this:
# $ mod_python genconfig <this filename> > <new apache confg>
#\n
""" % mod_python.version.PYTHON_BIN
    s += "from mod_python.httpdconf import *\n\n"
    s += "config = " + `config`
    s += "\n\nprint config\n"

    print >> sys.stderr, "Writing %s." % `conf_path`
    open(conf_path, 'w').write(s)
    return conf_path
