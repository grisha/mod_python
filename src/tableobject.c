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
 * tableobject.c 
 *
 * $Id: tableobject.c,v 1.5 2000/12/18 19:50:03 gtrubetskoy Exp $
 *
 */

#include "mod_python.h"

/**
 **     make_tableobject
 **
 *      This routine creates a Python tableobject given an Apache
 *      table pointer.
 *
 */

PyObject * MpTable_FromTable(table *t)
{
    tableobject *result;

    result = PyMem_NEW(tableobject, 1);
    if (! result)
	return PyErr_NoMemory();

    result->table = t;
    result->ob_type = &MpTable_Type;
    result->pool = NULL;

    _Py_NewReference(result);
    return (PyObject *)result;
}

/** 
 ** MpTable_New
 **
 *  This returns a new object of built-in type table.
 *
 *  NOTE: The ap_table gets greated in its own pool, which lives
 *  throught the live of the tableobject. This is because this
 *  object may persist from hit to hit.
 *
 */

PyObject * MpTable_New()
{
    tableobject *t;
    pool *p;

    p = ap_make_sub_pool(NULL);
    
    /* two is a wild guess */
    t = (tableobject *)MpTable_FromTable(ap_make_table(p, 2));

    /* remember the pointer to our own pool */
    t->pool = p;

    return (PyObject *)t;

}

/**
 ** tablelength
 **
 *      Number of elements in a table. Called
 *      when you do len(table) in Python.
 */

static int tablelength(tableobject *self) 
{ 
    return ap_table_elts(self->table)->nelts;
}

/**
 ** tablegetitem
 **
 *      Gets a dictionary item
 */

static PyObject * tablegetitem(tableobject *self, PyObject *key)
{
    const char *v;
    char *k;

    k = PyString_AsString(key);

    v = ap_table_get(self->table, k);

    if (! v)
    {
	PyErr_SetObject(PyExc_KeyError, key);
	return NULL;
    }

    return PyString_FromString(v);
}

/**
 ** tablesetitem
 **
 *      insert into table dictionary-style
 *      *** NOTE ***
 *      Since the underlying ap_table_set makes a *copy* of the string,
 *      there is no need to increment the reference to the Python
 *      string passed in.
 */

static int tablesetitem(tableobject *self, PyObject *key, 
			PyObject *val)
{ 

    char *k;

    if (key && !PyString_Check(key)) {
	PyErr_SetString(PyExc_TypeError,
			"table keys must be strings");
	return -1;
    }

    k = PyString_AsString(key);

    if ((val == Py_None) || (val == NULL)) {
	ap_table_unset(self->table, k);
    }
    else {
	if (val && !PyString_Check(val)) {
	    PyErr_SetString(PyExc_TypeError,
			    "table values must be strings");
	    return -1;
	}
	ap_table_set(self->table, k, PyString_AsString(val));
    }
    return 0;
}

/* table as mapping */

static PyMappingMethods table_mapping = {
    (inquiry)       tablelength,           /*mp_length*/
    (binaryfunc)    tablegetitem,          /*mp_subscript*/
    (objobjargproc) tablesetitem,          /*mp_ass_subscript*/
};

/**
 ** table_keys
 **
 *
 *  Implements dictionary's keys() method.
 */

static PyObject * table_keys(tableobject *self)
{

    PyObject *v;
    array_header *ah;
    table_entry *elts;
    int i, j;

    ah = ap_table_elts(self->table);
    elts = (table_entry *) ah->elts;

    v = PyList_New(ah->nelts);

    for (i = 0, j = 0; i < ah->nelts; i++)
    {
	if (elts[i].key)
	{
	    PyObject *key = PyString_FromString(elts[i].key);
	    PyList_SetItem(v, j, key);
	    j++;
	}
    }
    return v;
}

/**
 ** table_has_key
 **
 */

static PyObject * table_has_key(tableobject *self, PyObject *args)
{

    const char *val, *key;

    if (! PyArg_ParseTuple(args, "s", &key))
	return NULL;

    val = ap_table_get (self->table, key);

    if (val)
	return PyInt_FromLong(1);
    else
	return PyInt_FromLong(0);
}

/**
 ** table_add
 **
 *     this function is equivalent of ap_table_add - 
 *     it can create duplicate entries. 
 */

static PyObject * table_add(tableobject *self, PyObject *args)
{

    const char *val, *key;

    if (! PyArg_ParseTuple(args, "ss", &key, &val))
	return NULL;

    ap_table_add(self->table, key, val);

    Py_INCREF(Py_None);
    return Py_None;
}

/* table method definitions */

static PyMethodDef tablemethods[] = {
    {"keys",                 (PyCFunction)table_keys,    METH_VARARGS},
    {"has_key",              (PyCFunction)table_has_key, METH_VARARGS},
    {"add",                  (PyCFunction)table_add,     METH_VARARGS},
    {NULL, NULL} /* sentinel */
};


/**
 ** table_dealloc
 **
 *      Frees table's memory
 */

static void table_dealloc(tableobject *self)
{  
    if (self->pool) 
	ap_destroy_pool(self->pool);
    
    free(self);
}

/**
 ** table_getattr
 **
 *      Gets table's attributes
 */

static PyObject * table_getattr(PyObject *self, char *name)
{
    return Py_FindMethod(tablemethods, self, name);
}

/**
 ** table_repr
 **
 *      prints table like a dictionary
 */

static PyObject * table_repr(tableobject *self)
{
    PyObject *s;
    array_header *ah;
    table_entry *elts;
    int i;

    s = PyString_FromString("{");

    ah = ap_table_elts (self->table);
    elts = (table_entry *) ah->elts;

    i = ah->nelts;
    if (i == 0)
	PyString_ConcatAndDel(&s, PyString_FromString("}"));

    while (i--)
	if (elts[i].key)
	{
	    PyString_ConcatAndDel(&s, PyString_FromString("'"));
	    PyString_ConcatAndDel(&s, PyString_FromString(elts[i].key));
	    PyString_ConcatAndDel(&s, PyString_FromString("': '"));
	    PyString_ConcatAndDel(&s, PyString_FromString(elts[i].val));
	    PyString_ConcatAndDel(&s, PyString_FromString("'"));
	    if (i > 0)
		PyString_ConcatAndDel(&s, PyString_FromString(", "));
	    else
		PyString_ConcatAndDel(&s, PyString_FromString("}"));
	}

    return s;
}

PyTypeObject MpTable_Type = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_table",
    sizeof(tableobject),
    0,
    (destructor) table_dealloc,     /*tp_dealloc*/
    0,                              /*tp_print*/
    (getattrfunc) table_getattr,    /*tp_getattr*/
    0,                              /*tp_setattr*/
    0,                              /*tp_compare*/
    (reprfunc) table_repr,          /*tp_repr*/
    0,                              /*tp_as_number*/
    0,                              /*tp_as_sequence*/
    &table_mapping,                 /*tp_as_mapping*/
    0,                              /*tp_hash*/
};


