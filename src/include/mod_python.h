#ifndef Mp_MOD_PYTHON_H
#define Mp_MOD_PYTHON_H
/*====================================================================
 * Copyright (c) 2000 Gregory Trubetskoy.  All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer. 
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in
 *    the documentation and/or other materials provided with the
 *    distribution.
 *
 * 3. All advertising materials mentioning features or use of this
 *    software must display the following acknowledgment:
 *    "This product includes software developed by Gregory Trubetskoy
 *    for use in the mod_python module for Apache HTTP server 
 *    (http://www.modpython.org/)."
 *
 * 4. The names "mod_python", "modpython" or "Gregory Trubetskoy" must not 
 *    be used to endorse or promote products derived from this software 
 *    without prior written permission. For written permission, please 
 *    contact grisha@ispol.com.
 *
 * 5. Products derived from this software may not be called "mod_python"
 *    or "modpython", nor may "mod_python" or "modpython" appear in their 
 *    names without prior written permission of Gregory Trubetskoy. For 
 *    written permission, please contact grisha@ispol.com..
 *
 * 6. Redistributions of any form whatsoever must retain the following
 *    acknowledgment:
 *    "This product includes software developed by Gregory Trubetskoy
 *    for use in the mod_python module for Apache HTTP server 
 *    (http://www.modpython.org/)."
 *
 * THIS SOFTWARE IS PROVIDED BY GREGORY TRUBETSKOY ``AS IS'' AND ANY
 * EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL GREGORY TRUBETSKOY OR
 * HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 * ====================================================================
 *
 * This software is based on the original concept
 * as published in the book "Internet Programming with Python"
 * by Aaron Watters, Guido van Rossum and James C. Ahlstrom, 
 * 1996 M&T Books, ISBN: 1-55851-484-8. The book and original
 * software is Copyright 1996 by M&T Books.
 *
 * This software consists of an extension to the Apache http server.
 * More information about Apache may be found at 
 *
 * http://www.apache.org/
 *
 * More information on Python language can be found at
 *
 * http://www.python.org/
 *
 *
 * mod_python.c 
 *
 * $Id: mod_python.h,v 1.9 2000/10/30 23:16:10 gtrubetskoy Exp $
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 * Apr 2000 - rename to mod_python and go apache-specific.
 * Nov 1998 - support for multiple interpreters introduced.
 * May 1998 - initial release (httpdapy).
 *
 */


/* Apache headers */
#include "httpd.h"
#include "http_config.h"
#include "http_core.h"
#include "http_main.h"
#include "http_protocol.h"
#include "util_script.h"
#include "http_log.h"


/* Python headers */
/* this gets rid of some comile warnings */
#if defined(_POSIX_THREADS)
#undef _POSIX_THREADS
#endif
#include "Python.h"
#include "structmember.h"

#if defined(WIN32) && !defined(WITH_THREAD)
#error Python threading must be enabled on Windows
#endif

#if !defined(WIN32)
#include <sys/socket.h>
#endif

/* _apache initialization function */
void init_apache();

/* pool given to us in ChildInit. We use it for 
   server.register_cleanup() */
extern pool *child_init_pool;

/* Apache module declaration */
extern module MODULE_VAR_EXPORT python_module;

#include "util.h"
#include "tableobject.h"
#include "serverobject.h"
#include "connobject.h"
#include "requestobject.h"
/* #include "arrayobject.h" */

/** Things specific to mod_python, as an Apache module **/

#define VERSION_COMPONENT "mod_python/2.7"
#define MODULENAME "mod_python.apache"
#define INITFUNC "init"
#define GLOBAL_INTERPRETER "global_interpreter"
#ifdef WIN32
#define SLASH '\\'
#define SLASH_S "\\"
#else
#define SLASH '/'
#define SLASH_S "/"
#endif

/* structure to hold interpreter data */
typedef struct {
    PyInterpreterState *istate;
    PyObject *obcallback;
} interpreterdata;

/* structure describing per directory configuration parameters */
typedef struct 
{
    int           authoritative;
    char         *config_dir;
    table        *options;
    table        *directives;
    table        *dirs;
} py_dir_config;

/* register_cleanup info */
typedef struct
{
    request_rec  *request_rec;
    server_rec   *server_rec;
    PyObject     *handler;
    const char   *interpreter;
    PyObject     *data;
} cleanup_info;

void python_cleanup(void *data);

#endif /* !Mp_MOD_PYTHON_H */
