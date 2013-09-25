mod_python
==========

Documentation for mod_python is on http://www.modpython.org/

Quick Start
-----------

If you can't read instructions:

```shell
$ ./configure
$ make
$ sudo make install
$ make test
```

If the above worked - read the tutorial in the documentation.

OS Hints
--------

### Windows:

HELP NEEDED! I do not have access to a Windows development
environment. If you get a Windows compile working, please create a
pull request or drop a note on the mod_python mailing list:
mod_python@modpython.org (Note: subscription required).

### Mac OS X/Darwin:

At least on OS X 10.8.5, the following was required in order for compile to work:

```shell
sudo ln -s /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain \
    /Applications/Xcode.app/Contents/Developer/Toolchains/OSX10.8.xctoolchain
```
