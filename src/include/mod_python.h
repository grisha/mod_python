#ifndef Mp_MOD_PYTHON_H
#define Mp_MOD_PYTHON_H

/* ====================================================================
 * The Apache Software License, Version 1.1
 *
 * Copyright (c) 2000-2002 The Apache Software Foundation.  All rights
 * reserved.
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
 * 3. The end-user documentation included with the redistribution,
 *    if any, must include the following acknowledgment:
 *       "This product includes software developed by the
 *        Apache Software Foundation (http://www.apache.org/)."
 *    Alternately, this acknowledgment may appear in the software itself,
 *    if and wherever such third-party acknowledgments normally appear.
 *
 * 4. The names "Apache" and "Apache Software Foundation" must
 *    not be used to endorse or promote products derived from this
 *    software without prior written permission. For written
 *    permission, please contact apache@apache.org.
 *
 * 5. Products derived from this software may not be called "Apache",
 *    "mod_python", or "modpython", nor may these terms appear in their
 *    name, without prior written permission of the Apache Software
 *    Foundation.
 *
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED.  IN NO EVENT SHALL THE APACHE SOFTWARE FOUNDATION OR
 * ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 * USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 * ====================================================================
 *
 * This software consists of voluntary contributions made by many
 * individuals on behalf of the Apache Software Foundation.  For more
 * information on the Apache Software Foundation, please see
 * <http://www.apache.org/>.
 *
 * Originally developed by Gregory Trubetskoy <grisha@apache.org>
 *
 *
 * mod_python.h 
 *
 * $Id: mod_python.h,v 1.24 2002/09/12 18:24:06 gstein Exp $
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

/* Apache headers */
#include "httpd.h"
#define CORE_PRIVATE
#include "http_config.h"
#include "http_core.h"
#include "http_main.h"
#include "http_connection.h"
#include "http_protocol.h"
#include "http_request.h"
#include "util_script.h"
#include "util_filter.h"
#include "http_log.h"
#include "apr_strings.h"
#include "apr_lib.h"
#include "apr_hash.h"
#include "scoreboard.h"

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
void init_apache(void);

/* pool given to us in ChildInit. We use it for 
   server.register_cleanup() */
extern apr_pool_t *child_init_pool;

/* Apache module declaration */
extern module AP_MODULE_DECLARE_DATA python_module;

#include "mpversion.h"
#include "_apachemodule.h"
#include "util.h"
#include "hlist.h"
#include "hlistobject.h"
#include "tableobject.h"
#include "serverobject.h"
#include "connobject.h"
#include "requestobject.h"
#include "filterobject.h"

/** Things specific to mod_python, as an Apache module **/

#define VERSION_COMPONENT "mod_python/" MPV_STRING
#define MODULENAME "mod_python.apache"
#define INITFUNC "init"
#define MAIN_INTERPRETER "main_interpreter"
#ifdef WIN32
#define SLASH '\\'
#define SLASH_S "\\"
#else
#define SLASH '/'
#define SLASH_S "/"
#endif
/* used in python_directive_handler */
#define SILENT 0
#define NOTSILENT 1

/* structure to hold interpreter data */
typedef struct {
    PyInterpreterState *istate;
    PyObject *obcallback;
} interpreterdata;

/* structure describing per directory configuration parameters */
typedef struct {
    int           authoritative;
    char         *config_dir;
    apr_table_t  *directives;
    apr_table_t  *options;
    apr_hash_t   *hlists; /* hlists for every phase */
    apr_hash_t   *in_filters;
    apr_hash_t   *out_filters;
} py_config;

/* register_cleanup info */
typedef struct
{
    request_rec  *request_rec;
    server_rec   *server_rec;
    PyObject     *handler;
    const char   *interpreter;
    PyObject     *data;
} cleanup_info;

/* request config structure */
typedef struct
{
    requestobject *request_obj;
    apr_hash_t    *dynhls;     /* dynamically registered handlers
				  for this request */
} py_req_config;

/* filter context */
typedef struct
{
    int transparent;
} python_filter_ctx;

/* a structure to hold a handler, 
   used in configuration for filters */
typedef struct
{
    char *handler;
    char *dir;
} py_handler;

apr_status_t python_cleanup(void *data);
static apr_status_t python_cleanup_handler(void *data);

#endif /* !Mp_MOD_PYTHON_H */
