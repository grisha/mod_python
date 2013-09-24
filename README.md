mod_python
==========

This is the mod_python README file. It consists of the following parts:

Getting Started
------------------

See the HTML documentation in the `doc-html` directory for installation
instructions and documentation.

If you can't read instructions:

```shell
$ ./configure
$ make
$ sudo make install
```

If the above worked - read the tutorial in the doc directory.


OS Hints
-----------

### Windows:

HELP NEEDED! I do not have access to a Windows development environment. If you get
a Windows compile working, please drop a note on the mod_python
mailing list.

### Mac OS X/Darwin:

At least on OS X 10.8.5, the following was required in order for compile to work:

sudo ln -s /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain \
    /Applications/Xcode.app/Contents/Developer/Toolchains/OSX10.8.xctoolchain

