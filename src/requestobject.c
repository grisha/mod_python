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
 * requestobject.c 
 *
 * $Id: requestobject.c,v 1.13 2001/11/03 04:24:30 gtrubetskoy Exp $
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
    result->Request = NULL;
    result->content_type_set = 0;
    result->hlo = NULL;
    result->rbuff = NULL;
    result->rbuff_pos = 0;
    result->rbuff_len = 0;

    _Py_NewReference(result);
    apr_pool_cleanup_register(req->pool, (PyObject *)result, python_decref, 
			      apr_pool_cleanup_null);

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

static PyObject * req_add_common_vars(requestobject *self, PyObject *args)
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
 ** request.get_all_config(request self)
 **
 *  returns get_config + all the handlers added by req.add_handler
 */

static PyObject *req_get_all_config(requestobject *self, PyObject *args)
{
    apr_table_t *all;
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);

    all = apr_table_copy(self->request_rec->pool, conf->directives);

    if (apr_table_get(self->request_rec->notes, "py_more_directives")) {

	apr_array_header_t *ah = apr_table_elts(self->request_rec->notes);
	apr_table_entry_t *elts = (apr_table_entry_t *)ah->elts;
	int i = ah->nelts;

	while (i--) {
	    if (elts[i].key) {
		if (valid_phase(elts[i].key)) {
		
		    /* if exists - append, otherwise add */
		    const char *val = apr_table_get(all, elts[i].key);
		    if (val) {
			apr_table_set(all, elts[i].key, 
				     apr_pstrcat(self->request_rec->pool,
						val, " ", elts[i].val,
						NULL));
		    }
		    else {
			apr_table_set(all, elts[i].key, elts[i].val);
		    }
		}
	    }
	}
    }
    return MpTable_FromTable(all);
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
 ** request.get_config(request self)
 **
 *     Returns the config directives set through Python* apache directives.
 *     except for Python*Handler and PythonOption (which you get via get_options).
 */

static PyObject * req_get_config(requestobject *self, PyObject *args)
{
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);
    return MpTable_FromTable(conf->directives);
}

//XXX document - get_dirs and get_all_dirs gone

/**
 ** request.get_remote_host(request self, [int type])
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
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);
    return MpTable_FromTable(conf->options);
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
	    PyErr_SetObject(Mp_ServerReturn, val);
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
	return result; 	/* we're done! */

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
    int len = -1;

    if (! PyArg_ParseTuple(args, "|i", &len)) 
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
	    PyErr_SetObject(Mp_ServerReturn, val);
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
	ci->interpreter = apr_table_get(self->request_rec->notes, "python_interpreter");
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

static PyObject * req_send_http_header(requestobject *self, PyObject *args)
{
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

static PyMethodDef requestobjectmethods[] = {
    {"add_common_vars",       (PyCFunction) req_add_common_vars,       METH_VARARGS},
    {"add_handler",           (PyCFunction) req_add_handler,           METH_VARARGS},
    {"allow_methods",         (PyCFunction) req_allow_methods,         METH_VARARGS},
    {"get_all_config",        (PyCFunction) req_get_all_config,        METH_VARARGS},
    {"get_basic_auth_pw",     (PyCFunction) req_get_basic_auth_pw,     METH_VARARGS},
    {"get_config",            (PyCFunction) req_get_config,            METH_VARARGS},
    {"get_remote_host",       (PyCFunction) req_get_remote_host,       METH_VARARGS},
    {"get_options",           (PyCFunction) req_get_options,           METH_VARARGS},
    {"read",                  (PyCFunction) req_read,                  METH_VARARGS},
    {"readline",              (PyCFunction) req_readline,              METH_VARARGS},
    {"register_cleanup",      (PyCFunction) req_register_cleanup,      METH_VARARGS},
    {"send_http_header",      (PyCFunction) req_send_http_header,      METH_VARARGS},
    {"write",                 (PyCFunction) req_write,                 METH_VARARGS},
    { NULL, NULL } /* sentinel */
};


#define OFF(x) offsetof(request_rec, x)

static struct memberlist request_memberlist[] = {
    /* connection, server, next, prev, main in getattr */
    {"connection",         T_OBJECT,    0,                         RO},
    {"server",             T_OBJECT,    0,                         RO},
    {"next",               T_OBJECT,    0,                         RO},
    {"prev",               T_OBJECT,    0,                         RO},
    {"main",               T_OBJECT,    0,                         RO},
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
    {"allowed_xmethods",   T_OBJECT,    0,                         RO},
    {"allowed_methods",    T_OBJECT,    0,                         RO},
    {"sent_bodyct",        T_INT,       OFF(sent_bodyct),          RO},
    {"bytes_sent",         T_LONG,      OFF(bytes_sent),           RO},
    {"mtime",              T_LONG,      OFF(mtime),                RO},
    {"chunked",            T_INT,       OFF(chunked),              RO},
    {"boundary",           T_STRING,    OFF(boundary),             RO},
    {"range",              T_STRING,    OFF(range),                RO},
    {"clength",            T_LONG,      OFF(clength),              RO},
    {"remaining",          T_LONG,      OFF(remaining),            RO},
    {"read_length",        T_LONG,      OFF(read_length),          RO},
    {"read_body",          T_INT,       OFF(read_body),            RO},
    {"read_chunked",       T_INT,       OFF(read_chunked),         RO},
    {"expecting_100",      T_INT,       OFF(expecting_100),        RO},
    {"headers_in",         T_OBJECT,    0,                         RO},
    {"headers_out",        T_OBJECT,    0,                         RO},
    {"err_headers_out",    T_OBJECT,    0,                         RO},
    {"subprocess_env",     T_OBJECT,    0,                         RO},
    {"notes",              T_OBJECT,    0,                         RO},
    {"content_type",       T_STRING,    OFF(content_type)            },
    {"_content_type_set",  T_INT,       0,                         RO},
    {"handler",            T_STRING,    OFF(handler),              RO},
    {"content_encoding",   T_STRING,    OFF(content_encoding),     RO},
    {"content_language",   T_STRING,    OFF(content_language),     RO},
    {"content_languages",  T_OBJECT,                                 },
    {"vlist_validator",    T_STRING,    OFF(vlist_validator),      RO},
    {"user",               T_STRING,    OFF(user),                   },
    {"ap_auth_type",       T_STRING,    OFF(ap_auth_type),         RO},
    {"unparsed_uri",       T_STRING,    OFF(unparsed_uri),         RO},
    {"no_cache",           T_INT,       OFF(no_cache),             RO},
    {"no_local_copy",      T_INT,       OFF(no_local_copy),        RO},
    {"unparsed_uri",       T_STRING,    OFF(unparsed_uri),         RO},
    {"uri",                T_STRING,    OFF(uri),                  RO},
    {"filename",           T_STRING,    OFF(filename),               },
    {"path_info",          T_STRING,    OFF(path_info),            RO},
    {"args",               T_STRING,    OFF(args),                 RO},
    {"finfo",              T_OBJECT,    0,                         RO},
    {"parsed_uri",         T_OBJECT,    0,                         RO},
    {"phase",              T_OBJECT,    0,                         RO},
    /* XXX per_dir_config */
    /* XXX request_config */
    /* XXX htaccess */
    /* XXX filters and eos */
    {NULL}  /* Sentinel */
};

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
    Py_XDECREF(self->phase);
    Py_XDECREF(self->Request);

    free(self);
}

/**
 ** tuple_from_finfo
 **
 *  makes a tuple from apr_finfo_t
 *
 */

static PyObject *tuple_from_finfo(apr_finfo_t f)
{
    PyObject *t;

    t = PyTuple_New(14);

    PyTuple_SET_ITEM(t, 0, PyInt_FromLong(f.valid));
    PyTuple_SET_ITEM(t, 1, PyInt_FromLong(f.protection));
    PyTuple_SET_ITEM(t, 2, PyInt_FromLong(f.user));
    PyTuple_SET_ITEM(t, 3, PyInt_FromLong(f.group));
    PyTuple_SET_ITEM(t, 4, PyInt_FromLong(f.inode));
    PyTuple_SET_ITEM(t, 5, PyInt_FromLong(f.device));
    PyTuple_SET_ITEM(t, 6, PyInt_FromLong(f.nlink));
    PyTuple_SET_ITEM(t, 7, PyLong_FromLong(f.size));
    PyTuple_SET_ITEM(t, 8, PyLong_FromLong(f.csize));
    PyTuple_SET_ITEM(t, 9, PyFloat_FromDouble(f.atime/1000000));
    PyTuple_SET_ITEM(t, 10, PyFloat_FromDouble(f.mtime/1000000));
    PyTuple_SET_ITEM(t, 11, PyFloat_FromDouble(f.ctime/1000000));
    if (f.fname) {
	PyTuple_SET_ITEM(t, 12, PyString_FromString(f.fname));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 12, Py_None);
    }
    if (f.name) {
	PyTuple_SET_ITEM(t, 13, PyString_FromString(f.name));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 13, Py_None);
    }

    //XXX
    //filehand (remember to adjust tuple size above, also constant in apache.py!)

    return t;
}


/**
 ** tuple_from_parsed_uri
 **
 *  makes a tuple from uri_components
 *
 */

static PyObject *tuple_from_parsed_uri(uri_components u)
{
    PyObject *t;

    t = PyTuple_New(9);

    if (u.scheme) {
	PyTuple_SET_ITEM(t, 0, PyString_FromString(u.scheme));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 0, Py_None);
    }
    if (u.hostinfo) {
	PyTuple_SET_ITEM(t, 1, PyString_FromString(u.hostinfo));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 1, Py_None);
    }
    if (u.user) {
	PyTuple_SET_ITEM(t, 2, PyString_FromString(u.user));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 2, Py_None);
    }
    if (u.password) {
	PyTuple_SET_ITEM(t, 3, PyString_FromString(u.password));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 3, Py_None);
    }
    if (u.hostname) {
	PyTuple_SET_ITEM(t, 4, PyString_FromString(u.hostname));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 4, Py_None);
    }
    if (u.port_str) {
	PyTuple_SET_ITEM(t, 5, PyInt_FromLong(u.port));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 5, Py_None);
    }
    if (u.path) {
	PyTuple_SET_ITEM(t, 6, PyString_FromString(u.path));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 6, Py_None);
    }
    if (u.query) {
	PyTuple_SET_ITEM(t, 7, PyString_FromString(u.query));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 7, Py_None);
    }
    if (u.fragment) {
	PyTuple_SET_ITEM(t, 8, PyString_FromString(u.fragment));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 8, Py_None);
    }
    // XXX hostent, is_initialized, dns_*

    return t;
}

/**
 ** request_getattr
 **
 *  Get request object attributes
 *
 */

static PyObject *request_getattr(requestobject *self, char *name)
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
		self->connection = MpConn_FromConn(self->request_rec->connection);
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
		self->server = MpServer_FromServer(self->request_rec->server);
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
		self->next = MpRequest_FromRequest(self->request_rec->next);
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
		self->prev = MpRequest_FromRequest(self->request_rec->prev);
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
		self->main = MpRequest_FromRequest(self->request_rec->main);
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
    else if (strcmp(name, "allowed_xmethods") == 0) {
	return tuple_from_array_header(self->request_rec->allowed_xmethods);
    } 
    else if (strcmp(name, "allowed_methods") == 0) {
	return tuple_from_method_list(self->request_rec->allowed_methods);
    } 
    else if (strcmp(name, "content_languages") == 0) {
	return tuple_from_array_header(self->request_rec->content_languages);
    } 
    else if (strcmp(name, "finfo") == 0) {
	return tuple_from_finfo(self->request_rec->finfo);
    }
    else if (strcmp(name, "parsed_uri") == 0) {
	return tuple_from_parsed_uri(self->request_rec->parsed_uri);
    }
    else if (strcmp(name, "hlist") == 0) {
	Py_INCREF(self->hlo);
	return (PyObject *)self->hlo;
    }
    else if (strcmp(name, "_content_type_set") == 0) {
	return PyInt_FromLong(self->content_type_set);
    }
    else if (strcmp(name, "phase") == 0) {
	if (self->phase == NULL) {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
	else {
	    Py_INCREF(self->phase);
	    return self->phase;
	}
    }
    else if (strcmp(name, "_Request") == 0) {
	if (self->Request == NULL) {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
	else {
	    Py_INCREF(self->Request);
	    return (PyObject *) self->Request;
	}
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
	    apr_pstrdup(self->request_rec->pool, PyString_AsString(value));
	self->content_type_set = 1;
	return 0;
    }
    else if (strcmp(name, "filename") == 0) {
	self->request_rec->filename =
	    apr_pstrdup(self->request_rec->pool, PyString_AsString(value));
	return 0;
    }
    else if (strcmp(name, "user") == 0) {
	self->request_rec->user = 
	    apr_pstrdup(self->request_rec->pool, PyString_AsString(value));
	return 0;
    }
    else if (strcmp(name, "_Request") == 0) {
	/* it's ok to assign None */
	if (value == Py_None) {
	    Py_XDECREF(self->Request);
	    self->Request = NULL;
	    return 0;
	}
	/* but anything else has to be an instance */
	if (! PyInstance_Check(value)) {
	    PyErr_SetString(PyExc_AttributeError,
			    "special attribute _Request must be an instance");
	    return -1;
	}
	Py_INCREF(value);
	self->Request = value;
	return 0;
    }
    else
	return PyMember_Set((char *)self->request_rec, request_memberlist, name, value);
}

PyTypeObject MpRequest_Type = {
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



