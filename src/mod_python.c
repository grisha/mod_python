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
 * $Id: mod_python.c,v 1.28 2000/09/04 19:21:20 gtrubetskoy Exp $
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
#include "Python.h"
#include "structmember.h"

#if defined(WIN32) && !defined(WITH_THREAD)
#error Python threading must be enabled on Windows
#endif

#include <sys/socket.h>

/******************************************************************
                        Declarations
 ******************************************************************/

#define VERSION_COMPONENT "mod_python/2.5"
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

/* List of available Python obCallBacks/Interpreters
 * (In a Python dictionary) */
static PyObject * interpreters = NULL;

/* list of modules to be imported from PythonImport */
static table *python_imports = NULL;

/* some forward declarations */
void python_decref(void *object);
PyObject * make_obcallback();
PyObject * tuple_from_array_header(const array_header *ah);

/*********************************
           Python things 
 *********************************/
/*********************************
  members of _apache module 
 *********************************/

/* forward declarations */
static PyObject * log_error(PyObject *self, PyObject *args);
static PyObject * make_table(PyObject *self, PyObject *args);

/* methods of _apache */
static struct PyMethodDef _apache_module_methods[] = {
  {"log_error",                 (PyCFunction)log_error,        METH_VARARGS},
  {"make_table",                (PyCFunction)make_table,       METH_VARARGS},
  {NULL, NULL} /* sentinel */
};

/********************************
          tableobject 
 ********************************/

typedef struct tableobject {
    PyObject_VAR_HEAD
    table           *table;
    pool            *pool;
} tableobject;

static void table_dealloc(tableobject *self);
static PyObject * table_getattr(PyObject *self, char *name);
static PyObject * table_repr(tableobject *self);
static PyObject * tablegetitem(tableobject *self, PyObject *key);
static PyObject * table_has_key(tableobject *self, PyObject *args);
static PyObject * table_add(tableobject *self, PyObject *args);
static PyObject * table_keys(tableobject *self);
static int tablelength(tableobject *self);
static int tablesetitem(tableobject *self, PyObject *key, PyObject *val);
static int tb_setitem(tableobject *self, const char *key, const char *val);
static tableobject * make_tableobject(table * t);

static PyMappingMethods table_mapping = {
    (inquiry)       tablelength,           /*mp_length*/
    (binaryfunc)    tablegetitem,          /*mp_subscript*/
    (objobjargproc) tablesetitem,          /*mp_ass_subscript*/
};

static PyTypeObject tableobjecttype = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_table",
    sizeof(tableobject),
    0,
    (destructor) table_dealloc,     /*tp_dealloc*/
    0,                              /*tp_print*/
    (getattrfunc) table_getattr,    /*tp_getattr*/
    0,                              /*tp_setattr*/
    0,                              /*tp_compare*/
    (reprfunc) table_repr,          /*tp_repr*/
    0,                              /*tp_as_number*/
    0,                              /*tp_as_sequence*/
    &table_mapping,                 /*tp_as_mapping*/
    0,                              /*tp_hash*/
};

#define is_tableobject(op) ((op)->ob_type == &tableobjecttype)

static PyMethodDef tablemethods[] = {
    {"keys",                 (PyCFunction)table_keys,    METH_VARARGS},
    {"has_key",              (PyCFunction)table_has_key, METH_VARARGS},
    {"add",                  (PyCFunction)table_add,     METH_VARARGS},
    {NULL, NULL} /* sentinel */
};

/* another forward */
tableobject * headers_in(request_rec *req);

/********************************
          arrayobject 
 ********************************/

/* XXX NOTE the Array Object is experimental and isn't used anywhere
   so far */

typedef struct arrayobject {
    PyObject_VAR_HEAD
    array_header    *ah;
    pool            *pool;
} arrayobject;

static arrayobject *make_arrayobject(array_header *ah);
static void array_dealloc(arrayobject *self);
static PyObject *array_getattr(PyObject *self, char *name);
static PyObject *array_repr(arrayobject *self);
static int array_length(arrayobject *self);
static PyObject *array_item(arrayobject *self, int i); 
static PyObject *arrayappend(arrayobject *self, PyObject *args);
static PyObject *arrayinsert(arrayobject *self, PyObject *args);
static PyObject *arrayextend(arrayobject *self, PyObject *args);
static PyObject *arraypop(arrayobject *self, PyObject *args);
static PyObject *arrayremove(arrayobject *self, PyObject *args);
static PyObject *arrayindex(arrayobject *self, PyObject *args);
static PyObject *arraycount(arrayobject *self, PyObject *args);
static PyObject *arrayreverse(arrayobject *self, PyObject *args);
static PyObject *arraysort(arrayobject *self, PyObject *args);

static PySequenceMethods array_mapping = {
    (inquiry)         array_length,      /*sq_length*/
    NULL,
    /*    (binaryfunc)      array_concat,*/      /*sq_concat*/
    NULL,
    /*    (intargfunc)      array_repeat,*/      /*sq_repeat*/
    (intargfunc)      array_item,        /*sq_item*/
    NULL,
    /*    (intintargfunc)   array_slice,  */     /*sq_slice*/
    NULL,
    /*    (intobjargproc)   array_ass_item, */   /*sq_ass_item*/
    NULL,
    /*    (intintobjargproc)array_ass_slice, */  /*sq_ass_slice*/
};

static PyTypeObject arrayobjecttype = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_array",
    sizeof(arrayobject),
    0,
    (destructor) array_dealloc,     /*tp_dealloc*/
    0,                              /*tp_print*/
    (getattrfunc) array_getattr,    /*tp_getattr*/
    0,                              /*tp_setattr*/
    0,                              /*tp_compare*/
    (reprfunc) array_repr,          /*tp_repr*/
    0,                              /*tp_as_number*/
    &array_mapping,                 /*tp_as_sequence*/
    0,                              /*tp_as_mapping*/
    0,                              /*tp_hash*/
};

#define is_arrayobject(op) ((op)->ob_type == &arrayobjecttype)

static PyMethodDef arraymethods[] = {
    {"append",	(PyCFunction)arrayappend,  0},
    {"insert",	(PyCFunction)arrayinsert,  0},
    {"extend",  (PyCFunction)arrayextend,  METH_VARARGS},
    {"pop",	(PyCFunction)arraypop,     METH_VARARGS},
    {"remove",	(PyCFunction)arrayremove,  0},
    {"index",	(PyCFunction)arrayindex,   0},
    {"count",	(PyCFunction)arraycount,   0},
    {"reverse",	(PyCFunction)arrayreverse, 0},
    {"sort",	(PyCFunction)arraysort,    0},
    {NULL, NULL}		/* sentinel */
};

/********************************
          serverobject
 ********************************/

typedef struct serverobject {
    PyObject_HEAD
    server_rec     *server;
    PyObject       *next;
} serverobject;

static void server_dealloc(serverobject *self);
static PyObject * server_getattr(serverobject *self, char *name);

static PyTypeObject serverobjecttype = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_server",
    sizeof(serverobject),
    0,
    (destructor) server_dealloc,     /*tp_dealloc*/
    0,                               /*tp_print*/
    (getattrfunc) server_getattr,    /*tp_getattr*/
    0,                               /*tp_setattr*/
    0,                               /*tp_compare*/
    0,                               /*tp_repr*/
    0,                               /*tp_as_number*/
    0,                               /*tp_as_sequence*/
    0,                               /*tp_as_mapping*/
    0,                               /*tp_hash*/
};

#define is_serverobject(op) ((op)->ob_type == &serverobjecttype)

#define OFF(x) offsetof(server_rec, x)
static struct memberlist server_memberlist[] = {
  {"defn_name",          T_STRING,    OFF(defn_name),          RO},
  {"defn_line_number",   T_INT,       OFF(defn_line_number),   RO},
  {"srm_confname",       T_STRING,    OFF(srm_confname),       RO},
  {"access_confname",    T_STRING,    OFF(access_confname),    RO},
  {"server_admin",       T_STRING,    OFF(server_admin),       RO},
  {"server_hostname",    T_STRING,    OFF(server_hostname),    RO},
  {"port",               T_SHORT,     OFF(port),               RO},
  {"error_fname",        T_STRING,    OFF(error_fname),        RO},
  {"loglevel",           T_INT,       OFF(loglevel),           RO},
  {"is_virtual",         T_INT,       OFF(is_virtual),         RO},
  /* XXX implement module_config ? */
  /* XXX implement lookup_defaults ? */
  /* XXX implement server_addr_rec ? */
  {"timeout",            T_INT,       OFF(timeout),            RO},
  {"keep_alive_timeout", T_INT,       OFF(keep_alive_timeout), RO},
  {"keep_alive_max",     T_INT,       OFF(keep_alive_max),     RO},
  {"keep_alive",         T_INT,       OFF(keep_alive),         RO},
  {"send_buffer_size",   T_INT,       OFF(send_buffer_size),   RO},
  {"path",               T_STRING,    OFF(path),               RO},
  {"pathlen",            T_INT,       OFF(pathlen),            RO},
  {"server_uid",         T_INT,       OFF(server_uid),         RO},
  {"server_gid",         T_INT,       OFF(server_gid),         RO},
  {NULL}  /* Sentinel */
};

/********************************
          connobject
 ********************************/

typedef struct connobject {
  PyObject_HEAD
  conn_rec     *conn;
  PyObject     *server;
  PyObject     *base_server;
} connobject;

static void conn_dealloc(connobject *self);
static PyObject * conn_getattr(connobject *self, char *name);

static PyTypeObject connobjecttype = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_conn",
    sizeof(connobject),
    0,
    (destructor) conn_dealloc,       /*tp_dealloc*/
    0,                               /*tp_print*/
    (getattrfunc) conn_getattr,      /*tp_getattr*/
    0,                               /*tp_setattr*/
    0,                               /*tp_compare*/
    0,                               /*tp_repr*/
    0,                               /*tp_as_number*/
    0,                               /*tp_as_sequence*/
    0,                               /*tp_as_mapping*/
    0,                               /*tp_hash*/
};

#define is_connobject(op) ((op)->ob_type == &connobjecttype)

#undef OFF
#define OFF(x) offsetof(conn_rec, x)
static struct memberlist conn_memberlist[] = {
  {"server",             T_OBJECT                                },
  {"base_server",        T_OBJECT                                },
  /* XXX vhost_lookup_data? */
  {"child_num",          T_INT,       OFF(child_num),          RO},
  /* XXX BUFF? */
  {"local_addr",         T_OBJECT                                },
  {"remote_addr",        T_OBJECT                                },
  {"remote_ip",          T_STRING,    OFF(remote_ip),          RO},
  {"remote_ip",          T_STRING,    OFF(remote_ip),          RO},
  {"remote_host",        T_STRING,    OFF(remote_host),        RO},
  {"remote_logname",     T_STRING,    OFF(remote_logname),     RO},
  {"user",               T_STRING,    OFF(user),               RO},
  {"ap_auth_type",       T_STRING,    OFF(ap_auth_type),       RO},
  /* XXX aborted, keepalive, keptalive, double_reverse ? */
  {"local_ip",           T_STRING,    OFF(remote_ip),          RO},
  {"local_host",         T_STRING,    OFF(remote_host),        RO},
  {"keepalives",         T_INT,       OFF(keepalives),         RO},
  {NULL}  /* Sentinel */
};

/********************************
          requestobject 
 ********************************/

typedef struct requestobject {
    PyObject_HEAD
    request_rec    * request_rec;
    PyObject       * connection;
    PyObject       * server;
    PyObject       * next;
    PyObject       * prev;
    PyObject       * main;
    tableobject    * headers_in;
    tableobject    * headers_out;
    tableobject    * err_headers_out;
    tableobject    * subprocess_env;
    tableobject    * notes;
    int              header_sent;
    char           * hstack;
} requestobject;


static void request_dealloc(requestobject *self);
static PyObject * request_getattr(requestobject *self, char *name);
static int request_setattr(requestobject *self, char *name, PyObject *value);
static PyObject * req_child_terminate      (requestobject *self, PyObject *args);
static PyObject * req_add_common_vars      (requestobject *self, PyObject *args);
static PyObject * req_add_handler          (requestobject *self, PyObject *args);
static PyObject * req_get_all_config       (requestobject *self, PyObject *args);
static PyObject * req_get_all_dirs         (requestobject *self, PyObject *args);
static PyObject * req_get_basic_auth_pw    (requestobject *self, PyObject *args);
static PyObject * req_get_config           (requestobject *self, PyObject *args);
static PyObject * req_get_dirs             (requestobject *self, PyObject *args);
static PyObject * req_get_remote_host      (requestobject *self, PyObject *args);
static PyObject * req_get_options          (requestobject *self, PyObject *args);
static PyObject * req_read                 (requestobject *self, PyObject *args);
static PyObject * req_register_cleanup     (requestobject *self, PyObject *args);
static PyObject * req_send_http_header     (requestobject *self, PyObject *args);
static PyObject * req_write                (requestobject *self, PyObject *args);

static PyTypeObject requestobjecttype = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_request",
    sizeof(requestobject),
    0,
    (destructor) request_dealloc,    /*tp_dealloc*/
    0,                               /*tp_print*/
    (getattrfunc) request_getattr,   /*tp_getattr*/
    (setattrfunc) request_setattr,   /*tp_setattr*/
    0,                               /*tp_compare*/
    0,                               /*tp_repr*/
    0,                               /*tp_as_number*/
    0,                               /*tp_as_sequence*/
    0,                               /*tp_as_mapping*/
    0,                               /*tp_hash*/
};

#define is_requestobject(op) ((op)->ob_type == &requestobjecttype)

static PyMethodDef requestobjectmethods[] = {
    {"add_common_vars",      (PyCFunction) req_add_common_vars,      METH_VARARGS},
    {"add_handler",          (PyCFunction) req_add_handler,          METH_VARARGS},
    {"child_terminate",      (PyCFunction) req_child_terminate,      METH_VARARGS},
    {"get_all_config",       (PyCFunction) req_get_all_config,       METH_VARARGS},
    {"get_all_dirs",         (PyCFunction) req_get_all_dirs,         METH_VARARGS},
    {"get_basic_auth_pw",    (PyCFunction) req_get_basic_auth_pw,    METH_VARARGS},
    {"get_config",           (PyCFunction) req_get_config,           METH_VARARGS},
    {"get_dirs",             (PyCFunction) req_get_dirs,             METH_VARARGS},
    {"get_remote_host",      (PyCFunction) req_get_remote_host,      METH_VARARGS},
    {"get_options",          (PyCFunction) req_get_options,          METH_VARARGS},
    {"read",                 (PyCFunction) req_read,                 METH_VARARGS},
    {"register_cleanup",     (PyCFunction) req_register_cleanup,     METH_VARARGS},
    {"send_http_header",     (PyCFunction) req_send_http_header,     METH_VARARGS},
    {"write",                (PyCFunction) req_write,                METH_VARARGS},
    { NULL, NULL } /* sentinel */
};

#undef OFF
#define OFF(x) offsetof(request_rec, x)
static struct memberlist request_memberlist[] = {
    /* connection, server, next, prev, main in getattr */
    {"connection",         T_OBJECT,                                 },
    {"server",             T_OBJECT,                                 },
    {"next",               T_OBJECT,                                 },
    {"prev",               T_OBJECT,                                 },
    {"main",               T_OBJECT,                                 },
    {"the_request",        T_STRING,    OFF(the_request),          RO},
    {"assbackwards",       T_INT,       OFF(assbackwards),         RO},
    {"proxyreq",           T_INT,       OFF(proxyreq),             RO},
    {"header_only",        T_INT,       OFF(header_only),          RO},
    {"protocol",           T_STRING,    OFF(protocol),             RO},
    {"proto_num",          T_INT,       OFF(proto_num),            RO},
    {"hostname",           T_STRING,    OFF(hostname),             RO},
    {"request_time",       T_LONG,      OFF(request_time),         RO},
    {"status_line",        T_STRING,    OFF(status_line),          RO},
    {"status",             T_INT,       OFF(status)                  },
    {"method",             T_STRING,    OFF(method),               RO},
    {"method_number",      T_INT,       OFF(method_number),        RO},
    {"allowed",            T_INT,       OFF(allowed),              RO},
    {"sent_bodyct",        T_INT,       OFF(sent_bodyct),          RO},
    {"bytes_sent",         T_LONG,      OFF(bytes_sent),           RO},
    {"mtime",              T_LONG,      OFF(mtime),                RO},
    {"chunked",            T_INT,       OFF(chunked),              RO},
    {"byterange",          T_INT,       OFF(byterange),            RO},
    {"boundary",           T_STRING,    OFF(boundary),             RO},
    {"range",              T_STRING,    OFF(range),                RO},
    {"clength",            T_LONG,      OFF(clength),              RO},
    {"remaining",          T_LONG,      OFF(remaining),            RO},
    {"read_length",        T_LONG,      OFF(read_length),          RO},
    {"read_body",          T_INT,       OFF(read_body),            RO},
    {"read_chunked",       T_INT,       OFF(read_chunked),         RO},
    {"content_type",       T_STRING,    OFF(content_type)            },
    {"handler",            T_STRING,    OFF(handler),              RO},
    {"content_encoding",   T_STRING,    OFF(content_encoding),     RO},
    {"content_language",   T_STRING,    OFF(content_language),     RO},
    {"content_languages",  T_OBJECT,                                 },
    {"vlist_validator",    T_STRING,    OFF(vlist_validator),      RO},
    {"no_cache",           T_INT,       OFF(no_cache),             RO},
    {"no_local_copy",      T_INT,       OFF(no_local_copy),        RO},
    {"unparsed_uri",       T_STRING,    OFF(unparsed_uri),         RO},
    {"uri",                T_STRING,    OFF(uri),                  RO},
    {"filename",           T_STRING,    OFF(filename),               },
    {"path_info",          T_STRING,    OFF(path_info),            RO},
    {"args",               T_STRING,    OFF(args),                 RO},
    /* XXX - test an array header */
    /* XXX finfo */
    /* XXX parsed_uri */
    /* XXX per_dir_config */
    /* XXX request_config */
    /* XXX htaccess */
    {NULL}  /* Sentinel */
};

/********************************
   *** end of Python things *** 
 ********************************/

/********************************
          Apache things
 ********************************/

/* Apache module declaration */
module MODULE_VAR_EXPORT python_module;

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
    PyObject     *handler;
    const char   *interpreter;
    PyObject     *data;
} cleanup_info;

/* cleanup function */
void python_cleanup(void *data);


/********************************
   *** end of Apache things *** 
 ********************************/

/******************************************************************
     ***               end of declarations                 ***
 ******************************************************************/


/******************************************************************
                 Python objects and their methods    
 ******************************************************************/

/********************************
         array object
     XXX VERY EXPERIMENTAL
 ********************************/

/* This is a mapping of a Python object to an Apache
 * array_header.
 *
 * The idea is to make it appear as a Python list. The main difference
 * between an array and a Python list is that arrays are typed (i.e. all
 * items must be of the same type), and in this case the type is assumed 
 * to be a character string.
 */

/**
 **     make_arrayobject
 **
 *      This routine creates a Python arrayobject given an Apache
 *      array_header pointer.
 *
 */

static arrayobject * make_arrayobject(array_header * ah)
{
  arrayobject *result;

  result = PyMem_NEW(arrayobject, 1);
  if (! result)
      return (arrayobject *) PyErr_NoMemory();
  
  result->ah = ah;
  result->ob_type = &arrayobjecttype;
  result->pool = NULL;
  
  _Py_NewReference(result);
  return result;
}

/**
 ** array_getattr
 **
 *      Gets array's attributes
 */

static PyObject *array_getattr(PyObject *self, char *name)
{
    return Py_FindMethod(arraymethods, self, name);
}

/**
 ** array_repr
 **
 *      prints array like a list
 */

static PyObject * array_repr(arrayobject *self)
{
    PyObject *s;
    array_header *ah;
    char **elts;
    int i;

    s = PyString_FromString("[");

    ah = self->ah;
    elts = (char **)ah->elts;

    i = ah->nelts;
    if (i == 0)
	PyString_ConcatAndDel(&s, PyString_FromString("]"));

    while (i--) {
	PyString_ConcatAndDel(&s, PyString_FromString("'"));
	PyString_ConcatAndDel(&s, PyString_FromString(elts[i]));
	PyString_ConcatAndDel(&s, PyString_FromString("'"));
	if (i > 0)
	    PyString_ConcatAndDel(&s, PyString_FromString(", "));
	else
	    PyString_ConcatAndDel(&s, PyString_FromString("]"));
    }

    return s;
}

/**
 ** array_length
 **
 *      Number of elements in a array. Called
 *      when you do len(array) in Python.
 */

static int array_length(arrayobject *self) 
{ 
    return self->ah->nelts;
}

/**
 ** array_item
 **
 *
 *      Returns an array item.
 */

static PyObject *array_item(arrayobject *self, int i) 
{ 

    char **items;

    if (i < 0 || i >= self->ah->nelts) {
	PyErr_SetString(PyExc_IndexError, "array index out of range");
	return NULL;
    }

    items = (char **) self->ah->elts;
    return PyString_FromString(items[i]);
}

/**
 ** arrayappend
 **
 *
 *      Appends a string to an array.
 */

static PyObject *arrayappend(arrayobject *self, PyObject *args) 
{
    
    char **item;
    PyObject *s;
    
    if (!PyArg_Parse(args, "O", &s))
	return NULL;
    
    if (!PyString_Check(s)) {
	PyErr_SetString(PyExc_TypeError,
			"array items can only be strings");
	return NULL;
    }
    
    item = ap_push_array(self->ah);
    *item = ap_pstrdup(self->ah->pool, PyString_AS_STRING(s));

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** arrayinsert
 **
 *
 *      XXX Not implemented
 */
static PyObject *arrayinsert(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "insert not implemented");
    return NULL;
}

/**
 ** arrayextend
 **
 *
 *      Appends another array to this one.
 *      XXX Not Implemented
 */

static PyObject *arrayextend(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "extend not implemented");
    return NULL;
}

/**
 ** arraypop
 **
 *
 *      Get an item and remove it from the list
 *      XXX Not Implemented
 */

static PyObject *arraypop(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "pop not implemented");
    return NULL;
}

/**
 ** arrayremove
 **
 *
 *      Remove an item from the array
 *      XXX Not Implemented
 */

static PyObject *arrayremove(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "remove not implemented");
    return NULL;
}

/**
 ** arrayindex
 **
 *
 *      Find an item in an array
 *      XXX Not Implemented
 */

static PyObject *arrayindex(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "index not implemented");
    return 0;
}

/**
 ** arraycount
 **
 *
 *      Count a particular item in an array
 *      XXX Not Implemented
 */

static PyObject *arraycount(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "count not implemented");
    return NULL;
}

/**
 ** arrayreverse
 **
 *
 *      Reverse the order of items in an array
 *      XXX Not Implemented
 */

static PyObject *arrayreverse(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "reverse not implemented");
    return NULL;
}

/**
 ** arraysort
 **
 *
 *      Sort items in an array
 *      XXX Not Implemented
 */

static PyObject *arraysort(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "sort not implemented");
    return NULL;
}

/**
 ** array_dealloc
 **
 *      Frees array's memory
 */

static void array_dealloc(arrayobject *self)
{  

    if (self->pool) 
	ap_destroy_pool(self->pool);

    free(self);
}

/********************************
         table object
 ********************************/

/*
 * This is a mapping of a Python object to an Apache table.
 *
 * This object behaves like a dictionary. Note that the
 * underlying table can have duplicate keys, which can never
 * happen to a Python dictionary. But this is such a rare thing 
 * that I can't even think of a possible scenario or implications.
 *
 */

/**
 **     make_tableobject
 **
 *      This routine creates a Python tableobject given an Apache
 *      table pointer.
 *
 */

static tableobject * make_tableobject(table * t)
{
  tableobject *result;

  result = PyMem_NEW(tableobject, 1);
  if (! result)
    return (tableobject *) PyErr_NoMemory();

  result->table = t;
  result->ob_type = &tableobjecttype;
  result->pool = NULL;

  _Py_NewReference(result);
  return result;
}


/** 
 ** make_table
 **
 *  This returns a new object of built-in type table.
 *
 *  NOTE: The ap_table gets greated in its own pool, which lives
 *  throught the live of the tableobject. This is because this
 *  object may persist from hit to hit.
 * 
 *  make_table()
 *
 */

static PyObject * make_table(PyObject *self, PyObject *args)
{
    tableobject *t;
    pool *p;

    p = ap_make_sub_pool(NULL);
    
    /* two is a wild guess */
    t = make_tableobject(ap_make_table(p, 2));

    /* remember the pointer to our own pool */
    t->pool = p;

    return (PyObject *)t;

}

/**
 ** table_getattr
 **
 *      Gets table's attributes
 */

static PyObject * table_getattr(PyObject *self, char *name)
{
    return Py_FindMethod(tablemethods, self, name);
}

/**
 ** tablegetitem
 **
 *      Gets a dictionary item
 */

static PyObject * tablegetitem(tableobject *self, PyObject *key)
{
    const char *v;
    char *k;

    k = PyString_AsString(key);

    v = ap_table_get(self->table, k);

    if (! v)
    {
	PyErr_SetObject(PyExc_KeyError, key);
	return NULL;
    }

    return PyString_FromString(v);
}

/**
 ** table_has_key
 **
 */

static PyObject * table_has_key(tableobject *self, PyObject *args)
{

    const char *val, *key;

    if (! PyArg_ParseTuple(args, "s", &key))
	return NULL;

    val = ap_table_get (self->table, key);

    if (val)
	return PyInt_FromLong(1);
    else
	return PyInt_FromLong(0);
}

/**
 ** table_add
 **
 *     this function is equivalent of ap_table_add - 
 *     it can create duplicate entries. 
 */

static PyObject * table_add(tableobject *self, PyObject *args)
{

    const char *val, *key;

    if (! PyArg_ParseTuple(args, "ss", &key, &val))
	return NULL;

    ap_table_add(self->table, key, val);

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** tablelength
 **
 *      Number of elements in a table. Called
 *      when you do len(table) in Python.
 */

static int tablelength(tableobject *self) 
{ 
    return ap_table_elts(self->table)->nelts;
}

/**
 ** tablesetitem
 **
 *      insert into table dictionary-style
 *      *** NOTE ***
 *      Since the underlying ap_table_set makes a *copy* of the string,
 *      there is no need to increment the reference to the Python
 *      string passed in.
 */

static int tablesetitem(tableobject *self, PyObject *key, 
			PyObject *val)
{ 

    char *k;

    if (key && !PyString_Check(key)) {
	PyErr_SetString(PyExc_TypeError,
			"table keys must be strings");
	return -1;
    }

    k = PyString_AsString(key);

    if ((val == Py_None) || (val == NULL)) {
	ap_table_unset(self->table, k);
    }
    else {
	if (val && !PyString_Check(val)) {
	    PyErr_SetString(PyExc_TypeError,
			    "table values must be strings");
	    return -1;
	}
	ap_table_set(self->table, k, PyString_AsString(val));
    }
    return 0;
}

/**
 ** tb_setitem
 **
 *      This is a wrapper around tablesetitem that takes
 *      char * for convenience, for internal use.
 */

static int tb_setitem(tableobject *self, const char *key, const char *val) 
{ 
    PyObject *ps1, *ps2;

    ps1 = PyString_FromString(key);
    ps2 = PyString_FromString(val);

    tablesetitem(self, ps1, ps2);

    Py_DECREF(ps1);
    Py_DECREF(ps2);

    return 0;

    /* prevent complier warning about function
       never used */
    tb_setitem(self, key, val);
}

/**
 ** table_dealloc
 **
 *      Frees table's memory
 */
static void table_dealloc(tableobject *self)
{  

    if (self->pool) 
	ap_destroy_pool(self->pool);

    free(self);
}

/**
 ** table_repr
 **
 *      prints table like a dictionary
 */

static PyObject * table_repr(tableobject *self)
{
    PyObject *s;
    array_header *ah;
    table_entry *elts;
    int i;

    s = PyString_FromString("{");

    ah = ap_table_elts (self->table);
    elts = (table_entry *) ah->elts;

    i = ah->nelts;
    if (i == 0)
	PyString_ConcatAndDel(&s, PyString_FromString("}"));

    while (i--)
	if (elts[i].key)
	{
	    PyString_ConcatAndDel(&s, PyString_FromString("'"));
	    PyString_ConcatAndDel(&s, PyString_FromString(elts[i].key));
	    PyString_ConcatAndDel(&s, PyString_FromString("': '"));
	    PyString_ConcatAndDel(&s, PyString_FromString(elts[i].val));
	    PyString_ConcatAndDel(&s, PyString_FromString("'"));
	    if (i > 0)
		PyString_ConcatAndDel(&s, PyString_FromString(", "));
	    else
		PyString_ConcatAndDel(&s, PyString_FromString("}"));
	}

    return s;
}

/**
 ** table_keys
 **
 *
 *  Implements dictionary's keys() method.
 */

static PyObject * table_keys(tableobject *self)
{

    PyObject *v;
    array_header *ah;
    table_entry *elts;
    int i, j;

    ah = ap_table_elts(self->table);
    elts = (table_entry *) ah->elts;

    v = PyList_New(ah->nelts);

    for (i = 0, j = 0; i < ah->nelts; i++)
    {
	if (elts[i].key)
	{
	    PyObject *key = PyString_FromString(elts[i].key);
	    PyList_SetItem(v, j, key);
	    j++;
	}
    }
    return v;
}


/**
 ** copy_table
 **
 *   Merge two tables into one. Matching key values 
 *   in second overlay the first.
 */

static void copy_table(table *t1, table *t2)
{

    array_header *ah;
    table_entry *elts;
    int i;

    ah = ap_table_elts(t2);
    elts = (table_entry *)ah->elts;
    i = ah->nelts;

    while (i--)
	if (elts[i].key)
	    ap_table_set(t1, elts[i].key, elts[i].val);
}


/********************************
  ***  end of table object ***
 ********************************/

/********************************
         server object
 ********************************/

/*
 * This is a mapping of a Python object to an Apache server_rec.
 *
 */

/**
 **     make_serverobject
 **
 *      This routine creates a Python serverobject given an Apache
 *      server_rec pointer.
 *
 */

static serverobject * make_serverobject(server_rec *t)
{
    serverobject *result;

    result = PyMem_NEW(serverobject, 1);
    if (! result)
	return (serverobject *) PyErr_NoMemory();

    result->server = t;
    result->ob_type = &serverobjecttype;
    result->next = NULL;

    _Py_NewReference(result);
    return result;
}

/**
 ** server_dealloc
 **
 *
 */

static void server_dealloc(serverobject *self)
{  

    Py_XDECREF(self->next);
    free(self);
}

/**
 ** server_getattr
 **
 *  Get server object attributes
 *
 *
 */

static PyObject * server_getattr(serverobject *self, char *name)
{
    if (strcmp(name, "next") == 0)
	/* server.next serverobject is created as needed */
	if (self->next == NULL) {
	    if (self->server->next == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->next = (PyObject *)make_serverobject(self->server->next);
		Py_INCREF(self->next);
		return self->next;
	    }
	}
	else {
	    Py_INCREF(self->next);
	    return self->next;
	}

    else if (strcmp(name, "error_log") == 0)
	return PyInt_FromLong((long)fileno(self->server->error_log));
  
    else if (strcmp(name, "names") == 0) {
	return tuple_from_array_header(self->server->names);
    }
    else if (strcmp(name, "wild_names") == 0) {
	return tuple_from_array_header(self->server->wild_names);
    }
    else
	return PyMember_Get((char *)self->server, server_memberlist, name);

}

/********************************
  ***  end of server object ***
 ********************************/

/********************************
         conn object
 ********************************/

/*
 * This is a mapping of a Python object to an Apache conn_rec.
 *
 */

/**
 **     make_connobject
 **
 *      This routine creates a Python connobject given an Apache
 *      conn_rec pointer.
 *
 */

static connobject * make_connobject(conn_rec *t)
{
    connobject *result;

    result = PyMem_NEW(connobject, 1);
    if (! result)
	return (connobject *) PyErr_NoMemory();

    result->conn = t;
    result->ob_type = &connobjecttype;
    result->server = NULL;
    result->base_server = NULL;

    _Py_NewReference(result);
    return result;
}

/**
 ** conn_dealloc
 **
 *
 */

static void conn_dealloc(connobject *self)
{  
    Py_XDECREF(self->server);
    Py_XDECREF(self->base_server);
    free(self);
}

/**
 ** makeipaddr
 **
 *  utility func to make an ip address
 */

static PyObject *makeipaddr(struct sockaddr_in *addr)
{
    long x = ntohl(addr->sin_addr.s_addr);
    char buf[100];
    sprintf(buf, "%d.%d.%d.%d",
	    (int) (x>>24) & 0xff, (int) (x>>16) & 0xff,
	    (int) (x>> 8) & 0xff, (int) (x>> 0) & 0xff);
    return PyString_FromString(buf);
}

/**
 ** makesockaddr
 **
 *  utility func to make a socket address
 */

static PyObject *makesockaddr(struct sockaddr_in *addr)
{
    PyObject *addrobj = makeipaddr(addr);
    PyObject *ret = NULL;
    if (addrobj) {
	ret = Py_BuildValue("Oi", addrobj, ntohs(addr->sin_port));
	Py_DECREF(addrobj);
    }
    return ret;
}

/**
 ** conn_getattr
 **
 *  Get conn object attributes
 *
 */

static PyObject * conn_getattr(connobject *self, char *name)
{
    if (strcmp(name, "server") == 0) {

	/* server serverobject is created as needed */
	if (self->server == NULL) {
	    if (self->conn->server == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->server = (PyObject *)make_serverobject(self->conn->server);
		Py_INCREF(self->server);
		return self->server;
	    }
	}
	else {
	    Py_INCREF(self->server);
	    return self->server;
	}
    }
    else if (strcmp(name, "base_server") == 0) {

	/* base_server serverobject is created as needed */
	if (self->base_server == NULL) {
	    if (self->conn->base_server == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->base_server = (PyObject *)make_serverobject(self->conn->base_server);
		Py_INCREF(self->base_server);
		return self->base_server;
	    }
	}
	else {
	    Py_INCREF(self->base_server);
	    return self->base_server;
	}
    }
    else if (strcmp(name, "local_addr") == 0) {
	return makesockaddr(&(self->conn->local_addr));
    }
    else if (strcmp(name, "remote_addr") == 0) {
	return makesockaddr(&(self->conn->remote_addr));
    }
    else
	return PyMember_Get((char *)self->conn, conn_memberlist, name);

}

/********************************
  ***  end of conn object ***
 ********************************/

/********************************
         request object
 ********************************/

/*
 * This is a mapping of a Python object to an Apache request_rec.
 *
 */

/**
 **     make_requestobject
 **
 *      This routine creates a Python requestobject given an Apache
 *      request_rec pointer.
 *
 */

static requestobject * make_requestobject(request_rec *req)
{
    requestobject *result;

    result = PyMem_NEW(requestobject, 1);
    if (! result)
	return (requestobject *) PyErr_NoMemory();

    result->request_rec = req;
    result->ob_type = &requestobjecttype;
    result->connection = NULL;
    result->server = NULL;
    result->next = NULL;
    result->prev = NULL;
    result->main = NULL;
    result->headers_in = make_tableobject(req->headers_in);
    result->headers_out = make_tableobject(req->headers_out);
    result->err_headers_out = make_tableobject(req->err_headers_out);
    result->subprocess_env = make_tableobject(req->subprocess_env);
    result->notes = make_tableobject(req->notes);
    result->header_sent = 0;
    result->hstack = NULL;

    _Py_NewReference(result);
    ap_register_cleanup(req->pool, (PyObject *)result, python_decref, 
			ap_null_cleanup);

    return result;
}

/**
 ** request_dealloc
 **
 *
 */

static void request_dealloc(requestobject *self)
{  
    Py_XDECREF(self->connection);
    Py_XDECREF(self->server);
    Py_XDECREF(self->next);
    Py_XDECREF(self->prev);
    Py_XDECREF(self->main);
    Py_XDECREF(self->headers_in);
    Py_XDECREF(self->headers_out);
    Py_XDECREF(self->err_headers_out);
    Py_XDECREF(self->subprocess_env);
    Py_XDECREF(self->notes);

    free(self);
}

/**
 ** request_getattr
 **
 *  Get request object attributes
 *
 */

static PyObject * request_getattr(requestobject *self, char *name)
{

    PyObject *res;

    res = Py_FindMethod(requestobjectmethods, (PyObject *)self, name);
    if (res != NULL)
	return res;
    
    PyErr_Clear();
  
    if (strcmp(name, "connection") == 0) {
	  
	if (self->connection == NULL) {
	    if (self->request_rec->connection == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->connection = (PyObject *)make_connobject(self->request_rec->connection);
		Py_INCREF(self->connection);
		return self->connection;
	    }
	}
	else {
	    Py_INCREF(self->connection);
	    return self->connection;
	}
    }
    else if (strcmp(name, "server") == 0) {

	if (self->server == NULL) {
	    if (self->request_rec->server == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    } 
	    else {
		self->server = (PyObject *)make_serverobject(self->request_rec->server);
		Py_INCREF(self->server);
		return self->server;
	    }
	}
	else {
	    Py_INCREF(self->server);
	    return self->server;
	}
    }
    else if (strcmp(name, "next") == 0) {

	if (self->next == NULL) {
	    if (self->request_rec->next == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->next = (PyObject *)make_requestobject(self->request_rec->next);
		Py_INCREF(self->next);
		return self->next;
	    }
	}
	else {
	    Py_INCREF(self->next);
	    return self->next;
	}
    }
    else if (strcmp(name, "prev") == 0) {

	if (self->prev == NULL) {
	    if (self->request_rec->prev == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->prev = (PyObject *)make_requestobject(self->request_rec->prev);
		Py_INCREF(self->prev);
		return self->prev;
	    }
	}
	else {
	    Py_INCREF(self->prev);
	    return self->prev;
	}
    }
    else if (strcmp(name, "main") == 0) {

	if (self->main == NULL) {
	    if (self->request_rec->main == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->main = (PyObject *)make_requestobject(self->request_rec->main);
		Py_INCREF(self->main);
		return self->main;
	    }
	}
	else {
	    Py_INCREF(self->main);
	    return self->main;
	}
    }
    else if (strcmp(name, "headers_in") == 0) {
	Py_INCREF(self->headers_in);
	return (PyObject *) self->headers_in;
    } 
    else if (strcmp(name, "headers_out") == 0) {
	Py_INCREF(self->headers_out);
	return (PyObject *) self->headers_out;
    }
    else if (strcmp(name, "err_headers_out") == 0) {
	Py_INCREF(self->err_headers_out);
	return (PyObject *) self->err_headers_out;
    }
    else if (strcmp(name, "subprocess_env") == 0) {
	Py_INCREF(self->subprocess_env);
	return (PyObject *) self->subprocess_env;
    }
    else if (strcmp(name, "notes") == 0) {
	Py_INCREF(self->notes);
	return (PyObject *) self->notes;
    }
    else if (strcmp(name, "content_languages") == 0) {
	return tuple_from_array_header(self->request_rec->content_languages);
    } 
    else if (strcmp(name, "hstack") == 0) {
	return PyString_FromString(self->hstack);
    }
    else
	return PyMember_Get((char *)self->request_rec, request_memberlist, name);

}

/**
 ** request_setattr
 **
 *  Set request object attributes
 *
 */

static int request_setattr(requestobject *self, char *name, PyObject *value)
{
    if (value == NULL) {
	PyErr_SetString(PyExc_AttributeError,
			"can't delete request attributes");
	return -1;
    }
    else if (strcmp(name, "content_type") == 0) {
	self->request_rec->content_type = 
	    ap_pstrdup(self->request_rec->pool, PyString_AsString(value));
	return 0;
    }
    else if (strcmp(name, "filename") == 0) {
	self->request_rec->filename =
	    ap_pstrdup(self->request_rec->pool, PyString_AsString(value));
	return 0;
    }
    else if (strcmp(name, "hstack") == 0) {
	self->hstack = ap_pstrdup(self->request_rec->pool, PyString_AsString(value));
	return 0;
    }
    else
	return PyMember_Set((char *)self->request_rec, request_memberlist, name, value);
}

/**
 ** request.send_http_header(request self)
 **
 *      sends headers, same as ap_send_http_header
 */

static PyObject * req_send_http_header(requestobject *self, PyObject *args)
{

    if (! self->header_sent) {
	ap_send_http_header(self->request_rec);
	self->header_sent = 1;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.child_terminate(request self)
 **
 *    terminates a child process
 */

static PyObject * req_child_terminate(requestobject *self, PyObject *args)
{
    ap_child_terminate(self->request_rec);
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.register_cleanup(handler, data)
 **
 *    registers a cleanup at request pool destruction time. 
 *    optional data argument will be passed to the cleanup function.
 */

static PyObject *req_register_cleanup(requestobject *self, PyObject *args)
{
    cleanup_info *ci;
    PyObject *handler = NULL;
    PyObject *data = NULL;

    if (! PyArg_ParseTuple(args, "O|O", &handler, &data))
	return NULL;  /* bad args */

    ci = (cleanup_info *)malloc(sizeof(cleanup_info));
    ci->request_rec = self->request_rec;
    if (PyCallable_Check(handler)) {
	Py_INCREF(handler);
	ci->handler = handler;
	ci->interpreter = ap_table_get(self->request_rec->notes, "python_interpreter");
	if (data) {
	    Py_INCREF(data);
	    ci->data = data;
	}
	else {
	    Py_INCREF(Py_None);
	    ci->data = Py_None;
	}
    }
    else {
	PyErr_SetString(PyExc_ValueError, 
			"first argument must be a callable object");
	free(ci);
	return NULL;
    }
    
    ap_register_cleanup(self->request_rec->pool, ci, python_cleanup, 
			ap_null_cleanup);

    Py_INCREF(Py_None);
    return Py_None;

}

/**
 ** request.get_basic_auth_pw(request self)
 **
 *    get basic authentication password,
 *    similar to ap_get_basic_auth_pw
 */

static PyObject * req_get_basic_auth_pw(requestobject *self, PyObject *args)
{
    const char *pw;
    request_rec *req;
    
    req = self->request_rec;

    if (! ap_get_basic_auth_pw(req, &pw))
	return PyString_FromString(pw);
    else {
	Py_INCREF(Py_None);
	return Py_None;
    }

}

/**
 ** request.write(request self, string what)
 **
 *      write output to the client
 */

static PyObject * req_write(requestobject *self, PyObject *args)
{
    int len;
    int rc;
    char *buff;

    if (! PyArg_ParseTuple(args, "s#", &buff, &len))
	return NULL;  /* bad args */

    Py_BEGIN_ALLOW_THREADS
    ap_rwrite(buff, len, self->request_rec);
    rc = ap_rflush(self->request_rec);
    Py_END_ALLOW_THREADS
    if (rc == EOF) {
	PyErr_SetString(PyExc_IOError, "Write failed, client closed connection.");
	return NULL;
    }


    Py_INCREF(Py_None);
    return Py_None;

}

/**
 ** request.read(request self, int bytes)
 **
 *     Reads stuff like POST requests from the client
 *     (based on the old net_read)
 */

static PyObject * req_read(requestobject *self, PyObject *args)
{

    int len, rc, bytes_read, chunk_len;
    char *buffer;
    PyObject *result;

    if (! PyArg_ParseTuple(args, "i", &len)) 
	return NULL;

    if (len == 0) {
	return PyString_FromString("");
    }
    else if (len < 0) {
	PyErr_SetString(PyExc_ValueError, "must have positive integer parameter");
	return NULL;
    }

    /* is this the first read? */
    if (! self->request_rec->read_length) {
	/* then do some initial setting up */
	rc = ap_setup_client_block(self->request_rec, REQUEST_CHUNKED_ERROR);
	if(rc != OK) {
	    PyErr_SetObject(PyExc_IOError, PyInt_FromLong(rc));
	    return NULL;
	}

	if (! ap_should_client_block(self->request_rec)) {
	    /* client has nothing to send */
	    Py_INCREF(Py_None);
	    return Py_None;
	}
    }

    result = PyString_FromStringAndSize(NULL, len);

    /* possibly no more memory */
    if (result == NULL) 
	return NULL;

    /* set timeout */
    ap_soft_timeout("mod_python_read", self->request_rec);

    /* read it in */
    buffer = PyString_AS_STRING((PyStringObject *) result);
    Py_BEGIN_ALLOW_THREADS
    chunk_len = ap_get_client_block(self->request_rec, buffer, len);
    Py_END_ALLOW_THREADS
    bytes_read = chunk_len;

    /* if this is a "short read", try reading more */
    while ((bytes_read < len) && (chunk_len != 0)) {
	Py_BEGIN_ALLOW_THREADS
	chunk_len = ap_get_client_block(self->request_rec, 
					buffer+bytes_read, len-bytes_read);
	Py_END_ALLOW_THREADS
	ap_reset_timeout(self->request_rec);
	if (chunk_len == -1) {
	    ap_kill_timeout(self->request_rec);
	    PyErr_SetObject(PyExc_IOError, 
			    PyString_FromString("Client read error (Timeout?)"));
	    return NULL;
	}
	else
	    bytes_read += chunk_len;
    }

    ap_kill_timeout(self->request_rec);

    /* resize if necessary */
    if (bytes_read < len) 
	if(_PyString_Resize(&result, bytes_read))
	    return NULL;

    return result;
}

/**
 ** valid_handler()
 **
 *  utility func - makes sure a handler is valid
 */

static int valid_handler(const char *h)
{
    if ((strcmp(h, "PythonHandler") != 0) &&
	(strcmp(h, "PythonAuthenHandler") != 0) &&
	(strcmp(h, "PythonPostReadRequestHandler") != 0) &&
	(strcmp(h, "PythonTransHandler") != 0) &&
	(strcmp(h, "PythonHeaderParserHandler") != 0) &&
	(strcmp(h, "PythonAccessHandler") != 0) &&
	(strcmp(h, "PythonAuthzHandler") != 0) &&
	(strcmp(h, "PythonTypeHandler") != 0) &&
	(strcmp(h, "PythonFixupHandler") != 0) &&
	(strcmp(h, "PythonLogHandler") != 0) &&
	(strcmp(h, "PythonInitHandler") != 0))
	return 0;
    else
	return 1;
}

/**
 ** request.get_config(request self)
 **
 *     Returns the config directives set through Python* apache directives.
 *     except for PythonOption, which you get via get_options
 */

static PyObject * req_get_config(requestobject *self, PyObject *args)
{
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);
    return (PyObject *)make_tableobject(conf->directives);
}

/**
 ** request.get_all_config(request self)
 **
 *  returns get_config + all the handlers added by req.add_handler
 */

static PyObject * req_get_all_config(requestobject *self, PyObject *args)
{
    table *all;
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);

    all = ap_copy_table(self->request_rec->pool, conf->directives);

    if (ap_table_get(self->request_rec->notes, "py_more_directives")) {

	array_header *ah = ap_table_elts(self->request_rec->notes);
	table_entry *elts = (table_entry *)ah->elts;
	int i = ah->nelts;

	while (i--) {
	    if (elts[i].key) {
		if (valid_handler(elts[i].key)) {
		
		    /* if exists - append, otherwise add */
		    const char *val = ap_table_get(all, elts[i].key);
		    if (val) {
			ap_table_set(all, elts[i].key, 
				     ap_pstrcat(self->request_rec->pool,
						val, " ", elts[i].val,
						NULL));
		    }
		    else {
			ap_table_set(all, elts[i].key, elts[i].val);
		    }
		}
	    }
	}
    }
    return (PyObject *)make_tableobject(all);
}

/**
 ** request.get_all_dirs(request self)
 **
 *  returns get_dirs + all the dirs added by req.add_handler
 */

static PyObject * req_get_all_dirs(requestobject *self, PyObject *args)
{
    table *all;
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);

    all = ap_copy_table(self->request_rec->pool, conf->dirs);

    if (ap_table_get(self->request_rec->notes, "py_more_directives")) {

	array_header *ah = ap_table_elts(self->request_rec->notes);
	table_entry *elts = (table_entry *)ah->elts;
	int i = ah->nelts;

	while (i--) {
	    if (elts[i].key) {
		
		/* chop off _dir */
		char *s = ap_pstrdup(self->request_rec->pool, elts[i].key);
		if (valid_handler(s)) {
		    
		    s[strlen(s)-4] = 0;
		    ap_table_set(all, s, elts[i].val);
		}
	    }
	}
    }
    return (PyObject *)make_tableobject(all);
}

/**
 ** request.get_remote_host(request self, [int type])
 **
 *    An interface to the ap_get_remote_host function.
 */

static PyObject * req_get_remote_host(requestobject *self, PyObject *args)
{

    int type = REMOTE_NAME;
    const char *host;

    if (! PyArg_ParseTuple(args, "|i", &type)) 
	return NULL;
    
    host = ap_get_remote_host(self->request_rec->connection, 
			      self->request_rec->per_dir_config, type);

    if (! host) {
	Py_INCREF(Py_None);
	return Py_None;
    }
    else
	return PyString_FromString(host);
}

/**
 ** request.get_options(request self)
 **
 */

static PyObject * req_get_options(requestobject *self, PyObject *args)
{
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);
    return (PyObject *)make_tableobject(conf->options);
}

/**
 ** request.get_config(request self)
 **
 *  Returns a table keyed by directives with the last path in which the
 *  directive was encountered.
 */

static PyObject * req_get_dirs(requestobject *self, PyObject *args)
{
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);
    return (PyObject *)make_tableobject(conf->dirs);
}

/**
 ** request.add_common_vars(reqeust self)
 **
 *     Interface to ap_add_common_vars. Adds a bunch of CGI
 *     environment variables.
 *
 */

static PyObject * req_add_common_vars(requestobject *self, PyObject *args)
{

    ap_add_common_vars(self->request_rec);

    Py_INCREF(Py_None);
    return Py_None;

}

/**
 ** request.add_handler(request self, string handler, string function)
 **
 *     Allows to add another handler to the handler list.
 *
 * The dynamic handler mechanism works like this: we have
 * the original config, which gets build via the standard Apache
 * config functions. The calls to add_handler() slap new values into
 * req->notes. At handler execution time, prior to calling into python, 
 * but after the requestobject has been created/obtained, a concatenation 
 * of values of conf->directives+req->notes for the handler currently
 * being executed is placed in req->hstack. Inside Python, in Dispatch(),
 * handlers will be chopped from the begining of the string as they
 * get executed. Add_handler is also smart enough to append to
 * req->hstack if the handler being added is the same as the one 
 * being currently executed.
 */

static PyObject *req_add_handler(requestobject *self, PyObject *args)
{
    char *handler;
    char *function;
    const char *dir = NULL;
    const char *currhand;

    if (! PyArg_ParseTuple(args, "ss|s", &handler, &function, &dir)) 
        return NULL;

    if (! valid_handler(handler)) {
	PyErr_SetString(PyExc_IndexError, 
			ap_psprintf(self->request_rec->pool,
				   "Invalid handler: %s", handler));
	return NULL;
    }
    
    /* which handler are we processing? */
    currhand = ap_table_get(self->request_rec->notes, "python_handler");

    if (strcmp(currhand, handler) == 0) {

	/* if it's the same as what's being added, then just append to hstack */
	self->hstack = ap_pstrcat(self->request_rec->pool, self->hstack, 
				  function, NULL);
        
	if (dir) 
            ap_table_set(self->request_rec->notes, 
			 ap_pstrcat(self->request_rec->pool, handler, "_dir", NULL), 
			 dir);
    }
    else {

	const char *existing;

	/* is there a handler like this in the notes already? */
	existing = ap_table_get(self->request_rec->notes, handler);

	if (existing) {

	    /* append the function to the list using the request pool */
	    ap_table_set(self->request_rec->notes, handler, 
			 ap_pstrcat(self->request_rec->pool, existing, " ", 
				    function, NULL));

	    if (dir) {
		char *s = ap_pstrcat(self->request_rec->pool, handler, "_dir", NULL);
		ap_table_set(self->request_rec->notes, s, dir);
	    }

	}
	else {

	    char *s;

	    /* a completely new handler */
	    ap_table_set(self->request_rec->notes, handler, function);

	    if (! dir) {

		/*
		 * If no directory was explicitely specified, the new handler will 
		 * have the same directory associated with it as the handler 
		 * currently being processed.
		 */

		py_dir_config *conf;

		/* get config */
		conf = (py_dir_config *) ap_get_module_config(
		    self->request_rec->per_dir_config, &python_module);
        
		/* what's the directory for this handler? */
		dir = ap_table_get(conf->dirs, currhand);

		/*
		 * make a note that the handler's been added. 
		 * req_get_all_* rely on this to be faster
		 */
		ap_table_set(self->request_rec->notes, "py_more_directives", "1");

	    }
	    s = ap_pstrcat(self->request_rec->pool, handler, "_dir", NULL);
	    ap_table_set(self->request_rec->notes, s, dir);
	}
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}

/********************************
  ***  end of request object ***
 ********************************/

/******************************************************************
   ***        end of Python objects and their methods        ***
 ******************************************************************/


/******************************************************************
               functions called by Apache or Python     
 ******************************************************************/

/**
 ** python_decref
 ** 
 *   This function is used with ap_register_cleanup to destroy
 *   python objects when a certain pool is destroyed.
 */

void python_decref(void *object)
{
    Py_XDECREF((PyObject *) object);
}


/**
 ** python_init()
 **
 *      Called at Apache mod_python initialization time.
 */

void python_init(server_rec *s, pool *p)
{

    char buff[255];

    /* mod_python version */
    ap_add_version_component(VERSION_COMPONENT);
    
    /* Python version */
    sprintf(buff, "Python/%s", strtok((char *)Py_GetVersion(), " "));
    ap_add_version_component(buff);

    /* initialize global Python interpreter if necessary */
    if (! Py_IsInitialized()) 
    {

	/* initialize types */
	tableobjecttype.ob_type = &PyType_Type;
	serverobjecttype.ob_type = &PyType_Type;
	connobjecttype.ob_type = &PyType_Type;
	requestobjecttype.ob_type = &PyType_Type;

	/* initialze the interpreter */
	Py_Initialize();

#ifdef WITH_THREAD
	/* create and acquire the interpreter lock */
	PyEval_InitThreads();
	/* Release the thread state because we will never use 
	 * the main interpreter, only sub interpreters created later. */
        PyThreadState_Swap(NULL); 
#endif
	/* create the obCallBack dictionary */
	interpreters = PyDict_New();
	if (! interpreters) {
	    ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, s,
			 "python_init: PyDict_New() failed! No more memory?");
	    exit(1);
	}
	
#ifdef WITH_THREAD
	
	/* release the lock; now other threads can run */
	PyEval_ReleaseLock();
#endif
    }
}

/**
 ** python_create_dir_config
 **
 *      Allocate memory and initialize the strucure that will
 *      hold configuration parametes.
 *
 *      This function is called on every hit it seems.
 */

static void *python_create_dir_config(pool *p, char *dir)
{

    py_dir_config *conf = 
	(py_dir_config *) ap_pcalloc(p, sizeof(py_dir_config));

    conf->authoritative = 1;
    /* make sure directory ends with a slash */
    if (dir && (dir[strlen(dir) - 1] != SLASH))
	conf->config_dir = ap_pstrcat(p, dir, SLASH_S, NULL);
    else
	conf->config_dir = ap_pstrdup(p, dir);
    conf->options = ap_make_table(p, 4);
    conf->directives = ap_make_table(p, 4);
    conf->dirs = ap_make_table(p, 4);

    return conf;
}

/**
 ** tuple_from_array_header
 **
 *   Given an array header return a tuple. The array elements
 *   assumed to be strings.
 */

PyObject * tuple_from_array_header(const array_header *ah)
{

    PyObject *t;
    int i;
    char **s;

    if (ah == NULL)
    {
	Py_INCREF(Py_None);
	return Py_None;
    }
    else
    {
	t = PyTuple_New(ah->nelts);

	s = (char **) ah->elts;
	for (i = 0; i < ah->nelts; i++)
	    PyTuple_SetItem(t, i, PyString_FromString(s[i]));
	
	return t;
    }
}

/**
 ** python_merge_dir_config
 **
 */

static void *python_merge_dir_config(pool *p, void *cc, void *nc)
{

    py_dir_config *merged_conf = (py_dir_config *) ap_pcalloc(p, sizeof(py_dir_config));
    py_dir_config *current_conf = (py_dir_config *) cc;
    py_dir_config *new_conf = (py_dir_config *) nc;

    /* we basically allow the local configuration to override global,
     * by first copying current values and then new values on top
     */

    /** create **/
    merged_conf->directives = ap_make_table(p, 4);
    merged_conf->dirs = ap_make_table(p, 16);
    merged_conf->options = ap_make_table(p, 16);

    /** copy current **/

    merged_conf->authoritative = current_conf->authoritative;
    merged_conf->config_dir = ap_pstrdup(p, current_conf->config_dir);

    copy_table(merged_conf->directives, current_conf->directives);
    copy_table(merged_conf->dirs, current_conf->dirs);
    copy_table(merged_conf->options, current_conf->options);


    /** copy new **/

    if (new_conf->authoritative != merged_conf->authoritative)
	merged_conf->authoritative = new_conf->authoritative;
    if (new_conf->config_dir)
	merged_conf->config_dir = ap_pstrdup(p, new_conf->config_dir);

    copy_table(merged_conf->directives, new_conf->directives);
    copy_table(merged_conf->dirs, new_conf->dirs);
    copy_table(merged_conf->options, new_conf->options);

    return (void *) merged_conf;
}

/**
 ** python_directive
 **
 *  Called by Python*Handler directives.
 *
 *  When used within the same directory, this will have a
 *  cumulative, rather than overriding effect - i.e. values
 *  from same directives specified multiple times will be appended
 *  with a space in between.
 */

static const char *python_directive(cmd_parms *cmd, void * mconfig, 
				    char *key, const char *val)
{
    py_dir_config *conf;
    const char *s;
    
    conf = (py_dir_config *) mconfig;
    
    /* something there already? */
    s = ap_table_get(conf->directives, key);
    if (s)
	val = ap_pstrcat(cmd->pool, s, " ", val, NULL);
    
    ap_table_set(conf->directives, key, val);
    
    /* remember the directory where the directive was found */
    if (conf->config_dir) {
	ap_table_set(conf->dirs, key, conf->config_dir);
    }
    else {
	ap_table_set(conf->dirs, key, "");
    }
    
    return NULL;
}


/**
 ** make_interpreter
 **
 *      Creates a new Python interpeter.
 */

PyInterpreterState *make_interpreter(const char *name, server_rec *srv)
{
    PyThreadState *tstate;
    
    /* create a new interpeter */
    tstate = Py_NewInterpreter();

    if (! tstate) {

       /* couldn't create an interpreter, this is bad */
       ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, srv,
                     "make_interpreter: Py_NewInterpreter() returned NULL. No more memory?");
       return NULL;
    }
    else {

#ifdef WITH_THREAD
        /* release the thread state */
        PyThreadState_Swap(NULL); 
#endif
        /* Strictly speaking we don't need that tstate created
	 * by Py_NewInterpreter but is preferable to waste it than re-write
	 * a cousin to Py_NewInterpreter 
	 * XXX (maybe we can destroy it?)
	 */
        return tstate->interp;
    }
    
}

/**
 ** get_interpreter_data
 **
 *      Get interpreter given its name. 
 *      NOTE: Lock must be acquired prior to entering this function.
 */

interpreterdata *get_interpreter_data(const char *name, server_rec *srv)
{
    PyObject *p;
    interpreterdata *idata = NULL;
    
    if (! name)
	name = GLOBAL_INTERPRETER;

    p = PyDict_GetItemString(interpreters, (char *)name);
    if (!p)
    {
        PyInterpreterState *istate = make_interpreter(name, srv);
	if (istate) {
	    idata = (interpreterdata *)malloc(sizeof(interpreterdata));
	    idata->istate = istate;
	    /* obcallback will be created on first use */
	    idata->obcallback = NULL; 
	    p = PyCObject_FromVoidPtr((void *) idata, NULL);
	    PyDict_SetItemString(interpreters, (char *)name, p);
	}
    }
    else {
	idata = (interpreterdata *)PyCObject_AsVoidPtr(p);
    }

    return idata;
}

/**
 ** make_obcallback
 **
 *      This function instantiates an obCallBack object. 
 *      NOTE: The obCallBack object is instantiated by Python
 *      code. This C module calls into Python code which returns 
 *      the reference to obCallBack.
 */

PyObject * make_obcallback()
{

    PyObject *m;
    PyObject *obCallBack = NULL;

    /* This makes _apache appear imported, and subsequent
     * >>> import _apache 
     * will not give an error.
     */
    Py_InitModule("_apache", _apache_module_methods);

    /* Now execute the equivalent of
     * >>> import <module>
     * >>> <initstring>
     * in the __main__ module to start up Python.
     */

    if (! ((m = PyImport_ImportModule(MODULENAME)))) {
	fprintf(stderr, "make_obcallback(): could not import %s.\n", MODULENAME);
    }
    
    if (! ((obCallBack = PyObject_CallMethod(m, INITFUNC, NULL)))) {
	fprintf(stderr, "make_obcallback(): could not call %s.\n",
		INITFUNC);
    }
    
    return obCallBack;

}

/** 
 ** log_error
 **
 *  A wrpapper to ap_log_error
 * 
 *  log_error(string message, int level, server server)
 *
 */

static PyObject * log_error(PyObject *self, PyObject *args)
{

    int level = 0;
    char *message = NULL;
    serverobject *server = NULL;
    server_rec *serv_rec;

    if (! PyArg_ParseTuple(args, "z|iO", &message, &level, &server)) 
	return NULL; /* error */

    if (message) {

	if (! level) 
	    level = APLOG_NOERRNO|APLOG_ERR;
      
	if (!server)
	    serv_rec = NULL;
	else {
	    if (! is_serverobject(server)) {
		PyErr_BadArgument();
		return NULL;
	    }
	    serv_rec = server->server;
	}
	ap_log_error(APLOG_MARK, level, serv_rec, "%s", message);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** get_request_object
 **
 *      This creates or retrieves a previously created request object.
 *      The pointer to request object is stored in req->notes.
 */

static requestobject *get_request_object(request_rec *req)
{
    requestobject *request_obj;
    char *s;
    char s2[40];

    /* see if there is a request object already */
    /* XXX there must be a cleaner way to do this, atol is slow? */
    /* since tables only understand strings, we need to do some conversion */
    
    s = (char *) ap_table_get(req->notes, "python_request_ptr");
    if (s) {
	request_obj = (requestobject *) atol(s);
	return request_obj;
    }
    else {
	if ((req->path_info) && 
	    (req->path_info[strlen(req->path_info) - 1] == SLASH))
	{
	    int i;
	    i = strlen(req->path_info);
	    /* take out the slash */
	    req->path_info[i - 1] = 0;

	    Py_BEGIN_ALLOW_THREADS;
	    ap_add_cgi_vars(req);
	    Py_END_ALLOW_THREADS;
	    request_obj = make_requestobject(req);

	    /* put the slash back in */
	    req->path_info[i - 1] = SLASH; 
	    req->path_info[i] = 0;
	} 
	else 
	{ 
	    Py_BEGIN_ALLOW_THREADS;
	    ap_add_cgi_vars(req);
	    Py_END_ALLOW_THREADS;
	    request_obj = make_requestobject(req);
	}
	
	/* store the pointer to this object in notes */
	/* XXX this is not good... */
	sprintf(s2, "%ld", (long) request_obj);
	ap_table_set(req->notes, "python_request_ptr", s2);
	return request_obj;
    }
}

/**
 ** python_handler
 **
 *      A generic python handler. Most handlers should use this.
 */

static int python_handler(request_rec *req, char *handler)
{

    PyObject *resultobject = NULL;
    interpreterdata *idata;
    requestobject *request_obj;
    const char *s;
    py_dir_config * conf;
    int result;
    const char * interpreter = NULL;
#ifdef WITH_THREAD
    PyThreadState *tstate;
#endif

    /* get configuration */
    conf = (py_dir_config *) ap_get_module_config(req->per_dir_config, &python_module);

    /* is there a handler? */
    if (! ap_table_get(conf->directives, handler)) {
	if (! ap_table_get(req->notes, handler))
	    return DECLINED;
    }

    /*
     * determine interpreter to use 
     */

    if ((s = ap_table_get(conf->directives, "PythonInterpreter"))) {
	/* forced by configuration */
	interpreter = s;
    }
    else {
	if ((s = ap_table_get(conf->directives, "PythonInterpPerDirectory"))) {
	    /* base interpreter on directory where the file is found */
	    if (ap_is_directory(req->filename))
		interpreter = ap_make_dirstr_parent(req->pool, 
						    ap_pstrcat(req->pool, req->filename, 
							       SLASH_S, NULL ));
	    else {
		if (req->filename)
		    interpreter = ap_make_dirstr_parent(req->pool, req->filename);
		else
		    /* 
		     * In early stages of the request, req->filename is not known,
		     * so this would have to run in the global interpreter.
		     */
		    interpreter = NULL;
	    }
	}
	else if (ap_table_get(conf->directives, "PythonInterpPerServer")) {
	    interpreter = req->server->server_hostname;
	}
	else {
	    /* - default -
	     * base interpreter name on directory where the handler directive
	     * was last found. If it was in http.conf, then we will use the 
	     * global interpreter.
	     */
	    
	    if (! s) {
		s = ap_table_get(conf->dirs, handler);
		if (! s) {
		    /* this one must have been added via req.add_handler() */
		    char * ss = ap_pstrcat(req->pool, handler, "_dir", NULL);
		    s = ap_table_get(req->notes, ss);
		}
		if (strcmp(s, "") == 0)
		    interpreter = NULL;
		else
		    interpreter = s;
	    }
	}
    }
    
#ifdef WITH_THREAD  
    /* acquire lock (to protect the interpreters dictionary) */
    PyEval_AcquireLock();
#endif

    /* get/create interpreter */
    idata = get_interpreter_data(interpreter, req->server);
   
#ifdef WITH_THREAD
    /* release the lock */
    PyEval_ReleaseLock();
#endif

    if (!idata) {
        ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, req,
		      "python_handler: get_interpreter_data returned NULL!");
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    
#ifdef WITH_THREAD  
    /* create thread state and acquire lock */
    tstate = PyThreadState_New(idata->istate);
    PyEval_AcquireThread(tstate);
#endif

    if (!idata->obcallback) {

        idata->obcallback = make_obcallback();
        /* we must have a callback object to succeed! */
        if (!idata->obcallback) 
        {
	    ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, req,
			  "python_handler: make_obcallback returned no obCallBack!");
#ifdef WITH_THREAD
	    PyThreadState_Swap(NULL);
	    PyThreadState_Delete(tstate);
	    PyEval_ReleaseLock();
#endif
	    return HTTP_INTERNAL_SERVER_ERROR;
        }
    }

    /* 
     * make a note of which subinterpreter we're running under.
     * this information is used by register_cleanup()
     */
    if (interpreter)
	ap_table_set(req->notes, "python_interpreter", interpreter);
    else
	ap_table_set(req->notes, "python_interpreter", GLOBAL_INTERPRETER);
    
    /* create/acquire request object */
    request_obj = get_request_object(req);

    /* make a note of which handler we are in right now */
    ap_table_set(req->notes, "python_handler", handler);

    /* put the list of handlers on the hstack */
    if ((s = ap_table_get(conf->directives, handler))) {
	request_obj->hstack = ap_pstrdup(req->pool, ap_table_get(conf->directives,
								 handler));
    }
    if ((s = ap_table_get(req->notes, handler))) {
	if (request_obj->hstack) {
	    request_obj->hstack = ap_pstrcat(req->pool, request_obj->hstack,
					     " ", s, NULL);
	}
	else {
	    request_obj->hstack = ap_pstrdup(req->pool, s);
	}
    }
    /* 
     * Here is where we call into Python!
     * This is the C equivalent of
     * >>> resultobject = obCallBack.Dispatch(request_object, handler)
     */
    resultobject = PyObject_CallMethod(idata->obcallback, "Dispatch", "Os", 
				       request_obj, handler);
     
#ifdef WITH_THREAD
    /* release the lock and destroy tstate*/
    /* XXX Do not use 
     * . PyEval_ReleaseThread(tstate); 
     * . PyThreadState_Delete(tstate);
     * because PyThreadState_delete should be done under 
     * interpreter lock to work around a bug in 1.5.2 (see patch to pystate.c 2.8->2.9) 
     */
    PyThreadState_Swap(NULL);
    PyThreadState_Delete(tstate);
    PyEval_ReleaseLock();
#endif

    if (! resultobject) {
	ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, req, 
		      "python_handler: Dispatch() returned nothing.");
	return HTTP_INTERNAL_SERVER_ERROR;
    }
    else {
	/* Attempt to analyze the result as a string indicating which
	   result to return */
	if (! PyInt_Check(resultobject)) {
	    ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, req, 
			  "python_handler: Dispatch() returned non-integer.");
	    return HTTP_INTERNAL_SERVER_ERROR;
	}
	else {
	    result = PyInt_AsLong(resultobject);

	    /* authen handlers need one more thing
	     * if authentication failed and this handler is not
	     * authoritative, let the others handle it
	     */
	    if (strcmp(handler, "PythonAuthenHandler") == 0) {
		if ((result == HTTP_UNAUTHORIZED) && 
		    (! conf->authoritative))
		    result = DECLINED;
	    }
	}
    } 

    /* When the script sets an error status by using req.status,
     * it can then either provide its own HTML error message or have
     * Apache provide one. To have Apache provide one, you need to send
     * no output and return the error from the handler function. However,
     * if the script is providing HTML, then the return value of the 
     * handler should be OK, else the user will get both the script
     * output and the Apache output.
     */

    /* Another note on status. req->status is used to build req->status_line
     * unless status_line is not NULL. req->status has no effect on how the
     * server will behave. The error behaviour is dictated by the return 
     * value of this handler. When the handler returns anything other than OK,
     * the server will display the error that matches req->status, unless it is
     * 200 (HTTP_OK), in which case it will just show the error matching the return
     * value. If the req->status and the return of the handle do not match,
     * then the server will first show what req->status shows, then it will
     * print "Additionally, X error was recieved", where X is the return code
     * of the handle. If the req->status or return code is a weird number that the 
     * server doesn't know, it will default to 500 Internal Server Error.
     */

    /* clean up */
    Py_XDECREF(resultobject);

    /* return the translated result (or default result) to the Server. */
    return result;

}

/**
 ** python_cleanup
 **
 *     This function gets called for registered cleanups
 */

void python_cleanup(void *data)
{
    interpreterdata *idata;

#ifdef WITH_THREAD
    PyThreadState *tstate;
#endif
    cleanup_info *ci = (cleanup_info *)data;

#ifdef WITH_THREAD  
    /* acquire lock (to protect the interpreters dictionary) */
    PyEval_AcquireLock();
#endif

    /* get/create interpreter */
    idata = get_interpreter_data(ci->interpreter, ci->request_rec->server);

#ifdef WITH_THREAD
    /* release the lock */
    PyEval_ReleaseLock();
#endif

    if (!idata) {
        ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, ci->request_rec,
		      "python_cleanup: get_interpreter_data returned NULL!");
	Py_DECREF(ci->handler);
	Py_DECREF(ci->data);
	free(ci);
        return;
    }
    
#ifdef WITH_THREAD  
    /* create thread state and acquire lock */
    tstate = PyThreadState_New(idata->istate);
    PyEval_AcquireThread(tstate);
#endif

    /* 
     * Call the cleanup function.
     */
    if (! PyObject_CallFunction(ci->handler, "O", ci->data)) {
	PyObject *ptype;
	PyObject *pvalue;
	PyObject *ptb;
	PyObject *handler;
	PyObject *stype;
	PyObject *svalue;

	PyErr_Fetch(&ptype, &pvalue, &ptb);
	handler = PyObject_Str(ci->handler);
	stype = PyObject_Str(ptype);
	svalue = PyObject_Str(pvalue);

	Py_DECREF(ptype);
	Py_DECREF(pvalue);
	Py_DECREF(ptb);

        ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, ci->request_rec,
		      "python_cleanup: Error calling cleanup object %s", 
		      PyString_AsString(handler));
        ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, ci->request_rec,
		      "    %s: %s", PyString_AsString(stype), 
		      PyString_AsString(svalue));

	Py_DECREF(handler);
	Py_DECREF(stype);
	Py_DECREF(svalue);
    }
     
#ifdef WITH_THREAD
    /* release the lock and destroy tstate*/
    /* XXX Do not use 
     * . PyEval_ReleaseThread(tstate); 
     * . PyThreadState_Delete(tstate);
     * because PyThreadState_delete should be done under 
     * interpreter lock to work around a bug in 1.5.2 (see patch to pystate.c 2.8->2.9) 
     */
    PyThreadState_Swap(NULL);
    PyThreadState_Delete(tstate);
    PyEval_ReleaseLock();
#endif

    Py_DECREF(ci->handler);
    Py_DECREF(ci->data);
    free(ci);
    return;
}

/**
 ** directive_PythonImport
 **
 *      This function called whenever PythonImport directive
 *      is encountered. Note that this function does not actually
 *      import anything, it just remembers what needs to be imported
 *      in the python_imports table. The actual importing is done later
 *      in the ChildInitHandler. This is because this function here
 *      is called before the python_init and before the suid and fork.
 *
 *      The reason why this infor stored in a global variable as opposed
 *      to the actual config, is that the config info doesn't seem to
 *      be available within the ChildInit handler.
 */
static const char *directive_PythonImport(cmd_parms *cmd, void *mconfig, 
					  const char *module) 
{
    const char *s = NULL; /* general purpose string */
    py_dir_config *conf;
    const char *key = "PythonImport";

    /* get config */
    conf = (py_dir_config *) mconfig;

#ifdef WITH_THREAD  
    PyEval_AcquireLock();
#endif

    /* make the table if not yet */
    if (! python_imports)
	python_imports = ap_make_table(cmd->pool, 4);
    
    /* remember the module name and the directory in which to
       import it (this is for ChildInit) */
    ap_table_add(python_imports, module, conf->config_dir);

#ifdef WITH_THREAD  
    PyEval_ReleaseLock();
#endif

    /* the rest is basically for consistency */

    /* Append the module to the directive. (this is ITERATE) */
    if ((s = ap_table_get(conf->directives, key))) {
	ap_pstrcat(cmd->pool, s, " ", module, NULL);
    }
    else {
	ap_table_set(conf->directives, key, module);
    }

    /* remember the directory where the directive was found */
    if (conf->config_dir) {
	ap_table_set(conf->dirs, key, conf->config_dir);
    }
    else {
	ap_table_set(conf->dirs, key, "");
    }

    return NULL;
}

/**
 ** directive_PythonPath
 **
 *      This function called whenever PythonPath directive
 *      is encountered.
 */
static const char *directive_PythonPath(cmd_parms *cmd, void *mconfig, 
					const char *val) {
    return python_directive(cmd, mconfig, "PythonPath", val);
}

/**
 ** directive_PythonInterpreter
 **
 *      This function called whenever PythonInterpreter directive
 *      is encountered.
 */
static const char *directive_PythonInterpreter(cmd_parms *cmd, void *mconfig, 
				       const char *val) {
    return python_directive(cmd, mconfig, "PythonInterpreter", val);
}

/**
 ** directive_PythonDebug
 **
 *      This function called whenever PythonDebug directive
 *      is encountered.
 */
static const char *directive_PythonDebug(cmd_parms *cmd, void *mconfig,
					 int val) {
    if (val)
	return python_directive(cmd, mconfig, "PythonDebug", "On");
    else
	return python_directive(cmd, mconfig, "PythonDebug", "");
}

/**
 ** directive_PythonEnablePdb
 **
 *      This function called whenever PythonEnablePdb
 *      is encountered.
 */
static const char *directive_PythonEnablePdb(cmd_parms *cmd, void *mconfig,
					     int val) {
    if (val)
	return python_directive(cmd, mconfig, "PythonEnablePdb", "On");
    else
	return python_directive(cmd, mconfig, "PythonEnablePdb", "");
}

/**
 ** directive_PythonInterpPerDirectory
 **
 *      This function called whenever PythonInterpPerDirectory directive
 *      is encountered.
 */

static const char *directive_PythonInterpPerDirectory(cmd_parms *cmd, 
						      void *mconfig, int val) {
    py_dir_config *conf;
    const char *key = "PythonInterpPerDirectory";

    conf = (py_dir_config *) mconfig;

    if (val) {
	ap_table_set(conf->directives, key, "1");

	/* remember the directory where the directive was found */
	if (conf->config_dir) {
	    ap_table_set(conf->dirs, key, conf->config_dir);
	}
	else {
	    ap_table_set(conf->dirs, key, "");
	}
    }
    else {
	ap_table_unset(conf->directives, key);
	ap_table_unset(conf->dirs, key);
    }

    return NULL;
}

/**
 ** directive_PythonInterpPerServer
 **
 *      This function called whenever PythonInterpPerServer directive
 *      is encountered.
 */

static const char *directive_PythonInterpPerServer(cmd_parms *cmd, 
						   void *mconfig, int val) {
    py_dir_config *conf;
    const char *key = "PythonInterpPerServer";

    conf = (py_dir_config *) mconfig;

    if (val) {
	ap_table_set(conf->directives, key, "1");
    }
    else {
	ap_table_unset(conf->directives, key);
    }

    return NULL;
}

/**
 ** directive_PythonNoReload
 **
 *      This function called whenever PythonNoReload directive
 *      is encountered.
 */

static const char *directive_PythonNoReload(cmd_parms *cmd, 
					    void *mconfig, int val) {

    py_dir_config *conf;
    const char *key = "PythonNoReload";
    
    conf = (py_dir_config *) mconfig;

    if (val) {
	ap_table_set(conf->directives, key, "1");

	/* remember the directory where the directive was found */
	if (conf->config_dir) {
	    ap_table_set(conf->dirs, key, conf->config_dir);
	}
	else {
	    ap_table_set(conf->dirs, key, "");
	}
    }
    else {
	ap_table_unset(conf->directives, key);
	ap_table_unset(conf->dirs, key);
    }

    return NULL;
}

/**
 **
 *       This function is called every time PythonOption directive
 *       is encountered. It sticks the option into a table containing
 *       a list of options. This table is part of the local config structure.
 */

static const char *directive_PythonOption(cmd_parms *cmd, void * mconfig, 
				       const char * key, const char * val)
{

    py_dir_config *conf;

    conf = (py_dir_config *) mconfig;
    ap_table_set(conf->options, key, val);

    return NULL;

}

/**
 ** directive_PythonOptimize
 **
 *      This function called whenever PythonOptimize directive
 *      is encountered.
 */
static const char *directive_PythonOptimize(cmd_parms *cmd, void *mconfig,
					    int val) {
    if ((val) && (Py_OptimizeFlag != 2))
	Py_OptimizeFlag = 2;
    return NULL;
}

/**
 ** Python*Handler directives
 **
 */

static const char *directive_PythonAccessHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonAccessHandler", val);
}
static const char *directive_PythonAuthenHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonAuthenHandler", val);
}
static const char *directive_PythonAuthzHandler(cmd_parms *cmd, void * mconfig, 
						const char *val) {
    return python_directive(cmd, mconfig, "PythonAuthzHandler", val);
}
static const char *directive_PythonFixupHandler(cmd_parms *cmd, void * mconfig, 
						const char *val) {
    return python_directive(cmd, mconfig, "PythonFixupHandler", val);
}
static const char *directive_PythonHandler(cmd_parms *cmd, void * mconfig, 
					   const char *val) {
    return python_directive(cmd, mconfig, "PythonHandler", val);
}
static const char *directive_PythonHeaderParserHandler(cmd_parms *cmd, void * mconfig, 
						       const char *val) {
    return python_directive(cmd, mconfig, "PythonHeaderParserHandler", val);
}
static const char *directive_PythonInitHandler(cmd_parms *cmd, void * mconfig,
					       const char *val) {
    return python_directive(cmd, mconfig, "PythonInitHandler", val);
}
static const char *directive_PythonPostReadRequestHandler(cmd_parms *cmd, 
							  void * mconfig, 
							  const char *val) {
    return python_directive(cmd, mconfig, "PythonPostReadRequestHandler", val);
}
static const char *directive_PythonTransHandler(cmd_parms *cmd, void * mconfig, 
						const char *val) {
    return python_directive(cmd, mconfig, "PythonTransHandler", val);
}
static const char *directive_PythonTypeHandler(cmd_parms *cmd, void * mconfig, 
					       const char *val) {
    return python_directive(cmd, mconfig, "PythonTypeHandler", val);
}
static const char *directive_PythonLogHandler(cmd_parms *cmd, void * mconfig, 
					      const char *val) {
    return python_directive(cmd, mconfig, "PythonLogHandler", val);
}


/**
 ** Handlers
 **
 */

static void PythonChildInitHandler(server_rec *s, pool *p) 
{

    array_header *ah;
    table_entry *elts;
    PyObject *sys, *path, *dirstr;
    interpreterdata *idata;
    int i;
    const char *interpreter;
#ifdef WITH_THREAD
    PyThreadState *tstate;
#endif


    if (python_imports) {

	/* iterate throught the python_imports table and import all
	   modules specified by PythonImport */

	ah = ap_table_elts(python_imports);
	elts = (table_entry *)ah->elts;
	for (i = 0; i < ah->nelts; i++) {
	
	    char *module = elts[i].key;
	    char *dir = elts[i].val;

	    /* Note: PythonInterpreter has no effect */
	    interpreter = dir;

#ifdef WITH_THREAD  
	    PyEval_AcquireLock();
#endif
    
	    idata = get_interpreter_data(interpreter, s);

#ifdef WITH_THREAD
	    PyEval_ReleaseLock();
#endif

	    if (!idata) {
		ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, s,
			     "ChildInitHandler: (PythonImport) get_interpreter_data returned NULL!");
		return;
	    }

#ifdef WITH_THREAD  
	    /* create thread state and acquire lock */
	    tstate = PyThreadState_New(idata->istate);
	    PyEval_AcquireThread(tstate);
#endif

	    if (!idata->obcallback) {
		idata->obcallback = make_obcallback();
		/* we must have a callback object to succeed! */
		if (!idata->obcallback) {
		    ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, s,
				 "python_handler: get_obcallback returned no obCallBack!");
#ifdef WITH_THREAD
		    PyThreadState_Swap(NULL);
		    PyThreadState_Delete(tstate);
		    PyEval_ReleaseLock();
#endif
		    return;
		}
	    }
	
	    /* add dir to pythonpath if not in there already */
	    if (dir) {
		sys = PyImport_ImportModule("sys");
		path = PyObject_GetAttrString(sys, "path");
		dirstr = PyString_FromString(dir);
		if (PySequence_Index(path, dirstr) == -1)
		    PyList_SetSlice(path, 0, 0, dirstr);
		Py_DECREF(dirstr);
		Py_DECREF(path);
		Py_DECREF(sys);
	    }

	    /* now import the specified module */
	    if (! PyImport_ImportModule(module)) {
		if (PyErr_Occurred())
		    PyErr_Print();
		ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, s,
			     "directive_PythonImport: error importing %s", module);
	    }

#ifdef WITH_THREAD
	    PyThreadState_Swap(NULL);
	    PyThreadState_Delete(tstate);
	    PyEval_ReleaseLock();
#endif

	}
    }
}

static int PythonAccessHandler(request_rec *req) {
    return python_handler(req, "PythonAccessHandler");
}
static int PythonAuthenHandler(request_rec *req) {
    return python_handler(req, "PythonAuthenHandler");
}
static int PythonAuthzHandler(request_rec *req) {
    return python_handler(req, "PythonAuthzHandler");
}
static void PythonChildExitHandler(server_rec *srv, pool *p) {
    Py_Finalize();
}
static int PythonFixupHandler(request_rec *req) {
    return python_handler(req, "PythonFixupHandler");
}
static int PythonHandler(request_rec *req) {
    return python_handler(req, "PythonHandler");
}
static int PythonHeaderParserHandler(request_rec *req) {
    int rc;
    
    if (! ap_table_get(req->notes, "python_init_ran")) {
	rc = python_handler(req, "PythonInitHandler");
	if ((rc != OK) && (rc != DECLINED))
	    return rc;
    }
    return python_handler(req, "PythonHeaderParserHandler");
}
static int PythonLogHandler(request_rec *req) {
    return python_handler(req, "PythonLogHandler");
}
static int PythonPostReadRequestHandler(request_rec *req) {
    int rc;

    rc = python_handler(req, "PythonInitHandler");
    ap_table_set(req->notes, "python_init_ran", "1");
    if ((rc != OK) && (rc != DECLINED))
	return rc;

    return python_handler(req, "PythonPostReadRequestHandler");
}
static int PythonTransHandler(request_rec *req) {
    return python_handler(req, "PythonTransHandler");
}
static int PythonTypeHandler(request_rec *req) {
    return python_handler(req, "PythonTypeHandler");
}



/******************************************************************
 *       *** end of functions called by Apache or Python ***    
 ******************************************************************/


/******************************************************************
 *                Apache module stuff 
 ******************************************************************/

/* content handlers */
static handler_rec python_handlers[] = 
{
    { "python-program", PythonHandler },
    { NULL }
};

/* command table */
command_rec python_commands[] =
{
    {
	"PythonAccessHandler",
	directive_PythonAccessHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python access by host address handlers."
    },
    {
	"PythonAuthenHandler",
	directive_PythonAuthenHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python authentication handlers."
    },
    {
	"PythonAuthzHandler",
	directive_PythonAuthzHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python authorization (user allowed _here_) handlers."
    },
    {
	"PythonDebug",                 
	directive_PythonDebug,         
	NULL,                                
	OR_ALL,                         
	FLAG,                               
	"Send (most) Python error output to the client rather than logfile."
    },
    {
	"PythonEnablePdb",
	directive_PythonEnablePdb,         
	NULL,                                
	OR_ALL,                         
	FLAG,                               
	"Run handlers in pdb (Python Debugger). Use with -X."
    },
    {
	"PythonFixupHandler",
	directive_PythonFixupHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python fixups handlers."
    },
    {
	"PythonHandler",
	directive_PythonHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python request handlers."
    },
    {
	"PythonHeaderParserHandler",
	directive_PythonHeaderParserHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python header parser handlers."
    },
    {
	"PythonImport",
	directive_PythonImport,
	NULL,
	ACCESS_CONF,
	ITERATE,
	"Modules to be imported when this directive is processed."
    },
    {
	"PythonInitHandler",
	directive_PythonInitHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python request initialization handler."
    },
    {
	"PythonInterpPerDirectory",                 
	directive_PythonInterpPerDirectory,         
	NULL,                                
	OR_ALL,                         
	FLAG,                               
	"Create subinterpreters per directory rather than per directive."
    },
    {
	"PythonInterpPerServer",
	directive_PythonInterpPerServer,
	NULL,                                
	RSRC_CONF,
	FLAG,                               
	"Create subinterpreters per server rather than per directive."
    },
    {
	"PythonInterpreter",                 
	directive_PythonInterpreter,         
	NULL,                                
	OR_ALL,                         
	TAKE1,                               
	"Forces a specific Python interpreter name to be used here."
    },
    {
	"PythonLogHandler",
	directive_PythonLogHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python logger handlers."
    },
    {
	"PythonNoReload",                 
	directive_PythonNoReload,         
	NULL,                                
	OR_ALL,                         
	FLAG,                               
	"Do not reload already imported modules if they changed."
    },
    {
	"PythonOptimize",
	directive_PythonOptimize,         
	NULL,                                
	OR_ALL,                         
	FLAG,                               
	"Set the equivalent of the -O command-line flag on the interpreter."
    },
    {
	"PythonOption",
	directive_PythonOption,                           
	NULL, 
	OR_ALL,                                      
	TAKE2,                                            
	"Useful to pass custom configuration information to scripts."
    },
    {
	"PythonPath",
	directive_PythonPath,
	NULL,
	OR_ALL,
	TAKE1,
	"Python path, specified in Python list syntax."
    },
    {
	"PythonPostReadRequestHandler",
	directive_PythonPostReadRequestHandler,
	NULL,
	RSRC_CONF,
	RAW_ARGS,
	"Python post read-request handlers."
    },
    {
	"PythonTransHandler",
	directive_PythonTransHandler,
	NULL,
	RSRC_CONF,
	RAW_ARGS,
	"Python filename to URI translation handlers."
    },
    {
	"PythonTypeHandler",
	directive_PythonTypeHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python MIME type checker/setter handlers."
    },
    {NULL}
};

/* module definition */

/* This is read by Configure script to provide "magical"
 * linking with the Python libraries....
 * Credit goes to Lele Gaifax and his amazing PyApache module!
 *
 * MODULE-DEFINITION-START
 * Name: python_module
 * ConfigStart
 PyVERSION=`python -c "import sys; print sys.version[:3]"`
 PyEXEC_INSTALLDIR=`python -c "import sys; print sys.exec_prefix"`
 PyLIBP=${PyEXEC_INSTALLDIR}/lib/python${PyVERSION}
 PyLIBPL=${PyLIBP}/config
 PyLIBS=`grep "^LIB[SMC]=" ${PyLIBPL}/Makefile | cut -f2 -d= | tr '\011\012\015' '   '`
 PyMODLIBS=`grep "^LOCALMODLIBS=" ${PyLIBPL}/Makefile | cut -f2 -d= | tr '\011\012\015' '   '`
 PyLFS=`grep "^LINKFORSHARED=" ${PyLIBPL}/Makefile | cut -f2 -d= | tr '\011\012\015' '   '`
 PyLDFLAGS=`grep "^LDFLAGS=" ${PyLIBPL}/Makefile | cut -f2 -d= | tr '\011\012\015' '   '`
 PyPYTHONLIBS=${PyLIBPL}/libpython${PyVERSION}.a
 LIBS="${LIBS} ${PyPYTHONLIBS} ${PyLIBS} ${PyMODLIBS}"
 LDFLAGS="${LDFLAGS} ${PyLFS} ${PyLDFLAGS}"
 INCLUDES="${INCLUDES} -I${PyEXEC_INSTALLDIR}/include/python${PyVERSION}"
 * ConfigEnd
 * MODULE-DEFINITION-END
 */


/* XXX
 * PythonChildInitHandler and PythonChildExitHandler
 * NOTE - it's not clear which interpreter would those run in
 * since the interprters exist per-path, and at those stages
 * there is no request to get the path from....
 */

module python_module =
{
  STANDARD_MODULE_STUFF,
  python_init,                   /* module initializer */
  python_create_dir_config,      /* per-directory config creator */
  python_merge_dir_config,       /* dir config merger */
  NULL,                          /* server config creator */
  NULL,                          /* server config merger */
  python_commands,               /* command table */
  python_handlers,               /* [7] list of handlers */
  PythonTransHandler,            /* [2] filename-to-URI translation */
  PythonAuthenHandler,           /* [5] check/validate user_id */
  PythonAuthzHandler,            /* [6] check user_id is valid *here* */
  PythonAccessHandler,           /* [4] check access by host address */
  PythonTypeHandler,             /* [7] MIME type checker/setter */
  PythonFixupHandler,            /* [8] fixups */
  PythonLogHandler,              /* [10] logger */
  PythonHeaderParserHandler,     /* [3] header parser */
  PythonChildInitHandler,        /* process initializer */
  PythonChildExitHandler,        /* process exit/cleanup */
  PythonPostReadRequestHandler   /* [1] post read_request handling */
};

/******************************************************************
 * LE FIN
 ******************************************************************/








