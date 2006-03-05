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
 * serverobject.c 
 *
 * $Id$
 *
 */

#include "mod_python.h"


/**
 **     MpServer_FromServer
 **
 *      This routine creates a Python serverobject given an Apache
 *      server_rec pointer.
 *
 */

PyObject * MpServer_FromServer(server_rec *s)
{
    serverobject *result;

    result = PyObject_New(serverobject, &MpServer_Type);
    if (! result)
        return PyErr_NoMemory();

    result->dict = PyDict_New();
    if (!result->dict)
        return PyErr_NoMemory();

    result->server = s;
    result->next = NULL;

    return (PyObject *)result;
}

/**
 ** server.get_config(server self)
 **
 *     Returns the config directives set through Python* apache directives.
 *     unlike req.get_config, this one returns the per-server config
 */

static PyObject * server_get_config(serverobject *self)
{
    py_config *conf =
        (py_config *) ap_get_module_config(self->server->module_config, 
                                           &python_module);
    return MpTable_FromTable(conf->directives);
}

/**
 ** server.get_options(server self)
 **
 *     Returns the options set through PythonOption directives.
 *     unlike req.get_options, this one returns the per-server config
 */

static PyObject * server_get_options(serverobject *self)
{
    py_config *conf =
        (py_config *) ap_get_module_config(self->server->module_config,
                                           &python_module);
    return MpTable_FromTable(conf->options);
}

/**
 ** server.register_cleanup(req, handler, data)
 **
 *    same as request.register_cleanup, except the server pool is used.
 *    the server pool gets destroyed before the child dies or when the
 *    whole process dies in multithreaded situations.
 */

static PyObject *server_register_cleanup(serverobject *self, PyObject *args)
{

    cleanup_info *ci;
    PyObject *handler = NULL;
    PyObject *data = NULL;
    requestobject *req = NULL;

    if (! PyArg_ParseTuple(args, "OO|O", &req, &handler, &data))
        return NULL; 

    if (! MpRequest_Check(req)) {
        PyErr_SetString(PyExc_ValueError, 
                        "first argument must be a request object");
        return NULL;
    }
    else if(!PyCallable_Check(handler)) {
        PyErr_SetString(PyExc_ValueError, 
                        "second argument must be a callable object");
        return NULL;
    }
    
    ci = (cleanup_info *)malloc(sizeof(cleanup_info));
    ci->request_rec = NULL;
    ci->server_rec = self->server;
    Py_INCREF(handler);
    ci->handler = handler;
    ci->interpreter = strdup(req->interpreter);
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

static PyMethodDef server_methods[] = {
    {"get_config",           (PyCFunction) server_get_config,        METH_NOARGS},
    {"get_options",          (PyCFunction) server_get_options,       METH_NOARGS},
    {"register_cleanup",     (PyCFunction) server_register_cleanup,  METH_VARARGS},
    { NULL, NULL } /* sentinel */
};


/* 
   These are offsets into the Apache server_rec structure.
   They are accessed via getset functions. Note that the types
   specified here are irrelevant if a function other than
   getreq_recmbr() is used. E.g. bytes_sent is a long long,
   and is retrieved via getreq_recmbr_off() which ignores what's
   here.
*/

#define OFF(x) offsetof(server_rec, x)

static struct PyMemberDef server_rec_mbrs[] = {
    {"defn_name",          T_STRING,  OFF(defn_name)},
    {"defn_line_number",   T_INT,     OFF(defn_line_number)},
    {"server_admin",       T_STRING,  OFF(server_admin)},
    {"server_hostname",    T_STRING,  OFF(server_hostname)},
    {"port",               T_SHORT,   OFF(port)},
    {"error_fname",        T_STRING,  OFF(error_fname)},
    {"loglevel",           T_INT,     OFF(loglevel)},
    {"is_virtual",         T_INT,     OFF(is_virtual)},
    /* XXX implement module_config ? */
    /* XXX implement lookup_defaults ? */
    /* XXX implement server_addr_rec ? */
    {"timeout",            T_LONG,    OFF(timeout)},
    {"keep_alive_timeout", T_LONG,    OFF(keep_alive_timeout)},
    {"keep_alive_max",     T_INT,     OFF(keep_alive_max)},
    {"keep_alive",         T_INT,     OFF(keep_alive)},
    /* XXX send_buffer_size gone. where? document */
    /*{"send_buffer_size",   T_INT,       OFF(send_buffer_size),   RO},*/
    {"path",               T_STRING,  OFF(path)},
    {"pathlen",            T_INT,     OFF(pathlen)},
    {"names",              T_OBJECT,  OFF(names)},
    {"wild_names",         T_OBJECT,  OFF(wild_names)},
    /* XXX server_uid and server_gid seem gone. Where? Document. */
    /*{"server_uid",         T_INT,       OFF(server_uid),         RO},*/
    /*{"server_gid",         T_INT,       OFF(server_gid),         RO},*/
    /* XXX Document limit* below. Make RW? */
    {"limit_req_line",       T_INT,   OFF(limit_req_line)},
    {"limit_req_fieldsize",  T_INT,   OFF(limit_req_fieldsize)},
    {"limit_req_fields",     T_INT,   OFF(limit_req_fields)},
    {NULL}  /* Sentinel */
};

/**
 ** getsrv_recmbr
 **
 *    Retrieves server_rec structure members
 */

static PyObject *getsrv_recmbr(serverobject *self, void *name) 
{
    return PyMember_GetOne((char*)self->server,
                           find_memberdef(server_rec_mbrs, name));
}

/* we don't need setsrv_recmbr for now */

/**
 ** getsrv_recmbr_time
 **
 *    Retrieves apr_time_t server_rec members
 */

static PyObject *getsrv_recmbr_time(serverobject *self, void *name) 
{
    PyMemberDef *md = find_memberdef(server_rec_mbrs, name);
    char *addr = (char *)self->server + md->offset;
    apr_time_t time = *(apr_time_t*)addr;
    return PyFloat_FromDouble(time*0.000001);
}

/**
 ** getsrv_rec_ah
 **
 *    For array headers that will get converted to tuple
 */

static PyObject *getsrv_recmbr_ah(serverobject *self, void *name) 
{
    const PyMemberDef *md = find_memberdef(server_rec_mbrs, name);
    apr_array_header_t *ah = 
        *(apr_array_header_t **)((char *)self->server + md->offset);

    return tuple_from_array_header(ah);
}

/**
 ** getmakeobj
 **
 *    A getter func that creates an object as needed.
 */

static PyObject *getmakeobj(serverobject* self, void *objname) 
{
    char *name = (char *)objname;
    PyObject *result = NULL;

    if (strcmp(name, "next") == 0) {
        if (!self->next && self->server->next)
            self->next = MpServer_FromServer(self->server->next);
        result = self->next;
    }

    if (!result)
        result = Py_None;

    Py_INCREF(result);
    return result;
}

static PyObject *my_generation(serverobject *self, void *objname)
{
    return PyInt_FromLong((long)ap_my_generation);
}

static PyObject *restart_time(serverobject *self, void *objname)
{
    return PyFloat_FromDouble(ap_scoreboard_image->global->restart_time*0.000001);
}

static PyGetSetDef server_getsets[] = {
    /* XXX process */
    {"next",         (getter)getmakeobj,    NULL, "The next server in the list", "next"},
    {"defn_name",    (getter)getsrv_recmbr, NULL, "The name of the server", "defn_name"},
    {"defn_line_number",    (getter)getsrv_recmbr, NULL, 
          "The line of the config file that the server was defined on", "defn_line_number"},
    {"server_admin", (getter)getsrv_recmbr, NULL, "The admin's contact information", "server_admin"},
    {"server_hostname",    (getter)getsrv_recmbr, NULL, "The server hostname", "server_hostname"},
    {"port",    (getter)getsrv_recmbr, NULL, " for redirects, etc.", "port"},
    {"error_fname",    (getter)getsrv_recmbr, NULL, "The name of the error log", "error_fname"},
    /* XXX error_log apr_file_t */
    {"loglevel",    (getter)getsrv_recmbr, NULL, "The log level for this server", "loglevel"},
    {"is_virtual",    (getter)getsrv_recmbr, NULL, "true if this is the virtual server", "is_virtual"},
    {"timeout",    (getter)getsrv_recmbr_time, NULL, "Timeout, as interval, before we give up", "timeout"},
    {"keep_alive_timeout",    (getter)getsrv_recmbr_time, NULL, "The apr interval we will wait for another request", "keep_alive_timeout"},
    {"keep_alive_max",    (getter)getsrv_recmbr, NULL, "Maximum requests per connection", "keep_alive_max"},
    {"keep_alive",    (getter)getsrv_recmbr, NULL, "Use persistent connections?", "keep_alive"},
    {"path",    (getter)getsrv_recmbr, NULL, "Pathname for ServerPath", "path"},
    {"pathlen",    (getter)getsrv_recmbr, NULL, "Length of path", "pathlen"},
    {"names",    (getter)getsrv_recmbr_ah, NULL, "Normal names for ServerAlias servers", "names"},
    {"wild_names",    (getter)getsrv_recmbr_ah, NULL, "Wildcarded names for ServerAlias servers", "wild_names"},
    {"limit_req_line",    (getter)getsrv_recmbr, NULL, "limit on size of the HTTP request line", "limit_req_line"},
    {"limit_req_fieldsize",    (getter)getsrv_recmbr, NULL, "limit on size of any request header field", "limit_req_fieldsize"},
    {"limit_req_fields",    (getter)getsrv_recmbr, NULL, "limit on number of request header fields", "limit_req_fields"},
    {"my_generation",    (getter)my_generation, NULL, "Generation of this child", "my_generation"},
    {"restart_time",    (getter)restart_time, NULL, "Server restart time", "restart_time"},
    {NULL}  /* Sentinel */
};


/**
 ** server_dealloc
 **
 *
 */

static void server_dealloc(serverobject *self)
{  
    Py_XDECREF(self->dict);
    Py_XDECREF(self->next);
    PyObject_Del(self);
}

static char server_doc[] =
"Apache server_rec structure\n";

PyTypeObject MpServer_Type = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_server",
    sizeof(serverobject),
    0,
    (destructor) server_dealloc,     /*tp_dealloc*/
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
    server_doc,                      /* tp_doc */
    0,                               /* tp_traverse */
    0,                               /* tp_clear */
    0,                               /* tp_richcompare */
    0,                               /* tp_weaklistoffset */
    0,                               /* tp_iter */
    0,                               /* tp_iternext */
    server_methods,                  /* tp_methods */
    0,                               /* tp_members */
    server_getsets,                  /* tp_getset */
    0,                               /* tp_base */
    0,                               /* tp_dict */
    0,                               /* tp_descr_get */
    0,                               /* tp_descr_set */
    offsetof(serverobject, dict),    /* tp_dictoffset */
    0,                               /* tp_init */
    0,                               /* tp_alloc */
    0,                               /* tp_new */
    (destructor)server_dealloc,      /* tp_free */
};





