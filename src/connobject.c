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
 * connobject.c 
 *
 * $Id: connobject.c,v 1.10 2002/09/12 18:24:06 gstein Exp $
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
    result->hlo = NULL;

    _Py_NewReference(result);
    return (PyObject *)result;
}

/**
 ** conn.read(conn self, int bytes)
 **
 */

static PyObject * _conn_read(conn_rec *c, ap_input_mode_t mode, long len)
{

    apr_bucket *b;
    apr_bucket_brigade *bb;
    apr_status_t rc;
    long bytes_read;
    PyObject *result;
    char *buffer;
    long bufsize;

    bb = apr_brigade_create(c->pool, c->bucket_alloc);

    Py_BEGIN_ALLOW_THREADS;
    rc = ap_get_brigade(c->input_filters, bb, mode, APR_BLOCK_READ, len);
    Py_END_ALLOW_THREADS;

    if (! APR_STATUS_IS_SUCCESS(rc)) {
        PyErr_SetObject(PyExc_IOError, 
                        PyString_FromString("Connection read error"));
        return NULL;
    }

    /* 
     * loop through the brigade reading buckets into the string 
     */

    b = APR_BRIGADE_FIRST(bb);

    if (APR_BUCKET_IS_EOS(b)) { 
        apr_bucket_delete(b);
	Py_INCREF(Py_None);
        return Py_None;
    }

    bufsize = len == 0 ? HUGE_STRING_LEN : len;
    result = PyString_FromStringAndSize(NULL, bufsize);

    /* possibly no more memory */
    if (result == NULL) 
        return PyErr_NoMemory();
    
    buffer = PyString_AS_STRING((PyStringObject *) result);

    bytes_read = 0;

    while ((bytes_read < len || len == 0) &&
           !(b == APR_BRIGADE_SENTINEL(b) ||
             APR_BUCKET_IS_EOS(b) || APR_BUCKET_IS_FLUSH(b))) {

	const char *data;
	apr_size_t size;
	apr_bucket *old;

	if (apr_bucket_read(b, &data, &size, APR_BLOCK_READ) != APR_SUCCESS) {
	    PyErr_SetObject(PyExc_IOError, 
			    PyString_FromString("Connection read error"));
	    return NULL;
	}

	if (bytes_read + size > bufsize) {
	    apr_bucket_split(b, bufsize - bytes_read);
	    size = bufsize - bytes_read;
	    /* now the bucket is the exact size we need */
	}

	memcpy(buffer, data, size);
	buffer += size;
	bytes_read += size;

	/* time to grow destination string? */
	if (len == 0 && bytes_read == bufsize) {

	    _PyString_Resize(&result, bufsize + HUGE_STRING_LEN);
	    buffer = PyString_AS_STRING((PyStringObject *) result);
	    buffer += HUGE_STRING_LEN;
	    bufsize += HUGE_STRING_LEN;
	}


        if (mode == AP_MODE_GETLINE) {
            apr_bucket_delete(b);
            break;
        }

	old = b;
	b = APR_BUCKET_NEXT(b);
	apr_bucket_delete(old);
    }

    /* resize if necessary */
    if (bytes_read < len || len == 0) 
	if(_PyString_Resize(&result, bytes_read))
	    return NULL;

    return result;
}

/**
 ** conn.read(conn self, int bytes)
 **
 */

static PyObject * conn_read(connobject *self, PyObject *args)
{

    long len = 0;

    if (! PyArg_ParseTuple(args, "l|i", &len)) 
        return NULL;

    if (len == 0)
        return PyString_FromString("");

    if (len == -1)
        return _conn_read(self->conn, AP_MODE_EXHAUSTIVE, 0);
    else
        return _conn_read(self->conn, AP_MODE_READBYTES, len);
}

/**
 ** conn.readline(conn self, int bytes)
 **
 */

static PyObject * conn_readline(connobject *self, PyObject *args)
{

    long len = 0;

    if (! PyArg_ParseTuple(args, "|l", &len)) 
        return NULL;

    return _conn_read(self->conn, AP_MODE_GETLINE, len);
}

/**
 ** conn.write(conn self, int bytes)
 **
 */

static PyObject * conn_write(connobject *self, PyObject *args)
{
    char *buff;
    int len;
    apr_bucket_brigade *bb;
    apr_bucket *b;
    PyObject *s;
    conn_rec *c = self->conn;

    if (! PyArg_ParseTuple(args, "O", &s)) 
	return NULL;

    if (! PyString_Check(s)) {
	PyErr_SetString(PyExc_TypeError, "Argument to write() must be a string");
	return NULL;
    }

    len = PyString_Size(s);

    if (len) {
	buff = apr_pmemdup(c->pool, PyString_AS_STRING(s), len);

        bb = apr_brigade_create(c->pool, c->bucket_alloc);

	b = apr_bucket_pool_create(buff, len, c->pool, c->bucket_alloc);
	APR_BRIGADE_INSERT_TAIL(bb, b);

        /* Make sure the data is flushed to the client */
        b = apr_bucket_flush_create(c->bucket_alloc);
        APR_BRIGADE_INSERT_TAIL(bb, b);

        ap_pass_brigade(c->output_filters, bb);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef connobjectmethods[] = {
    {"read",      (PyCFunction) conn_read,      METH_VARARGS},
    {"readline",  (PyCFunction) conn_readline,  METH_VARARGS},
    {"write",     (PyCFunction) conn_write,     METH_VARARGS},
    { NULL, NULL } /* sentinel */
};

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
    Py_XDECREF(self->hlo);
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

    PyObject *res;

    res = Py_FindMethod(connobjectmethods, (PyObject *)self, name);
    if (res != NULL)
	return res;
    
    PyErr_Clear();

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
    else if (strcmp(name, "hlist") == 0) {
        Py_INCREF(self->hlo);
        return self->hlo;
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


