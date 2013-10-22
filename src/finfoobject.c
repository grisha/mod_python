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
 * finfoobject.c
 *
 *
 */

#include "mod_python.h"

/**
 **     MpFinfo_FromFinfo
 **
 *      This routine creates a Python finfoobject given an Apache
 *      finfo pointer.
 *
 */

PyObject * MpFinfo_FromFinfo(apr_finfo_t *f)
{
    finfoobject *result;

    result = PyObject_New(finfoobject, &MpFinfo_Type);
    if (! result)
        return PyErr_NoMemory();

    result->finfo = f;
    result->pool = NULL;

    return (PyObject *)result;
}

/**
 ** MpFinfo_New
 **
 *  This returns a new object of built-in type finfo.
 *
 *  NOTE: The apr_finfo_t gets greated in its own pool, which lives
 *  throught the life of the finfoobject.
 *
 */

PyObject * MpFinfo_New()
{
    finfoobject *f;
    apr_pool_t *p;

    /* XXX need second arg abort function to report mem error */
    apr_pool_create_ex(&p, NULL, NULL, NULL);

    f = (finfoobject *)MpFinfo_FromFinfo(apr_pcalloc(p, sizeof(apr_finfo_t)));

    /* remember the pointer to our own pool */
    f->pool = p;

    return (PyObject *)f;
}

/**
 ** finfo_dealloc
 **
 *      Frees finfo's memory
 */

static void finfo_dealloc(register finfoobject *self)
{
    if (MpFinfo_Check(self)) {
        if (self->pool)
            apr_pool_destroy(self->pool);
        PyObject_Del(self);
    }
    else
        Py_TYPE(self)->tp_free((PyObject *)self);
}

/**
 ** finfo_getattr
 **
 *  Get finfo object attributes
 *
 */

static PyObject * finfo_getattr(finfoobject *self, char *name)
{
    if (strcmp(name, "fname") == 0) {
        if (self->finfo->fname)
            return MpBytesOrUnicode_FromString(self->finfo->fname);
    }
    else if (strcmp(name, "filetype") == 0) {
        return PyLong_FromLong(self->finfo->filetype);
    }
    else if (strcmp(name, "valid") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        return PyLong_FromLong(self->finfo->valid);
    }
    else if (strcmp(name, "protection") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_PROT)
            return PyLong_FromLong(self->finfo->protection);
    }
    else if (strcmp(name, "user") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_USER)
            return PyLong_FromLong(self->finfo->user);
    }
    else if (strcmp(name, "group") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_GROUP)
            return PyLong_FromLong(self->finfo->group);
    }
    else if (strcmp(name, "inode") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_INODE)
            return PyLong_FromLong(self->finfo->inode);
    }
    else if (strcmp(name, "device") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_DEV)
            return PyLong_FromLong(self->finfo->device);
    }
    else if (strcmp(name, "nlink") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_NLINK)
            return PyLong_FromLong(self->finfo->nlink);
    }
    else if (strcmp(name, "size") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_SIZE) {
            if (sizeof(apr_off_t) == sizeof(PY_LONG_LONG)) {
                return PyLong_FromLongLong(self->finfo->size);
            }
            else {
                return PyLong_FromLong(self->finfo->size);
            }
        }
    }
    else if (strcmp(name, "atime") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_ATIME)
            return PyLong_FromLong(self->finfo->atime*0.000001);
    }
    else if (strcmp(name, "mtime") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_MTIME)
            return PyLong_FromLong(self->finfo->mtime*0.000001);
    }
    else if (strcmp(name, "ctime") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_CTIME)
            return PyLong_FromLong(self->finfo->ctime*0.000001);
    }
    else if (strcmp(name, "name") == 0) {
        if (self->finfo->filetype == APR_NOFILE) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        if (self->finfo->valid & APR_FINFO_NAME)
            return MpBytesOrUnicode_FromString(self->finfo->name);
    }
    else {
        PyErr_Format(PyExc_AttributeError,
                     "class 'mp_finfo' has no attribute '%.400s'", name);
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
finfoseq_item(PyObject *o, Py_ssize_t i)
{
    finfoobject *self = (finfoobject *)o;
    if (i < 0 || i >= 12) {
        PyErr_SetString(PyExc_IndexError, "tuple index out of range");
        return NULL;
    }

    switch (i) {
        case 0: {
          return finfo_getattr(self, "protection");
        }
        case 1: {
            return finfo_getattr(self, "inode");
        }
        case 2: {
            return finfo_getattr(self, "device");
        }
        case 3: {
            return finfo_getattr(self, "nlink");
        }
        case 4: {
            return finfo_getattr(self, "user");
        }
        case 5: {
            return finfo_getattr(self, "group");
        }
        case 6: {
            return finfo_getattr(self, "size");
        }
        case 7: {
            return finfo_getattr(self, "atime");
        }
        case 8: {
            return finfo_getattr(self, "mtime");
        }
        case 9: {
            return finfo_getattr(self, "ctime");
        }
        case 10: {
            return finfo_getattr(self, "fname");
        }
        case 11: {
            return finfo_getattr(self, "name");
        }
        case 12: {
            return finfo_getattr(self, "filetype");
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PySequenceMethods finfoseq_as_sequence = {
        0,
        0,                                      /* sq_concat */
        0,                                      /* sq_repeat */
        finfoseq_item,                          /* sq_item */
        0,                                      /* sq_slice */
        0,                                      /* sq_ass_item */
        0,                                      /* sq_ass_slice */
        0,                                      /* sq_contains */
};

/**
 ** finfo_repr
 **
 *
 */

static PyObject *finfo_repr(finfoobject *self)
{
    PyObject *s = PyBytes_FromString("{");
    PyObject *t = NULL;

    PyBytes_ConcatAndDel(&s, PyBytes_FromString("'fname': "));
    t = finfo_getattr(self, "fname");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'filetype': "));
    t = finfo_getattr(self, "filetype");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'valid': "));
    t = finfo_getattr(self, "valid");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'protection': "));
    t = finfo_getattr(self, "protection");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'user': "));
    t = finfo_getattr(self, "user");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'group': "));
    t = finfo_getattr(self, "group");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'size': "));
    t = finfo_getattr(self, "size");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'inode': "));
    t = finfo_getattr(self, "inode");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'device': "));
    t = finfo_getattr(self, "device");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'nlink': "));
    t = finfo_getattr(self, "nlink");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'atime': "));
    t = finfo_getattr(self, "atime");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'mtime': "));
    t = finfo_getattr(self, "mtime");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'ctime': "));
    t = finfo_getattr(self, "ctime");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString(", 'name': "));
    t = finfo_getattr(self, "name");
    PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
    Py_XDECREF(t);

    PyBytes_ConcatAndDel(&s, PyBytes_FromString("}"));

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

PyTypeObject MpFinfo_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "mp_finfo",                         /* tp_name */
    sizeof(finfoobject),                /* tp_basicsize */
    0,                                  /* tp_itemsize */
    (destructor)finfo_dealloc,          /* tp_dealloc */
    0,                                  /* tp_print */
    (getattrfunc)finfo_getattr,         /* tp_getattr*/
    0,                                  /* tp_setattr*/
    0,                                  /* tp_compare */
    (reprfunc)finfo_repr,               /* tp_repr*/
    0,                                  /* tp_as_number */
    &finfoseq_as_sequence,              /* tp_as_sequence */
    0,                                  /* tp_as_mapping */
    0,                                  /* tp_hash */
};
