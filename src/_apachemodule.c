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
 * _apachemodule.c 
 *
 * $Id: _apachemodule.c,v 1.1 2000/10/16 20:58:57 gtrubetskoy Exp $
 *
 */

#include "mod_python.h"

/** 
 ** log_error
 **
 *  A wrpapper to ap_log_error
 * 
 *  log_error(string message, int level, server server)
 *
 */

static PyObject * log_error(PyObject *self, PyObject *args)
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
      
	if (!server)
	    serv_rec = NULL;
	else {
	    if (! MpServer_Check(server)) {
		PyErr_BadArgument();
		return NULL;
	    }
	    serv_rec = server->server;
	}
	ap_log_error(APLOG_MARK, level, serv_rec, "%s", message);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/** 
 ** make_table
 **
 *  This returns a new object of built-in type table.
 *
 *  make_table()
 *
 */

static PyObject * make_table(PyObject *self, PyObject *args)
{
    return MpTable_New();
}

/* methods of _apache */
struct PyMethodDef _apache_module_methods[] = {
  {"log_error",                 (PyCFunction)log_error,        METH_VARARGS},
  {"make_table",                (PyCFunction)make_table,       METH_VARARGS},
  {NULL, NULL} /* sentinel */
};

/* Module initialization */

DL_EXPORT(void) init_apache()
{
    Py_InitModule("_apache", _apache_module_methods);
}
