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
 * connobject.c
 *
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

    result = PyObject_New(connobject, &MpConn_Type);
    if (! result)
        return PyErr_NoMemory();

    result->conn = c;
    result->base_server = NULL;
    result->notes = MpTable_FromTable(c->notes);
    result->hlo = NULL;

    return (PyObject *)result;
}

/**
 ** conn.log_error(conn self, string message, int level)
 **
 *     calls ap_log_cerror
 */

static PyObject * conn_log_error(connobject *self, PyObject *args)
{
    int level = 0;
    char *message = NULL;

    if (! PyArg_ParseTuple(args, "z|i", &message, &level))
        return NULL; /* error */

    if (message) {

        if (! level)
            level = APLOG_ERR;

        Py_BEGIN_ALLOW_THREADS
#if AP_MODULE_MAGIC_AT_LEAST(20020903,10)
        ap_log_cerror(APLOG_MARK, level, 0, self->conn, "%s", message);
#else
        ap_log_error(APLOG_MARK, level, 0, self->conn->base_server, "%s", message);
#endif
        Py_END_ALLOW_THREADS
    }

    Py_INCREF(Py_None);
    return Py_None;
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

    bufsize = len == 0 ? HUGE_STRING_LEN : len;

    while (APR_BRIGADE_EMPTY(bb)) {
        Py_BEGIN_ALLOW_THREADS;
        rc = ap_get_brigade(c->input_filters, bb, mode, APR_BLOCK_READ, bufsize);
        Py_END_ALLOW_THREADS;

        if (rc != APR_SUCCESS) {
            PyErr_SetString(PyExc_IOError, "Connection read error");
            return NULL;
        }
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

    result = PyBytes_FromStringAndSize(NULL, bufsize);

    /* possibly no more memory */
    if (result == NULL)
        return PyErr_NoMemory();

    buffer = PyBytes_AS_STRING((PyBytesObject *) result);

    bytes_read = 0;

    while ((bytes_read < len || len == 0) &&
           !(b == APR_BRIGADE_SENTINEL(bb) ||
             APR_BUCKET_IS_EOS(b) || APR_BUCKET_IS_FLUSH(b))) {

        const char *data;
        apr_size_t size;
        apr_bucket *old;

        if (apr_bucket_read(b, &data, &size, APR_BLOCK_READ) != APR_SUCCESS) {
            PyErr_SetString(PyExc_IOError, "Connection read error");
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

            _PyBytes_Resize(&result, bufsize + HUGE_STRING_LEN);
            buffer = PyBytes_AS_STRING((PyBytesObject *) result);
            buffer += bufsize;
            bufsize += HUGE_STRING_LEN;
        }


        if (mode == AP_MODE_GETLINE || len == 0) {
            apr_bucket_delete(b);
            break;
        }

        old = b;
        b = APR_BUCKET_NEXT(b);
        apr_bucket_delete(old);
    }

    /* resize if necessary */
    if (bytes_read < len || len == 0)
        if(_PyBytes_Resize(&result, bytes_read))
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

    if (! PyArg_ParseTuple(args, "|l", &len))
        return NULL;

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
    Py_ssize_t len;
    apr_bucket_brigade *bb;
    apr_bucket *b;
    PyObject *s;
    conn_rec *c = self->conn;

    if (! PyArg_ParseTuple(args, "s#", &buff, &len))
        return NULL;  /* bad args */

    if (len) {
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
    {"log_error", (PyCFunction) conn_log_error, METH_VARARGS},
    {"read",      (PyCFunction) conn_read,      METH_VARARGS},
    {"readline",  (PyCFunction) conn_readline,  METH_VARARGS},
    {"write",     (PyCFunction) conn_write,     METH_VARARGS},
    { NULL, NULL } /* sentinel */
};

#define OFF(x) offsetof(conn_rec, x)

static PyMemberDef conn_memberlist[] = {
    {"base_server",        T_OBJECT,    0,                       READONLY},
    /* XXX vhost_lookup_data? */
    /* XXX client_socket? */
    {"local_addr",         T_OBJECT,    0,                       READONLY},
#if AP_MODULE_MAGIC_AT_LEAST(20111130,0)
    {"client_addr",        T_OBJECT,    0,                       READONLY},
    {"client_ip",          T_STRING,    OFF(client_ip),          READONLY},
    {"remote_ip",          T_STRING,    OFF(client_ip),          READONLY}, /* bw compat */
#else
    {"remote_addr",        T_OBJECT,    0,                       READONLY},
    {"remote_ip",          T_STRING,    OFF(remote_ip),          READONLY},
#endif
    {"remote_host",        T_STRING,    OFF(remote_host),        READONLY},
    {"remote_logname",     T_STRING,    OFF(remote_logname),     READONLY},
    {"aborted",            T_INT,       0,                       READONLY},
    {"keepalive",          T_INT,       0,                       READONLY},
    {"double_reverse",     T_INT,       0,                       READONLY},
    {"keepalives",         T_INT,       OFF(keepalives),         READONLY},
    {"local_addr",         T_OBJECT,    0,                       READONLY},
    {"local_ip",           T_STRING,    OFF(local_ip),           READONLY},
    {"local_host",         T_STRING,    OFF(local_host),         READONLY},
    {"id",                 T_LONG,      OFF(id),                 READONLY},
    /* XXX conn_config? */
    {"notes",              T_OBJECT,    0,                       READONLY},
    /* XXX filters ? */
    /* XXX document remain */
    /*{"remain",             T_LONG,      OFF(remain),             READONLY},*/
    {NULL}  /* Sentinel */
};

/**
 ** conn_dealloc
 **
 *
 */

static void conn_dealloc(connobject *self)
{
    Py_XDECREF(self->base_server);
    Py_XDECREF(self->notes);
    Py_XDECREF(self->hlo);
    PyObject_Del(self);
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

    PyMethodDef *ml = connobjectmethods;
    for (; ml->ml_name != NULL; ml++) {
        if (name[0] == ml->ml_name[0] &&
            strcmp(name+1, ml->ml_name+1) == 0)
            return PyCFunction_New(ml, (PyObject*)self);
    }

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
        return PyLong_FromLong(self->conn->aborted);
    }
    else if (strcmp(name, "keepalive") == 0) {
        return PyLong_FromLong(self->conn->keepalive);
    }
    else if (strcmp(name, "double_reverse") == 0) {
        return PyLong_FromLong(self->conn->double_reverse);
    }
    else if (strcmp(name, "local_addr") == 0) {
        return makesockaddr(self->conn->local_addr);
    }
#if AP_MODULE_MAGIC_AT_LEAST(20111130,0)
    else if (strcmp(name, "client_addr") == 0) {
        return makesockaddr(self->conn->client_addr);
    }
    else if (strcmp(name, "remote_addr") == 0) {
        ap_log_cerror(APLOG_MARK, APLOG_WARNING, 0, self->conn, "%s",
                      "mod_python: conn.remote_addr deprecated in 2.4, "
                      "use req.useragent_addr or conn.client_addr");
        return makesockaddr(self->conn->client_addr);
#else
    else if (strcmp(name, "remote_addr") == 0) {
        return makesockaddr(self->conn->remote_addr);
#endif
    }
    else if (strcmp(name, "notes") == 0) {
        Py_INCREF(self->notes);
        return (PyObject *) self->notes;
    }
    else if (strcmp(name, "hlist") == 0) {
        Py_INCREF(self->hlo);
        return (PyObject *)self->hlo;
    }
    else if (strcmp(name, "_conn_rec") == 0) {
#if PY_MAJOR_VERSION == 2 && PY_MINOR_VERSION < 7
        return PyCObject_FromVoidPtr(self->conn, 0);
#else
        return PyCapsule_New((void *)self->conn, NULL, NULL);
#endif
    }
    else {

#if AP_MODULE_MAGIC_AT_LEAST(20111130,0)
        if (strcmp(name, "remote_ip") == 0) {
            ap_log_cerror(APLOG_MARK, APLOG_WARNING, 0, self->conn, "%s",
                          "mod_python: conn.remote_ip deprecated in 2.4, "
                          "use req.useragent_ip or conn.client_ip");
        }
#endif
        PyMemberDef *md = find_memberdef(conn_memberlist, name);
        if (!md) {
            PyErr_SetString(PyExc_AttributeError, name);
            return NULL;
        }
        return PyMember_GetOne((char*)self->conn, md);
    }
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
    else if (strcmp(name, "keepalive") == 0) {
        if (! PyLong_Check(value)) {
            PyErr_SetString(PyExc_TypeError, "keepalive must be a integer");
            return -1;
        }
        self->conn->keepalive = PyLong_AsLong(value);
        return 0;
    }
    else {
        PyMemberDef *md = find_memberdef(conn_memberlist, name);
        if (!md) {
            PyErr_SetString(PyExc_AttributeError, name);
            return -1;
        }
        return PyMember_SetOne((char*)self->conn, md, value);
    }
}

PyTypeObject MpConn_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "mp_conn",                       /* tp_name */
    sizeof(connobject),              /* tp_basicsize */
    0,                               /* tp_itemsize */
    (destructor) conn_dealloc,       /* tp_dealloc*/
    0,                               /* tp_print*/
    (getattrfunc) conn_getattr,      /* tp_getattr*/
    (setattrfunc) conn_setattr,      /* tp_setattr*/
    0,                               /* tp_compare*/
    0,                               /* tp_repr*/
    0,                               /* tp_as_number*/
    0,                               /* tp_as_sequence*/
    0,                               /* tp_as_mapping*/
    0,                               /* tp_hash*/
};


