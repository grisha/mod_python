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
 * connobject.c 
 *
 * $Id: connobject.c,v 1.1 2000/10/16 20:58:57 gtrubetskoy Exp $
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

    _Py_NewReference(result);
    return (PyObject *)result;
}


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
		self->server = MpServer_FromServer(self->conn->server);
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
    else if (strcmp(name, "local_addr") == 0) {
	return makesockaddr(&(self->conn->local_addr));
    }
    else if (strcmp(name, "remote_addr") == 0) {
	return makesockaddr(&(self->conn->remote_addr));
    }
    else
	return PyMember_Get((char *)self->conn, conn_memberlist, name);

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
    0,                               /*tp_setattr*/
    0,                               /*tp_compare*/
    0,                               /*tp_repr*/
    0,                               /*tp_as_number*/
    0,                               /*tp_as_sequence*/
    0,                               /*tp_as_mapping*/
    0,                               /*tp_hash*/
};


