#ifndef Mp_MOD_PYTHON_H
#define Mp_MOD_PYTHON_H

/*
 * Copyright (C) 2000, 2001, 2013 Gregory Trubetskoy
 * Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007 Apache Software Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you
 * may not use this file except in compliance with the License.  You
 * may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied.  See the License for the specific language governing
 * permissions and limitations under the License.
 *
 * Originally developed by Gregory Trubetskoy.
 *
 *
 * mod_python.h
 *
 * $Id: mod_python.h 231054 2005-08-09 15:37:04Z jgallacher $
 *
 * See accompanying documentation and source code comments
 * for details.
 *
 */

/*
 *
 *
 * DO NOT EDIT  -  DO NOT EDIT -  DO NOT EDIT - DO NOT EDIT
 *
 *
 *
 * If you are looking at mod_python.h, it is an auto-generated file on
 * UNIX.  This file is kept around for the Win32 platform which
 * does not use autoconf. Any changes to mod_python.h must also be
 * reflected in mod_python.h.in.
 */

/* Python headers */
#include "Python.h"
#include "structmember.h"

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
#include "apr_fnmatch.h"
#include "scoreboard.h"
#include "ap_mpm.h"
#include "ap_mmn.h"
#include "mod_include.h"
#if !defined(OS2) && !defined(WIN32) && !defined(BEOS) && !defined(NETWARE)
#include "unixd.h"
#endif

#if !AP_MODULE_MAGIC_AT_LEAST(20050127,0)
/* Debian backported ap_regex_t to Apache 2.0 and
 * thus made official version checking break. */
#ifndef AP_REG_EXTENDED
typedef regex_t ap_regex_t;
#define AP_REG_EXTENDED REG_EXTENDED
#define AP_REG_ICASE REG_ICASE
#endif
#endif

#if defined(WIN32) && !defined(WITH_THREAD)
#error Python threading must be enabled on Windows
#endif

#if !defined(WIN32)
#include <sys/socket.h>
#endif

/* pool given to us in ChildInit. We use it for
   server.register_cleanup() */
extern apr_pool_t *child_init_pool;

/* Apache module declaration */
extern module AP_MODULE_DECLARE_DATA python_module;

#include "util.h"
#include "hlist.h"
#include "hlistobject.h"
#include "tableobject.h"
#include "serverobject.h"
#include "connobject.h"
#include "_apachemodule.h"
#include "requestobject.h"
#include "filterobject.h"
#include "finfoobject.h"

/** Things specific to mod_python, as an Apache module **/

#if PY_MAJOR_VERSION < 3

#define PyBytesObject PyStringObject
#define PyBytes_Check PyString_Check
#define PyBytes_CheckExact PyString_CheckExact
#define PyBytes_FromString PyString_FromString
#define PyBytes_FromStringAndSize PyString_FromStringAndSize
#define PyBytes_AS_STRING PyString_AS_STRING
#define PyBytes_ConcatAndDel PyString_ConcatAndDel
#define PyBytes_Size PyString_Size
#define _PyBytes_Resize _PyString_Resize
#define MpObject_ReprAsBytes PyObject_Repr
#define MpBytesOrUnicode_FromString PyString_FromString

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size)       \
    PyObject_HEAD_INIT(type) size,
#endif

#ifndef Py_TYPE
#define Py_TYPE(ob) (((PyObject*)(ob))->ob_type)
#endif

#else

#define MpBytesOrUnicode_FromString PyUnicode_FromString

#endif /* PY_MAJOR_VERSION < 3 */

#define MP_CONFIG_KEY "mod_python_config"
#define MAIN_INTERPRETER "main_interpreter"
#define FILTER_NAME "MOD_PYTHON"

/* used in python_directive_handler */
#define SILENT 1
#define NOTSILENT 0

/* MAX_LOCKS can now be set as a configure option
 * ./configure --with-max-locks=INTEGER
 */
#define MAX_LOCKS 8

/* MUTEX_DIR can be set as a configure option
 * ./configure --with-mutex-dir=/path/to/dir
 */
#define MUTEX_DIR "/tmp"

/* version stuff */
extern const int mp_version_major;
extern const int mp_version_minor;
extern const int mp_version_patch;
extern const char * const mp_version_string;
extern const char * const mp_version_component;

/* structure to hold interpreter data */
typedef struct {
    apr_array_header_t * tstates; /* tstates available for use */
    PyInterpreterState *interp;
    PyObject *obcallback;
} interpreterdata;

/* global configuration parameters */
typedef struct
{
    apr_global_mutex_t **g_locks;
    int                  nlocks;
    int                  parent_pid;
} py_global_config;

/* structure describing per directory configuration parameters */
typedef struct {
    int           authoritative;
    char         *config_dir;
    char         d_is_location;
    apr_table_t  *directives;
    apr_table_t  *options;
    apr_hash_t   *hlists; /* hlists for every phase */
    apr_hash_t   *in_filters;
    apr_hash_t   *out_filters;
    apr_table_t  *imports;  /* for PythonImport */
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
    apr_hash_t   *in_filters;  /* dynamically registered input filters
                                  for this request */
    apr_hash_t   *out_filters; /* dynamically registered output filters
                                  for this request */

} py_req_config;

/* filter context */
typedef struct
{
    char *name;
    int transparent;
} python_filter_ctx;

/* a structure to hold a handler,
   used in configuration for filters */
typedef struct
{
    char *handler;
    char *directory;
    unsigned d_is_fnmatch : 1;
    unsigned d_is_location : 1;
    ap_regex_t *regex;
} py_handler;

apr_status_t python_cleanup(void *data);
PyObject* python_interpreter_name(void);
requestobject *python_get_request_object(request_rec *req, const char *phase);
PyObject *_apache_module_init();

APR_DECLARE_OPTIONAL_FN(PyInterpreterState *, mp_acquire_interpreter, (const char *));
APR_DECLARE_OPTIONAL_FN(void, mp_release_interpreter, ());
APR_DECLARE_OPTIONAL_FN(PyObject *, mp_get_request_object, (request_rec *));
APR_DECLARE_OPTIONAL_FN(PyObject *, mp_get_server_object, (server_rec *));
APR_DECLARE_OPTIONAL_FN(PyObject *, mp_get_connection_object, (conn_rec *));

/* This macro assigns a C string representation of PyObject *obj to
 * char *str. obj must be a Unicode Latin1 or Bytes. It will try its
 * best to accomplish this with zero-copy. WARNING - it DECREFs
 * (unless obj_is_borrowed) and changes the value of obj when it is
 * unicode that must be recoded, so do not use obj afterwards other
 * than to DECREF it - it may not be what you expected. You MUST
 * Py_DECREF(obj) afterward (even if error), but not before you're
 * done with the value of str. Note that if the obj reference was
 * borrowed, and without the macro you wouldn't be DECREFing it, you
 * should indicate that by setting obj_is_borrowed to 1 and DECREF
 * it. If after this macro str is NULL, then a TypeError error has
 * been set by the macro.
 */
#if PY_MAJOR_VERSION < 3
#define PyUnicode_1BYTE_KIND NULL
#define PyUnicode_KIND(str)  NULL
#define PyUnicode_1BYTE_DATA(obj) ""
#endif
#define MP_ANYSTR_AS_STR(str, obj, obj_is_borrowed) do {                \
        str = NULL;                                                     \
        if (PyUnicode_CheckExact(obj)) {                                \
            if (PY_MAJOR_VERSION >= 3 && PY_MINOR_VERSION >= 3 &&       \
                PyUnicode_KIND(obj) == PyUnicode_1BYTE_KIND) {          \
                if (obj_is_borrowed) Py_INCREF(obj); /* so DECREF ok */ \
                str = PyUnicode_1BYTE_DATA(obj);                        \
            } else {                                                    \
                PyObject *latin = PyUnicode_AsLatin1String(obj);        \
                if (latin) {                                            \
                    str = PyBytes_AsString(latin); /* #define on 2.6 */ \
                    if (!obj_is_borrowed) Py_DECREF(obj);               \
                    obj = latin;           /* remember to DECREF me! */ \
                }                                                       \
            }                                                           \
        } else if (PyBytes_CheckExact(obj)) {   /* #define on 2.6 */    \
            str = PyBytes_AsString(obj);        /* #define on 2.6 */    \
            if (obj_is_borrowed) Py_INCREF(obj);     /* so DECREF ok */ \
        }                                                               \
        if (!str) {                                                     \
            if (obj_is_borrowed) Py_INCREF(obj);     /* so DECREF ok */ \
            PyErr_SetString(PyExc_TypeError,                            \
                            "not an ISO-8859-1 string");                \
        }                                                               \
    } while (0)

#ifndef MpObject_ReprAsBytes
static inline PyObject *MpObject_ReprAsBytes(PyObject *o) {
    PyObject *result;
    PyObject *ucode = PyObject_Repr(o);
    /* we can do this because repr() should never have non-ascii characters XXX (really?) */
    char *c = PyUnicode_1BYTE_DATA(ucode);
    if (c[0] == 'b')
        result = PyBytes_FromStringAndSize(PyUnicode_1BYTE_DATA(ucode)+1, PyUnicode_GET_LENGTH(ucode)-1);
    else
        result = PyBytes_FromStringAndSize(PyUnicode_1BYTE_DATA(ucode), PyUnicode_GET_LENGTH(ucode));
    Py_DECREF(ucode);
    return result;
}
#endif

#endif /* !Mp_MOD_PYTHON_H */

/*
# makes emacs go into C mode
### Local Variables:
### mode:c
### End:
*/
