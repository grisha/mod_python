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
 * requestobject.c 
 *
 * $Id: requestobject.c,v 1.35 2002/10/15 15:47:31 grisha Exp $
 *
 */

#include "mod_python.h"

/**
 **     MpRequest_FromRequest
 **
 *      This routine creates a Python requestobject given an Apache
 *      request_rec pointer.
 *
 */

PyObject * MpRequest_FromRequest(request_rec *req)
{
    requestobject *result;

    result = PyMem_NEW(requestobject, 1);
    if (! result)
        return PyErr_NoMemory();

    result->dict = PyDict_New();
    if (!result->dict)
        return PyErr_NoMemory();
    result->request_rec = req;
    result->ob_type = &MpRequest_Type;
    result->connection = NULL;
    result->server = NULL;
    result->next = NULL;
    result->prev = NULL;
    result->main = NULL;
    result->headers_in = MpTable_FromTable(req->headers_in);
    result->headers_out = MpTable_FromTable(req->headers_out);
    result->err_headers_out = MpTable_FromTable(req->err_headers_out);
    result->subprocess_env = MpTable_FromTable(req->subprocess_env);
    result->notes = MpTable_FromTable(req->notes);
    result->phase = NULL;
    result->interpreter = NULL;
    result->content_type_set = 0;
    result->hlo = NULL;
    result->rbuff = NULL;
    result->rbuff_pos = 0;
    result->rbuff_len = 0;

    _Py_NewReference(result);

    return (PyObject *) result;
}

/* Methods */

/**
 ** request.add_common_vars(reqeust self)
 **
 *     Interface to ap_add_common_vars. Adds a bunch of CGI
 *     environment variables.
 *
 */

static PyObject * req_add_common_vars(requestobject *self)
{

    ap_add_common_vars(self->request_rec);

    Py_INCREF(Py_None);
    return Py_None;

}

/**
 ** valid_phase()
 **
 *  utility func - makes sure a phase is valid
 */

static int valid_phase(const char *p)
{
    if ((strcmp(p, "PythonHandler") != 0) &&
        (strcmp(p, "PythonAuthenHandler") != 0) &&
        (strcmp(p, "PythonPostReadRequestHandler") != 0) &&
        (strcmp(p, "PythonTransHandler") != 0) &&
        (strcmp(p, "PythonHeaderParserHandler") != 0) &&
        (strcmp(p, "PythonAccessHandler") != 0) &&
        (strcmp(p, "PythonAuthzHandler") != 0) &&
        (strcmp(p, "PythonTypeHandler") != 0) &&
        (strcmp(p, "PythonFixupHandler") != 0) &&
        (strcmp(p, "PythonLogHandler") != 0) &&
        (strcmp(p, "PythonInitHandler") != 0))
        return 0;
    else
        return 1;
}

/**
 ** request.add_handler(request self, string phase, string handler)
 **
 *     Allows to add another handler to the handler list.
 */

static PyObject *req_add_handler(requestobject *self, PyObject *args)
{
    char *phase;
    char *handler;
    const char *dir = NULL;
    const char *currphase;

    if (! PyArg_ParseTuple(args, "ss|s", &phase, &handler, &dir)) 
        return NULL;

    if (! valid_phase(phase)) {
        PyErr_SetString(PyExc_IndexError, 
                        apr_psprintf(self->request_rec->pool,
                                     "Invalid phase: %s", phase));
        return NULL;
    }
    
    /* which phase are we processing? */
    currphase = PyString_AsString(self->phase);

    /* are we in same phase as what's being added? */
    if (strcmp(currphase, phase) == 0) {

        /* then just append to hlist */
        hlist_append(self->request_rec->pool, self->hlo->head,
                     handler, dir, 0);
    }
    else {
        /* this is a phase that we're not in */

        py_req_config *req_config;
        hl_entry *hle;

        /* get request config */
        req_config = (py_req_config *) 
            ap_get_module_config(self->request_rec->request_config,
                                 &python_module);

        hle = apr_hash_get(req_config->dynhls, phase, APR_HASH_KEY_STRING);

        if (! hle) {
            hle = hlist_new(self->request_rec->pool, handler, dir, 0);
            apr_hash_set(req_config->dynhls, phase, APR_HASH_KEY_STRING, hle);
        }
        else {
            hlist_append(self->request_rec->pool, hle, handler, dir, 0);
        }
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.allow_methods(request self, list methods, reset=0)
 **
 *  a wrapper around ap_allow_methods. (used for the "allow:" header
 *  to be passed to client when needed.)
 */

static PyObject *req_allow_methods(requestobject *self, PyObject *args)
{
    
    PyObject *methods;
    int reset = 0;
    int len, i;

    if (! PyArg_ParseTuple(args, "O|i", &methods, &reset)) 
        return NULL;

    if (! PySequence_Check(methods)){
        PyErr_SetString(PyExc_TypeError,
                        "First argument must be a sequence");
        return NULL;
    }

    len = PySequence_Length(methods);

    if (len) {

        PyObject *method;

        method = PySequence_GetItem(methods, 0);
        if (! PyString_Check(method)) {
            PyErr_SetString(PyExc_TypeError, 
                            "Methods must be strings");
            return NULL;
        }

        ap_allow_methods(self->request_rec, (reset == REPLACE_ALLOW), 
                         PyString_AS_STRING(method), NULL);

        for (i = 1; i < len; i++) {
            method = PySequence_GetItem(methods, i);
            if (! PyString_Check(method)) {
                PyErr_SetString(PyExc_TypeError, 
                                "Methods must be strings");
                return NULL;
            }

            ap_allow_methods(self->request_rec, MERGE_ALLOW, 
                             PyString_AS_STRING(method), NULL);
        }
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.document_root(self)
 **
 *  ap_docuement_root wrapper
 */

static PyObject *req_document_root(requestobject *self)
{

    return PyString_FromString(ap_document_root(self->request_rec));
    
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
 ** request.get_addhandler_exts(request self)
 **
 *     Returns file extentions that were given as argument to AddHandler mod_mime
 *     directive, if any, if at all. This is useful for the Publisher, which can
 *     chop off file extentions for modules based on this info.
 *
 *     XXX Due to the way this is implemented, it is best stay undocumented.
 */

static PyObject * req_get_addhandler_exts(requestobject *self, PyObject *args)
{

    char *exts = get_addhandler_extensions(self->request_rec);

    if (exts) 
        return PyString_FromString(exts);
    else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

/**
 ** request.get_config(request self)
 **
 *     Returns the config directives set through Python* apache directives.
 *     except for Python*Handler and PythonOption (which you get via get_options).
 */

static PyObject * req_get_config(requestobject *self)
{
    py_config *conf =
        (py_config *) ap_get_module_config(self->request_rec->per_dir_config, 
                                           &python_module);
    return MpTable_FromTable(conf->directives);
}

/**
 ** request.get_remodte_host(request self, [int type])
 **
 *    An interface to the ap_get_remote_host function.
 */

static PyObject * req_get_remote_host(requestobject *self, PyObject *args)
{

    int type = REMOTE_NAME;
    PyObject *str_is_ip = Py_None;
    int _str_is_ip;
    const char *host;

    if (! PyArg_ParseTuple(args, "|iO", &type, &str_is_ip)) 
        return NULL;
    
    if (str_is_ip != Py_None) {
        host = ap_get_remote_host(self->request_rec->connection, 
                                  self->request_rec->per_dir_config, type, &_str_is_ip);
    }
    else {
        host = ap_get_remote_host(self->request_rec->connection, 
                                  self->request_rec->per_dir_config, type, NULL);
    }

    if (! host) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else {
        if (str_is_ip != Py_None) {
            return Py_BuildValue("(s,i)", host, _str_is_ip);
        }
        else {
            return PyString_FromString(host);
        }
    }
}

/**
 ** request.get_options(request self)
 **
 */

static PyObject * req_get_options(requestobject *self, PyObject *args)
{
    py_config *conf =
        (py_config *) ap_get_module_config(self->request_rec->per_dir_config, 
                                           &python_module);
    return MpTable_FromTable(conf->options);
}

/**
 ** request.internal_redirect(request self, string newuri)
 **
 */

static PyObject * req_internal_redirect(requestobject *self, PyObject *args)
{
    char *new_uri;

    if (! PyArg_ParseTuple(args, "z", &new_uri))
        return NULL; /* error */

    Py_BEGIN_ALLOW_THREADS
    ap_internal_redirect(new_uri, self->request_rec);
    Py_END_ALLOW_THREADS

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.log_error(req self, string message, int level)
 **
 *     calls ap_log_rerror
 */

static PyObject * req_log_error(requestobject *self, PyObject *args)
{
    int level = 0;
    char *message = NULL;

    if (! PyArg_ParseTuple(args, "z|iO", &message, &level))
        return NULL; /* error */

    if (message) {

        if (! level)
            level = APLOG_NOERRNO|APLOG_ERR;

        ap_log_rerror(APLOG_MARK, level, 0, self->request_rec, "%s", message);
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
    int rc, bytes_read, chunk_len;
    char *buffer;
    PyObject *result;
    int copied = 0;
    long len = -1;

    if (! PyArg_ParseTuple(args, "|l", &len)) 
        return NULL;

    if (len == 0) {
        return PyString_FromString("");
    }

    /* is this the first read? */
    if (! self->request_rec->read_length) {

        /* then do some initial setting up */
        rc = ap_setup_client_block(self->request_rec, REQUEST_CHUNKED_ERROR);
        if(rc != OK) {
            PyObject *val = PyInt_FromLong(rc);
            if (val == NULL)
                return NULL;
            PyErr_SetObject(get_ServerReturn(), val);
            Py_DECREF(val);
            return NULL;
        }

        if (! ap_should_client_block(self->request_rec)) {
            /* client has nothing to send */
            return PyString_FromString("");
        }
    }

    if (len < 0)
        /* XXX ok to use request_rec->remaining? */
        len = self->request_rec->remaining +
            (self->rbuff_len - self->rbuff_pos);

    result = PyString_FromStringAndSize(NULL, len);

    /* possibly no more memory */
    if (result == NULL) 
        return NULL;

    buffer = PyString_AS_STRING((PyStringObject *) result);

    /* if anything left in the readline buffer */
    while ((self->rbuff_pos < self->rbuff_len) && (copied < len))
        buffer[copied++] = self->rbuff[self->rbuff_pos++];
    
    if (copied == len)
        return result;  /* we're done! */

    /* read it in */
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
        if (chunk_len == -1) {
            PyErr_SetObject(PyExc_IOError, 
                            PyString_FromString("Client read error (Timeout?)"));
            return NULL;
        }
        else
            bytes_read += chunk_len;
    }

    /* resize if necessary */
    if (bytes_read < len) 
        if(_PyString_Resize(&result, bytes_read))
            return NULL;

    return result;
}

/**
 ** request.readline(request self, int maxbytes)
 **
 *     Reads stuff like POST requests from the client
 *     (based on the old net_read) until EOL
 */

static PyObject * req_readline(requestobject *self, PyObject *args)
{

    int rc, chunk_len, bytes_read;
    char *buffer;
    PyObject *result;
    int copied = 0;
    long len = -1;

    if (! PyArg_ParseTuple(args, "|l", &len)) 
        return NULL;

    if (len == 0) {
        return PyString_FromString("");
    }

    /* is this the first read? */
    if (! self->request_rec->read_length) {

        /* then do some initial setting up */
        rc = ap_setup_client_block(self->request_rec, REQUEST_CHUNKED_ERROR);

        if(rc != OK) {
            PyObject *val = PyInt_FromLong(rc);
            if (val == NULL)
                return NULL;
            PyErr_SetObject(get_ServerReturn(), val);
            Py_DECREF(val);
            return NULL;
        }

        if (! ap_should_client_block(self->request_rec)) {
            /* client has nothing to send */
            return PyString_FromString("");
        }
    }

    if (len < 0)
        len = self->request_rec->remaining + 
            (self->rbuff_len - self->rbuff_pos);

    /* create the result buffer */
    result = PyString_FromStringAndSize(NULL, len);

    /* possibly no more memory */
    if (result == NULL) 
        return NULL;

    buffer = PyString_AS_STRING((PyStringObject *) result);

    /* is there anything left in the rbuff from previous reads? */
    if (self->rbuff_pos < self->rbuff_len) {
        
        /* if yes, process that first */
        while (self->rbuff_pos < self->rbuff_len) {

            buffer[copied++] = self->rbuff[self->rbuff_pos];
            if ((self->rbuff[self->rbuff_pos++] == '\n') || 
                (copied == len)) {

                /* our work is done */

                /* resize if necessary */
                if (copied < len) 
                    if(_PyString_Resize(&result, copied))
                        return NULL;

                return result;
            }
        }
    }

    /* if got this far, the buffer should be empty, we need to read more */
        
    /* create a read buffer */
    self->rbuff_len = len > HUGE_STRING_LEN ? len : HUGE_STRING_LEN;
    self->rbuff_pos = self->rbuff_len;
    self->rbuff = apr_palloc(self->request_rec->pool, self->rbuff_len);
    if (! self->rbuff)
        return PyErr_NoMemory();

    /* read it in */
    Py_BEGIN_ALLOW_THREADS
        chunk_len = ap_get_client_block(self->request_rec, self->rbuff, 
                                        self->rbuff_len);
    Py_END_ALLOW_THREADS;
    bytes_read = chunk_len;

    /* if this is a "short read", try reading more */
    while ((chunk_len != 0 ) && (bytes_read + copied < len)) {

        Py_BEGIN_ALLOW_THREADS
            chunk_len = ap_get_client_block(self->request_rec, 
                                            self->rbuff + bytes_read, 
                                            self->rbuff_len - bytes_read);
        Py_END_ALLOW_THREADS

        if (chunk_len == -1) {
            PyErr_SetObject(PyExc_IOError, 
                            PyString_FromString("Client read error (Timeout?)"));
            return NULL;
        }
        else
            bytes_read += chunk_len;
    }
    self->rbuff_len = bytes_read;
    self->rbuff_pos = 0;

    /* now copy the remaining bytes */
    while (self->rbuff_pos < self->rbuff_len) {

        buffer[copied++] = self->rbuff[self->rbuff_pos];
        if ((self->rbuff[self->rbuff_pos++] == '\n') || 
            (copied == len)) 
            /* our work is done */
            break;
    }

    /* resize if necessary */
    if (copied < len) 
        if(_PyString_Resize(&result, copied))
            return NULL;

    return result;
}

/**
 ** request.readlines([long maxsize])
 **
 *    just like file.readlines()
 */

static PyObject *req_readlines(requestobject *self, PyObject *args)
{

    PyObject *result = PyList_New(0);
    PyObject *line, *rlargs;
    long sizehint = -1;
    long size = 0;

    if (! PyArg_ParseTuple(args, "|l", &sizehint)) 
        return NULL;

    if (result == NULL)
        return PyErr_NoMemory();

    rlargs = PyTuple_New(0);
    if (result == NULL)
        return PyErr_NoMemory();

    line = req_readline(self, rlargs);
    while (line && !(strcmp(PyString_AsString(line), "") == 0)) {
        PyList_Append(result, line);
        size += PyString_Size(line);
        if ((sizehint != -1) && (size >= size))
            break;
        line = req_readline(self, args);
    }

    if (!line)
        return NULL;

    return result;
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
    ci->server_rec = self->request_rec->server;
    if (PyCallable_Check(handler)) {
        Py_INCREF(handler);
        ci->handler = handler;
        ci->interpreter = self->interpreter;
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

    apr_pool_cleanup_register(self->request_rec->pool, ci, python_cleanup, 
                              apr_pool_cleanup_null);

    Py_INCREF(Py_None);
    return Py_None;

}

/**
 ** request.send_http_header(request self)
 **
 *      this is a noop, just so we don't break old scripts
 */

static PyObject * req_send_http_header(requestobject *self)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.set_content_length(request self, long content_length)
 **
 *      write output to the client
 */

static PyObject * req_set_content_length(requestobject *self, PyObject *args)
{
    long len;

    if (! PyArg_ParseTuple(args, "l", &len))
        return NULL;  /* bad args */

    ap_set_content_length(self->request_rec, len);

    Py_INCREF(Py_None);
    return Py_None;
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

static PyMethodDef request_methods[] = {
    {"add_common_vars",       (PyCFunction) req_add_common_vars,       METH_NOARGS},
    {"add_handler",           (PyCFunction) req_add_handler,           METH_VARARGS},
    {"allow_methods",         (PyCFunction) req_allow_methods,         METH_VARARGS},
    {"document_root",         (PyCFunction) req_document_root,         METH_NOARGS},
    {"get_basic_auth_pw",     (PyCFunction) req_get_basic_auth_pw,     METH_NOARGS},
    {"get_addhandler_exts",   (PyCFunction) req_get_addhandler_exts,   METH_NOARGS},
    {"get_config",            (PyCFunction) req_get_config,            METH_NOARGS},
    {"get_remote_host",       (PyCFunction) req_get_remote_host,       METH_VARARGS},
    {"get_options",           (PyCFunction) req_get_options,           METH_NOARGS},
    {"internal_redirect",     (PyCFunction) req_internal_redirect,     METH_VARARGS},
    {"log_error",             (PyCFunction) req_log_error,             METH_VARARGS},
    {"read",                  (PyCFunction) req_read,                  METH_VARARGS},
    {"readline",              (PyCFunction) req_readline,              METH_VARARGS},
    {"readlines",             (PyCFunction) req_readlines,             METH_VARARGS},
    {"register_cleanup",      (PyCFunction) req_register_cleanup,      METH_VARARGS},
    {"send_http_header",      (PyCFunction) req_send_http_header,      METH_NOARGS},
    {"set_content_length",    (PyCFunction) req_set_content_length,    METH_VARARGS},
    {"write",                 (PyCFunction) req_write,                 METH_VARARGS},
    { NULL, NULL } /* sentinel */
};

/**
 ** getmakeobj
 **
 *    A getter func that creates an object as needed.
 */

static PyObject *getmakeobj(requestobject* self, void *objname) 
{
    char *name = (char *)objname;
    PyObject *result = NULL;

    if (strcmp(name, "connection") == 0) {
        if (!self->connection && self->request_rec->connection)
            self->connection = MpConn_FromConn(self->request_rec->connection);
        result = self->connection;
    }
    else if (strcmp(name, "server") == 0) {
        if (!self->server && self->request_rec->server) 
            self->server = MpServer_FromServer(self->request_rec->server);
        result = self->server;
    }
    else if (strcmp(name, "next") == 0) {
        if (!self->next && self->request_rec->next)
            self->next = MpRequest_FromRequest(self->request_rec->next);
        result = self->next;
    }
    else if (strcmp(name, "prev") == 0) {
        if (!self->prev && self->request_rec->prev)
            self->prev = MpRequest_FromRequest(self->request_rec->prev);
        result = self->prev;
    }
    else if (strcmp(name, "main") == 0) {
        if (!self->main && self->request_rec->main)
            self->main = MpRequest_FromRequest(self->request_rec->main);
        result = self->main;
    }

    if (!result)
        result = Py_None;

    Py_INCREF(result);
    return result;

}

/* 
   These are offsets into the Apache request_rec structure.
   They are accessed via getset functions.
*/

#define OFF(x) offsetof(request_rec, x)

static struct PyMemberDef request_rec_mbrs[] = {
    {"the_request",        T_STRING,  OFF(the_request)},
    {"assbackwards",       T_INT,     OFF(assbackwards)},
    {"proxyreq",           T_INT,     OFF(proxyreq)},
    {"header_only",        T_INT,     OFF(header_only)},
    {"protocol",           T_STRING,  OFF(protocol)},
    {"proto_num",          T_INT,     OFF(proto_num)},
    {"hostname",           T_STRING,  OFF(hostname)},
    {"request_time",       T_LONG,    OFF(request_time)},
    {"status_line",        T_STRING,  OFF(status_line)},
    {"status",             T_INT,     OFF(status)},
    {"method",             T_STRING,  OFF(method)},
    {"method_number",      T_INT,     OFF(method_number)},
    {"allowed",            T_LONG,    OFF(allowed)},
    {"allowed_xmethods",   T_OBJECT,  OFF(allowed_xmethods)},
    {"allowed_methods",    T_OBJECT,  OFF(allowed_methods)},
    {"sent_boduct",        T_LONG,    OFF(sent_bodyct)},
    {"bytes_sent",         T_LONG,    OFF(bytes_sent)},
    {"mtime",              T_LONG,    OFF(mtime)},
    {"chunked",            T_INT,     OFF(chunked)},
/*    {"boundary",           T_STRING,  OFF(boundary)}, */
    {"range",              T_STRING,  OFF(range)},
    {"clength",            T_LONG,    OFF(clength)},
    {"remaining",          T_LONG,    OFF(remaining)},
    {"read_length",        T_LONG,    OFF(read_length)},
    {"read_body",          T_INT,     OFF(read_body)},
    {"read_chunked",       T_INT,     OFF(read_chunked)},
    {"expecting_100",      T_INT,     OFF(expecting_100)},
    {"content_type",       T_STRING,  OFF(content_type)},
    {"handler",            T_STRING,  OFF(handler)},
    {"content_encoding",   T_STRING,  OFF(content_encoding)},
    {"content_languages",  T_OBJECT,  OFF(content_languages)},
    {"vlist_validator",    T_STRING,  OFF(vlist_validator)},
    {"user",               T_STRING,  OFF(user)},
    {"ap_auth_type",       T_STRING,  OFF(ap_auth_type)},
    {"no_cache",           T_INT,     OFF(no_cache)},
    {"no_local_copy",      T_INT,     OFF(no_local_copy)},
    {"unparsed_uri",       T_STRING,  OFF(unparsed_uri)},
    {"uri",                T_STRING,  OFF(uri)},
    {"filename",           T_STRING,  OFF(filename)},
    {"canonical_filename", T_STRING,  OFF(canonical_filename)},
    {"path_info",          T_STRING,  OFF(path_info)},
    {"args",               T_STRING,  OFF(args)},
    {"finfo",              T_OBJECT,  OFF(finfo)},
    {"parsed_uri",         T_OBJECT,  OFF(parsed_uri)},
    {"used_path_info",     T_INT,     OFF(used_path_info)},
    {"eos_sent",           T_INT,     OFF(eos_sent)},
    {NULL}  /* Sentinel */
};

/**
 ** getreq_recmbr
 **
 *    Retrieves request_rec structure members
 */

static PyObject *getreq_recmbr(requestobject *self, void *name) 
{
    return PyMember_GetOne((char*)self->request_rec,
                           find_memberdef(request_rec_mbrs, name));
}

/**
 ** setreq_recmbr
 **
 *    Sets request_rec structure members
 */

static int setreq_recmbr(requestobject *self, PyObject *val, void *name) 
{

    if (strcmp(name, "content_type") == 0) {
        if (! PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "content_type must be a string");
            return -1;
        }
        self->request_rec->content_type = 
            apr_pstrdup(self->request_rec->pool, PyString_AsString(val));
        self->content_type_set = 1;
        return 0;
    } 
    else if (strcmp(name, "user") == 0) {
        if (! PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "user must be a string");
            return -1;
        }
        self->request_rec->user = 
            apr_pstrdup(self->request_rec->pool, PyString_AsString(val));
        return 0;
    }
    else if (strcmp(name, "filename") == 0) {
        if (! PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "filename must be a string");
            return -1;
        }
        self->request_rec->filename = 
            apr_pstrdup(self->request_rec->pool, PyString_AsString(val));
        return 0;
    }
    
    return PyMember_SetOne((char*)self->request_rec, 
                           find_memberdef(request_rec_mbrs, (char*)name),
                           val);
}

/**
 ** getreq_recmbr_time
 **
 *    Retrieves apr_time_t request_rec members
 */

static PyObject *getreq_recmbr_time(requestobject *self, void *name) 
{
    PyMemberDef *md = find_memberdef(request_rec_mbrs, name);
    char *addr = (char *)self->request_rec + md->offset;
    apr_time_t time = *(apr_time_t*)addr;
    return PyFloat_FromDouble(time*0.000001);
}

/**
 ** getreq_rec_ah
 **
 *    For array headers that will get converted to tuple
 */

static PyObject *getreq_rec_ah(requestobject *self, void *name) 
{
    const PyMemberDef *md = find_memberdef(request_rec_mbrs, name);
    apr_array_header_t *ah = 
        (apr_array_header_t *)((char *)self->request_rec + md->offset);

    return tuple_from_array_header(ah);
}

/**
 ** getreq_rec_ml
 **
 *    For method lists that will get converted to tuple
 */

static PyObject *getreq_rec_ml(requestobject *self, void *name) 
{
    const PyMemberDef *md = find_memberdef(request_rec_mbrs, (char*)name);
    ap_method_list_t *ml = 
        (ap_method_list_t *)((char *)self->request_rec + md->offset);

    return tuple_from_method_list(ml);
}

/**
 ** getreq_rec_fi
 **
 *    For file info that will get converted to tuple
 */

static PyObject *getreq_rec_fi(requestobject *self, void *name) 
{
    const PyMemberDef *md = find_memberdef(request_rec_mbrs, (char*)name);
    apr_finfo_t *fi = 
        (apr_finfo_t *)((char *)self->request_rec + md->offset);

    return tuple_from_finfo(fi);
}

/**
 ** getreq_rec_uri
 **
 *    For parsed uri that will get converted to tuple
 */

static PyObject *getreq_rec_uri(requestobject *self, void *name) 
{
    const PyMemberDef *md = find_memberdef(request_rec_mbrs, (char*)name);
    apr_uri_t *uri = (apr_uri_t *)((char *)self->request_rec + md->offset);

    return tuple_from_apr_uri(uri);
}

static PyGetSetDef request_getsets[] = {
    {"connection", (getter)getmakeobj, NULL, "Connection object", "connection"},
    {"server",     (getter)getmakeobj, NULL, "Server object", "server"},
    {"next",       (getter)getmakeobj, NULL, "If redirected, pointer to the to request", "next"},
    {"prev",       (getter)getmakeobj, NULL, "If redirected, pointer to the from request", "prev"},
    {"main",       (getter)getmakeobj, NULL, "If subrequest, pointer to the main request", "main"},
    {"the_request", (getter)getreq_recmbr, NULL, "First line of request", "the_request"},
    {"assbackwards", (getter)getreq_recmbr, NULL, "HTTP/0.9 \"simple\" request", "assbackwards"},
    {"proxyreq",     (getter)getreq_recmbr, NULL, "A proxy request: one of apache.PROXYREQ_* values", "proxyreq"},
    {"header_only",  (getter)getreq_recmbr, NULL, "HEAD request, as oppsed to GET", "header_only"},
    {"protocol",     (getter)getreq_recmbr, NULL, "Protocol as given to us, or HTTP/0.9", "protocol"},
    {"proto_num",    (getter)getreq_recmbr, NULL, "Protocol version. 1.1 = 1001", "proto_num"},
    {"hostname",     (getter)getreq_recmbr, NULL, "Host, as set by full URI or Host:", "hostname"},
    {"request_time", (getter)getreq_recmbr_time, NULL, "When request started", "request_time"},
    {"status_line",  (getter)getreq_recmbr, NULL, "Status line, if set by script", "status_line"},
    {"status",       (getter)getreq_recmbr, (setter)setreq_recmbr, "Status", "status"},
    {"method",       (getter)getreq_recmbr, NULL, "Request method", "method"},
    {"method_number", (getter)getreq_recmbr, NULL, "Request method number, one of apache.M_*", "method_number"},
    {"allowed",      (getter)getreq_recmbr, NULL, "Status", "allowed"},
    {"allowed_xmethods", (getter)getreq_rec_ah, NULL, "Allowed extension methods", "allowed_xmethods"},
    {"allowed_methods", (getter)getreq_rec_ml, NULL, "Allowed methods", "allowed_methods"},
    {"sent_bodyct",  (getter)getreq_recmbr, NULL, "Byte count in stream for body", "sent_boduct"},
    {"bytes_sent",   (getter)getreq_recmbr, NULL, "Bytes sent", "bytes_sent"},
    {"mtime",        (getter)getreq_recmbr_time, NULL, "Time resource was last modified", "mtime"},
    {"chunked",      (getter)getreq_recmbr, NULL, "Sending chunked transfer-coding", "chunked"},
    {"boundary",     (getter)getreq_recmbr, NULL, "Multipart/byteranges boundary", "boundary"},
    {"range",        (getter)getreq_recmbr, NULL, "The Range: header", "range"},
    {"clength",      (getter)getreq_recmbr, NULL, "The \"real\" contenct length", "clength"},
    {"remaining",    (getter)getreq_recmbr, NULL, "Bytes left to read", "remaining"},
    {"read_length",  (getter)getreq_recmbr, NULL, "Bytes that have been read", "read_length"},
    {"read_body",    (getter)getreq_recmbr, NULL, "How the request body should be read", "read_body"},
    {"read_chunked", (getter)getreq_recmbr, NULL, "Reading chunked transfer-coding", "read_chunked"},
    {"expecting_100", (getter)getreq_recmbr, NULL, "Is client waitin for a 100 response?", "expecting_100"},
    {"content_type",  (getter)getreq_recmbr, (setter)setreq_recmbr, "Content type", "content_type"},
    {"handler",       (getter)getreq_recmbr, NULL, "The handler string", "handler"},
    {"content_encoding", (getter)getreq_recmbr, NULL, "How to encode the data", "content_encoding"},
    {"content_languages", (getter)getreq_rec_ah, NULL, "Content languages", "content_languages"},
    {"vlist_validator", (getter)getreq_recmbr, NULL, "Variant list validator (if negotiated)", "vlist_validator"},
    {"user",          (getter)getreq_recmbr, (setter)setreq_recmbr, "If authentication check was made, the user name", "user"},
    {"ap_auth_type",  (getter)getreq_recmbr, NULL, "If authentication check was made, auth type", "ap_auth_type"},
    {"no_cache",      (getter)getreq_recmbr, NULL, "This response in non-cacheable", "no_cache"},
    {"no_local_copy", (getter)getreq_recmbr, NULL, "There is no local copy of the response", "no_local_copy"},
    {"unparsed_uri",  (getter)getreq_recmbr, NULL, "The URI without any parsing performed", "unparsed_uri"},
    {"uri",           (getter)getreq_recmbr, NULL, "The path portion of URI", "uri"},
    {"filename",      (getter)getreq_recmbr, (setter)setreq_recmbr, "The file name on disk that this request corresponds to", "filename"},
    {"canonical_filename", (getter)getreq_recmbr, NULL, "The true filename (req.filename is canonicalized if they dont match)", "canonical_filename"},
    {"path_info",     (getter)getreq_recmbr, NULL, "Path_info, if any", "path_info"},
    {"args",          (getter)getreq_recmbr, NULL, "QUERY_ARGS, if any", "args"},
    {"finfo",         (getter)getreq_rec_fi, NULL, "File information", "finfo"},
    {"parsed_uri",    (getter)getreq_rec_uri, NULL, "Components of URI", "parsed_uri"},
    {"used_path_info", (getter)getreq_recmbr, NULL, "Flag to accept or reject path_info on current request", "used_path_info"},
    /* XXX per_dir_config */
    /* XXX request_config */
    /* XXX htaccess */
    /* XXX filters and eos */
    {"eos_sent", (getter)getreq_recmbr, NULL, "EOS bucket sent", "eos_sent"},
    {NULL}  /* Sentinel */
};

#undef OFF
#define OFF(x) offsetof(requestobject, x)

static struct PyMemberDef request_members[] = {
    {"headers_in",         T_OBJECT,    OFF(headers_in),        RO},
    {"headers_out",        T_OBJECT,    OFF(headers_out),       RO},
    {"err_headers_out",    T_OBJECT,    OFF(err_headers_out),   RO},
    {"subprocess_env",     T_OBJECT,    OFF(subprocess_env),    RO},
    {"notes",              T_OBJECT,    OFF(notes),             RO},
    {"_content_type_set",  T_INT,       OFF(content_type_set),  RO},
    {"phase",              T_OBJECT,    OFF(phase),             RO},
    {"interpreter",        T_STRING,    OFF(interpreter),       RO},
    {"hlist",              T_OBJECT,    OFF(hlo),               RO},
    {NULL}  /* Sentinel */
};

/**
 ** request_dealloc
 **
 *
 */

static void request_dealloc(requestobject *self)
{  
    Py_XDECREF(self->dict);
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
    Py_XDECREF(self->phase);
    Py_XDECREF(self->hlo);

    free(self);
}

static char request_doc[] =
"Apache request_rec structure\n";

PyTypeObject MpRequest_Type = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_request",
    sizeof(requestobject),
    0,
    (destructor) request_dealloc,    /*tp_dealloc*/
    0,                               /*tp_print*/
    0,                               /*tp_getattr*/
    0,                               /*tp_setattr*/
    0,                               /*tp_compare*/
    0,                               /*tp_repr*/
    0,                               /*tp_as_number*/
    0,                               /*tp_as_sequence*/
    0,                               /*tp_as_mapping*/
    0,                               /*tp_hash*/
    0,                               /* tp_call */
    0,                               /* tp_str */
    PyObject_GenericGetAttr,         /* tp_getattro */
    PyObject_GenericSetAttr,         /* tp_setattro */
    0,                               /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT |
    Py_TPFLAGS_BASETYPE,             /* tp_flags */
    request_doc,                     /* tp_doc */
    0,                               /* tp_traverse */
    0,                               /* tp_clear */
    0,                               /* tp_richcompare */
    0,                               /* tp_weaklistoffset */
    0,                               /* tp_iter */
    0,                               /* tp_iternext */
    request_methods,                 /* tp_methods */
    request_members,                 /* tp_members */
    request_getsets,                 /* tp_getset */
    0,                               /* tp_base */
    0,                               /* tp_dict */
    0,                               /* tp_descr_get */
    0,                               /* tp_descr_set */
    offsetof(requestobject, dict),   /* tp_dictoffset */
    0,                               /* tp_init */
    0,                               /* tp_alloc */
    0,                               /* tp_new */
    (destructor)request_dealloc,     /* tp_free */
};






