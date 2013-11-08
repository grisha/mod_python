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
 * tableobject.c
 *
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

    TABLE_DEBUG("MpTable_FromTable");
	MpTable_Type.ob_type = &PyType_Type;
    result = PyObject_New(tableobject, &MpTable_Type);
    if (! result)
        return PyErr_NoMemory();

    result->table = t;
    result->pool = NULL;

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

    TABLE_DEBUG("MpTable_New");

    /* XXX need second arg abort function to report mem error */
    apr_pool_create_ex(&p, NULL, NULL, NULL);

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

static void table_dealloc(register void *o)
{
    tableobject *self = (tableobject *)o;

    TABLE_DEBUG("table_dealloc");

    if (MpTable_Check(self)) {
        if (self->pool)
            apr_pool_destroy(self->pool);
        PyObject_Del(self);
    }
    else
        Py_TYPE(self)->tp_free((PyObject *)self);

}

/**
 ** table_print
 **
 *      prints table like a dictionary
 *      (Useful when debugging)
 */

static int table_print(register tableobject *self, register FILE *fp, register int flags)
{
    const apr_array_header_t *ah = NULL;
    apr_table_entry_t *elts;
    register int i;

    TABLE_DEBUG("table_print");

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
 *      repr table like a dictionary
 */

static PyObject * table_repr(tableobject *self)
{
    PyObject *s;
    PyObject *t = NULL;
    const apr_array_header_t *ah;
    apr_table_entry_t *elts;
    int i;

    TABLE_DEBUG("table_repr");

    s = PyBytes_FromString("{");

    ah = apr_table_elts (self->table);
    elts = (apr_table_entry_t *) ah->elts;

    i = ah->nelts;
    if (i == 0)
        PyBytes_ConcatAndDel(&s, PyBytes_FromString("}"));

    while (i--)
        if (elts[i].key)
        {
            t = PyBytes_FromString(elts[i].key);
            PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));;
            Py_XDECREF(t);

            PyBytes_ConcatAndDel(&s, PyBytes_FromString(": "));

            if (elts[i].val) {
              t = PyBytes_FromString(elts[i].val);
            } else {
              t = Py_None;
              Py_INCREF(t);
            }

            PyBytes_ConcatAndDel(&s, MpObject_ReprAsBytes(t));
            Py_XDECREF(t);

            if (i > 0)
                PyBytes_ConcatAndDel(&s, PyBytes_FromString(", "));
            else
                PyBytes_ConcatAndDel(&s, PyBytes_FromString("}"));
        }

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

/**
 ** tablelength
 **
 *      Number of elements in a table. Called
 *      when you do len(table) in Python.
 */

static Py_ssize_t tablelength(PyObject *self)
{
    TABLE_DEBUG("tablelength");

    return apr_table_elts(((tableobject *)self)->table)->nelts;
}

/**
 ** table_subscript
 **
 *      Gets a dictionary item
 */

static PyObject * table_subscript(PyObject *self, register PyObject *key)
{
    char *k;
    const apr_array_header_t *ah;
    apr_table_entry_t *elts;
    register int i;
    PyObject *list;

    TABLE_DEBUG("table_subscript");

    MP_ANYSTR_AS_STR(k, key, 1);
    if (!k) {
        Py_DECREF(key);
        return NULL;
    }

    /* it's possible that we have duplicate keys, so
       we can't simply use apr_table_get since that just
       returns the first match.
    */

    list = PyList_New(0);
    if (!list)
        return NULL;

    ah = apr_table_elts (((tableobject *)self)->table);
    elts = (apr_table_entry_t *) ah->elts;

    i = ah->nelts;

    while (i--)
        if (elts[i].key) {
            if (apr_strnatcasecmp(elts[i].key, k) == 0) {
                PyObject *v = NULL;
                if (elts[i].val != NULL)
                    v = MpBytesOrUnicode_FromString(elts[i].val);
                else {
                    v = Py_None;
                    Py_INCREF(v);
                }
                PyList_Insert(list, 0, v);
                Py_DECREF(v);
            }
        }

    Py_DECREF(key); /* becasue of MP_ANYSTR_AS_STR */

    /* if no match */
    if (PyList_Size(list) == 0) {
        Py_DECREF(list);
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

static int table_ass_subscript(PyObject *self, PyObject *key,
                               PyObject *val)
{
    char *k, *v;

    TABLE_DEBUG("table_ass_subscript");

    MP_ANYSTR_AS_STR(k, key, 1);
    if (!k) {
        Py_XDECREF(key); /* MP_ANYSTR_AS_STR */
        return -1;
    }

    if (val == NULL)
        apr_table_unset(((tableobject *)self)->table, k);
    else {
        MP_ANYSTR_AS_STR(v, val, 1);
        if (!v) {
            Py_XDECREF(key); /* MP_ANYSTR_AS_STR */
            Py_XDECREF(val); /* MP_ANYSTR_AS_STR */
            return -1;
        }
        apr_table_set(((tableobject *)self)->table, k, v);
    }
    Py_XDECREF(key); /* MP_ANYSTR_AS_STR */
    Py_XDECREF(val); /* MP_ANYSTR_AS_STR */
    return 0;
}

/* table as mapping */

static PyMappingMethods table_as_mapping = {
    tablelength,           /*mp_length*/
    table_subscript,       /*mp_subscript*/
    table_ass_subscript,   /*mp_ass_subscript*/
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

    TABLE_DEBUG("table_keys");

    ah = apr_table_elts(self->table);
    elts = (apr_table_entry_t *) ah->elts;

    v = PyList_New(ah->nelts);

    for (i = 0, j = 0; i < ah->nelts; i++)
    {
        if (elts[i].key)
        {
            PyObject *key = MpBytesOrUnicode_FromString(elts[i].key);
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

    TABLE_DEBUG("table_values");

    ah = apr_table_elts(self->table);
    elts = (apr_table_entry_t *) ah->elts;
    v = PyList_New(ah->nelts);

    for (i = 0, j = 0; i < ah->nelts; i++)
    {
        if (elts[i].key)
        {
            PyObject *val = NULL;
            if (elts[i].val != NULL)
                val = MpBytesOrUnicode_FromString(elts[i].val);
            else {
                val = Py_None;
                Py_INCREF(val);
            }
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

    TABLE_DEBUG("table_items");

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

    TABLE_DEBUG("table_merge");

    if (keys == NULL) {
        TABLE_DEBUG("  table_merge: keys NULL");
        return -1;
    }

    iter = PyObject_GetIter(keys);
    Py_DECREF(keys);
    if (iter == NULL) {
        TABLE_DEBUG("  table_merge: iter NULL");
        return -1;
    }

    for (key = PyIter_Next(iter); key; key = PyIter_Next(iter)) {
        char *c_skey;

        skey = PyObject_Str(key);
        if (skey == NULL) {
            Py_DECREF(iter);
            Py_DECREF(key);
            TABLE_DEBUG("  table_merge: skey NULL");
            return -1;
        }
        MP_ANYSTR_AS_STR(c_skey, skey, 0);
        if (!c_skey) {
            Py_DECREF(key);
            Py_DECREF(skey);
            TABLE_DEBUG("  table_merge: c_skey NULL");
            return -1;
        }
        if (!override && apr_table_get(a->table, c_skey) != NULL) {
            Py_DECREF(key);
            Py_DECREF(skey);
            continue;
        }

        value = PyObject_GetItem(b, key);
        if (value == NULL) {
            Py_DECREF(iter);
            Py_DECREF(key);
            Py_DECREF(skey);
            TABLE_DEBUG("  table_merge: value NULL");
            return -1;
        }
        svalue = PyObject_Str(value);
        if (svalue == NULL) {
            Py_DECREF(iter);
            Py_DECREF(key);
            Py_DECREF(skey);
            Py_DECREF(value);
            TABLE_DEBUG("  table_merge: svalue NULL");
            return -1;
        }
        status = table_ass_subscript((PyObject *)a, skey, svalue);
        Py_DECREF(key);
        Py_DECREF(value);
        Py_DECREF(skey);
        Py_DECREF(svalue);
        if (status < 0) {
            Py_DECREF(iter);
            TABLE_DEBUG("  table_merge: status < 0");
            return -1;
        }
    }
    Py_DECREF(iter);
    if (PyErr_Occurred()) {
        /* Iterator completed, via error */
        TABLE_DEBUG("  table_merge: PyErr_Occurred()");
        return -1;
    }

    return 0;
}

/**
 ** table_update
 **
 */

static PyObject *table_update(tableobject *self, PyObject *other)
{
    TABLE_DEBUG("table_update");

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

    TABLE_DEBUG("table_mergefromseq2");

    it = PyObject_GetIter(seq2);
    if (it == NULL)
        return -1;

    for (i = 0; ; ++i) {
        PyObject *key, *value, *skey, *svalue;
        char *c_skey;
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

        MP_ANYSTR_AS_STR(c_skey, skey, 0);
        if (!c_skey) {
            Py_DECREF(skey);
            Py_DECREF(svalue);
            goto Fail;
        }

        if (override || apr_table_get(self->table, c_skey) == NULL) {
            int status = table_ass_subscript((PyObject *)self, skey, svalue);
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

    TABLE_DEBUG("table_copy");

    if (to != NULL)
        apr_table_overlap(to->table, from->table, 0);

    return (PyObject*)to;
}

#if PY_MAJOR_VERSION < 3
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

    TABLE_DEBUG("table_compare");

    ad = PyDict_New();
    bd = PyDict_New();

    PyDict_Merge(ad, (PyObject*)a, 0);
    PyDict_Merge(bd, (PyObject*)b, 0);

    result = PyObject_Compare(ad, bd);

    Py_DECREF(ad);
    Py_DECREF(bd);

    return result;
}
#endif

/**
 ** table_richcompare
 **
 */

static PyObject *table_richcompare(PyObject *a, PyObject *b, int op)
{

    PyObject *ad, *bd, *result;

    TABLE_DEBUG("table_richcompare");

    ad = PyDict_New();
    bd = PyDict_New();

    PyDict_Merge(ad, (PyObject*)a, 0);
    PyDict_Merge(bd, (PyObject*)b, 0);

    result = PyObject_RichCompare(ad, bd, op);

    Py_DECREF(ad);
    Py_DECREF(bd);

    return result;

}

/**
 ** table_has_key
 **
 */

static PyObject * table_has_key(tableobject *self, PyObject *key)
{

    const char *k;

    TABLE_DEBUG("table_has_key");

    MP_ANYSTR_AS_STR(k, key, 1);
    if (!k) {
        Py_DECREF(key); /* MP_ANYSTR_AS_STR */
        return NULL;
    }

    if (apr_table_get(self->table, k))
        return PyLong_FromLong(1);
    else
        return PyLong_FromLong(0);
}

/**
 ** table_get
 **
 *    implements get([failobj]) method
 *    (only returns the first match)
 */

static PyObject *table_get(register tableobject *self, PyObject *args)
{
    PyObject *key;
    PyObject *failobj = Py_None;
    PyObject *val = NULL;
    const char *k, *v;

    TABLE_DEBUG("table_get");

    if (!PyArg_ParseTuple(args, "O|O:get", &key, &failobj))
        return NULL;

    MP_ANYSTR_AS_STR(k, key, 1);
    if (!k) {
        Py_DECREF(key); /* MP_ANYSTR_AS_STR */
        return NULL;
    }

    v = apr_table_get(self->table, k);
    if (!v) {
        val = failobj;
        Py_INCREF(val);
    }
    else
        val = MpBytesOrUnicode_FromString(v);

    Py_DECREF(key); /* MP_ANYSTR_AS_STR */
    return val;
}

/**
 ** table_setdefault
 **
 *    implements setdefault(key, [val]) method
 */

static PyObject *table_setdefault(register tableobject *self, PyObject *args)
{
    int len;
    PyObject *failobj = NULL;
    PyObject *key, *val = NULL;
    char *k = NULL, *f = NULL;
    const char *v = NULL;

    TABLE_DEBUG("table_setdefault");

    if (!PyArg_ParseTuple(args, "O|O:setdefault", &key, &failobj))
        return NULL;

    MP_ANYSTR_AS_STR(k, key, 1);
    if (!k) {
        Py_DECREF(key); /* MP_ANYSTR_AS_STR */
        return NULL;
    }

    if (failobj) {
        MP_ANYSTR_AS_STR(f, failobj, 1);
        if (!f) {
            Py_DECREF(failobj); /* MP_ANYSTR_AS_ATR */
            return NULL;
        }
    }

    v = apr_table_get(self->table, k);
    if (!v) {
        if (f) {
            apr_table_set(self->table, k, f);
            val = failobj;
            Py_INCREF(val);
        }
        else {
            apr_table_set(self->table, k, "");
            v = "";
        }
    }

    val = MpBytesOrUnicode_FromString(v);

    Py_XDECREF(failobj); /* MP_ANYSTR_AS_ATR */
    return val;
}

/**
 ** table_clear
 **
 */

static PyObject *table_clear(register tableobject *self)
{
    TABLE_DEBUG("table_clear");

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

    TABLE_DEBUG("table_popitem");

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

    TABLE_DEBUG("table_traverse");

    ah = apr_table_elts (self->table);
    elts = (apr_table_entry_t *) ah->elts;

    i = ah->nelts;

    while (i--)
        if (elts[i].key) {
            int err;

            PyObject *v = NULL;
            if (elts[i].val != NULL)
                v = MpBytesOrUnicode_FromString(elts[i].val);
            else {
                v = Py_None;
                Py_INCREF(v);
            }

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
    TABLE_DEBUG("table_tp_clear");

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
    PyObject *key, *val;
    const char *k, *v;

    TABLE_DEBUG("mp_table_add");

    if (! PyArg_ParseTuple(args, "OO", &key, &val))
        return NULL;

    MP_ANYSTR_AS_STR(k, key, 1);
    MP_ANYSTR_AS_STR(v, val, 1);
    if ((!k) || (!v)) {
        Py_DECREF(key); /* MP_ANYSTR_AS_STR */
        Py_DECREF(val); /* MP_ANYSTR_AS_STR */
        return NULL;
    }

    apr_table_add(self->table, k, v);

    Py_DECREF(key); /* MP_ANYSTR_AS_STR */
    Py_DECREF(val); /* MP_ANYSTR_AS_STR */

    Py_INCREF(Py_None);
    return Py_None;
}

typedef PyObject * (*tableselectfunc)(apr_table_entry_t *);

static PyObject *tableiter_new(tableobject *, tableselectfunc);

static PyObject *select_key(apr_table_entry_t *elts)
{
    return MpBytesOrUnicode_FromString(elts->key);
}

static PyObject *select_value(apr_table_entry_t *elts)
{
    PyObject *val = NULL;

    TABLE_DEBUG("select_value");

    if (elts->val != NULL)
        val = MpBytesOrUnicode_FromString(elts->val);
    else {
        val = Py_None;
        Py_INCREF(val);
    }

    return val;
}

static PyObject *select_item(apr_table_entry_t *elts)
{
    TABLE_DEBUG("select_item");

    return Py_BuildValue("(s,s)", elts->key, elts->val);
}

static PyObject *table_iterkeys(tableobject *self)
{
    TABLE_DEBUG("table_iterkeys");

    return tableiter_new(self, select_key);
}

static PyObject *table_itervalues(tableobject *self)
{
    TABLE_DEBUG("table_itervalues");

    return tableiter_new(self, select_value);
}

static PyObject *table_iteritems(tableobject *self)
{
    TABLE_DEBUG("table_iteritems");

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
    char *k;
    const char *v;
    int rc;

    TABLE_DEBUG("table_contains");

    MP_ANYSTR_AS_STR(k, key, 1);
    if (!k) {
        Py_DECREF(key);
        return -1;
    }
    v = apr_table_get(self->table, k);
    Py_DECREF(key);
    return (v != NULL);
}

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

/**
 ** table_new
 **
 */

static PyObject *table_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    TABLE_DEBUG("table_new");

    return MpTable_New();
}

static int table_init(tableobject *self, PyObject *args, PyObject *kwds)
{
    PyObject *arg = NULL;
    static char *kwlist[] = {"items", 0};
    int result = 0;

    TABLE_DEBUG("table_init");

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
    TABLE_DEBUG("table_nohash");

    PyErr_SetString(PyExc_TypeError, "mp_table objects are unhashable");
    return -1;
}

static PyObject *table_iter(tableobject *self)
{
    TABLE_DEBUG("table_iter");

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
    PyVarObject_HEAD_INIT(NULL, 0)
    "mp_table",                         /* tp_name */
    sizeof(tableobject),                /* tp_basicsize */
    0,                                  /* tp_itemsize */
    (destructor)table_dealloc,          /* tp_dealloc */
    (printfunc)table_print,             /* tp_print */
    0,                                  /* tp_getattr */
    0,                                  /* tp_setattr */
#if PY_MAJOR_VERSION < 3
    (cmpfunc)table_compare,             /* tp_compare */
#else
    0,                                  /* tp_reserved */
#endif
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
    /* PYTHON 2.5: 'inquiry' should be perhaps replaced with 'lenfunc' */
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
    0,                                  /* tp_alloc */
    table_new,                          /* tp_new */
    table_dealloc,                      /* tp_free */
};

/* Table iterator type */

extern PyTypeObject MpTableIter_Type; /* Forward */

typedef struct {
    PyObject_HEAD
    tableobject *table;
    int ti_nelts;
    int ti_pos;
    tableselectfunc ti_select;
} tableiterobject;

static PyObject *tableiter_new(tableobject *table, tableselectfunc select)
{
    tableiterobject *ti;

    TABLE_DEBUG("tableiter_new");
	MpTableIter_Type.ob_type = &PyType_Type;
    ti = PyObject_NEW(tableiterobject, &MpTableIter_Type);
    if (ti == NULL)
        return NULL;
    Py_INCREF(table);
    ti->table = table;
    ti->ti_nelts = table->table->a.nelts;
    ti->ti_pos = 0;
    ti->ti_select = select;
    return (PyObject *)ti;
}

static void tableiter_dealloc(tableiterobject *ti)
{
    Py_DECREF(ti->table);
    PyObject_DEL(ti);
}

static PyObject *tableiter_next(tableiterobject *ti, PyObject *args)
{
    apr_table_entry_t *elts = (apr_table_entry_t *) ti->table->table->a.elts;

    TABLE_DEBUG("tableiter_next");

    /* make sure the table hasn't change while being iterated */

    if (ti->ti_nelts != ti->table->table->a.nelts) {
        PyErr_SetString(PyExc_RuntimeError,
                        "table changed size during iteration");
        return NULL;
    }

    /* return the next key/val */

    if (ti->ti_pos < ti->table->table->a.nelts) {
        return (*ti->ti_select)(&elts[ti->ti_pos++]);
    }

    /* the end has been reached */

    PyErr_SetObject(PyExc_StopIteration, Py_None);
    return NULL;
}

static PyObject *tableiter_getiter(PyObject *it)
{
    TABLE_DEBUG("tableiter_getiter");

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
    apr_table_entry_t *elts = (apr_table_entry_t *) ti->table->table->a.elts;

    TABLE_DEBUG("tableiter_iternext");

    /* make sure the table hasn't change while being iterated */

    if (ti->ti_nelts != ti->table->table->a.nelts) {
        PyErr_SetString(PyExc_RuntimeError,
                        "table changed size during iteration");
        return NULL;
    }

    /* return the next key/val */

    if (ti->ti_pos < ti->table->table->a.nelts) {
        return (*ti->ti_select)(&elts[ti->ti_pos++]);
    }

    /* the end has been reached */

    PyErr_SetObject(PyExc_StopIteration, Py_None);
    return NULL;

}

PyTypeObject MpTableIter_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dictionary-iterator",              /* tp_name */
    sizeof(tableiterobject),            /* tp_basicsize */
    0,                                  /* tp_itemsize */
    /* methods */
    (destructor)tableiter_dealloc,      /* tp_dealloc */
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
    (getiterfunc)tableiter_getiter,     /* tp_iter */
    (iternextfunc)tableiter_iternext,   /* tp_iternext */
    tableiter_methods,                  /* tp_methods */
    0,                                  /* tp_members */
    0,                                  /* tp_getset */
    0,                                  /* tp_base */
    0,                                  /* tp_dict */
    0,                                  /* tp_descr_get */
    0,                                  /* tp_descr_set */
};


