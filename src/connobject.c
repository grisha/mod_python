/* ====================================================================
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
 * 3. The end-user documentation included with the redistribution, if
 *    any, must include the following acknowledgment: "This product 
 *    includes software developed by Gregory Trubetskoy."
 *    Alternately, this acknowledgment may appear in the software itself, 
 *    if and wherever such third-party acknowledgments normally appear.
 *
 * 4. The names "mod_python", "modpython" or "Gregory Trubetskoy" must not 
 *    be used to endorse or promote products derived from this software 
 *    without prior written permission. For written permission, please 
 *    contact grisha@modpython.org.
 *
 * 5. Products derived from this software may not be called "mod_python"
 *    or "modpython", nor may "mod_python" or "modpython" appear in their 
 *    names without prior written permission of Gregory Trubetskoy.
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
 * connobject.c 
 *
 * $Id: connobject.c,v 1.7 2001/08/18 22:43:45 gtrubetskoy Exp $
 *
 */

/*
 * This is a mapping of a Python object to an Apache conn_rec.
 *
 */

#include "mod_python.h"

/**
 **     MpConn_FromConn
 **
 *      This routine creates a Python connobject given an Apache
 *      conn_rec pointer.
 *
 */

PyObject * MpConn_FromConn(conn_rec *c)
{
    connobject *result;

    result = PyMem_NEW(connobject, 1);
    if (! result)
	return PyErr_NoMemory();

    result->conn = c;
    result->ob_type = &MpConn_Type;
    result->server = NULL;
    result->base_server = NULL;
    result->notes = MpTable_FromTable(c->notes);

    _Py_NewReference(result);
    return (PyObject *)result;
}


#define OFF(x) offsetof(conn_rec, x)

static struct memberlist conn_memberlist[] = {
    {"base_server",        T_OBJECT,    0,                       RO},
    /* XXX vhost_lookup_data? */
    /* XXX client_socket? */
    {"local_addr",         T_OBJECT,    0,                       RO},
    {"remote_addr",        T_OBJECT,    0,                       RO},
    {"remote_ip",          T_STRING,    OFF(remote_ip),          RO},
    {"remote_host",        T_STRING,    OFF(remote_host),        RO},
    {"remote_logname",     T_STRING,    OFF(remote_logname),     RO},
    {"aborted",            T_INT,       0,                       RO},
    {"keepalive",          T_INT,       0,                       RO},
    {"double_reverse",     T_INT,       0,                       RO},
    {"keepalives",         T_INT,       OFF(keepalives),         RO},
    {"local_ip",           T_STRING,    OFF(remote_ip),          RO},
    {"local_host",         T_STRING,    OFF(remote_host),        RO},
    {"id",                 T_LONG,      OFF(id),                 RO},
    /* XXX conn_config? */
    {"notes",              T_OBJECT,    0,                       RO},
    /* XXX filters ? */
    /* XXX document remain */
    //{"remain",             T_LONG,      OFF(remain),             RO},
    {NULL}  /* Sentinel */
};

/**
 ** conn_dealloc
 **
 *
 */

static void conn_dealloc(connobject *self)
{  
    Py_XDECREF(self->server);
    Py_XDECREF(self->base_server);
    Py_XDECREF(self->notes);
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

    if (strcmp(name, "base_server") == 0) {

	/* base_server serverobject is created as needed */
	if (self->base_server == NULL) {
	    if (self->conn->base_server == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		self->base_server = MpServer_FromServer(self->conn->base_server);
		Py_INCREF(self->base_server);
		return self->base_server;
	    }
	}
	else {
	    Py_INCREF(self->base_server);
	    return self->base_server;
	}
    }
    else if (strcmp(name, "aborted") == 0) {
	return PyInt_FromLong(self->conn->aborted);
    }
    else if (strcmp(name, "keepalive") == 0) {
	return PyInt_FromLong(self->conn->keepalive);
    }
    else if (strcmp(name, "double_reverse") == 0) {
	return PyInt_FromLong(self->conn->double_reverse);
    }
    else if (strcmp(name, "remote_addr") == 0) {
	/* XXX this needs to be compatible with apr_sockaddr_t */
	return makesockaddr(&(self->conn->remote_addr));
    }
    else if (strcmp(name, "notes") == 0) {
	Py_INCREF(self->notes);
	return (PyObject *) self->notes;
    }
    else
	return PyMember_Get((char *)self->conn, conn_memberlist, name);

}

/**
 ** conn_setattr
 **
 *  Set connection object attribute
 */

static int conn_setattr(connobject *self, char* name, PyObject* value)
{

    if (value == NULL) {
	PyErr_SetString(PyExc_AttributeError,
			"can't delete connection attributes");
	return -1;
    }
    else
	return PyMember_Set((char *)self->conn, conn_memberlist, name, value);

}

PyTypeObject MpConn_Type = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_conn",
    sizeof(connobject),
    0,
    (destructor) conn_dealloc,       /*tp_dealloc*/
    0,                               /*tp_print*/
    (getattrfunc) conn_getattr,      /*tp_getattr*/
    (setattrfunc) conn_setattr,      /*tp_setattr*/
    0,                               /*tp_compare*/
    0,                               /*tp_repr*/
    0,                               /*tp_as_number*/
    0,                               /*tp_as_sequence*/
    0,                               /*tp_as_mapping*/
    0,                               /*tp_hash*/
};


