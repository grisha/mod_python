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
 * Originally developed by Gregory Trubetskoy.
 *
 *
 * hlist.c 
 *
 * $Id: hlistobject.c,v 1.7 2002/11/08 00:15:11 gstein Exp $
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

#include "mod_python.h"

/**
 ** MpHList_FromHSEntry()
 **
 * new list from hl_entry
 */

PyObject *MpHList_FromHLEntry(hl_entry *hle) 
{
    hlistobject *result;
    apr_pool_t *p;

    result = PyMem_NEW(hlistobject, 1);
    result->ob_type = &MpHList_Type;
    if (! result) 
        PyErr_NoMemory();

    /* XXX need second arg abort function to report mem error */
    apr_pool_sub_make(&p, NULL, NULL);

    result->pool = p;
    result->head = hlist_copy(p, hle);

    _Py_NewReference(result);
    return (PyObject *) result;
}

/**
 ** MpHlist_Append(hlistobject, hl_entry)
 **
 *  Append hl_entry to hlistobject, copying everything.
 */

void MpHList_Append(hlistobject *self, hl_entry *hle)
{
    hl_entry *tail;

    /* find tail */
    for (tail = self->head; tail->next; tail=tail->next);

    tail->next = hlist_copy(self->pool, hle);
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
    if (self->pool)
        apr_pool_destroy(self->pool);
    free(self);
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
    PyObject *s = PyString_FromString("{");
    if (self->head->handler) {
        PyString_ConcatAndDel(&s, PyString_FromString("'handler:'"));
        PyString_ConcatAndDel(&s, PyString_FromString(self->head->handler));
        PyString_ConcatAndDel(&s, PyString_FromString("'"));
    }
    if (self->head->directory) {
        PyString_ConcatAndDel(&s, PyString_FromString(",'directory':'"));
        PyString_ConcatAndDel(&s, PyString_FromString(self->head->directory));
        PyString_ConcatAndDel(&s, PyString_FromString("'"));
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
    sizeof(hl_entry),
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


