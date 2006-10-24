/*
 * Copyright 2004 Apache Software Foundation 
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
 * requestobject.c 
 *
 * $Id$
 *
 */

#include "mod_python.h"

/* mod_ssl.h is not safe for inclusion in 2.0, so duplicate the
 * optional function declarations. */
APR_DECLARE_OPTIONAL_FN(char *, ssl_var_lookup,
                        (apr_pool_t *, server_rec *,
                         conn_rec *, request_rec *,
                         char *));
APR_DECLARE_OPTIONAL_FN(int, ssl_is_https, (conn_rec *));

/* Optional functions imported from mod_ssl when loaded: */
static APR_OPTIONAL_FN_TYPE(ssl_var_lookup) *optfn_ssl_var_lookup = NULL;
static APR_OPTIONAL_FN_TYPE(ssl_is_https) *optfn_is_https = NULL;


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

    result = PyObject_GC_New(requestobject, &MpRequest_Type);
    if (! result)
        return PyErr_NoMemory();

    result->dict = PyDict_New();
    if (!result->dict)
        return PyErr_NoMemory();
    result->request_rec = req;
    result->connection = NULL;
    result->server = NULL;
    result->headers_in = MpTable_FromTable(req->headers_in);
    result->headers_out = MpTable_FromTable(req->headers_out);
    result->err_headers_out = MpTable_FromTable(req->err_headers_out);
    result->subprocess_env = MpTable_FromTable(req->subprocess_env);
    result->notes = MpTable_FromTable(req->notes);
    result->phase = NULL;
    result->extension = NULL;
    result->content_type_set = 0;
    result->bytes_queued = 0;
    result->hlo = NULL;
    /* PYTHON 2.5: 'PyList_New' uses Py_ssize_t for input parameters */
    result->callbacks = PyList_New(0);
    if (!result->callbacks)
        return PyErr_NoMemory();
    result->rbuff = NULL;
    result->rbuff_pos = 0;
    result->rbuff_len = 0;

    /* we make sure that the object dictionary is there
     * before registering the object with the GC
     */
    PyObject_GC_Track(result);

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
    char *phase = NULL;
    char *handler = NULL;
    PyObject *callable = NULL;
    const char *dir = NULL;
    const char *currphase;

    if (! PyArg_ParseTuple(args, "ss|s", &phase, &handler, &dir)) {
        PyErr_Clear();
        if (! PyArg_ParseTuple(args, "sO|s", &phase, &callable, &dir)) {
            PyErr_SetString(PyExc_ValueError, 
                            "handler must be a string or callable object");
            return NULL;
        }
    }

    if (! valid_phase(phase)) {
        PyErr_SetString(PyExc_IndexError, 
                        apr_psprintf(self->request_rec->pool,
                                     "Invalid phase: %s", phase));
        return NULL;
    }

    if (callable) {
        if (!PyCallable_Check(callable)) {
            PyErr_SetString(PyExc_ValueError, 
                            "handler must be a string or callable object");
            return NULL;
        } else {
            /* Cache reference in list of callable handler objects
             * so that they can be dereferenced when request object
             * destroyed at end of phase. */
            if (PyList_Append(self->callbacks, callable) == -1)
                return NULL;
        }
    }

    /* Canonicalize path and add trailing slash at
     * this point if directory was provided. */

    if (dir) {

        char *newpath = 0;
        apr_status_t rv;

        rv = apr_filepath_merge(&newpath, NULL, dir,
                                APR_FILEPATH_TRUENAME,
                                self->request_rec->pool);

        /* If there is a failure, use the original path
         * which was supplied. */

        if (rv == APR_SUCCESS || rv == APR_EPATHWILD) {
            dir = newpath;
            if (dir[strlen(dir) - 1] != '/') {
                dir = apr_pstrcat(self->request_rec->pool, dir, "/", NULL);
            }
        }
        else {
            /* dir is from Python, so duplicate it */

            dir = apr_pstrdup(self->request_rec->pool, dir);
        }
    }

    /* handler is from Python, so duplicate it */

    handler = apr_pstrdup(self->request_rec->pool, handler);

    /* which phase are we processing? */
    currphase = PyString_AsString(self->phase);

    /* are we in same phase as what's being added? */
    if (strcmp(currphase, phase) == 0) {

        /* then just append to hlist */
        hlist_append(self->request_rec->pool, self->hlo->head,
                     handler, callable, dir, 0, NULL, NULL, 0, NULL, NOTSILENT,
                     self->hlo->head);
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
            hle = hlist_new(self->request_rec->pool, handler, callable, dir,
                            0, NULL, NULL, 0, NULL, NOTSILENT, self->hlo->head);
            apr_hash_set(req_config->dynhls, phase, APR_HASH_KEY_STRING, hle);
        }
        else {
            hlist_append(self->request_rec->pool, hle, handler, callable, dir,
                         0, NULL, NULL, 0, NULL, NOTSILENT, self->hlo->head);
        }
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.add_input_filter(request self, string name)
 **
 *     Specifies that a pre registered filter be added to input filter chain.
 */

static PyObject *req_add_input_filter(requestobject *self, PyObject *args)
{
    char *name;
    py_req_config *req_config;
    python_filter_ctx *ctx;

    if (! PyArg_ParseTuple(args, "s", &name)) 
        return NULL;

    req_config = (py_req_config *) ap_get_module_config(
                  self->request_rec->request_config, &python_module);

    if (apr_hash_get(req_config->in_filters, name, APR_HASH_KEY_STRING)) {
        ctx = (python_filter_ctx *) apr_pcalloc(self->request_rec->pool,
                                                sizeof(python_filter_ctx));
        ctx->name = apr_pstrdup(self->request_rec->pool, name);

        ap_add_input_filter(FILTER_NAME, ctx, self->request_rec,
                            self->request_rec->connection);
    } else {
        ap_add_input_filter(name, NULL, self->request_rec,
                            self->request_rec->connection);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.add_output_filter(request self, string name)
 **
 *     Specifies that a pre registered filter be added to output filter chain.
 */

static PyObject *req_add_output_filter(requestobject *self, PyObject *args)
{
    char *name;
    py_req_config *req_config;
    python_filter_ctx *ctx;

    if (! PyArg_ParseTuple(args, "s", &name)) 
        return NULL;

    req_config = (py_req_config *) ap_get_module_config(
                  self->request_rec->request_config, &python_module);

    if (apr_hash_get(req_config->out_filters, name, APR_HASH_KEY_STRING)) {
        ctx = (python_filter_ctx *) apr_pcalloc(self->request_rec->pool,
                                                sizeof(python_filter_ctx));
        ctx->name = apr_pstrdup(self->request_rec->pool, name);

        ap_add_output_filter(FILTER_NAME, ctx, self->request_rec,
                             self->request_rec->connection);
    } else {
        ap_add_output_filter(name, NULL, self->request_rec,
                             self->request_rec->connection);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.register_input_filter(request self, string name, string handler, list dir)
 **
 *     Registers an input filter active for life of the request.
 */

static PyObject *req_register_input_filter(requestobject *self, PyObject *args)
{
    char *name = NULL;
    char *handler = NULL;
    PyObject *callable = NULL;
    char *dir = NULL;
    py_req_config *req_config;
    py_handler *fh;

    if (! PyArg_ParseTuple(args, "ss|s", &name, &handler, &dir)) {
        PyErr_Clear();
        if (! PyArg_ParseTuple(args, "sO|s", &name, &callable, &dir)) {
            PyErr_SetString(PyExc_ValueError, 
                            "handler must be a string or callable object");
            return NULL;
        }
    }

    if (callable) {
        /* Cache reference in list of callable filter objects
         * so that they can be dereferenced when request object
         * destroyed at end of phase. */
        if (PyList_Append(self->callbacks, callable) == -1)
            return NULL;
    }

    req_config = (py_req_config *) ap_get_module_config(
                  self->request_rec->request_config, &python_module);

    fh = (py_handler *) apr_pcalloc(self->request_rec->pool,
                                    sizeof(py_handler));
    fh->handler = apr_pstrdup(self->request_rec->pool, handler);
    fh->callable = callable;
    fh->parent = self->hlo->head;

    /* Canonicalize path and add trailing slash at
     * this point if directory was provided. */

    if (dir) {

        char *newpath = 0;
        apr_status_t rv;

        rv = apr_filepath_merge(&newpath, NULL, dir,
                                APR_FILEPATH_TRUENAME,
                                self->request_rec->pool);

        /* If there is a failure, use the original path
         * which was supplied. */

        if (rv == APR_SUCCESS || rv == APR_EPATHWILD) {
            dir = newpath;
            if (dir[strlen(dir) - 1] != '/') {
                dir = apr_pstrcat(self->request_rec->pool, dir, "/", NULL);
            }
            fh->directory = dir;
        } else {
            fh->directory = apr_pstrdup(self->request_rec->pool, dir);
        }
    }

    apr_hash_set(req_config->in_filters,
                 apr_pstrdup(self->request_rec->pool, name),
                 APR_HASH_KEY_STRING, fh);

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.register_output_filter(request self, string name, string handler, list dir)
 **
 *     Registers an output filter active for life of the request.
 */

static PyObject *req_register_output_filter(requestobject *self, PyObject *args)
{
    char *name = NULL;
    char *handler = NULL;
    PyObject *callable = NULL;
    char *dir = NULL;
    py_req_config *req_config;
    py_handler *fh;

    if (! PyArg_ParseTuple(args, "ss|s", &name, &handler, &dir))  {
        PyErr_Clear();
        if (! PyArg_ParseTuple(args, "sO|s", &name, &callable, &dir)) {
            PyErr_SetString(PyExc_ValueError, 
                            "handler must be a string or callable object");
            return NULL;
        }
    }

    if (callable) {
        /* Cache reference in list of callable filter objects
         * so that they can be dereferenced when request object
         * destroyed at end of phase. */
        if (PyList_Append(self->callbacks, callable) == -1)
            return NULL;
    }

    req_config = (py_req_config *) ap_get_module_config(
                  self->request_rec->request_config, &python_module);

    fh = (py_handler *) apr_pcalloc(self->request_rec->pool,
                                    sizeof(py_handler));
    fh->handler = apr_pstrdup(self->request_rec->pool, handler);
    fh->callable = callable;
    fh->parent = self->hlo->head;

    /* Canonicalize path and add trailing slash at
     * this point if directory was provided. */

    if (dir) {

        char *newpath = 0;
        apr_status_t rv;

        rv = apr_filepath_merge(&newpath, NULL, dir,
                                APR_FILEPATH_TRUENAME,
                                self->request_rec->pool);

        /* If there is a failure, use the original path
         * which was supplied. */

        if (rv == APR_SUCCESS || rv == APR_EPATHWILD) {
            dir = newpath;
            if (dir[strlen(dir) - 1] != '/') {
                dir = apr_pstrcat(self->request_rec->pool, dir, "/", NULL);
            }
            fh->directory = dir;
        } else {
            fh->directory = apr_pstrdup(self->request_rec->pool, dir);
        }
    }

    apr_hash_set(req_config->out_filters,
                 apr_pstrdup(self->request_rec->pool, name),
                 APR_HASH_KEY_STRING, fh);

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

    /* PYTHON 2.5: 'PySequence_Length' uses Py_ssize_t for input parameters */
    len = PySequence_Length(methods);

    if (len) {

        PyObject *method;

        /* PYTHON 2.5: 'PySequence_GetItem' uses Py_ssize_t for input parameters */
        method = PySequence_GetItem(methods, 0);
        if (! PyString_Check(method)) {
            PyErr_SetString(PyExc_TypeError, 
                            "Methods must be strings");
            return NULL;
        }

        ap_allow_methods(self->request_rec, (reset == REPLACE_ALLOW), 
                         PyString_AS_STRING(method), NULL);

        for (i = 1; i < len; i++) {
            /* PYTHON 2.5: 'PySequence_GetItem' uses Py_ssize_t for input parameters */
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
 ** request.is_https(self)
 **
 * mod_ssl ssl_is_https() wrapper
 */

static PyObject * req_is_https(requestobject *self)
{
    int is_https;

    if (!optfn_is_https)
        optfn_is_https = APR_RETRIEVE_OPTIONAL_FN(ssl_is_https);

    is_https = optfn_is_https && optfn_is_https(self->request_rec->connection);

    return PyInt_FromLong(is_https);
}


/**
 ** request.ssl_var_lookup(self, string variable_name)
 **
 * mod_ssl ssl_var_lookup() wrapper
 */

static PyObject * req_ssl_var_lookup(requestobject *self, PyObject *args)
{
    char *var_name;

    if (! PyArg_ParseTuple(args, "s", &var_name))
        return NULL; /* error */

    if (!optfn_ssl_var_lookup)
        optfn_ssl_var_lookup = APR_RETRIEVE_OPTIONAL_FN(ssl_var_lookup);

    if (optfn_ssl_var_lookup) {
        const char *val;
        val = optfn_ssl_var_lookup(self->request_rec->pool,
                               self->request_rec->server,
                               self->request_rec->connection,
                               self->request_rec,
                               var_name);
        if (val)
            return PyString_FromString(val);
    }

    /* variable not found, or mod_ssl is not loaded */
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
 ** request.auth_name(self)
 **
 *  ap_auth_name wrapper
 */

static PyObject *req_auth_name(requestobject *self)
{
    const char *auth_name = ap_auth_name(self->request_rec);

    if (!auth_name) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    return PyString_FromString(auth_name);
}

/**
 ** request.auth_type(self)
 **
 *  ap_auth_type wrapper
 */

static PyObject *req_auth_type(requestobject *self)
{
    const char *auth_type = ap_auth_type(self->request_rec);

    if (!auth_type) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    return PyString_FromString(auth_type);
}

/**
 ** request.construct_url(self)
 **
 *  ap_construct_url wrapper
 */

static PyObject *req_construct_url(requestobject *self, PyObject *args)
{
    char *uri;

    if (! PyArg_ParseTuple(args, "s", &uri))
        return NULL;

    return PyString_FromString(ap_construct_url(self->request_rec->pool,
                               uri, self->request_rec));
}

/**
 ** request.discard_request_body(request self)
 **
 *      discard content supplied with request
 */

static PyObject * req_discard_request_body(requestobject *self)
{
    return PyInt_FromLong(ap_discard_request_body(self->request_rec));
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
    else
        return PyString_FromString("");
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
    apr_table_t* table = conf->options;

    int i;
    const apr_array_header_t* ah = apr_table_elts(table);
    apr_table_entry_t* elts = (apr_table_entry_t *) ah->elts;

    /*
     * We remove the empty values, since they cannot have been defined
     * by the directive.
     */
    for(i=0;i<ah->nelts;i++,elts++) {
        if(strlen(elts->val)==0) {
            apr_table_unset(table,elts->key);
        }
    }

    /* XXX shouldn't we free the apr_array_header_t* ah ? */

    return MpTable_FromTable(table);
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

    if (! PyArg_ParseTuple(args, "z|i", &message, &level))
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
 ** request.meets_conditions(req self)
 **
 *  ap_meets_conditions wrapper
 */

static PyObject * req_meets_conditions(requestobject *self) {
    return PyInt_FromLong(ap_meets_conditions(self->request_rec));
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

    /* PYTHON 2.5: 'PyString_FromStringAndSize' uses Py_ssize_t for input parameters */
    result = PyString_FromStringAndSize(NULL, len);

    /* possibly no more memory */
    if (result == NULL) 
        return NULL;

    buffer = PyString_AS_STRING((PyStringObject *) result);

    /* if anything left in the readline buffer */
    while ((self->rbuff_pos < self->rbuff_len) && (copied < len))
        buffer[copied++] = self->rbuff[self->rbuff_pos++];
    
    /* Free rbuff if we're done with it */
    if (self->rbuff_pos >= self->rbuff_len && self->rbuff != NULL) {
        free(self->rbuff);
        self->rbuff = NULL;
    }

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
        /* PYTHON 2.5: '_PyString_Resize' uses Py_ssize_t for input parameters */
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

        if (rc != OK) {
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
    /* PYTHON 2.5: 'PyString_FromStringAndSize' uses Py_ssize_t for input parameters */
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
                    /* PYTHON 2.5: '_PyString_Resize' uses Py_ssize_t for input parameters */
                    if(_PyString_Resize(&result, copied))
                        return NULL;

                /* fix for MODPYTHON-181 leak */
                if (self->rbuff_pos >= self->rbuff_len && self->rbuff != NULL) {
                    free(self->rbuff);
                    self->rbuff = NULL;
                } 

                return result;
            }
        }
    }

    /* Free old rbuff as the old contents have been copied over and
       we are about to allocate a new rbuff. Perhaps this could be reused
       somehow? */
    if (self->rbuff_pos >= self->rbuff_len && self->rbuff != NULL)
    {
        free(self->rbuff);
        self->rbuff = NULL;
    }

    /* if got this far, the buffer should be empty, we need to read more */
        
    /* create a read buffer
      
       The buffer len will be at least HUGE_STRING_LEN in size,
       to avoid memory fragmention
    */
    self->rbuff_len = len > HUGE_STRING_LEN ? len : HUGE_STRING_LEN;
    self->rbuff_pos = 0;
    self->rbuff = malloc(self->rbuff_len);
    if (! self->rbuff)
        return PyErr_NoMemory();

    /* read it in */
    Py_BEGIN_ALLOW_THREADS
        chunk_len = ap_get_client_block(self->request_rec, self->rbuff, 
                                        self->rbuff_len);
    Py_END_ALLOW_THREADS;

    /* ap_get_client_block could return -1 on error */
    if (chunk_len == -1) {

        /* Free rbuff since returning NULL here should end the request */
        free(self->rbuff);
        self->rbuff = NULL;

        PyErr_SetObject(PyExc_IOError, 
                        PyString_FromString("Client read error (Timeout?)"));
        return NULL;
    }
    
    bytes_read = chunk_len;

    /* if this is a "short read", try reading more */
    while ((chunk_len != 0 ) && (bytes_read + copied < len)) {

        Py_BEGIN_ALLOW_THREADS
            chunk_len = ap_get_client_block(self->request_rec, 
                                            self->rbuff + bytes_read, 
                                            self->rbuff_len - bytes_read);
        Py_END_ALLOW_THREADS

        if (chunk_len == -1) {

            /* Free rbuff since returning NULL here should end the request */
            free(self->rbuff);
            self->rbuff = NULL;

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

    /* Free rbuff if we're done with it */
    if (self->rbuff_pos >= self->rbuff_len && self->rbuff != NULL)
    {
        free(self->rbuff);
        self->rbuff = NULL;
    }

    /* resize if necessary */
    if (copied < len) 
        /* PYTHON 2.5: '_PyString_Resize' uses Py_ssize_t for input parameters */
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

    /* PYTHON 2.5: 'PyList_New' uses Py_ssize_t for input parameters */
    PyObject *result = PyList_New(0);
    PyObject *line, *rlargs;
    long sizehint = -1;
    long size = 0;
    long linesize;

    if (! PyArg_ParseTuple(args, "|l", &sizehint)) 
        return NULL;

    if (result == NULL)
        return PyErr_NoMemory();

    /* PYTHON 2.5: 'PyTuple_New' uses Py_ssize_t for input parameters */
    rlargs = PyTuple_New(0);
    if (result == NULL)
        return PyErr_NoMemory();

    line = req_readline(self, rlargs);
    /* PYTHON 2.5: 'PyString_Size' uses Py_ssize_t for input parameters */
    while (line && ((linesize=PyString_Size(line))>0)) {
        PyList_Append(result, line);
        size += linesize;
        if ((sizehint != -1) && (size >= sizehint))
            break;
        Py_DECREF(line);
        line = req_readline(self, args);
    }
    Py_XDECREF(line);

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
    PyObject *name_obj = NULL;
    char *name = NULL;

    if (! PyArg_ParseTuple(args, "O|O", &handler, &data))
        return NULL;  /* bad args */

    ci = (cleanup_info *)malloc(sizeof(cleanup_info));
    ci->request_rec = self->request_rec;
    ci->server_rec = self->request_rec->server;
    if (PyCallable_Check(handler)) {
        Py_INCREF(handler);
        ci->handler = handler;
        name_obj = python_interpreter_name();
        name = (char *)malloc(strlen(PyString_AsString(name_obj))+1);
        strcpy(name, PyString_AsString(name_obj));
        ci->interpreter = name;
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
 ** request.requires(self)
 **
 *     Interface to ap_requires()
 */

static PyObject * req_requires(requestobject *self)
{

    /* This function returns everything specified after the "requires"
       as is, without any attempts to parse/organize because
       "requires" args only need to be grokable by mod_auth if it is
       authoritative. When AuthAuthoritative is off, anything can
       follow requires, e.g. "requires role terminator".
    */

    const apr_array_header_t *reqs_arr = ap_requires(self->request_rec);
    require_line *reqs;
    int i, ti = 0;

    PyObject *result;

    if (!reqs_arr) {
        return Py_BuildValue("()");
    }

    /* PYTHON 2.5: 'PyTuple_New' uses Py_ssize_t for input parameters */
    result = PyTuple_New(reqs_arr->nelts);

    reqs = (require_line *) reqs_arr->elts;

    for (i = 0; i < reqs_arr->nelts; ++i) {
        if (reqs[i].method_mask & (AP_METHOD_BIT << self->request_rec->method_number)) {
        /* PYTHON 2.5: 'PyTuple_SetItem' uses Py_ssize_t for input parameters */
            PyTuple_SetItem(result, ti++, 
                            PyString_FromString(reqs[i].requirement));
        }
    }

    /* PYTHON 2.5: '_PyTuple_Resize' uses Py_ssize_t for input parameters */
    _PyTuple_Resize(&result, ti);

    return result;
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
 ** request.set_etag(request self)
 **
 *      sets the outgoing ETag header
 */

static PyObject * req_set_etag(requestobject *self, PyObject *args)
{
    ap_set_etag(self->request_rec);

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.set_last_modified(request self)
 **
 *      set the Last-modified header
 */

static PyObject * req_set_last_modified(requestobject *self, PyObject *args)
{
    ap_set_last_modified(self->request_rec);

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.update_mtime(request self, long mtime)
 **
 *      updates mtime attribute if newer
 */

static PyObject * req_update_mtime(requestobject *self, PyObject *args)
{
    double mtime;

    if (! PyArg_ParseTuple(args, "d", &mtime))
        return NULL;  /* bad args */

    ap_update_mtime(self->request_rec, apr_time_from_sec(mtime));

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.write(request self, string what, flush=1)
 **
 *      write output to the client
 */

static PyObject * req_write(requestobject *self, PyObject *args)
{
    int len;
    int rc;
    char *buff;
    int flush=1;

    if (! PyArg_ParseTuple(args, "s#|i", &buff, &len, &flush))
        return NULL;  /* bad args */

    if (len > 0 ) {

        Py_BEGIN_ALLOW_THREADS
        rc = ap_rwrite(buff, len, self->request_rec);
        if (flush && (rc != -1))
            rc = ap_rflush(self->request_rec);
        Py_END_ALLOW_THREADS
            if (rc == -1) {
                PyErr_SetString(PyExc_IOError, "Write failed, client closed connection.");
                return NULL;
            }
    }

    self->bytes_queued += len;

    Py_INCREF(Py_None);
    return Py_None;

}

/**
 ** request.flush(request self)
 **
 *      flush output buffer
 */

static PyObject * req_flush(requestobject *self)
{
    int rc;

    Py_BEGIN_ALLOW_THREADS
    rc = ap_rflush(self->request_rec);
    Py_END_ALLOW_THREADS
    if (rc == -1) {
        PyErr_SetString(PyExc_IOError, "Flush failed, client closed connection.");
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** request.sendfile
 **
 */

static PyObject * req_sendfile(requestobject *self, PyObject *args)
{
    char *fname;
    apr_file_t *fd;
    apr_size_t offset=0, len=-1, nbytes;
    apr_status_t status;
    PyObject * py_result = NULL;
    apr_finfo_t finfo;
    
    if (! PyArg_ParseTuple(args, "s|ll", &fname, &offset, &len))
        return NULL;  /* bad args */

    Py_BEGIN_ALLOW_THREADS
    status=apr_stat(&finfo, fname,
                    APR_FINFO_SIZE, self->request_rec->pool);
    Py_END_ALLOW_THREADS
    if (status != APR_SUCCESS) {
        PyErr_SetString(PyExc_IOError, "Could not stat file for reading");
        return NULL;
    }
    
    Py_BEGIN_ALLOW_THREADS                         
    status=apr_file_open(&fd, fname,
                         APR_READ, APR_OS_DEFAULT,
                         self->request_rec->pool);
    Py_END_ALLOW_THREADS
    if (status != APR_SUCCESS) {
        PyErr_SetString(PyExc_IOError, "Could not open file for reading");
        return NULL;
    }                         
    
    if (len==-1) len=finfo.size;
        
    Py_BEGIN_ALLOW_THREADS                         
        status = ap_send_fd(fd, self->request_rec, offset, 
                            len, &nbytes);
    Py_END_ALLOW_THREADS
    apr_file_close(fd);
    
    if (status != APR_SUCCESS) {
        PyErr_SetString(PyExc_IOError, "Write failed, client closed connection.");
        return NULL;
    }

    self->bytes_queued += len;

    py_result = PyLong_FromLong (nbytes);
    Py_INCREF(py_result);
    return py_result;
}

static PyMethodDef request_methods[] = {
    {"add_common_vars",       (PyCFunction) req_add_common_vars,       METH_NOARGS},
    {"add_handler",           (PyCFunction) req_add_handler,           METH_VARARGS},
    {"add_input_filter",      (PyCFunction) req_add_input_filter,      METH_VARARGS},
    {"add_output_filter",     (PyCFunction) req_add_output_filter,     METH_VARARGS},
    {"allow_methods",         (PyCFunction) req_allow_methods,         METH_VARARGS},
    {"auth_name",             (PyCFunction) req_auth_name,             METH_NOARGS},
    {"auth_type",             (PyCFunction) req_auth_type,             METH_NOARGS},
    {"construct_url",         (PyCFunction) req_construct_url,         METH_VARARGS},
    {"discard_request_body",  (PyCFunction) req_discard_request_body,  METH_NOARGS},
    {"get_config",            (PyCFunction) req_get_config,            METH_NOARGS},
    {"document_root",         (PyCFunction) req_document_root,         METH_NOARGS},
    {"flush",                 (PyCFunction) req_flush,                 METH_NOARGS},
    {"get_basic_auth_pw",     (PyCFunction) req_get_basic_auth_pw,     METH_NOARGS},
    {"get_addhandler_exts",   (PyCFunction) req_get_addhandler_exts,   METH_NOARGS},
    {"get_remote_host",       (PyCFunction) req_get_remote_host,       METH_VARARGS},
    {"get_options",           (PyCFunction) req_get_options,           METH_NOARGS},
    {"internal_redirect",     (PyCFunction) req_internal_redirect,     METH_VARARGS},
    {"is_https",              (PyCFunction) req_is_https,              METH_NOARGS},
    {"log_error",             (PyCFunction) req_log_error,             METH_VARARGS},
    {"meets_conditions",      (PyCFunction) req_meets_conditions,      METH_NOARGS},
    {"read",                  (PyCFunction) req_read,                  METH_VARARGS},
    {"readline",              (PyCFunction) req_readline,              METH_VARARGS},
    {"readlines",             (PyCFunction) req_readlines,             METH_VARARGS},
    {"register_cleanup",      (PyCFunction) req_register_cleanup,      METH_VARARGS},
    {"register_input_filter", (PyCFunction) req_register_input_filter, METH_VARARGS},
    {"register_output_filter", (PyCFunction) req_register_output_filter, METH_VARARGS},
    {"requires",              (PyCFunction) req_requires,              METH_NOARGS},
    {"send_http_header",      (PyCFunction) req_send_http_header,      METH_NOARGS},
    {"sendfile",              (PyCFunction) req_sendfile,              METH_VARARGS},
    {"set_content_length",    (PyCFunction) req_set_content_length,    METH_VARARGS},
    {"set_etag",              (PyCFunction) req_set_etag,              METH_NOARGS},
    {"set_last_modified",     (PyCFunction) req_set_last_modified,     METH_NOARGS},
    {"ssl_var_lookup",        (PyCFunction) req_ssl_var_lookup,        METH_VARARGS},
    {"update_mtime",          (PyCFunction) req_update_mtime,          METH_VARARGS},
    {"write",                 (PyCFunction) req_write,                 METH_VARARGS},
    { NULL, NULL } /* sentinel */
};


/* 
   These are offsets into the Apache request_rec structure.
   They are accessed via getset functions. Note that the types
   specified here are irrelevant if a function other than
   getreq_recmbr() is used. E.g. bytes_sent is a long long,
   and is retrieved via getreq_recmbr_off() which ignores what's
   here.
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
    {"sent_bodyct",        T_LONG,    OFF(sent_bodyct)},
    {"bytes_sent",         T_LONG,    OFF(bytes_sent)},
    {"mtime",              T_LONG,    OFF(mtime)},
    {"chunked",            T_INT,     OFF(chunked)},
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
    /* 
     * apparently at least ap_internal_fast_redirect blatently
     * substitute request members, and so we always have to make
     * sure that various apr_tables referenced haven't been
     * replaced in between handlers and we're left with a stale.
     */

    if (strcmp(name, "interpreter") == 0) {
        return python_interpreter_name();
    }
    else if (strcmp(name, "headers_in") == 0) {
        if (((tableobject*)self->headers_in)->table != self->request_rec->headers_in) 
            ((tableobject*)self->headers_in)->table = self->request_rec->headers_in;
        Py_INCREF(self->headers_in);
        return self->headers_in;
    }
    else if (strcmp(name, "headers_out") == 0) {
        if (((tableobject*)self->headers_out)->table != self->request_rec->headers_out) 
            ((tableobject*)self->headers_out)->table = self->request_rec->headers_out;
        Py_INCREF(self->headers_out);
        return self->headers_out;
    }
    else if (strcmp(name, "err_headers_out") == 0) {
        if (((tableobject*)self->err_headers_out)->table != self->request_rec->err_headers_out) 
            ((tableobject*)self->err_headers_out)->table = self->request_rec->err_headers_out;
        Py_INCREF(self->err_headers_out);
        return self->err_headers_out;
    }
    else if (strcmp(name, "subprocess_env") == 0) {
        if (((tableobject*)self->subprocess_env)->table != self->request_rec->subprocess_env) 
            ((tableobject*)self->subprocess_env)->table = self->request_rec->subprocess_env;
        Py_INCREF(self->subprocess_env);
        return self->subprocess_env;
    }
    else if (strcmp(name, "notes") == 0) {
        if (((tableobject*)self->notes)->table != self->request_rec->notes) 
            ((tableobject*)self->notes)->table = self->request_rec->notes;
        Py_INCREF(self->notes);
        return self->notes;
    }
    else if (strcmp(name, "_bytes_queued") == 0) {
        if (sizeof(apr_off_t) == sizeof(LONG_LONG)) {
            LONG_LONG l = self->bytes_queued;
            return PyLong_FromLongLong(l);
        }
        else {
            /* assume it's long */
            long l = self->bytes_queued;
            return PyLong_FromLong(l);
        }
    }
    else
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
        ap_set_content_type(self->request_rec, 
                            apr_pstrdup(self->request_rec->pool,
                                        PyString_AsString(val)));
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
    else if (strcmp(name, "ap_auth_type") == 0) {
        if (! PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "ap_auth_type must be a string");
            return -1;
        }
        self->request_rec->ap_auth_type = 
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
    else if (strcmp(name, "canonical_filename") == 0) {
        if (! PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "canonical_filename must be a string");
            return -1;
        }
        self->request_rec->canonical_filename = 
            apr_pstrdup(self->request_rec->pool, PyString_AsString(val));
        return 0;
    }
    else if (strcmp(name, "path_info") == 0) {
        if (! PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "path_info must be a string");
            return -1;
        }
        self->request_rec->path_info = 
            apr_pstrdup(self->request_rec->pool, PyString_AsString(val));
        return 0;
    }
    else if (strcmp(name, "handler") == 0) {
        if (! PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "handler must be a string");
            return -1;
        }
        self->request_rec->handler = 
            apr_pstrdup(self->request_rec->pool, PyString_AsString(val));
        return 0;
    }
    else if (strcmp(name, "uri") == 0) {
        if (! PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "uri must be a string");
            return -1;
        }
        self->request_rec->uri = 
            apr_pstrdup(self->request_rec->pool, PyString_AsString(val));
        return 0;
    }
    else if (strcmp(name, "finfo") == 0) {
        finfoobject *f;
        if (! MpFinfo_Check(val)) {
            PyErr_SetString(PyExc_TypeError, "finfo must be a finfoobject");
            return -1;
        }
        f = (finfoobject *)val;
        self->request_rec->finfo = *f->finfo;
        self->request_rec->finfo.fname = apr_pstrdup(self->request_rec->pool,
                                                      f->finfo->fname);
        self->request_rec->finfo.name = apr_pstrdup(self->request_rec->pool,
                                                      f->finfo->name);

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
 ** getreq_recmbr_off
 **
 *    Retrieves apr_off_t request_rec members
 */

static PyObject *getreq_recmbr_off(requestobject *self, void *name) 
{
    PyMemberDef *md = find_memberdef(request_rec_mbrs, name);
    char *addr = (char *)self->request_rec + md->offset;
    if (sizeof(apr_off_t) == sizeof(LONG_LONG)) {
        LONG_LONG l = *(LONG_LONG*)addr;
        return PyLong_FromLongLong(l);
    }
    else {
        /* assume it's long */
        long l = *(long*)addr;
        return PyLong_FromLong(l);
    }
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
        *(apr_array_header_t **)((char *)self->request_rec + md->offset);

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
        *(ap_method_list_t **)((char *)self->request_rec + md->offset);

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

    return MpFinfo_FromFinfo(fi);
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
        if (!self->connection && self->request_rec->connection) {
            self->connection = MpConn_FromConn(self->request_rec->connection);
        }
        result = self->connection;
    }
    else if (strcmp(name, "server") == 0) {
        if (!self->server && self->request_rec->server) {
            self->server = MpServer_FromServer(self->request_rec->server);
        }
        result = self->server;
    }
    else if (strcmp(name, "next") == 0) {
        if (self->request_rec->next) {
            result = (PyObject*)python_get_request_object(
                self->request_rec->next, 0);
        }
    }
    else if (strcmp(name, "prev") == 0) {
        if (self->request_rec->prev) {
            result = (PyObject*)python_get_request_object(
                self->request_rec->prev, 0);
        }
    }
    else if (strcmp(name, "main") == 0) {
        if (self->request_rec->main) {
            result = (PyObject*)python_get_request_object(
                self->request_rec->main, 0);
        }
    }

    if (!result)
        result = Py_None;

    Py_INCREF(result);
    return result;

}

static PyGetSetDef request_getsets[] = {
    {"interpreter", (getter)getreq_recmbr, NULL, "Python interpreter name", "interpreter"},
    {"connection", (getter)getmakeobj, NULL, "Connection object", "connection"},
    {"server",     (getter)getmakeobj, NULL, "Server object", "server"},
    {"next",       (getter)getmakeobj, NULL, "If redirected, pointer to the to request", "next"},
    {"prev",       (getter)getmakeobj, NULL, "If redirected, pointer to the from request", "prev"},
    {"main",       (getter)getmakeobj, NULL, "If subrequest, pointer to the main request", "main"},
    {"the_request", (getter)getreq_recmbr, NULL, "First line of request", "the_request"},
    {"assbackwards", (getter)getreq_recmbr, (setter)setreq_recmbr, "HTTP/0.9 \"simple\" request", "assbackwards"},
    {"proxyreq",     (getter)getreq_recmbr, (setter)setreq_recmbr, "A proxy request: one of apache.PROXYREQ_* values", "proxyreq"},
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
    {"sent_bodyct",  (getter)getreq_recmbr_off, NULL, "Byte count in stream for body", "sent_bodyct"},
    {"bytes_sent",   (getter)getreq_recmbr_off, NULL, "Bytes sent", "bytes_sent"},
    {"mtime",        (getter)getreq_recmbr_time, NULL, "Time resource was last modified", "mtime"},
    {"chunked",      (getter)getreq_recmbr, NULL, "Sending chunked transfer-coding", "chunked"},
    {"range",        (getter)getreq_recmbr, NULL, "The Range: header", "range"},
    {"clength",      (getter)getreq_recmbr_off, NULL, "The \"real\" contenct length", "clength"},
    {"remaining",    (getter)getreq_recmbr_off, NULL, "Bytes left to read", "remaining"},
    {"read_length",  (getter)getreq_recmbr_off, NULL, "Bytes that have been read", "read_length"},
    {"read_body",    (getter)getreq_recmbr, NULL, "How the request body should be read", "read_body"},
    {"read_chunked", (getter)getreq_recmbr, NULL, "Reading chunked transfer-coding", "read_chunked"},
    {"expecting_100", (getter)getreq_recmbr, NULL, "Is client waitin for a 100 response?", "expecting_100"},
    {"content_type",  (getter)getreq_recmbr, (setter)setreq_recmbr, "Content type", "content_type"},
    {"handler",       (getter)getreq_recmbr, (setter)setreq_recmbr, "The handler string", "handler"},
    {"content_encoding", (getter)getreq_recmbr, NULL, "How to encode the data", "content_encoding"},
    {"content_languages", (getter)getreq_rec_ah, NULL, "Content languages", "content_languages"},
    {"vlist_validator", (getter)getreq_recmbr, NULL, "Variant list validator (if negotiated)", "vlist_validator"},
    {"user",          (getter)getreq_recmbr, (setter)setreq_recmbr, "If authentication check was made, the user name", "user"},
    {"ap_auth_type",  (getter)getreq_recmbr, (setter)setreq_recmbr, "If authentication check was made, auth type", "ap_auth_type"},
    {"no_cache",      (getter)getreq_recmbr, (setter)setreq_recmbr, "This response in non-cacheable", "no_cache"},
    {"no_local_copy", (getter)getreq_recmbr, (setter)setreq_recmbr, "There is no local copy of the response", "no_local_copy"},
    {"unparsed_uri",  (getter)getreq_recmbr, NULL, "The URI without any parsing performed", "unparsed_uri"},
    {"uri",           (getter)getreq_recmbr, (setter)setreq_recmbr, "The path portion of URI", "uri"},
    {"filename",      (getter)getreq_recmbr, (setter)setreq_recmbr, "The file name on disk that this request corresponds to", "filename"},
    {"canonical_filename", (getter)getreq_recmbr, (setter)setreq_recmbr, "The true filename (req.filename is canonicalized if they dont match)", "canonical_filename"},
    {"path_info",     (getter)getreq_recmbr, (setter)setreq_recmbr, "Path_info, if any", "path_info"},
    {"args",          (getter)getreq_recmbr, NULL, "QUERY_ARGS, if any", "args"},
    {"finfo",         (getter)getreq_rec_fi, (setter)setreq_recmbr, "File information", "finfo"},
    {"parsed_uri",    (getter)getreq_rec_uri, NULL, "Components of URI", "parsed_uri"},
    {"used_path_info", (getter)getreq_recmbr, NULL, "Flag to accept or reject path_info on current request", "used_path_info"},
    {"headers_in", (getter)getreq_recmbr, NULL, "Incoming headers", "headers_in"},
    {"headers_out", (getter)getreq_recmbr, NULL, "Outgoing headers", "headers_out"},
    {"err_headers_out", (getter)getreq_recmbr, NULL, "Outgoing headers for errors", "err_headers_out"},
    {"subprocess_env", (getter)getreq_recmbr, NULL, "Subprocess environment", "subprocess_env"},
    {"notes", (getter)getreq_recmbr, NULL, "Notes", "notes"},
    /* XXX per_dir_config */
    /* XXX request_config */
    /* XXX htaccess */
    /* XXX filters and eos */
    {"eos_sent", (getter)getreq_recmbr, NULL, "EOS bucket sent", "eos_sent"},
    {"_bytes_queued", (getter)getreq_recmbr, NULL, "Bytes queued by handler", "_bytes_queued"},
    {NULL}  /* Sentinel */
};

#undef OFF
#define OFF(x) offsetof(requestobject, x)

static struct PyMemberDef request_members[] = {
    {"_content_type_set",  T_INT,       OFF(content_type_set),  RO},
    {"phase",              T_OBJECT,    OFF(phase),             RO},
    {"extension",          T_STRING,    OFF(extension),         RO},
    {"hlist",              T_OBJECT,    OFF(hlo),               RO},
    {NULL}  /* Sentinel */
};

/**
 ** request_tp_clear
 **
 *    
 */

#ifndef CLEAR_REQUEST_MEMBER 
#define CLEAR_REQUEST_MEMBER(member)\
    tmp = (PyObject *) member;\
    member = NULL;\
    Py_XDECREF(tmp)
#endif

static int request_tp_clear(requestobject *self)
{   
    PyObject* tmp;

    CLEAR_REQUEST_MEMBER(self->dict);
    CLEAR_REQUEST_MEMBER(self->connection);
    CLEAR_REQUEST_MEMBER(self->server);
    CLEAR_REQUEST_MEMBER(self->headers_in);
    CLEAR_REQUEST_MEMBER(self->headers_out);
    CLEAR_REQUEST_MEMBER(self->err_headers_out);
    CLEAR_REQUEST_MEMBER(self->subprocess_env);
    CLEAR_REQUEST_MEMBER(self->notes);
    CLEAR_REQUEST_MEMBER(self->phase);
    CLEAR_REQUEST_MEMBER(self->hlo);
    CLEAR_REQUEST_MEMBER(self->callbacks);
    
    return 0;
}


/**
 ** request_dealloc
 **
 *
 */

static void request_tp_dealloc(requestobject *self)
{  
    /* de-register the object from the GC
     * before its deallocation, to prevent the
     * GC to run on a partially de-allocated object
     */
    PyObject_GC_UnTrack(self);
    
    /* self->rebuff is used by req_readline.
     * It may not have been freed if req_readline was not
     * enough times to consume rbuff's contents.
     */
    if (self->rbuff != NULL)
        free(self->rbuff); 

    request_tp_clear(self);
  
    PyObject_GC_Del(self);
}

/**
 ** request_tp_traverse
 **
 *    Traversal of the request object
 */
#ifndef VISIT_REQUEST_MEMBER 
#define VISIT_REQUEST_MEMBER(member, visit, arg)\
    if (member) {\
        result = visit(member, arg);\
        if (result)\
            return result;\
    }
#endif

static int request_tp_traverse(requestobject* self, visitproc visit, void *arg) {
    int result;
    VISIT_REQUEST_MEMBER(self->dict, visit, arg);
    VISIT_REQUEST_MEMBER(self->connection, visit, arg);
    VISIT_REQUEST_MEMBER(self->server, visit, arg);
    VISIT_REQUEST_MEMBER(self->headers_in, visit, arg);
    VISIT_REQUEST_MEMBER(self->headers_out, visit, arg);
    VISIT_REQUEST_MEMBER(self->err_headers_out, visit, arg);
    VISIT_REQUEST_MEMBER(self->subprocess_env, visit, arg);
    VISIT_REQUEST_MEMBER(self->notes, visit, arg);
    VISIT_REQUEST_MEMBER(self->phase, visit, arg);
    
    /* no need to Py_DECREF(dict) since the reference is borrowed */
    return 0;
}
static char request_doc[] =
"Apache request_rec structure\n";

PyTypeObject MpRequest_Type = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_request",
    sizeof(requestobject),
    0,
    (destructor)request_tp_dealloc,       /*tp_dealloc*/
    0,                                 /*tp_print*/
    0,                                 /*tp_getattr*/
    0,                                 /*tp_setattr*/
    0,                                 /*tp_compare*/
    0,                                 /*tp_repr*/
    0,                                 /*tp_as_number*/
    0,                                 /*tp_as_sequence*/
    0,                                 /*tp_as_mapping*/
    0,                                 /*tp_hash*/
    0,                                 /* tp_call */
    0,                                 /* tp_str */
    PyObject_GenericGetAttr,           /* tp_getattro */
    PyObject_GenericSetAttr,           /* tp_setattro */
    0,                                 /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT |  
    Py_TPFLAGS_BASETYPE|  
    Py_TPFLAGS_HAVE_GC ,               /* tp_flags */
    request_doc,                       /* tp_doc */
    (traverseproc)request_tp_traverse, /* tp_traverse */
    /* PYTHON 2.5: 'inquiry' should be perhaps replaced with 'lenfunc' */ 
    (inquiry)request_tp_clear,         /* tp_clear */
    0,                                 /* tp_richcompare */
    0,                                 /* tp_weaklistoffset */
    0,                                 /* tp_iter */
    0,                                 /* tp_iternext */
    request_methods,                   /* tp_methods */
    request_members,                   /* tp_members */
    request_getsets,                   /* tp_getset */
    0,                                 /* tp_base */
    0,                                 /* tp_dict */
    0,                                 /* tp_descr_get */
    0,                                 /* tp_descr_set */
    offsetof(requestobject, dict),     /* tp_dictoffset */
    0,                                 /* tp_init */
    0,                                 /* tp_alloc */
    0,                                 /* tp_new */
    0,                                 /* tp_free */
};






