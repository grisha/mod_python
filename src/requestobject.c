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
 * $Id: requestobject.c,v 1.5 2000/12/06 03:05:37 gtrubetskoy Exp $
 *
 */

#include "mod_python.h"

/*
 * This is a mapping of a Python object to an Apache request_rec.
 *
 */

/**
 ** python_decref
 ** 
 *   This helper function is used with ap_register_cleanup to destroy
 *   python objects when a certain pool is destroyed.
 */

static void python_decref(void *object)
{
    Py_XDECREF((PyObject *) object);
}

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
    result->header_sent = 0;
    result->hstack = NULL;
    result->rbuff = NULL;
    result->rbuff_pos = 0;
    result->rbuff_len = 0;

    _Py_NewReference(result);
    ap_register_cleanup(req->pool, (PyObject *)result, python_decref, 
			ap_null_cleanup);

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

/**
 ** request.child_terminate(request self)
 **
 *    terminates a child process
 */

static PyObject * req_child_terminate(requestobject *self, PyObject *args)
{
#ifndef MULTITHREAD
    ap_child_terminate(self->request_rec);
#endif
    Py_INCREF(Py_None);
    return Py_None;
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
    return MpTable_FromTable(all);
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
 *     except for PythonOption, which you get via get_options
 */

static PyObject * req_get_config(requestobject *self, PyObject *args)
{
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);
    return MpTable_FromTable(conf->directives);
}

/**
 ** request.get_dirs(request self)
 **
 *  Returns a table keyed by directives with the last path in which the
 *  directive was encountered.
 */

static PyObject * req_get_dirs(requestobject *self, PyObject *args)
{
    py_dir_config *conf =
	(py_dir_config *) ap_get_module_config(self->request_rec->per_dir_config, 
					       &python_module);
    return MpTable_FromTable(conf->dirs);
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

    /* set timeout */
    ap_soft_timeout("mod_python_read", self->request_rec);

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
    self->rbuff = ap_palloc(self->request_rec->pool, self->rbuff_len);
    if (! self->rbuff)
	return PyErr_NoMemory();

    /* set timeout */
    ap_soft_timeout("mod_python_read", self->request_rec);

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
    self->rbuff_len = bytes_read;
    self->rbuff_pos = 0;
    ap_kill_timeout(self->request_rec);

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
    {"readline",             (PyCFunction) req_readline,             METH_VARARGS},
    {"register_cleanup",     (PyCFunction) req_register_cleanup,     METH_VARARGS},
    {"send_http_header",     (PyCFunction) req_send_http_header,     METH_VARARGS},
    {"write",                (PyCFunction) req_write,                METH_VARARGS},
    { NULL, NULL } /* sentinel */
};


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

PyTypeObject MpRequest_Type = {
    PyObject_HEAD_INIT(&PyType_Type)
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



