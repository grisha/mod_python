/* ====================================================================
 * The Apache Software License, Version 1.1
 *
 * Copyright (c) 2001-2002 The Apache Software Foundation.  All rights
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
 * Originally developed by Gregory Trubetskoy.
 *
 *
 * filterobject.c 
 *
 * $Id: filterobject.c,v 1.19 2003/01/18 03:43:07 grisha Exp $
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

#include "mod_python.h"

/**
 **     MpFilter_FromFilter
 **
 *      This routine creates a Python filerobject.
 *
 */

PyObject *MpFilter_FromFilter(ap_filter_t *f, apr_bucket_brigade *bb, int is_input,
			      ap_input_mode_t mode, apr_size_t readbytes,
			      char * handler, char *dir)
{
    filterobject *result;

    result = PyMem_NEW(filterobject, 1);
    if (! result)
	return PyErr_NoMemory();

    result->f = f;
    result->ob_type = &MpFilter_Type;
    result->is_input = is_input;

    result->rc = APR_SUCCESS;

    if (is_input) {
	result->bb_in = NULL;
	result->bb_out = bb;
	result->mode = mode;
	result->readbytes = readbytes;
    }
    else {
	result->bb_in = bb;
	result->bb_out = NULL;
	result->mode = 0;
	result->readbytes = 0;
    }

    result->closed = 0;
    result->softspace = 0;

    result->handler = handler;
    result->dir = dir;

    result->request_obj = NULL; 

    _Py_NewReference(result);
    apr_pool_cleanup_register(f->r->pool, (PyObject *)result, python_decref, 
			      apr_pool_cleanup_null);

    return (PyObject *)result;
}

/**
 ** filter_pass_on
 **
 *     just passes everything on
 */

static PyObject *filter_pass_on(filterobject *self)
{

    Py_BEGIN_ALLOW_THREADS;

    if (self->is_input) 
        self->rc = ap_get_brigade(self->f->next, self->bb_out, 
                                  self->mode, APR_BLOCK_READ, 
                                  self->readbytes);
    else
        self->rc = ap_pass_brigade(self->f->next, self->bb_in);

    Py_END_ALLOW_THREADS;

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** _filter_read
 **
 *     read from filter - works for both read() and readline()
 */

static PyObject *_filter_read(filterobject *self, PyObject *args, int readline)
{

    apr_bucket *b;
    long bytes_read;
    PyObject *result;
    char *buffer;
    long bufsize;
    int newline = 0;
    long len = -1;
    conn_rec *c = self->request_obj->request_rec->connection;

    if (! PyArg_ParseTuple(args, "|l", &len)) 
	return NULL;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "I/O operation on closed filter");
        return NULL;
    }

    if (self->is_input) {

	/* does the output brigade exist? */
	if (!self->bb_in) {
	    self->bb_in = apr_brigade_create(self->f->r->pool, 
					     c->bucket_alloc);
	}

	Py_BEGIN_ALLOW_THREADS;
	self->rc = ap_get_brigade(self->f->next, self->bb_in, self->mode, 
				  APR_BLOCK_READ, self->readbytes);
	Py_END_ALLOW_THREADS;

	if (! APR_STATUS_IS_SUCCESS(self->rc)) {
	    PyErr_SetObject(PyExc_IOError, 
			    PyString_FromString("Input filter read error"));
	    return NULL;
	}
    }

    /* 
     * loop through the brigade reading buckets into the string 
     */

    b = APR_BRIGADE_FIRST(self->bb_in);

    if (b == APR_BRIGADE_SENTINEL(self->bb_in))
        return PyString_FromString("");

    /* reached eos ? */
    if (APR_BUCKET_IS_EOS(b)) {
        apr_bucket_delete(b);
        Py_INCREF(Py_None);
        return Py_None;
    }

    bufsize = len < 0 ? HUGE_STRING_LEN : len;
    result = PyString_FromStringAndSize(NULL, bufsize);

    /* possibly no more memory */
    if (result == NULL) 
        return PyErr_NoMemory();
    
    buffer = PyString_AS_STRING((PyStringObject *) result);

    bytes_read = 0;

    while ((bytes_read < len || len == -1) && 
           !(APR_BUCKET_IS_EOS(b) || APR_BUCKET_IS_FLUSH(b) ||
             b == APR_BRIGADE_SENTINEL(self->bb_in))) {

	const char *data;
	apr_size_t size;
	apr_bucket *old;
	int i;

	if (apr_bucket_read(b, &data, &size, APR_BLOCK_READ) != APR_SUCCESS) {
	    PyErr_SetObject(PyExc_IOError, 
			    PyString_FromString("Filter read error"));
	    return NULL;
	}

	if (bytes_read + size > bufsize) {
	    apr_bucket_split(b, bufsize - bytes_read);
	    size = bufsize - bytes_read;
	    /* now the bucket is the exact size we need */
	}

	if (readline) {

	    /* scan for newline */
	    for (i=0; i<size; i++) {
		if (data[i] == '\n') {
                    if (i+1 != size) {   /* (no need to split if we're at end of bucket) */
                        
                        /* split after newline */
                        apr_bucket_split(b, i+1);   
                        size = i + 1;
                    }
                    newline = 1;
		    break;
		}
	    }
	}

	memcpy(buffer, data, size);
	buffer += size;
	bytes_read += size;

	/* time to grow destination string? */
	if (newline == 0 && len < 0 && bytes_read == bufsize) {

	    _PyString_Resize(&result, bufsize + HUGE_STRING_LEN);
	    buffer = PyString_AS_STRING((PyStringObject *) result);
	    buffer += HUGE_STRING_LEN;

	    bufsize += HUGE_STRING_LEN;
	}

	if (readline && newline) {
            apr_bucket_delete(b);
	    break;
        }

	old = b;
	b = APR_BUCKET_NEXT(b);
	apr_bucket_delete(old);
	
	if (self->is_input) {

	    if (b == APR_BRIGADE_SENTINEL(self->bb_in)) {
		/* brigade ended, but no EOS - get another
		   brigade */

		Py_BEGIN_ALLOW_THREADS;
		self->rc = ap_get_brigade(self->f->next, self->bb_in, self->mode, 
					  APR_BLOCK_READ, self->readbytes);
		Py_END_ALLOW_THREADS;

		if (! APR_STATUS_IS_SUCCESS(self->rc)) {
		    PyErr_SetObject(PyExc_IOError, 
				    PyString_FromString("Input filter read error"));
		    return NULL;
		}
		b = APR_BRIGADE_FIRST(self->bb_in);
	    }
	}
    }

    /* resize if necessary */
    if (bytes_read < len || len < 0) 
	if(_PyString_Resize(&result, bytes_read))
	    return NULL;

    return result;
}

/**
 ** filter.read(filter self, int bytes)
 **
 *     Reads from previous filter
 */

static PyObject *filter_read(filterobject *self, PyObject *args)
{
    return _filter_read(self, args, 0);
}

/**
 ** filter.readline(filter self, int bytes)
 **
 *     Reads a line from previous filter
 */

static PyObject *filter_readline(filterobject *self, PyObject *args)
{
    return _filter_read(self, args, 1);
}


/**
 ** filter.write(filter self)
 **
 *     Write to next filter
 */

static PyObject *filter_write(filterobject *self, PyObject *args)
{

    char *buff;
    int len;
    apr_bucket *b;
    PyObject *s;
    conn_rec *c = self->request_obj->request_rec->connection;

    if (! PyArg_ParseTuple(args, "O", &s)) 
	return NULL;

    if (! PyString_Check(s)) {
	PyErr_SetString(PyExc_TypeError, "Argument to write() must be a string");
	return NULL;
    }

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "I/O operation on closed filter");
        return NULL;
    }

    len = PyString_Size(s);

    if (len) {

	/* does the output brigade exist? */
	if (!self->bb_out) {
	    self->bb_out = apr_brigade_create(self->f->r->pool, 
					      c->bucket_alloc);
	}
	
        buff = apr_bucket_alloc(len, c->bucket_alloc);
        memcpy(buff, PyString_AS_STRING(s), len);

        b = apr_bucket_heap_create(buff, len, apr_bucket_free,
                                   c->bucket_alloc);

	APR_BRIGADE_INSERT_TAIL(self->bb_out, b);

    }

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** filter.flush(filter self)
 **
 *     Flush output (i.e. pass brigade)
 */

static PyObject *filter_flush(filterobject *self, PyObject *args)
{

    conn_rec *c = self->request_obj->request_rec->connection;

    /* does the output brigade exist? */
    if (!self->bb_out) {
	self->bb_out = apr_brigade_create(self->f->r->pool,
					  c->bucket_alloc);
    }

    APR_BRIGADE_INSERT_TAIL(self->bb_out, 
			    apr_bucket_flush_create(c->bucket_alloc));

    Py_BEGIN_ALLOW_THREADS;
    self->rc = ap_pass_brigade(self->f->next, self->bb_out);
    apr_brigade_destroy(self->bb_out);
    Py_END_ALLOW_THREADS;

    if(self->rc != APR_SUCCESS) { 
	PyErr_SetString(PyExc_IOError, "Flush failed.");
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;

}

/**
 ** filter.close(filter self)
 **
 *     passes EOS 
 */

static PyObject *filter_close(filterobject *self, PyObject *args)
{

    conn_rec *c = self->request_obj->request_rec->connection;

    if (! self->closed) {

        /* does the output brigade exist? */
        if (!self->bb_out) {
            self->bb_out = apr_brigade_create(self->f->r->pool,
                                              c->bucket_alloc);
        }

        APR_BRIGADE_INSERT_TAIL(self->bb_out, 
                                apr_bucket_eos_create(c->bucket_alloc));
	
        if (! self->is_input) {
            Py_BEGIN_ALLOW_THREADS;
            self->rc = ap_pass_brigade(self->f->next, self->bb_out);
            Py_END_ALLOW_THREADS;
            self->bb_out = NULL;
        }

	self->closed = 1;
    }

    Py_INCREF(Py_None);
    return Py_None;
    
}

/**
 ** filter.disable(filter self)
 **
 *     Sets the transparent flag on causeing the filter_handler to
 *     just pass the data through without envoking Python at all.
 *     This is used during filter error output. 
 */

static PyObject *filter_disable(filterobject *self, PyObject *args)
{

    python_filter_ctx *ctx;

    ctx = (python_filter_ctx *) self->f->ctx;
    ctx->transparent = 1;

    Py_INCREF(Py_None);
    return Py_None;

}

static PyMethodDef filterobjectmethods[] = {
    {"pass_on",   (PyCFunction) filter_pass_on,   METH_NOARGS},
    {"read",      (PyCFunction) filter_read,      METH_VARARGS},
    {"readline",  (PyCFunction) filter_readline,  METH_VARARGS},
    {"write",     (PyCFunction) filter_write,     METH_VARARGS},
    {"flush",     (PyCFunction) filter_flush,     METH_VARARGS},
    {"close",     (PyCFunction) filter_close,     METH_VARARGS},
    {"disable",   (PyCFunction) filter_disable,   METH_VARARGS},
    {NULL, NULL}
};

#define OFF(x) offsetof(filterobject, x)

static struct memberlist filter_memberlist[] = {
    {"softspace",          T_INT,       OFF(softspace),            },
    {"closed",             T_INT,       OFF(closed),             RO},
    {"name",               T_OBJECT,    0,                       RO},
    {"req",                T_OBJECT,    OFF(request_obj),          },
    {"is_input",           T_INT,       OFF(is_input),           RO},
    {"handler",            T_STRING,    OFF(handler),            RO},
    {"dir",                T_STRING,    OFF(dir),                RO},
    {NULL}  /* Sentinel */
};

/**
 ** filter_dealloc
 **
 *
 */

static void filter_dealloc(filterobject *self)
{  
    Py_XDECREF(self->request_obj);
    free(self);
}


/**
 ** filter_getattr
 **
 *  Get filter object attributes
 *
 *
 */

static PyObject * filter_getattr(filterobject *self, char *name)
{

    PyObject *res;

    res = Py_FindMethod(filterobjectmethods, (PyObject *)self, name);
    if (res != NULL)
	return res;
    
    PyErr_Clear();

    if (strcmp(name, "name") == 0) {
	if (! self->f->frec->name) {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
	else {
	    return PyString_FromString(self->f->frec->name);
	}
    } 
    else if (strcmp(name, "req") == 0) {
	if (! self->request_obj) {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
	else {
	    Py_INCREF(self->request_obj);
	    return (PyObject *)self->request_obj;
	}
    }
    else
	return PyMember_Get((char *)self, filter_memberlist, name);
}

/**
 ** filter_setattr
 **
 *  Set filter object attributes
 *
 */

static int filter_setattr(filterobject *self, char *name, PyObject *v)
{
    if (v == NULL) {
	PyErr_SetString(PyExc_AttributeError,
			"can't delete filter attributes");
	return -1;
    }
    return PyMember_Set((char *)self, filter_memberlist, name, v);
}

PyTypeObject MpFilter_Type = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_filter",
    sizeof(filterobject),
    0,
    (destructor) filter_dealloc,    /*tp_dealloc*/
    0,                              /*tp_print*/
    (getattrfunc) filter_getattr,   /*tp_getattr*/
    (setattrfunc) filter_setattr,   /*tp_setattr*/
    0,                              /*tp_compare*/
    0,                              /*tp_repr*/
    0,                              /*tp_as_number*/
    0,                              /*tp_as_sequence*/
    0,                              /*tp_as_mapping*/
    0,                              /*tp_hash*/
};

