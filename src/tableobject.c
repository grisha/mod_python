/* ====================================================================
 * The Apache Software License, Version 1.1
 *
 * Copyright (c) 2002 The Apache Software Foundation.  All rights
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
 * tableobject.c 
 *
 * $Id: tableobject.c,v 1.26 2002/12/19 15:55:02 grisha Exp $
 *
 */

#include "mod_python.h"

/** XXX this is a hack. because apr_table_t 
    is not available in a header file */
#define TABLE_HASH_SIZE 32
struct apr_table_t {
    apr_array_header_t a;
#ifdef MAKE_TABLE_PROFILE
    void *creator;
#endif
    apr_uint32_t index_initialized;
    int index_first[TABLE_HASH_SIZE];
    int index_last[TABLE_HASH_SIZE];
};

/**
 **     MpTable_FromTable
 **
 *      This routine creates a Python tableobject given an Apache
 *      table pointer.
 *
 */

PyObject * MpTable_FromTable(apr_table_t *t)
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
 *  ALSO NOTE: table_new() also creates tables, independent of this
 *  (it gets called when table is being subclassed)
 *
 */

PyObject * MpTable_New()
{
    tableobject *t;
    apr_pool_t *p;

    /* XXX need second arg abort function to report mem error */
    apr_pool_sub_make(&p, NULL, NULL);
    
    /* two is a wild guess */
    t = (tableobject *)MpTable_FromTable(apr_table_make(p, 2));

    /* remember the pointer to our own pool */
    t->pool = p;

    return (PyObject *)t;

}

/**
 ** table_dealloc
 **
 *      Frees table's memory
 */

static void table_dealloc(register tableobject *self)
{  

    if (MpTable_Check(self)) {
        if (self->pool) 
            apr_pool_destroy(self->pool);
        free(self);
    }
    else
        self->ob_type->tp_free((PyObject *)self);

}

/**
 ** table_print
 **
 *      prints table like a dictionary
 */

static int table_print(register tableobject *self, register FILE *fp, register int flags)
{
    const apr_array_header_t *ah = NULL;
    apr_table_entry_t *elts;
    register int i;

    fprintf(fp, "{");

    ah = apr_table_elts(self->table);
    elts = (apr_table_entry_t *) ah->elts;

    i = ah->nelts;
    if (i == 0) {
        fprintf(fp, "}");
        return 0;
    }

    while (i--)
        if (elts[i].key)
        {
            fprintf(fp, "'%s': '%s'", elts[i].key, elts[i].val);

            if (i > 0)
                fprintf(fp, ", ");
            else
                fprintf(fp, "}");
        }

    return 0;
}

/**
 ** table_repr
 **
 *      prints table like a dictionary
 */

static PyObject * table_repr(tableobject *self)
{
    PyObject *s;
    const apr_array_header_t *ah;
    apr_table_entry_t *elts;
    int i;

    s = PyString_FromString("{");

    ah = apr_table_elts (self->table);
    elts = (apr_table_entry_t *) ah->elts;

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

/**
 ** tablelength
 **
 *      Number of elements in a table. Called
 *      when you do len(table) in Python.
 */

static int tablelength(tableobject *self) 
{ 
    return apr_table_elts(self->table)->nelts;
}

/**
 ** table_subscript
 **
 *      Gets a dictionary item
 */

static PyObject * table_subscript(tableobject *self, register PyObject *key)
{
    char *k;
    const apr_array_header_t *ah;
    apr_table_entry_t *elts;
    register int i;
    PyObject *list;

    if (key && !PyString_Check(key)) {
        PyErr_SetString(PyExc_TypeError,
                        "table keys must be strings");
        return NULL;
    }
    k = PyString_AsString(key);

    /* it's possible that we have duplicate keys, so
       we can't simply use apr_table_get since that just
       returns the first match.
    */

    list = PyList_New(0);
    if (!list) 
        return NULL;

    ah = apr_table_elts (self->table);
    elts = (apr_table_entry_t *) ah->elts;

    i = ah->nelts;

    while (i--)
        if (elts[i].key) {
            if (apr_strnatcasecmp(elts[i].key, k) == 0) {
                PyObject *v = PyString_FromString(elts[i].val);
                PyList_Insert(list, 0, v);
                Py_DECREF(v);
            }
        }

    /* if no mach */
    if (PyList_Size(list) == 0) {
        PyErr_SetObject(PyExc_KeyError, key);
        return NULL;
    }

    /* if we got one match */
    if (PyList_Size(list) == 1) {
        PyObject *v = PyList_GetItem(list, 0);
        Py_INCREF(v);
        Py_DECREF(list);
        return v;
    }

    /* else we return a list */
    return list;
}

/**
 ** table_ass_subscript
 **
 *      insert into table dictionary-style
 *      *** NOTE ***
 *      Since the underlying ap_table_set makes a *copy* of the string,
 *      there is no need to increment the reference to the Python
 *      string passed in.
 */

static int table_ass_subscript(tableobject *self, PyObject *key, 
                               PyObject *val)
{ 

    char *k;

    if (key && !PyString_Check(key)) {
        PyErr_SetString(PyExc_TypeError,
                        "table keys must be strings");
        return -1;
    }

    k = PyString_AsString(key);

    if (val == NULL) {
        apr_table_unset(self->table, k);
    }
    else {
        if (val && !PyString_Check(val)) {
            PyErr_SetString(PyExc_TypeError,
                            "table values must be strings");
            return -1;
        }
        apr_table_set(self->table, k, PyString_AsString(val));
    }
    return 0;
}

/* table as mapping */

static PyMappingMethods table_as_mapping = {
    (inquiry)       tablelength,           /*mp_length*/
    (binaryfunc)    table_subscript,       /*mp_subscript*/
    (objobjargproc) table_ass_subscript,   /*mp_ass_subscript*/
};

/**
 ** table_keys
 **
 *
 *  Implements dictionary's keys() method.
 */

static PyObject * table_keys(register tableobject *self)
{

    PyObject *v;
    const apr_array_header_t *ah;
    apr_table_entry_t *elts;
    int i, j;

    ah = apr_table_elts(self->table);
    elts = (apr_table_entry_t *) ah->elts;

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
 ** table_values
 **
 *
 *  Implements dictionary's values() method.
 */

static PyObject * table_values(register tableobject *self)
{

    PyObject *v;
    const apr_array_header_t *ah;
    apr_table_entry_t *elts;
    int i, j;

    ah = apr_table_elts(self->table);
    elts = (apr_table_entry_t *) ah->elts;

    v = PyList_New(ah->nelts);

    for (i = 0, j = 0; i < ah->nelts; i++)
    {
        if (elts[i].key)
        {
            PyObject *val = PyString_FromString(elts[i].val);
            PyList_SetItem(v, j, val);
            j++;
        }
    }
    return v;
}

/**
 ** table_items
 **
 *
 *  Implements dictionary's items() method.
 */

static PyObject * table_items(register tableobject *self)
{

    PyObject *v;
    const apr_array_header_t *ah;
    apr_table_entry_t *elts;
    int i, j;

    ah = apr_table_elts(self->table);
    elts = (apr_table_entry_t *) ah->elts;

    v = PyList_New(ah->nelts);

    for (i = 0, j = 0; i < ah->nelts; i++)
    {
        if (elts[i].key)
        {
            PyObject *keyval = Py_BuildValue("(s,s)", elts[i].key, elts[i].val);
            PyList_SetItem(v, j, keyval);
            j++;
        }
    }
    return v;
}

/**
 ** table_merge
 **
 *  Since tables can only store strings, key/vals from
 *  mapping object b will be str()ingized.
 */

static int table_merge(tableobject *a, PyObject *b, int override)
{
    /* Do it the generic, slower way */
    PyObject *keys = PyMapping_Keys(b);
    PyObject *iter;
    PyObject *key, *value, *skey, *svalue;
    int status;

    if (keys == NULL)
        return -1;

    iter = PyObject_GetIter(keys);
    Py_DECREF(keys);
    if (iter == NULL)
        return -1;
    
    for (key = PyIter_Next(iter); key; key = PyIter_Next(iter)) {

        skey = PyObject_Str(key);
        if (skey == NULL) {
            Py_DECREF(iter);
            Py_DECREF(key);
            return -1;
        }
        if (!override && apr_table_get(a->table, PyString_AsString(skey)) != NULL) {
            Py_DECREF(key);
            Py_DECREF(skey);
            continue;
        }

        value = PyObject_GetItem(b, key);
        if (value == NULL) {
            Py_DECREF(iter);
            Py_DECREF(key);
            Py_DECREF(skey);
            return -1;
        }
        svalue = PyObject_Str(value);
        if (svalue == NULL) {
            Py_DECREF(iter);
            Py_DECREF(key);
            Py_DECREF(skey);
            Py_DECREF(value);
            return -1;
        }
        status = table_ass_subscript(a, skey, svalue);
        Py_DECREF(key);
        Py_DECREF(value);
        Py_DECREF(skey);
        Py_DECREF(svalue);
        if (status < 0) {
            Py_DECREF(iter);
            return -1;
        }
    }
    Py_DECREF(iter);
    if (PyErr_Occurred())
        /* Iterator completed, via error */
        return -1;
    
    return 0;
}

/**
 ** table_update
 **
 */

static PyObject *table_update(tableobject *self, PyObject *other)
{
    if (table_merge(self, other, 1) < 0)
        return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** table_mergefromseq2
 **
 *  Similar to PyDict_MergeFromSeq2 (code borrowed from there).
 */

static int table_mergefromseq2(tableobject *self, PyObject *seq2, int override)
{
    PyObject *it;       /* iter(seq2) */
    int i;              /* index into seq2 of current element */
    PyObject *item;     /* seq2[i] */
    PyObject *fast;     /* item as a 2-tuple or 2-list */

    it = PyObject_GetIter(seq2);
    if (it == NULL)
        return -1;

    for (i = 0; ; ++i) {
        PyObject *key, *value, *skey, *svalue;
        int n;

        fast = NULL;
        item = PyIter_Next(it);
        if (item == NULL) {
            if (PyErr_Occurred())
                goto Fail;
            break;
        }

        /* Convert item to sequence, and verify length 2. */
        fast = PySequence_Fast(item, "");
        if (fast == NULL) {
            if (PyErr_ExceptionMatches(PyExc_TypeError))
                PyErr_Format(PyExc_TypeError,
                             "cannot convert table update "
                             "sequence element #%d to a sequence",
                             i);
            goto Fail;
        }
        n = PySequence_Fast_GET_SIZE(fast);
        if (n != 2) {
            PyErr_Format(PyExc_ValueError,
                         "table update sequence element #%d "
                         "has length %d; 2 is required",
                         i, n);
            goto Fail;
        }

        /* Update/merge with this (key, value) pair. */
        key = PySequence_Fast_GET_ITEM(fast, 0);
        value = PySequence_Fast_GET_ITEM(fast, 1);
        skey = PyObject_Str(key);
        if (skey == NULL)
            goto Fail;
        svalue = PyObject_Str(value);
        if (svalue == NULL) {
            Py_DECREF(svalue);
            goto Fail;
        }

        if (override || apr_table_get(self->table, 
                                      PyString_AsString(skey)) == NULL) {
            int status = table_ass_subscript(self, skey, svalue);
            if (status < 0) {
                Py_DECREF(skey);
                Py_DECREF(svalue);
                goto Fail;
            }
        }

        Py_DECREF(skey);
        Py_DECREF(svalue);
        Py_DECREF(fast);
        Py_DECREF(item);
    }

    i = 0;
    goto Return;
 Fail:
    Py_XDECREF(item);
    Py_XDECREF(fast);
    i = -1;
 Return:
    Py_DECREF(it);
    return i;
}

/**
 ** table_copy
 **
 */

static PyObject *table_copy(register tableobject *from)
{
    tableobject *to = (tableobject *)MpTable_New();
    if (to != NULL)
        apr_table_overlap(to->table, from->table, 0);

    return (PyObject*)to;
}

/**
 ** table_compare
 **
 */

static int table_compare(tableobject *a, tableobject *b)
{
    /* 
       we're so lazy that we just copy tables to dicts
       and rely on dict's compare ability. this is not
       the best way to do this to say the least
    */

    PyObject *ad, *bd;
    int result;

    ad = PyDict_New();
    bd = PyDict_New();

    PyDict_Merge(ad, (PyObject*)a, 0);
    PyDict_Merge(bd, (PyObject*)b, 0);

    result = PyObject_Compare(ad, bd);

    Py_DECREF(ad);
    Py_DECREF(bd);

    return result;
}

/**
 ** table_richcompare
 **
 */

static PyObject *table_richcompare(PyObject *v, PyObject *w, int op)
{
    Py_INCREF(Py_NotImplemented); /* XXX */
    return Py_NotImplemented;
}

/**
 ** table_has_key
 **
 */

static PyObject * table_has_key(tableobject *self, PyObject *key)
{

    const char *val;

    if (!PyString_CheckExact(key))
        return NULL;

    val = apr_table_get(self->table, PyString_AsString(key));

    if (val)
        return PyInt_FromLong(1);
    else
        return PyInt_FromLong(0);
}

/**
 ** table_get
 **
 *    implements get([failobj]) method
 */

static PyObject *table_get(register tableobject *self, PyObject *args)
{
    PyObject *key;
    PyObject *failobj = Py_None;
    PyObject *val = NULL;
    const char *sval;

    if (!PyArg_ParseTuple(args, "S|O:get", &key, &failobj))
        return NULL;

    sval = apr_table_get(self->table, PyString_AsString(key));
    
    if (sval == NULL) {
        val = failobj;
        Py_INCREF(val);
    }
    else
        val = PyString_FromString(sval);

    return val;
}

/**
 ** table_setdefault
 **
 *    implements setdefault(key, [val]) method
 */

static PyObject *table_setdefault(register tableobject *self, PyObject *args)
{
    PyObject *key;
    PyObject *failobj = NULL;
    PyObject *val = NULL;
    char *k = NULL;
    const char *v = NULL;

    if (!PyArg_ParseTuple(args, "O|O:setdefault", &key, &failobj))
        return NULL;

    if (!PyString_Check(key)) {
        PyErr_SetString(PyExc_TypeError,
                        "table keys must be strings");
        return NULL;
    }

    if (failobj && !PyString_Check(failobj)) {
        PyErr_SetString(PyExc_TypeError,
                        "table values must be strings");
        return NULL;
    }

    k = PyString_AsString(key);
    v = apr_table_get(self->table, k);

    if (v == NULL) {
        if (failobj == NULL) {
            apr_table_set(self->table, k, "");
            val = PyString_FromString("");
        }
        else {
            apr_table_set(self->table, k, PyString_AsString(failobj));
            val = failobj;
            Py_XINCREF(val);
        }
    }
    else
        val = PyString_FromString(v);

    return val;
}

/**
 ** table_clear
 **
 */

static PyObject *table_clear(register tableobject *self)
{
    apr_table_clear(self->table);

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** table_popitem
 **
 */

static PyObject *table_popitem(tableobject *self)
{
    apr_array_header_t *ah;
    apr_table_entry_t *elts;
    PyObject *res;

    ah = (apr_array_header_t *) apr_table_elts(self->table);
    elts = (apr_table_entry_t *) ah->elts;

    if (ah->nelts == 0) {
        PyErr_SetString(PyExc_KeyError,
                        "popitem(): table is empty");
        return NULL;
    }

    res = Py_BuildValue("(s,s)", elts[0].key, elts[0].val);
    ah->nelts--;
    elts++;

    return res;
}

/**
 ** table_traverse
 **
 */

static int table_traverse(tableobject *self, visitproc visit, void *arg)
{
    const apr_array_header_t *ah;
    apr_table_entry_t *elts;
    register int i;

    ah = apr_table_elts (self->table);
    elts = (apr_table_entry_t *) ah->elts;

    i = ah->nelts;

    while (i--)
        if (elts[i].key) {
            int err;
            PyObject *v = PyString_FromString(elts[i].val);
            err = visit(v, arg);
            Py_XDECREF(v);
            if (err)
                return err;
        }

    return 0;
}

/**
 ** table_tp_clear
 **
 */

static int table_tp_clear(tableobject *self)
{
    table_clear(self);
    return 0;
}

/**
 ** mp_table_add
 **
 *     this function is equivalent of ap_table_add - 
 *     it can create duplicate entries. 
 */

static PyObject * mp_table_add(tableobject *self, PyObject *args)
{

    const char *val, *key;

    if (! PyArg_ParseTuple(args, "ss", &key, &val))
        return NULL;

    apr_table_add(self->table, key, val);

    Py_INCREF(Py_None);
    return Py_None;
}

typedef PyObject * (*tableselectfunc)(apr_table_entry_t *);

staticforward PyObject *tableiter_new(tableobject *, tableselectfunc);

static PyObject *select_key(apr_table_entry_t *elts)
{
    return PyString_FromString(elts->key);
}

static PyObject *select_value(apr_table_entry_t *elts)
{
    return PyString_FromString(elts->val);
}

static PyObject *select_item(apr_table_entry_t *elts)
{
    return Py_BuildValue("(s,s)", elts->key, elts->val);
}

static PyObject *table_iterkeys(tableobject *self)
{
    return tableiter_new(self, select_key);
}

static PyObject *table_itervalues(tableobject *self)
{
    return tableiter_new(self, select_value);
}

static PyObject *table_iteritems(tableobject *self)
{
    return tableiter_new(self, select_item);
}

static char has_key__doc__[] =
"T.has_key(k) -> 1 if T has a key k, else 0";

static char get__doc__[] =
"T.get(k[,d]) -> T[k] if T.has_key(k), else d.  d defaults to None.";

static char setdefault_doc__[] =
"T.setdefault(k[,d]) -> T.get(k,d), also set T[k]=d if not T.has_key(k)";

static char popitem__doc__[] =
"T.popitem() -> (k, v), remove and return some (key, value) pair as a\n\
2-tuple; but raise KeyError if T is empty";

static char keys__doc__[] =
"T.keys() -> list of T's keys";

static char items__doc__[] =
"T.items() -> list of T's (key, value) pairs, as 2-tuples";

static char values__doc__[] =
"T.values() -> list of T's values";

static char update__doc__[] =
"T.update(E) -> None.  Update T from E: for k in E.keys(): T[k] = E[k]";

static char clear__doc__[] =
"T.clear() -> None.  Remove all items from T.";

static char copy__doc__[] =
"T.copy() -> a shallow copy of T";

static char iterkeys__doc__[] =
"T.iterkeys() -> an iterator over the keys of T";

static char itervalues__doc__[] =
"T.itervalues() -> an iterator over the values of T";

static char iteritems__doc__[] =
"T.iteritems() -> an iterator over the (key, value) items of T";

static char add__doc__[] =
"T.add(k, v) -> add (as oppsed to replace) a key k and value v";

/* table method definitions */
static PyMethodDef mp_table_methods[] = {
    {"has_key",     (PyCFunction)table_has_key,      METH_O,       has_key__doc__},
    {"get",         (PyCFunction)table_get,          METH_VARARGS, get__doc__},
    {"setdefault",  (PyCFunction)table_setdefault,   METH_VARARGS, setdefault_doc__},
    {"popitem",     (PyCFunction)table_popitem,      METH_NOARGS,  popitem__doc__},
    {"keys",        (PyCFunction)table_keys,         METH_NOARGS,  keys__doc__},
    {"items",       (PyCFunction)table_items,        METH_NOARGS,  items__doc__},
    {"values",      (PyCFunction)table_values,       METH_NOARGS,  values__doc__},
    {"update",      (PyCFunction)table_update,       METH_O,       update__doc__},
    {"clear",       (PyCFunction)table_clear,        METH_NOARGS,  clear__doc__},
    {"copy",        (PyCFunction)table_copy,         METH_NOARGS,  copy__doc__},
    {"iterkeys",    (PyCFunction)table_iterkeys,     METH_NOARGS,  iterkeys__doc__},
    {"itervalues",  (PyCFunction)table_itervalues,   METH_NOARGS,  itervalues__doc__},
    {"iteritems",   (PyCFunction)table_iteritems,    METH_NOARGS,  iteritems__doc__},
    {"add",         (PyCFunction)mp_table_add,       METH_VARARGS, add__doc__},
    {NULL,          NULL}       /* sentinel */
};

static int table_contains(tableobject *self, PyObject *key)
{
    return apr_table_get(self->table, PyString_AsString(key)) != NULL;
}

/* Hack to implement "key in table" */
static PySequenceMethods table_as_sequence = {
    0,                                  /* sq_length */
    0,                                  /* sq_concat */
    0,                                  /* sq_repeat */
    0,                                  /* sq_item */
    0,                                  /* sq_slice */
    0,                                  /* sq_ass_item */
    0,                                  /* sq_ass_slice */
    (objobjproc)table_contains,         /* sq_contains */
    0,                                  /* sq_inplace_concat */
    0,                                  /* sq_inplace_repeat */
};

static PyObject *table_alloc(PyTypeObject *type, int nitems)
{
    return MpTable_New();
}

/**
 ** table_new
 **
 */

static PyObject *table_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyObject *self;

    assert(type != NULL && type->tp_alloc != NULL);
    self = type->tp_alloc(type, 0);
    if (self != NULL) {
        apr_pool_t *p;
        tableobject *t = (tableobject *)self;
        apr_pool_sub_make(&p, NULL, NULL);
        t->pool = p;
        t->table = apr_table_make(p, 2);
    }

    return self;

}

static int table_init(tableobject *self, PyObject *args, PyObject *kwds)
{
    PyObject *arg = NULL;
    static char *kwlist[] = {"items", 0};
    int result = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O:mp_table",
                                     kwlist, &arg))
        result = -1;

    else if (arg != NULL) {
        if (PyObject_HasAttrString(arg, "keys"))
            result = table_merge(self, arg, 1);
        else
            result = table_mergefromseq2(self, arg, 1);
    }
    return result;
}

static long table_nohash(PyObject *self)
{
    PyErr_SetString(PyExc_TypeError, "mp_table objects are unhashable");
    return -1;
}

static PyObject *table_iter(tableobject *self)
{
    return tableiter_new(self, select_key);
}

static char mp_table_doc[] =
"table() -> new empty table.\n"
"table(mapping) -> new table initialized from a mapping object's\n"
"    (key, value) pairs.\n"
"table(seq) -> new table initialized as if via:\n"
"    d = {}\n"
"    for k, v in seq:\n"
"        d[k] = v";

PyTypeObject MpTable_Type = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_table",
    sizeof(tableobject),
    0,
    (destructor)table_dealloc,          /* tp_dealloc */
    (printfunc)table_print,             /* tp_print */
    0,                                  /* tp_getattr */
    0,                                  /* tp_setattr */
    (cmpfunc)table_compare,             /* tp_compare */
    (reprfunc)table_repr,               /* tp_repr */
    0,                                  /* tp_as_number */
    &table_as_sequence,                 /* tp_as_sequence */
    &table_as_mapping,                  /* tp_as_mapping */
    table_nohash,                       /* tp_hash */
    0,                                  /* tp_call */
    0,                                  /* tp_str */
    PyObject_GenericGetAttr,            /* tp_getattro */
    0,                                  /* tp_setattro */
    0,                                  /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT |
    Py_TPFLAGS_BASETYPE,                /* tp_flags */
    mp_table_doc,                       /* tp_doc */
    (traverseproc)table_traverse,       /* tp_traverse */
    (inquiry)table_tp_clear,            /* tp_clear */
    table_richcompare,                  /* tp_richcompare */
    0,                                  /* tp_weaklistoffset */
    (getiterfunc)table_iter,            /* tp_iter */
    0,                                  /* tp_iternext */
    mp_table_methods,                   /* tp_methods */
    0,                                  /* tp_members */
    0,                                  /* tp_getset */
    0,                                  /* tp_base */
    0,                                  /* tp_dict */
    0,                                  /* tp_descr_get */
    0,                                  /* tp_descr_set */
    0,                                  /* tp_dictoffset */
    (initproc)table_init,               /* tp_init */
    (allocfunc)table_alloc,             /* tp_alloc */
    table_new,                          /* tp_new */
    (destructor)table_dealloc,          /* tp_free */
};

/* Table iterator type */

extern PyTypeObject MpTableIter_Type; /* Forward */

typedef struct {
    PyObject_HEAD
    tableobject *table;
    int ti_nelts;
    int ti_pos;
    binaryfunc ti_select;
} tableiterobject;

static PyObject *tableiter_new(tableobject *table, tableselectfunc select)
{
    tableiterobject *ti;
    ti = PyObject_NEW(tableiterobject, &MpTableIter_Type);
    if (ti == NULL)
        return NULL;
    Py_INCREF(table);
    ti->table = table;
    ti->ti_nelts = table->table->a.nelts;
    ti->ti_pos = 0;
    ti->ti_select = (binaryfunc)select;
    return (PyObject *)ti;
}

static void tableiter_dealloc(tableiterobject *ti)
{
    Py_DECREF(ti->table);
    PyObject_DEL(ti);
}

static PyObject *tableiter_next(tableiterobject *ti, PyObject *args)
{
    PyObject *key, *val;
    apr_table_entry_t *elts = (apr_table_entry_t *) ti->table->table->a.elts;

    /* make sure the table hasn't change while being iterated */

    if (ti->ti_nelts != ti->table->table->a.nelts) {
        PyErr_SetString(PyExc_RuntimeError,
                        "table changed size during iteration");
        return NULL;
    } 

    /* return the next key/val */

    if (ti->ti_pos < ti->table->table->a.nelts) {
        key = PyString_FromString(elts[ti->ti_pos].key);
        val = PyString_FromString(elts[ti->ti_pos].val);
        ti->ti_pos++;
        return (*ti->ti_select)(key, val);
    }

    /* the end has been reached */

    PyErr_SetObject(PyExc_StopIteration, Py_None);
    return NULL;
}

static PyObject *tableiter_getiter(PyObject *it)
{
    Py_INCREF(it);
    return it;
}

static PyMethodDef tableiter_methods[] = {
    {"next",    (PyCFunction)tableiter_next,    METH_VARARGS,
     "it.next() -- get the next value, or raise StopIteration"},
    {NULL,              NULL}           /* sentinel */
};

static PyObject *tableiter_iternext(tableiterobject *ti)
{
    PyObject *key, *val;
    apr_table_entry_t *elts = (apr_table_entry_t *) ti->table->table->a.elts;

    /* make sure the table hasn't change while being iterated */

    if (ti->ti_nelts != ti->table->table->a.nelts) {
        PyErr_SetString(PyExc_RuntimeError,
                        "table changed size during iteration");
        return NULL;
    } 

    /* return the next key/val */

    if (ti->ti_pos < ti->table->table->a.nelts) {
        key = PyString_FromString(elts[ti->ti_pos].key);
        val = PyString_FromString(elts[ti->ti_pos].val);
        ti->ti_pos++;
        return (*ti->ti_select)(key, val);
    }

    /* the end has been reached */

    PyErr_SetObject(PyExc_StopIteration, Py_None);
    return NULL;

}

PyTypeObject MpTableIter_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                  /* ob_size */
    "dictionary-iterator",                      /* tp_name */
    sizeof(tableiterobject),                    /* tp_basicsize */
    0,                                  /* tp_itemsize */
    /* methods */
    (destructor)tableiter_dealloc,              /* tp_dealloc */
    0,                                  /* tp_print */
    0,                                  /* tp_getattr */
    0,                                  /* tp_setattr */
    0,                                  /* tp_compare */
    0,                                  /* tp_repr */
    0,                                  /* tp_as_number */
    0,                                  /* tp_as_sequence */
    0,                                  /* tp_as_mapping */
    0,                                  /* tp_hash */
    0,                                  /* tp_call */
    0,                                  /* tp_str */
    PyObject_GenericGetAttr,            /* tp_getattro */
    0,                                  /* tp_setattro */
    0,                                  /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                 /* tp_flags */
    0,                                  /* tp_doc */
    0,                                  /* tp_traverse */
    0,                                  /* tp_clear */
    0,                                  /* tp_richcompare */
    0,                                  /* tp_weaklistoffset */
    (getiterfunc)tableiter_getiter,             /* tp_iter */
    (iternextfunc)tableiter_iternext,   /* tp_iternext */
    tableiter_methods,                  /* tp_methods */
    0,                                  /* tp_members */
    0,                                  /* tp_getset */
    0,                                  /* tp_base */
    0,                                  /* tp_dict */
    0,                                  /* tp_descr_get */
    0,                                  /* tp_descr_set */
};


