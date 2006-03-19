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
 * _apachemodule.c 
 *
 * $Id$
 *
 */

#include "mod_python.h"

/* A referende to the _apache.SERVER_RETURN */

PyObject *Mp_ServerReturn;

/** 
 ** mp_log_error
 **
 *  A wrapper to ap_log_error
 * 
 *  mp_log_error(string message, int level, server server)
 *
 */

static PyObject * mp_log_error(PyObject *self, PyObject *args)
{

    int level = 0;
    char *message = NULL;
    serverobject *server = NULL;
    server_rec *serv_rec;

    if (! PyArg_ParseTuple(args, "z|iO", &message, &level, &server)) 
        return NULL; /* error */

    if (message) {

        if (! level) 
            level = APLOG_NOERRNO|APLOG_ERR;
      
        if (!server || (PyObject *)server == Py_None)
            serv_rec = NULL;
        else {
            if (! MpServer_Check(server)) {
                PyErr_BadArgument();
                return NULL;
            }
            serv_rec = server->server;
        }
        ap_log_error(APLOG_MARK, level, 0, serv_rec, "%s", message);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** parse_qs
 **
 *   This is a C version of cgi.parse_qs
 */

static PyObject *parse_qs(PyObject *self, PyObject *args)
{

    PyObject *pairs, *dict;
    int i, n, len, lsize;
    char *qs;
    int keep_blank_values = 0;
    int strict_parsing = 0; /* XXX not implemented */

    if (! PyArg_ParseTuple(args, "s|ii", &qs, &keep_blank_values, 
                           &strict_parsing)) 
        return NULL; /* error */

    /* split query string by '&' and ';' into a list of pairs */
    pairs = PyList_New(0);
    if (pairs == NULL)
        return NULL;

    i = 0;
    len = strlen(qs);

    while (i < len) {

        PyObject *pair;
        char *cpair;
        int j = 0;

        pair = PyString_FromStringAndSize(NULL, len);
        if (pair == NULL)
            return NULL;

        /* split by '&' or ';' */
        cpair = PyString_AS_STRING(pair);
        while ((qs[i] != '&') && (qs[i] != ';') && (i < len)) {
            /* replace '+' with ' ' */
            cpair[j] = (qs[i] == '+') ? ' ' : qs[i];
            i++;
            j++;
        }

        if (j) {
            _PyString_Resize(&pair, j);
            if (pair)
                PyList_Append(pairs, pair);
        }

        Py_XDECREF(pair);
        i++;
    }

    /*
     * now we have a list of "abc=def" string (pairs), let's split 
     * them all by '=' and put them in a dictionary.
     */
    
    dict = PyDict_New();
    if (dict == NULL)
        return NULL;

    lsize = PyList_Size(pairs);
    n = 0;

    while (n < lsize) {

        PyObject *pair, *key, *val;
        char *cpair, *ckey, *cval;
        int k, v;

        pair = PyList_GET_ITEM(pairs, n);
        cpair = PyString_AS_STRING(pair);

        len = strlen(cpair);
        key = PyString_FromStringAndSize(NULL, len);
        if (key == NULL) 
            return NULL;
        val = PyString_FromStringAndSize(NULL, len);
        if (val == NULL) 
            return NULL;

        ckey = PyString_AS_STRING(key);
        cval = PyString_AS_STRING(val);

        i = 0;
        k = 0;
        v = 0;
        while (i < len) {
            if (cpair[i] != '=') {
                ckey[k] = cpair[i];
                k++;
                i++;
            }
            else {
                i++;      /* skip '=' */
                while (i < len) {
                    cval[v] = cpair[i];
                    v++;
                    i++;
                }
            }
        }

        ckey[k] = '\0';
        cval[v] = '\0';

        if (keep_blank_values || (v > 0)) {

            ap_unescape_url(ckey);
            ap_unescape_url(cval);

            _PyString_Resize(&key, strlen(ckey));
            _PyString_Resize(&val, strlen(cval));

            if (key && val) {

                ckey = PyString_AS_STRING(key);
                cval = PyString_AS_STRING(val);
        
                if (PyMapping_HasKeyString(dict, ckey)) {
                    PyObject *list;
                    list = PyDict_GetItem(dict, key);
                    PyList_Append(list, val);
                    /* PyDict_GetItem is a borrowed ref, no decref */
                }
                else {
                    PyObject *list;
                    list = Py_BuildValue("[O]", val);
                    PyDict_SetItem(dict, key, list);
                    Py_DECREF(list);
                }
            }
        }

        Py_XDECREF(key);
        Py_XDECREF(val);

        n++;
    }

    Py_DECREF(pairs);
    return dict;
}

/**
 ** parse_qsl
 **
 *   This is a C version of cgi.parse_qsl
 */

static PyObject *parse_qsl(PyObject *self, PyObject *args)
{

    PyObject *pairs;
    int i, len;
    char *qs;
    int keep_blank_values = 0;
    int strict_parsing = 0; /* XXX not implemented */

    if (! PyArg_ParseTuple(args, "s|ii", &qs, &keep_blank_values, 
                           &strict_parsing)) 
        return NULL; /* error */

    /* split query string by '&' and ';' into a list of pairs */
    pairs = PyList_New(0);
    if (pairs == NULL)
        return NULL;

    i = 0;
    len = strlen(qs);

    while (i < len) {

        PyObject *pair, *key, *val;
        char *cpair, *ckey, *cval;
        int plen, j, p, k, v;

        pair = PyString_FromStringAndSize(NULL, len);
        if (pair == NULL)
            return NULL;

        /* split by '&' or ';' */
        cpair = PyString_AS_STRING(pair);
        j = 0;
        while ((qs[i] != '&') && (qs[i] != ';') && (i < len)) {
            /* replace '+' with ' ' */
            cpair[j] = (qs[i] == '+') ? ' ' : qs[i];
            i++;
            j++;
        }

        if (j == 0) {
            Py_XDECREF(pair);
            i++;
            continue;
        }

        cpair[j] = '\0';
        _PyString_Resize(&pair, j);
        cpair = PyString_AS_STRING(pair);

        /* split the "abc=def" pair */
        plen = strlen(cpair);
        key = PyString_FromStringAndSize(NULL, plen);
        if (key == NULL) 
            return NULL;
        val = PyString_FromStringAndSize(NULL, plen);
        if (val == NULL) 
            return NULL;

        ckey = PyString_AS_STRING(key);
        cval = PyString_AS_STRING(val);

        p = 0;
        k = 0;
        v = 0;
        while (p < plen) {
            if (cpair[p] != '=') {
                ckey[k] = cpair[p];
                k++;
                p++;
            }
            else {
                p++;      /* skip '=' */
                while (p < plen) {
                    cval[v] = cpair[p];
                    v++;
                    p++;
                }
            }
        }
        ckey[k] = '\0';
        cval[v] = '\0';

        if (keep_blank_values || (v > 0)) {

            ap_unescape_url(ckey);
            ap_unescape_url(cval);

            _PyString_Resize(&key, strlen(ckey));
            _PyString_Resize(&val, strlen(cval));

            if (key && val)
                PyList_Append(pairs, Py_BuildValue("(O,O)", key, val));

        }
        Py_XDECREF(pair);
        Py_XDECREF(key);
        Py_XDECREF(val);
        i++;
    }

    return pairs;
}

/**
 ** config_tree
 **
 *   Returns a copy of the config tree
 */

static PyObject *config_tree(void)
{
    return cfgtree_walk(ap_conftree);
}

/**
 ** server_root
 **
 *   Returns ServerRoot
 */

static PyObject *server_root(void)
{
    return PyString_FromString(ap_server_root);
}

/**
 ** _global_lock
 **
 *   Lock one of our global_mutexes
 */

static PyObject *_global_lock(PyObject *self, PyObject *args)
{

    PyObject *server;
    PyObject *key;
    server_rec *s;
    py_global_config *glb;
    int index = -1;
    apr_status_t rv;

    if (! PyArg_ParseTuple(args, "OO|i", &server, &key, &index)) 
        return NULL;

    if (!  MpServer_Check(server)) {
        PyErr_SetString(PyExc_TypeError,
                        "First argument must be a server object");
        return NULL;
    }

    s = ((serverobject *)server)->server;

    apr_pool_userdata_get((void **)&glb, MP_CONFIG_KEY,
                          s->process->pool);
    
    if ((index >= (glb->nlocks)) || (index < -1)) {
        ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s,
                     "Index %d is out of range for number of global mutex locks", index);
        PyErr_SetString(PyExc_ValueError,
                        "Lock index is out of range for number of global mutex locks");
        return NULL;
    }
    
    if (index == -1) {

        int hash = PyObject_Hash(key);
        if (hash == -1) {
            return NULL;
        }
        else {
            hash = abs(hash);
        }

        /* note that this will never result in 0,
         * which is reserved for things like dbm
         * locking (see Session.py)
         */
        
        index = (hash % (glb->nlocks-1)+1);
    }

/*     ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s, */
/*               "_global_lock at index %d from pid %d", index, getpid()); */
    Py_BEGIN_ALLOW_THREADS
    rv = apr_global_mutex_lock(glb->g_locks[index]);        
    Py_END_ALLOW_THREADS                               
    if (rv != APR_SUCCESS) {
        ap_log_error(APLOG_MARK, APLOG_WARNING, rv, s,
                     "Failed to acquire global mutex lock at index %d", index);
        PyErr_SetString(PyExc_ValueError,
                        "Failed to acquire global mutex lock");
        return NULL;
    }
/*     ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s, */
/*               "_global_lock DONE at index %d from pid %d", index, getpid()); */
        
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** _global_trylock
 **
 *   Try to lock one of our global_mutexes
 */

static PyObject *_global_trylock(PyObject *self, PyObject *args)
{

    PyObject *server;
    PyObject *key;
    server_rec *s;
    py_global_config *glb;
    int index = -1;
    apr_status_t rv;

    if (! PyArg_ParseTuple(args, "OO|i", &server, &key, &index)) 
        return NULL;

    if (!  MpServer_Check(server)) {
        PyErr_SetString(PyExc_TypeError,
                        "First argument must be a server object");
        return NULL;
    }

    s = ((serverobject *)server)->server;

    apr_pool_userdata_get((void **)&glb, MP_CONFIG_KEY,
                          s->process->pool);

    if ((index >= (glb->nlocks)) || (index < -1)) {
        ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s,
                     "Index %d is out of range for number of global mutex locks", index);
        PyErr_SetString(PyExc_ValueError,
                        "Lock index is out of range for number of global mutex locks");
        return NULL;
    }
   
    if (index == -1) {

        int hash = PyObject_Hash(key);
        if (hash == -1) {
            return NULL;
        }
        else {
            hash = abs(hash);
        }

        /* note that this will never result in 0,
         * which is reserved for things like dbm
         * locking (see Session.py)
         */
        
        index = (hash % (glb->nlocks-1)+1);
    }

    /*  
     * ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s,
     *           "_global_trylock at index %d from pid %d", index, getpid());
     */
    Py_BEGIN_ALLOW_THREADS
    rv = apr_global_mutex_trylock(glb->g_locks[index]);        
    Py_END_ALLOW_THREADS
    
    if (rv == APR_SUCCESS) {
        /*
         * ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s,
         *         "_global_trylock DONE at index %d from pid %d", index, getpid());
         */
        Py_INCREF(Py_True);
        return Py_True;
    }
    else if(APR_STATUS_IS_EBUSY(rv)) {
        /*
         * ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s,
         *         "_global_trylock BUSY at index %d from pid %d", index, getpid());
         */
        Py_INCREF(Py_False);
        return Py_False;
    }
    else {
        ap_log_error(APLOG_MARK, APLOG_WARNING, rv, s,
                     "Failed to acquire global mutex lock at index %d", index);
        PyErr_SetString(PyExc_ValueError,
                        "Failed to acquire global mutex lock");
        return NULL;
    }
}

/**
 ** _global_unlock
 **
 *   Unlock one of our global_mutexes
 */

static PyObject *_global_unlock(PyObject *self, PyObject *args)
{

    PyObject *server;
    PyObject *key;
    server_rec *s;
    py_global_config *glb;
    int index = -1;
    apr_status_t rv;

    if (! PyArg_ParseTuple(args, "OO|i", &server, &key, &index)) 
        return NULL;

    if (!  MpServer_Check(server)) {
        PyErr_SetString(PyExc_TypeError,
                        "First argument must be a server object");
        return NULL;
    }

    s = ((serverobject *)server)->server;

    apr_pool_userdata_get((void **)&glb, MP_CONFIG_KEY,
                          s->process->pool);

    if ((index >= (glb->nlocks)) || (index < -1)) {
        ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s,
                     "Index %d is out of range for number of global mutex locks", index);
        PyErr_SetString(PyExc_ValueError,
                        "Lock index is out of range for number of global mutex locks");
        return NULL;
    }
   
    if (index == -1) {

        int hash = PyObject_Hash(key);
        if (hash == -1) {
            return NULL;
        }
        else {
            hash = abs(hash);
        }

        /* note that this will never result in 0,
         * which is reserved for things like dbm
         * locking (see Session.py)
         */
        
        index = (hash % (glb->nlocks-1)+1);
    }
    
/*     ap_log_error(APLOG_MARK, APLOG_WARNING, 0, s, */
/*                      "_global_unlock at index %d from pid %d", index, getpid()); */
    if ((rv = apr_global_mutex_unlock(glb->g_locks[index])) != APR_SUCCESS) {
        ap_log_error(APLOG_MARK, APLOG_WARNING, rv, s,
                     "Failed to release global mutex lock at index %d", index);
        PyErr_SetString(PyExc_ValueError,
                        "Failed to release global mutex lock");
        return NULL;
    }
        
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** mpm_query
 **
 *   ap_mpm_query interface
 */

static PyObject *mpm_query(PyObject *self, PyObject *code)
{
    int result;

    if (!PyInt_Check(code)) {
        PyErr_SetString(PyExc_TypeError,
                        "The argument must be an integer");
        return NULL;
    }

    ap_mpm_query(PyInt_AS_LONG(code), &result);
    
    return PyInt_FromLong(result);
}

/**
 ** register_cleanup(interpreter, server, handler, data)
 **
 *    more low level version of request.register_cleanup where it is
 *    necessary to specify the actual interpreter name. the server pool
 *    is used. the server pool gets destroyed before the child dies or
 *    when the whole process dies in multithreaded situations.
 */

static PyObject *register_cleanup(PyObject *self, PyObject *args)
{

    cleanup_info *ci;
    char *interpreter = NULL;
    serverobject *server = NULL;
    PyObject *handler = NULL;
    PyObject *data = NULL;

    if (! PyArg_ParseTuple(args, "sOO|O", &interpreter, &server, &handler, &data))
        return NULL; 

    if (! MpServer_Check(server)) {
        PyErr_SetString(PyExc_ValueError, 
                        "second argument must be a server object");
        return NULL;
    }
    else if(!PyCallable_Check(handler)) {
        PyErr_SetString(PyExc_ValueError, 
                        "third argument must be a callable object");
        return NULL;
    }
    
    ci = (cleanup_info *)malloc(sizeof(cleanup_info));
    ci->request_rec = NULL;
    ci->server_rec = server->server;
    Py_INCREF(handler);
    ci->handler = handler;
    ci->interpreter = strdup(interpreter);
    if (data) {
        Py_INCREF(data);
        ci->data = data;
    }
    else {
        Py_INCREF(Py_None);
        ci->data = Py_None;
    }
    
    apr_pool_cleanup_register(child_init_pool, ci, python_cleanup, 
                              apr_pool_cleanup_null);
    
    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** exists_config_define(name)
 **
 *  Check for a definition from the server command line.
 */

static PyObject *exists_config_define(PyObject *self, PyObject *args)
{

    char *name = NULL;

    if (! PyArg_ParseTuple(args, "s", &name))
        return NULL; 

    if(ap_exists_config_define(name)) {
        Py_INCREF(Py_True);
        return Py_True;
    }
    else {
        Py_INCREF(Py_False);
        return Py_False;
    }
}

/* methods of _apache */
struct PyMethodDef _apache_module_methods[] = {
    {"config_tree",           (PyCFunction)config_tree,          METH_NOARGS},
    {"log_error",             (PyCFunction)mp_log_error,         METH_VARARGS},
    {"mpm_query",             (PyCFunction)mpm_query,            METH_O},
    {"parse_qs",              (PyCFunction)parse_qs,             METH_VARARGS},
    {"parse_qsl",             (PyCFunction)parse_qsl,            METH_VARARGS},
    {"server_root",           (PyCFunction)server_root,          METH_NOARGS},
    {"register_cleanup",      (PyCFunction)register_cleanup,     METH_VARARGS},
    {"exists_config_define",  (PyCFunction)exists_config_define, METH_VARARGS},
    {"_global_lock",          (PyCFunction)_global_lock,         METH_VARARGS},
    {"_global_trylock",       (PyCFunction)_global_trylock,      METH_VARARGS},
    {"_global_unlock",        (PyCFunction)_global_unlock,       METH_VARARGS},
    {NULL, NULL} /* sentinel */
};

/* Module initialization */

DL_EXPORT(void) init_apache()
{
    PyObject *m, *d, *o;

    /* initialize types XXX break windows? */
    MpTable_Type.ob_type = &PyType_Type; 
    MpTableIter_Type.ob_type = &PyType_Type;
    MpServer_Type.ob_type = &PyType_Type;
    MpConn_Type.ob_type = &PyType_Type;  
    MpRequest_Type.ob_type = &PyType_Type; 
    MpFilter_Type.ob_type = &PyType_Type;
    MpHList_Type.ob_type = &PyType_Type;

    m = Py_InitModule("_apache", _apache_module_methods);
    d = PyModule_GetDict(m);
    Mp_ServerReturn = PyErr_NewException("_apache.SERVER_RETURN", NULL, NULL);
    if (Mp_ServerReturn == NULL)
        return;
    PyDict_SetItemString(d, "SERVER_RETURN", Mp_ServerReturn);

    PyDict_SetItemString(d, "table", (PyObject *)&MpTable_Type);

    o = PyInt_FromLong(AP_CONN_UNKNOWN);
    PyDict_SetItemString(d, "AP_CONN_UNKNOWN", o);
    Py_DECREF(o);
    o = PyInt_FromLong(AP_CONN_CLOSE);
    PyDict_SetItemString(d, "AP_CONN_CLOSE", o);
    Py_DECREF(o);
    o = PyInt_FromLong(AP_CONN_KEEPALIVE);
    PyDict_SetItemString(d, "AP_CONN_KEEPALIVE", o);
    Py_DECREF(o);

    o = PyInt_FromLong(APR_NOFILE);
    PyDict_SetItemString(d, "APR_NOFILE", o);
    Py_DECREF(o);
    o = PyInt_FromLong(APR_REG);
    PyDict_SetItemString(d, "APR_REG", o);
    Py_DECREF(o);
    o = PyInt_FromLong(APR_DIR);
    PyDict_SetItemString(d, "APR_DIR", o);
    Py_DECREF(o);
    o = PyInt_FromLong(APR_CHR);
    PyDict_SetItemString(d, "APR_CHR", o);
    Py_DECREF(o);
    o = PyInt_FromLong(APR_BLK);
    PyDict_SetItemString(d, "APR_BLK", o);
    Py_DECREF(o);
    o = PyInt_FromLong(APR_PIPE);
    PyDict_SetItemString(d, "APR_PIPE", o);
    Py_DECREF(o);
    o = PyInt_FromLong(APR_LNK);
    PyDict_SetItemString(d, "APR_LNK", o);
    Py_DECREF(o);
    o = PyInt_FromLong(APR_SOCK);
    PyDict_SetItemString(d, "APR_SOCK", o);
    Py_DECREF(o);
    o = PyInt_FromLong(APR_UNKFILE);
    PyDict_SetItemString(d, "APR_UNKFILE", o);
    Py_DECREF(o);
}

PyObject *get_ServerReturn() 
{
    return Mp_ServerReturn;
}
