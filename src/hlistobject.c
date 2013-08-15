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

static struct memberlist hlist_memberlist[] = {
    {"handler",            T_STRING,    OFF(handler),              RO},
    {"directory",          T_STRING,    OFF(directory),            RO},
    {"silent",             T_INT,       OFF(silent),               RO},
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

    res = Py_FindMethod(hlistmethods, (PyObject *)self, name);
    if (res != NULL)
        return res;

    PyErr_Clear();

    /* when we are at the end of the list, everything
       would return None */
    if (! self->head) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    return PyMember_Get((char *)self->head, hlist_memberlist, name);

}

/**
 ** hlist_repr
 **
 *
 */

static PyObject *hlist_repr(hlistobject *self)
{
    PyObject *t;
    PyObject *s = PyString_FromString("{");
    if (self->head->handler) {
        PyString_ConcatAndDel(&s, PyString_FromString("'handler':"));
        t = PyString_FromString(self->head->handler);
        PyString_ConcatAndDel(&s, PyObject_Repr(t));
        Py_XDECREF(t);
    }
    if (self->head->directory) {
        PyString_ConcatAndDel(&s, PyString_FromString(",'directory':"));
        t = PyString_FromString(self->head->directory);
        PyString_ConcatAndDel(&s, PyObject_Repr(t));
        Py_XDECREF(t);
    }
    PyString_ConcatAndDel(&s, PyString_FromString(",'silent':"));
    if (self->head->silent)
        PyString_ConcatAndDel(&s, PyString_FromString("1}"));
    else
        PyString_ConcatAndDel(&s, PyString_FromString("0}"));

    return s;
}

PyTypeObject MpHList_Type = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_hlist",
    sizeof(hlistobject),
    0,
    (destructor) hlist_dealloc,      /*tp_dealloc*/
    0,                               /*tp_print*/
    (getattrfunc) hlist_getattr,     /*tp_getattr*/
    0,                               /*tp_setattr*/
    0,                               /*tp_compare*/
    (reprfunc)hlist_repr,            /*tp_repr*/
    0,                               /*tp_as_number*/
    0,                               /*tp_as_sequence*/
    0,                               /*tp_as_mapping*/
    0,                               /*tp_hash*/
};


