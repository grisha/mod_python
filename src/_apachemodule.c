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
 * _apachemodule.c 
 *
 * $Id: _apachemodule.c,v 1.18 2002/09/19 20:11:35 grisha Exp $
 *
 */

#include "mod_python.h"

/* A referende to the _apache.SERVER_RETURN */

PyObject *Mp_ServerReturn;

/** 
 ** mp_log_error
 **
 *  A wrpapper to ap_log_error
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
      
	if (!server || server == Py_None)
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
	_PyString_Resize(&pair, j);
	cpair = PyString_AS_STRING(pair);

	PyList_Append(pairs, pair);
	Py_DECREF(pair);
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
	    ckey = PyString_AS_STRING(key);
	    _PyString_Resize(&val, strlen(cval));
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

	Py_DECREF(key);
	Py_DECREF(val);

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

	    PyList_Append(pairs, Py_BuildValue("(O,O)", key, val));

	}
	Py_DECREF(pair);
	Py_DECREF(key);
	Py_DECREF(val);
	i++;
    }

    return pairs;
}

/**
 ** config_tree
 **
 *   Returns a copy of the config tree
 */

static PyObject *config_tree()
{
    return cfgtree_walk(ap_conftree);
}

/**
 ** server_root
 **
 *   Returns ServerRoot
 */

static PyObject *server_root()
{
    return PyString_FromString(ap_server_root);
}

/* methods of _apache */
struct PyMethodDef _apache_module_methods[] = {
    {"log_error",                 (PyCFunction)mp_log_error,     METH_VARARGS},
    {"parse_qs",                  (PyCFunction)parse_qs,         METH_VARARGS},
    {"parse_qsl",                 (PyCFunction)parse_qsl,        METH_VARARGS},
    {"config_tree",               (PyCFunction)config_tree,      METH_NOARGS},
    {"server_root",               (PyCFunction)server_root,      METH_NOARGS},
    {NULL, NULL} /* sentinel */
};

/* Module initialization */

DL_EXPORT(void) init_apache()
{
    PyObject *m, *d;

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

}

PyObject *get_ServerReturn() 
{
  return Mp_ServerReturn;
}
