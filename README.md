Mod_Python
==========

This is the Mod_Python README file. It consists of the following parts:

1. Getting Started
2. Flex
3. New in 3.3
4. New in 3.0
5. Migrating from Mod_Python 2.7.8
6. OS Hints


1. Getting Started
------------------

See the HTML documentation in the `doc-html` directory for installation instructions and documentation.

If you can't read instructions:

```shell
$ ./configure --with-apxs=/usr/local/apache/sbin/apxs

$ make
$ su
# make install
```

Edit `httpd.conf` as instructed at the end of `make install`.

If the above worked - read the tutorial in the doc directory.

2. Flex
-------

`./configure` will generate a WARNING if it cannot find flex, or it is the wrong version. Generally you can ignore this warning and still successfully compile mod_python as the timestamp of the `src/psp_parser.c` file will be newer than that for the src/psp_parser.l file. If for some reason it still tries to run flex to regenerate the `src/psp_parser.c` file, running `touch src/psp_parser.c` to update the timestamp should stop this and it will use the provided file.

The parser used by psp is written in C generated using flex. This requires a reentrant version of flex, which at this time is 2.5.31. Most platforms however ship with version 2.5.4 which is not suitable, so a pre-generated copy of `src/psp_parser.c` is included with the source. If you make changes to `src/psp_parser.l` and need to recompile the `src/psp_parser.c` file, you must get the correct flex version.

You can specify the path the flex binary by using:

```shell
./configure --with-flex=/path/to/flex/binary
```

3. New in 3.3
-------------

Please refer to doc-html/ for more information.

4. New in 3.0
-------------

* Compatibility with Apache Httpd 2.0 and Python 2.2. (Apache Httpd 1.3 and versions of Python prior to 2.2 will not work.)
* Support for filters (HTTP content only).
* Support for connection handlers allowing for implementation of layer 4 protocols.
* Python*Handler directives can now be assigned to specific file extensions.
* The publisher handler supports default module and method names allowing for cleaner more intuitive url's.
* A basic test suite.
* Many other miscellaneous and internal changes.

5. Migrating from Mod_Python 2.7.8
----------------------------------

First, this version of Mod_Python requires Apache Httpd 2, and Python
2.2. (Python 2.2.2 and Apache Httpd 2.0.43 are latest at the time of
this writing). Please make sure you read the appropriate docs to
understand the impact of upgrading both of those, especially upgrading
httpd. Check out http://httpd.apache.org/docs-2.0/upgrading.html

### Some changes in Mod_Python may impact your existing code:

* When configuring/compiling, note that `--with-python` argument of `./configure` now takes the path to a Python executable, rather than a directory where the source is. The option of having a source directory is no longer supported. If you want a separate version of Python for use with mod_python, you must have it installed.

* Apache 2 will use threads by default, and so will Python. The old warnings about threads no longer apply, for the most part you shouldn't worry about it.

* The user name is now `req.user` instead of `req.connection.user`.

* There is no need for the `req.send_http_header()` method. It is still there for backwards compatibility, but it is a noop. Httpd automatically sends out headers as soon as the first byte of output comes through.

* The request object no longer has a `_req` member. `_req` was undocumented and shouldn't have been used, but if you were using it anyway, your code will break.

* It appears that `req.server.port` is 0 always, but if you need the local port number, you can look at `req.connection.local_addr`.

6. OS Hints
-----------

### FreeBSD:

Apache has to be compiled with threads, even if using the prefork MPM (recommended). In the ports collection, edit the Makefile to add `--enable-threads` in the CONFIGURE_ARGS section.  This has been tested on FreeBSD 4.7; it is possible that earlier versions of FreeBSD may have issues with httpd's use of threads.

### Mac OS X/Darwin:

(Disclaimer: I am not an expert on Darwin, if you see something
incorrect or have suggestions, please mail the dev list. This worked
for me on OS X 10.2.2, fink Python 2.2.1 and httpd 2.0.43 compiled
from source)

1. Libtool that comes with OS X 10.2.2 or earlier is buggy. Here is a patch to fix it:

```shell
--- /usr/bin/glibtool.orig  Fri Nov 15 16:14:59 2002
+++ /usr/bin/glibtool    Fri Nov 15 16:16:36 2002
@@ -181,7 +181,7 @@
 old_archive_from_expsyms_cmds=""

 # Commands used to build and install a shared archive.
-archive_cmds="\$nonopt \$(test \\\"x\$module\\\" = xyes && echo -bundle || echo -dynamiclib) \$allow_undefined_flag -o \$lib \$libobjs \$deplibs\$linker_flags -install_name \$rpath/\$soname \$verstring"
+archive_cmds="\$nonopt \$(test x\$module = xyes && echo -bundle || echo -dynamiclib -install_name \$rpath/\$soname) \$allow_undefined_flag -o \$lib \$libobjs \$deplibs\$linker_flags \$verstring"
 archive_expsym_cmds=""
 postinstall_cmds=""
 postuninstall_cmds=""
--- /usr/share/aclocal/libtool.m4.orig     Fri Nov 15 16:18:23 2002
+++ /usr/share/aclocal/libtool.m4  Fri Nov 15 16:18:45 2002
@@ -1580,7 +1580,7 @@
     # FIXME: Relying on posixy $() will cause problems for
     #        cross-compilation, but unfortunately the echo tests do not
     #        yet detect zsh echo's removal of \ escapes.
-    archive_cmds='$nonopt $(test "x$module" = xyes && echo -bundle || echo -dynamiclib) $allow_undefined_flag -o $lib $libobjs $deplibs$linker_flags -install_name $rpath/$soname $verstring'
+    archive_cmds='$nonopt $(test x$module = xyes && echo -bundle || echo -dynamiclib -install_name $rpath/$soname) $allow_undefined_flag -o $lib $libobjs $deplibs$linker_flags $verstring'
     # We need to add '_' to the symbols in $export_symbols first
     #archive_expsym_cmds="$archive_cmds"' && strip -s $export_symbols'
     hardcode_direct=yes
```

Note that the Fink libtool (1.4.2-5) has a bug too. The Fink libtool is half way there in that it will work with gcc2, but gcc3 does not allow `-install_name` without `-dynamiclib`. I don't provide a patch for Fink libtool since it's so easy to just fix it by manually editing the file.

2. Now that libtool situation is fixed, rebuild httpd. Make sure to rerun `./buildconf` before `./configure`. Also make sure `--enable-so` is specified as argument to `./configure`.

3. On Darwin, libpython cannot be linked statically with mod_python using libtool. libpython has to be a dynamic shared object. The Python distribution does not provide a way of building libpython as a shared library, but the Fink Python distribution comes with one (`/sw/lib/python2.2/config/libpython2.2.dylib`), so the easiest thing is to install Python from [Fink](fink.sourceforge.net).

4. Now configure, build, install mod_python like you normally would:

```shell
./configure --with-apxs=/where/ever/apxs
make
(su)
make install
```

5. You are not out of the woods yet. Python has a lot of its built-in modules as shared libraries (or mach-o bundles to be precise). They are linked with `--bundle_loader python.exe`, which means that many symbols are expected to be defined in the executable loading the bundle. Such would not be the case when the module is loaded from within mod_python, and therefore you will get "undefined symbol" errors when trying to import a built-in module, e.g. "time".

I don't know what the *right* solution for this is, but here is a
trick that works: define `DYLD_FORCE_FLAT_NAMESPACE` environment
variable prior to launching httpd.

### Linux/Debian:

For apache2 installations, use apxs2 rather than apxs:
```shell
./configure --with-apxs=/usr/bin/apxs2
make
(su)
make install
```