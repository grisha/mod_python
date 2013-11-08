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
 * hlist.c
 *
 *
 * See accompanying documentation and source code comments
 * for details.
 *
 */

#include "mod_python.h"

/**
 ** MpHList_FromHLEntry()
 **
 * new list from hl_entry
 */

PyObject *MpHList_FromHLEntry(hl_entry *hle)
{
    hlistobject *result;
	MpHList_Type.ob_type = &PyType_Type;
    result = PyObject_New(hlistobject, &MpHList_Type);
    if (! result)
        PyErr_NoMemory();

    result->head = hle;

    return (PyObject *) result;
}

/**
 ** hlist_next
 **
 */

static PyObject *hlist_next(hlistobject *self, PyObject *args)
{
    self->head = self->head->next;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef hlistmethods[] = {
    {"next",                 (PyCFunction) hlist_next,       METH_VARARGS},
    { NULL, NULL } /* sentinel */
};

#define OFF(x) offsetof(hl_entry, x)

static PyMemberDef hlist_memberlist[] = {
    {"handler",            T_STRING,    OFF(handler),              READONLY},
    {"silent",             T_INT,       OFF(silent),               READONLY},
    {"is_location",        T_INT,       OFF(d_is_location),        READONLY},
    {"directory",          T_STRING,    OFF(directory),            READONLY},
    {NULL}  /* Sentinel */
};

/**
 ** hlist_dealloc
 **
 */

static void hlist_dealloc(hlistobject *self)
{
    PyObject_Del(self);
}

/**
 ** hlist_getattr
 **
 */

static PyObject *hlist_getattr(hlistobject *self, char *name)
{
    PyObject *res;
	PyMemberDef *md;

    PyMethodDef *ml = hlistmethods;
    for (; ml->ml_name != NULL; ml++) {
        if (name[0] == ml->ml_name[0] &&
            strcmp(name+1, ml->ml_name+1) == 0)
            return PyCFunction_New(ml, (PyObject*)self);
    }

    PyErr_Clear();

    /* when we are at the end of the list, everything
       would return None */
    if (! self->head) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    md = find_memberdef(hlist_memberlist, name);
    if (!md) {
        PyErr_SetString(PyExc_AttributeError, name);
        return NULL;
    }

    return PyMember_GetOne((char*)self->head, md);
}

/**
 ** hlist_repr
 **
 *
 */

static PyObject *hlist_repr(hlistobject *self)
{
    PyObject *t;
    PyObject *s = PyBytes_FromString("{");

    if (self->head->handler) {
        PyBytes_ConcatAndDel(&s, PyBytes_FromString("'handler':"));
        t = PyBytes_FromString(self->head->handler);
        PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
        Py_XDECREF(t);
    }
    if (self->head->directory) {
        PyBytes_ConcatAndDel(&s, PyBytes_FromString(",'directory':"));
        t = PyBytes_FromString(self->head->directory);
        PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
        Py_XDECREF(t);
    }
    PyBytes_ConcatAndDel(&s, PyBytes_FromString(",'is_location':"));
    if (self->head->d_is_location)
        PyBytes_ConcatAndDel(&s, PyBytes_FromString("True"));
    else
        PyBytes_ConcatAndDel(&s, PyBytes_FromString("False"));
    PyBytes_ConcatAndDel(&s, PyBytes_FromString(",'silent':"));
    if (self->head->silent)
        PyBytes_ConcatAndDel(&s, PyBytes_FromString("1}"));
    else
        PyBytes_ConcatAndDel(&s, PyBytes_FromString("0}"));

#if PY_MAJOR_VERSION < 3
    return s;
#else
    {
        PyObject *str = PyUnicode_FromString(PyBytes_AS_STRING(s));
        Py_DECREF(s);
        return str;
    }
#endif
}

PyTypeObject MpHList_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "mp_hlist",                      /* tp_name */
    sizeof(hlistobject),             /* tp_basicsize */
    0,                               /* tp_itemsize */
    (destructor) hlist_dealloc,      /* tp_dealloc*/
    0,                               /* tp_print*/
    (getattrfunc) hlist_getattr,     /* tp_getattr*/
    0,                               /* tp_setattr*/
    0,                               /* tp_compare*/
    (reprfunc)hlist_repr,            /* tp_repr*/
    0,                               /* tp_as_number*/
    0,                               /* tp_as_sequence*/
    0,                               /* tp_as_mapping*/
    0,                               /* tp_hash*/
};


