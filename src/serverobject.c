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
 * serverobject.c 
 *
 * $Id: serverobject.c,v 1.1 2000/10/16 20:58:57 gtrubetskoy Exp $
 *
 */

#include "mod_python.h"


/**
 **     MpServer_FromServer
 **
 *      This routine creates a Python serverobject given an Apache
 *      server_rec pointer.
 *
 */

PyObject * MpServer_FromServer(server_rec *s)
{
    serverobject *result;

    result = PyMem_NEW(serverobject, 1);
    if (! result)
	return PyErr_NoMemory();

    result->server = s;
    result->ob_type = &MpServer_Type;
    result->next = NULL;

    _Py_NewReference(result);
    return (PyObject *)result;
}

/**
 ** server.register_cleanup(handler, data)
 **
 *    same as request.register_cleanup, except the server pool is used.
 *    the server pool gets destroyed before the child dies or when the
 *    whole process dies in multithreaded situations.
 */

static PyObject *server_register_cleanup(serverobject *self, PyObject *args)
{

    cleanup_info *ci;
    PyObject *handler = NULL;
    PyObject *data = NULL;
    requestobject *req = NULL;

    if (! PyArg_ParseTuple(args, "OO|O", &req, &handler, &data))
	return NULL; 

    if (! MpRequest_Check(req)) {
	PyErr_SetString(PyExc_ValueError, "first argument must be a request object");
	return NULL;
    }
    else if(!PyCallable_Check(handler)) {
	PyErr_SetString(PyExc_ValueError, 
			"second argument must be a callable object");
	return NULL;
    }
    
    ci = (cleanup_info *)malloc(sizeof(cleanup_info));
    ci->request_rec = NULL;
    ci->server_rec = self->server;
    Py_INCREF(handler);
    ci->handler = handler;
    ci->interpreter = ap_table_get(req->request_rec->notes, "python_interpreter");
    if (data) {
	Py_INCREF(data);
	ci->data = data;
    }
    else {
	Py_INCREF(Py_None);
	ci->data = Py_None;
    }
    
    ap_register_cleanup(child_init_pool, ci, python_cleanup, 
			ap_null_cleanup);
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef serverobjectmethods[] = {
    {"register_cleanup",     (PyCFunction) server_register_cleanup,  METH_VARARGS},
    { NULL, NULL } /* sentinel */
};

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

    PyObject *res;

    res = Py_FindMethod(serverobjectmethods, (PyObject *)self, name);
    if (res != NULL)
	return res;
    
    PyErr_Clear();

    if (strcmp(name, "next") == 0)
	/* server.next serverobject is created as needed */
	if (self->next == NULL) {
	    if (self->server->next == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->next = MpServer_FromServer(self->server->next);
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

PyTypeObject MpServer_Type = {
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




