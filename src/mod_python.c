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
 * $Id: mod_python.c,v 1.8 2000/05/22 12:14:39 grisha Exp $
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
#include "http_protocol.h"
#include "util_script.h"
#include "http_log.h"

/* Python headers */
#include "Python.h"
#include "structmember.h"

/******************************************************************
                        Declarations
 ******************************************************************/

#define VERSION_COMPONENT "mod_python/2.0"
#define MODULENAME "mod_python.apache"
#define INITSTRING "mod_python.apache.init()"
#define INTERP_ATTR "__interpreter__"

/* Are we in single interpreter mode? */
static int single_mode = 0;

/* List of available Python obCallBacks/Interpreters
 * (In a Python dictionary) */
static PyObject * interpreters = NULL;

/* The CallBack object. This variable is used as
 * a way to pass a pointer between  SetCallBack()
 * function and make_obcallback(). Nothing else. 
 * Don't rely on its value.                      */
static PyObject *obCallBack = NULL;

/* This function is used with ap_register_cleanup() */
void noop(void *data) {};
void python_decref(void *object);

/* some forward declarations */
PyObject * make_obcallback(const char *module, const char *initstring);
PyObject * tuple_from_array_header(const array_header *ah);
PyObject * get_obcallback(const char *name, server_rec * req);

/*********************************
           Python things 
 *********************************/
/*********************************
  members of _apache module 
 *********************************/

/* froward declarations */
static PyObject * SetCallBack(PyObject *self, PyObject *args);
static PyObject * log_error(PyObject *self, PyObject *args);
static PyObject * make_table(PyObject *self, PyObject *args);

/* methods of _apache */
static struct PyMethodDef _apache_module_methods[] = {
  {"SetCallBack",               (PyCFunction)SetCallBack,      METH_VARARGS},
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

static PyTypeObject tableobjecttype;

#define is_tableobject(op) ((op)->ob_type == &tableobjecttype)

static PyObject * tablegetitem  (tableobject *self, PyObject *key );
static PyObject * table_has_key (tableobject *self, PyObject *args );
static PyObject * table_keys    (tableobject *self);
static int tablelength          (tableobject *self);
static int tablesetitem         (tableobject *self, PyObject *key, PyObject *val);
static int tb_setitem           (tableobject *self, const char *key, const char *val);
static tableobject * make_tableobject(table * t);

static PyMethodDef tablemethods[] = {
  {     "keys",                 (PyCFunction)table_keys,    1},
  {     "has_key",              (PyCFunction)table_has_key, 1},
  { NULL, NULL } /* sentinel */
};

static PyMappingMethods table_mapping = {
    (inquiry)       tablelength,           /*mp_length*/
    (binaryfunc)    tablegetitem,          /*mp_subscript*/
    (objobjargproc) tablesetitem,          /*mp_ass_subscript*/
};

/* another forward */
tableobject * headers_in(request_rec *req);

/********************************
          serverobject
 ********************************/

typedef struct serverobject {
    PyObject_HEAD
    server_rec     *server;
    PyObject       *next;
} serverobject;

static PyTypeObject serverobjecttype;

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

static PyTypeObject connobjecttype;

#define is_connobject(op) ((op)->ob_type == &connobjecttype)

#undef OFF
#define OFF(x) offsetof(conn_rec, x)
static struct memberlist conn_memberlist[] = {
  /* server in getattr */
  /* base_server in getattr */
  /* XXX vhost_lookup_data? */
  {"child_num",          T_INT,       OFF(child_num),          RO},
  /* XXX BUFF? */
  /* XXX struct sockaddr_in local_addr? */
  /* XXX struct sockaddr_in remote_addr? */
  {"remote_ip",          T_STRING,    OFF(remote_ip),          RO},
  {"remote_host",        T_STRING,    OFF(remote_host),        RO},
  {"remote_logname",     T_STRING,    OFF(remote_logname),    RO},
  {"user",               T_STRING,    OFF(user),               RO},
  {"ap_auth_type",       T_STRING,    OFF(ap_auth_type),       RO},
  /* XXX aborted, keepalive, keptalive, double_reverse, keepalives ? */
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
} requestobject;

static PyTypeObject requestobjecttype;

#define is_requestobject(op) ((op)->ob_type == &requestobjecttype)

static PyObject * req_send_http_header     (requestobject *self, PyObject *args);
static PyObject * req_get_basic_auth_pw    (requestobject *self, PyObject *args);
static PyObject * req_write                (requestobject *self, PyObject *args);
static PyObject * req_read                 (requestobject *self, PyObject *args);
static PyObject * req_get_config           (requestobject *self, PyObject *args);
static PyObject * req_get_options          (requestobject *self, PyObject *args);
static PyObject * req_get_dirs             (requestobject *self, PyObject *args);
static PyObject * req_add_common_vars      (requestobject *self, PyObject *args);

static PyMethodDef requestobjectmethods[] = {
    {"send_http_header",     (PyCFunction) req_send_http_header,     METH_VARARGS},
    {"get_basic_auth_pw",    (PyCFunction) req_get_basic_auth_pw,    METH_VARARGS},
    {"write",                (PyCFunction) req_write,                METH_VARARGS},
    {"read",                 (PyCFunction) req_read,                 METH_VARARGS},
    {"get_config",           (PyCFunction) req_get_config,           METH_VARARGS},
    {"get_options",          (PyCFunction) req_get_options,          METH_VARARGS},
    {"get_dirs",             (PyCFunction) req_get_dirs,             METH_VARARGS},
    {"add_common_vars",      (PyCFunction) req_add_common_vars,      METH_VARARGS},
    { NULL, NULL } /* sentinel */
};

#undef OFF
#define OFF(x) offsetof(request_rec, x)
static struct memberlist request_memberlist[] = {
    /* connection, server, next, prev, main in getattr */
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
    /* XXX content_languages */
    {"no_cache",           T_INT,       OFF(no_cache),             RO},
    {"no_local_copy",      T_INT,       OFF(no_local_copy),        RO},
    {"unparsed_uri",       T_STRING,    OFF(unparsed_uri),         RO},
    {"uri",                T_STRING,    OFF(uri),                  RO},
    {"filename",           T_STRING,    OFF(filename),             RO},
    {"path_info",          T_STRING,    OFF(path_info),            RO},
    {"args",               T_STRING,    OFF(args),                 RO},
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
 ** tablelength
 **
 *      Number of elements in a table. Called
 *      when you do len(table) in Python.
 */

static int tablelength(tableobject *self) 
{ 
    return ap_table_elts(self->table)->nelts;
};

/**
 ** tablesetitem
 **
 *      insert into table dictionary-style
 *      *** NOTE ***
 *      Since the underlying ap_table_set makes a *copy* of the string,
 *      there is no need to increment the reference to the Python
 *      string passed in.
 */

static int tablesetitem(tableobject *self,  PyObject *key, PyObject
			*val) 
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
};

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
 *   Merge two tables into one. Matching ley values 
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

/**
 ** print_table
 **
 *   Print apache table. Only used for debugging.
 */

static void print_table(table * t)
{
    array_header *ah;
    table_entry *elts;
    int i;

    ah = ap_table_elts (t);
    elts = (table_entry *) ah->elts;
    i = ah->nelts;

    while (i--)
	if (elts[i].key)
	    printf("   %s: \t%s\n", elts[i].key, elts[i].val);
}

/**
 ** print_array
 **
 *   Print apache array (of strings). Only used for debugging.
 */

static void *print_array(array_header *ah)
{
    int i;
    char **elts;

    elts = (char **)ah->elts;

    for (i = 0; i < ah->nelts; ++i) {
	printf("%s ", elts[i]);
    }
    printf("\n");

    return NULL;
    
    /* avoid compiler warning */
    print_array(ah);

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

    _Py_NewReference(result);
    ap_register_cleanup(req->pool, (PyObject *)result, python_decref, noop);

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
    } else

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
	self->request_rec->content_type = PyString_AS_STRING(value);
	return 0;
    }
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
 ** request.get_basic_auth_pw(request self)
 **
 *    get basic authentication password,
 *    similat to ap_get_basic_auth_pw
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

    ap_rwrite(buff, len, self->request_rec);
    rc = ap_rflush(self->request_rec);
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

    int len, rc, bytes_read;
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

    /* read it in */
    buffer = PyString_AS_STRING((PyStringObject *) result);
    bytes_read = ap_get_client_block(self->request_rec, buffer, len);

    /* resize if necessary */
    if (bytes_read < len) 
	if(_PyString_Resize(&result, bytes_read))
	    return NULL;

    return result;
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

/********************************
  ***  end of request object ***
 ********************************/

/**
 ** table2dict()
 **
 *      Converts Apache table to Python dictionary.
 */

static PyObject * table2dict(table * t)
{

    PyObject *result, *val;
    array_header *ah;
    table_entry *elts;
    int i;

    result = PyDict_New();

    ah = ap_table_elts (t);
    elts = (table_entry *) ah->elts;
    i = ah->nelts;

    while (i--)
	if (elts[i].key)
	{
	    val = PyString_FromString(elts[i].val);
	    PyDict_SetItemString(result, elts[i].key, val);
	    Py_DECREF(val);
	}

    return result;

    /* prevent compiler warning about unused 
       function, this statement never reached */
    table2dict(NULL);

}

/**
 ** python_dict_merge
 ** 
 *   Merges two Python dictionaries into one, overlaying
 *   items in the first argument by the second. Returns new
 *   reference.
 */

void python_dict_merge(PyObject *d1, PyObject *d2)
{

    /*
     * there are faster ways to do this if we were to bypas
     * the Python API and use functions from dictobject.c
     * directly
     */
    
    PyObject *items;
    PyObject *keyval;
    PyObject *x;
    PyObject *y;
    int i;

    items = PyDict_Items(d2);
    for (i = 0; i < PyList_Size(items); i++) {
	keyval = PyList_GetItem(items, i);
	x = PyTuple_GetItem(keyval, 0);
	y = PyTuple_GetItem(keyval, 1);
	PyDict_SetItem(d1, PyTuple_GetItem(keyval, 0),
		       PyTuple_GetItem(keyval, 1));
    }
    Py_DECREF(items);
}

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
    PyObject *obcallback = NULL;
    PyThreadState *tstate = NULL;
    PyObject *x;

    /* initialize serverobjecttype */
    PyTypeObject sot = {
	PyObject_HEAD_INIT(&PyType_Type)
	0,
	"server",
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

    /* initialize connobjecttype */
    PyTypeObject cot = {
	PyObject_HEAD_INIT(&PyType_Type)
	0,
	"conn",
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

    /* initialize requestobjecttype */
    PyTypeObject rot = {
	PyObject_HEAD_INIT(&PyType_Type)
	0,
	"request",
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

    /* initialize tableobjecttype */
    PyTypeObject tt = {
	PyObject_HEAD_INIT(&PyType_Type)
	0,
	"mptable",
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

    serverobjecttype = sot;
    connobjecttype = cot;
    requestobjecttype = rot;
    tableobjecttype = tt;

    /* mod_python version */
    ap_add_version_component(VERSION_COMPONENT);

    /* Python version */
    sprintf(buff, "Python/%s", strtok((char *)Py_GetVersion(), " "));
    ap_add_version_component(buff);

    /* initialize global Python interpreter if necessary */
    if (! Py_IsInitialized()) 
    {

	/* initialze the interpreter */
	Py_Initialize();
               

#ifdef WITH_THREAD
	/* create and acquire the interpreter lock */
	PyEval_InitThreads();         
#endif
	/* create the obCallBack dictionary */
	interpreters = PyDict_New();

	if (! interpreters)
	{
	    ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, s,
			 "python_init: PyDict_New() failed! No more memory?");
	    exit(1);
	}
	  
	/*  Initialize _apache. 
	 *  This makes an _apache module available for import, but remember,
	 *  the user should use "import apache" not "_apache". "_apache" 
	 *  is for internal use only. (The only time it's needed is to assign 
	 *  obCallBack)
	 */

	/* make obCallBack */
	obcallback = make_obcallback(NULL, NULL);

	/* get the current thread state */
	tstate = PyThreadState_Get();

	/* cast PyThreadState * to long and save it in obCallBack */
	x = PyInt_FromLong((long) tstate);
	PyObject_SetAttrString(obcallback, INTERP_ATTR, x);
	Py_DECREF(x);

	/* save the obCallBack */
	PyDict_SetItemString(interpreters, "global_interpreter", obcallback);

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
  char *s;

  if (ah == NULL)
    {
      Py_INCREF(Py_None);
      return Py_None;
    }
  else
    {
      t = PyTuple_New(ah->nelts);

      s = (char *) ah->elts;
      for (i = 0; i < ah->nelts; i++)
	PyTuple_SetItem(t, i, PyString_FromString(&s[i]));

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
 */

static const char *python_directive(cmd_parms *cmd, void * mconfig, 
				    char *key, const char *val)
{

    int directs_offset = XtOffsetOf(py_dir_config, directives);
    int dirs_offset = XtOffsetOf(py_dir_config, dirs);
    int config_dir_offset = XtOffsetOf(py_dir_config, config_dir);
    char *s;
    table *directives;
    table *dirs;

    directives = *(table **)(mconfig + directs_offset);
    dirs = *(table **)(mconfig + dirs_offset);

    ap_table_set(directives, ap_pstrdup(cmd->pool, key), 
		 ap_pstrdup(cmd->pool, val));

    /* remember the directory where the directive was found */
    s = *(char **)(mconfig + config_dir_offset);
    if (s) {
	ap_table_set(dirs, ap_pstrdup(cmd->pool, key), s);
    }
    else {
	ap_table_set(dirs, ap_pstrdup(cmd->pool, key), "");
    }

    return NULL;
}




/**
 ** make_obcallback
 **
 *      This function instantiates an obCallBack object. 
 *      NOTE: The obCallBack object is instantiated by Python
 *      code. This C module calls into Python code which sets the 
 *      reference by calling SetCallBack function back into C from
 *      Python. Thus the name "CallBack". 
 * 
 * Here is a visual:
 *
 * - Begin C code
 * .   PyRun_SimpleString("init()")
 * =   Begin Python code
 * .     obCallBack = CallBack()
 * .     import _apache # this module is in C
 * .     _apache.SetCallBack(obCallBack)
 * --    Begin C code
 * .       // assigns to global obCallBack
 * --    End of C code
 * =   End of Python code
 * - we're back in C, but now global obCallBack has a value
 */

PyObject * make_obcallback(const char *module, const char *initstring)
{

  char buff[256];

  /*  In the old verion of this module these varuables were assigned by
   *  PythonInitFunction directive, in the new version they'll be
   *  NULL and get assigned here.
   */

  if (! module)
    module = MODULENAME;

  if (! initstring)
    initstring = INITSTRING;

  /* This makes _apache appear imported, and subsequent
   * >>> import _apache 
   * will not give an error.
   */
  Py_InitModule("_apache", _apache_module_methods);

  /* Now execute the equivalent of
   * >>> import sys
   * >>> import <module>
   * >>> <initstring>
   * in the __main__ module to start up Python.
   */

  sprintf(buff, "import %s\n", module);

  if (PyRun_SimpleString(buff))
    {
      fprintf(stderr, "PythonInitFunction: could not import %s.\n", module);
      exit(1);
    }

  sprintf(buff, "%s\n", initstring);

  if (PyRun_SimpleString(buff))
    {
      fprintf(stderr, "PythonInitFunction: could not call %s.\n",
	       initstring);
      exit(1);
    }

  /* we can't see it, but the execution has moved into a Python script
   * which is doing something like this:
   *
   * >>> import _apache
   * >>> _apache.SetCallBack(someCallBackObject)
   *
   * By now (i.e while you're reading this comment), 
   * SetCallBack() has been called and obCallBack is assigned. 
   */

  if (! obCallBack) 
    {
      fprintf(stderr, "PythonInitFunction: after %s no callback object found.\n", 
	       initstring);
      exit(1);
    }

  /* Wow, this worked! */

  return obCallBack;

}

/**
 ** get_obcallback
 **
 *      We have a list of obCallBack's, one per each instance of
 *      interpreter we use.
 *
 *      This function gets an obCallBack instance:
 *      1. It checks if obCallBack with such name already exists
 *      2. If yes - return it
 *      3. If no - create one doing Python initialization
 *
 *      Lock must be acquired prior to entering this function.
 *      This function might make the resulting interpreter's state current,
 *      use PyThreadState_Swap to be sure.
 *
 *      name NULL means use global interpreter.
 */

PyObject * get_obcallback(const char *name, server_rec * server)
{

  PyObject * obcallback = NULL;
  PyThreadState * tstate = NULL;
  PyObject *p;

  if (! name)
    name = "global_interpreter";

  /* 
   * Note that this is somewhat of a hack because to store 
   * PyThreadState pointers in a Python object we are
   * casting PyThreadState * to an integer and back.
   *
   * The bad news is that one cannot cast a * to int on systems
   * where sizeof(void *) != sizeof(int). 
   *
   * The good news is that I don't know of any systems where
   * sizeof(void *) != sizeof(int) except for 16 bit DOS.
   *
   * The proper way to do this would be to write a separate
   * hashable Python type that contains a PyThreadState. At this
   * point it doesn't seem worth the trouble.
   */

  /* see if one exists by that name */
  obcallback = PyDict_GetItemString(interpreters, (char *) name);

  /* if obcallback is NULL at this point, no such interpeter exists */
  if (! obcallback) {

      /* create a new interpeter */
      tstate = Py_NewInterpreter();

      if (! tstate) {

	  /* couldn't create an interpreter, this is bad */
	  ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, server,
		       "get_obcallback: Py_NewInterpreter() returned NULL. No more memory?");
	  return NULL;
      }
      
      /* create an obCallBack */
      obcallback = make_obcallback(NULL, NULL);

      /* cast PyThreadState * to long and save it in obCallBack */
      p = PyInt_FromLong((long) tstate);
      PyObject_SetAttrString(obcallback, INTERP_ATTR, p);
      Py_DECREF(p);

      /* save the obCallBack */
      PyDict_SetItemString(interpreters, (char *)name, obcallback);
      
    }

  return  obcallback;

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
	ap_log_error(APLOG_MARK, level, serv_rec, message);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** SetCallBack - assign a CallBack object
 **
 *      This function must be called from Python upon executing
 *      the initstring parameter, like this
 *
 *       >>> import _apache
 *       >>> _apache.SetCallBack(instance)
 *
 *      to provide the instance as the CallBack object.
 */

static PyObject * SetCallBack(PyObject *self, PyObject *args)
{

    PyObject *callback;

    /* see if CallBack is in *args */
    if (! PyArg_ParseTuple(args, "O", &callback)) 
	return NULL;

    /* store the object, incref */
    obCallBack = callback;  
    Py_INCREF(obCallBack);

    /* return None */
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** get_request_object
 **
 *      This creates or retrieves a previously created request object 
 */

static void get_request_object(request_rec *req, requestobject **request_obj)

{

    char *s;
    char s2[40];

    /* see if there is a request object out there already */

    /* XXX there must be a cleaner way to do this, atoi is slow? */
    /* since tables only understand strings, we need to do some conversion */

    s = (char *) ap_table_get(req->notes, "python_request_ptr");
    if (s) {
	*request_obj = (requestobject *) atoi(s);
	/* we have one reference at creation that is shared, no INCREF here*/
	return;
    }
    else {
	/* ap_add_cgi_vars() is necessary for path-translated for example */
	/* ap_add_cgi_vars() sometimes recurses, so we temporarily release the lock */

	/* XXX - why do I need this? Still true as of ver 1.3.12.
	 * A trailing slash will make Apache call add_cgi_vars 
	 * recursively ad infinitum in some handlers. May be it's an Apache bug?
	 */
	if ((req->path_info) && 
	     (req->path_info[strlen(req->path_info) - 1] == '/'))
	{
	    int i;
	    i = strlen( req->path_info );
	    /* take out the slash */
	    req->path_info[ i - 1 ] = 0;

	    Py_BEGIN_ALLOW_THREADS;
	    ap_add_cgi_vars(req);
	    Py_END_ALLOW_THREADS;
	    *request_obj = make_requestobject(req);

	    /* put the slash back in */
	    req->path_info[ i - 1 ] = '/'; 
	    req->path_info[ i ] = 0;
	} 
	else 
	{ 
	    Py_BEGIN_ALLOW_THREADS;
	    ap_add_cgi_vars(req);
	    Py_END_ALLOW_THREADS;
	    *request_obj = make_requestobject(req);
	}

	/* store the pointer to this object in notes */
	sprintf(s2, "%d", (int) *request_obj);
	ap_table_set(req->notes, "python_request_ptr", s2);
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
    PyThreadState *tstate;
    PyObject *obcallback;
    requestobject *request_obj;
    const char *s;
    py_dir_config * conf;
    int result;
    const char * interpreter = NULL;

    /* get configuration */
    conf = (py_dir_config *) ap_get_module_config(req->per_dir_config, &python_module);
  
    /* is there a handler? */
    if (! ap_table_get(conf->directives, handler)) {
	return DECLINED;
    }

    /* determine interpreter to use */
    if ((s = ap_table_get(conf->directives, "PythonInterpreter"))) {
	/* forced by configuration */
	interpreter = s;
    }
    else {
	if (single_mode)
	    interpreter = NULL;
	else {
	    if ((s = ap_table_get(conf->directives, "PythonInterpPerDirectory"))) {
		/* base interpreter on directory where the file is found */
		if (ap_is_directory(req->filename))
		    interpreter = ap_make_dirstr_parent(req->pool, 
				 ap_pstrcat(req->pool, req->filename, "/", NULL ));
		else
		    interpreter = ap_make_dirstr_parent(req->pool, req->filename);
	    }
	    else {
		/* - default -
		 * base interpreter name on directory where the handler directive
		 * was last found. If it was in http.conf, then we will use the 
		 * global interpreter.
		 */
		s = ap_table_get(conf->dirs, handler);
		if (strcmp(s, "") == 0)
		    interpreter = NULL;
		else
		    interpreter = s;
	    }
	}
    }

#ifdef WITH_THREAD  
    /* acquire lock */
    PyEval_AcquireLock();
#endif

    /* get/create obcallback */
    obcallback = get_obcallback(interpreter, req->server);

    /* we must have a callback object to succeed! */
    if (!obcallback) 
    {
	ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, req->server,
		     "python_handler: get_obcallback returned no obCallBack!");
	return HTTP_INTERNAL_SERVER_ERROR;
    }

    /* find __interpreter__ in obCallBack */
    tstate = (PyThreadState *) PyInt_AsLong(PyObject_GetAttrString(obcallback, INTERP_ATTR));

    /* make this thread state current */
    PyThreadState_Swap(tstate);

    /* create/acquire request object */
    get_request_object(req, &request_obj);

    /* 
     * The current directory will be that of the last encountered 
     * Python*Handler directive. If the directive was in httpd.conf,
     * then the directory is null, and cwd could be anything (most
     * likely serverroot).
     */
    if ((s = ap_table_get(conf->dirs, handler)))
	chdir(s);
    /* 
     * Here is where we call into Python!
     * This is the C equivalent of
     * >>> resultobject = obCallBack.Dispatch(request_object, handler)
     */

    resultobject = PyObject_CallMethod(obcallback, "Dispatch", "Os", request_obj, handler);

#ifdef WITH_THREAD
    /* release the lock */
    PyEval_ReleaseLock();
#endif

    if (! resultobject) {
	ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, req->server, 
		     "python_handler: Dispatch() returned nothing.");
	return HTTP_INTERNAL_SERVER_ERROR;
    }
    else {
	/* Attempt to analyse the result as a string indicating which
	   result to return */
	if (! PyInt_Check(resultobject)) {
	    ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, req->server, 
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
static const char *directive_PythonDebug(cmd_parms *cmd, void *mconfig) {
    return python_directive(cmd, mconfig, "PythonDebug", "1");
}

/**
 ** directive_PythonInterpPerDirectory
 **
 *      This function called whenever PythonInterpPerDirectory directive
 *      is encountered.
 */

static const char *directive_PythonInterpPerDirectory(cmd_parms *cmd, 
						      void *mconfig) {
    return python_directive(cmd, mconfig, 
			    "PythonInterpPerDirectory", "");
}

/**
 ** directive_PythonNoReload
 **
 *      This function called whenever PythonNoReload directive
 *      is encountered.
 */
static const char *directive_PythonNoReload(cmd_parms *cmd, 
						      void *mconfig) {
    return python_directive(cmd, mconfig, 
			    "PythonNoReload", "");
}

/**
 ** directive_PythonOption
 **
 *       This function is called every time PythonOption directive
 *       is encountered. It sticks the option into a table containing
 *       a list of options. This table is part of the local config structure.
 */

static const char *directive_PythonOption(cmd_parms *cmd, void * mconfig, 
				       const char * key, const char * val)
{

    int offset = XtOffsetOf(py_dir_config, options);
    table * options;

    options = * (table **) (mconfig + offset);
    ap_table_set(options, key, val);

    return NULL;

}

/**
 ** Python*Handler directives
 **
 */

static const char *directive_PythonPostReadRequestHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonPostReadRequestHandler", val);
}
static const char *directive_PythonTransHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonTransHandler", val);
}
static const char *directive_PythonHeaderParserHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonHeaderParserHandler", val);
}
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
static const char *directive_PythonTypeHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonTypeHandler", val);
}
static const char *directive_PythonHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonHandler", val);
}
static const char *directive_PythonFixupHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonFixupHandler", val);
}
static const char *directive_PythonLogHandler(cmd_parms *cmd, void * mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonLogHandler", val);
}


/**
 ** Handlers
 **
 *  (In order, in which they get called by Apache)
 */

static int PythonPostReadRequestHandler(request_rec *req) {
    return python_handler(req, "PythonPostReadRequestHandler");
}
static int PythonTransHandler(request_rec *req) {
    return python_handler(req, "PythonTransHandler");
}
static int PythonHeaderParserHandler(request_rec *req) {
    return python_handler(req, "PythonHeaderParserHandler");
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
static int PythonTypeHandler(request_rec *req) {
    return python_handler(req, "PythonTypeHandler");
}
static int PythonHandler(request_rec *req) {
    return python_handler(req, "PythonHandler");
}
static int PythonFixupHandler(request_rec *req) {
    return python_handler(req, "PythonFixupHandler");
}
static int PythonLogHandler(request_rec *req) {
    return python_handler(req, "PythonLogHandler");
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
	"PythonPath",
	directive_PythonPath,
	NULL,
	OR_ALL,
	TAKE1,
	"Python path, specified in Python list syntax."
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
	"PythonInterpPerDirectory",                 
	directive_PythonInterpPerDirectory,         
	NULL,                                
	OR_ALL,                         
	NO_ARGS,                               
	"Create subinterpreters per directory rather than per directive."
    },
    {
	"PythonDebug",                 
	directive_PythonDebug,         
	NULL,                                
	OR_ALL,                         
	NO_ARGS,                               
	"Send (most) Python error output to the client rather than logfile."
    },
    {
	"PythonNoReload",                 
	directive_PythonNoReload,         
	NULL,                                
	OR_ALL,                         
	NO_ARGS,                               
	"Do not reload already imported modules if they changed."
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
	"PythonPostReadRequestHandler",
	directive_PythonPostReadRequestHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python post read-request handlers."
    },
    {
	"PythonTransHandler",
	directive_PythonTransHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python filename to URI translation handlers."
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
	"PythonTypeHandler",
	directive_PythonTypeHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python MIME type checker/setter handlers."
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
	"PythonFixupHandler",
	directive_PythonFixupHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python fixups handlers."
    },
    {
	"PythonLogHandler",
	directive_PythonLogHandler,
	NULL,
	OR_ALL,
	RAW_ARGS,
	"Python logger handlers."
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
 PyVERSION=`python1.5 -c "import sys; print sys.version[:3]"`
 PyEXEC_INSTALLDIR=`python1.5 -c "import sys; print sys.exec_prefix"`
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
  NULL,                          /* process initializer */
  NULL,                          /* process exit/cleanup */
  PythonPostReadRequestHandler   /* [1] post read_request handling */
};

/******************************************************************
 * LE FIN
 ******************************************************************/








