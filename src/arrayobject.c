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
 *    contact grisha@ispol.com.
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
 * arrayobject.c 
 *
 * $Id: arrayobject.c,v 1.2 2000/12/05 23:47:01 gtrubetskoy Exp $
 *
 */

#include "mod_python.h"

/********************************
         array object
     XXX VERY EXPERIMENTAL
 ********************************/

/* This is a mapping of a Python object to an Apache
 * array_header.
 *
 * The idea is to make it appear as a Python list. The main difference
 * between an array and a Python list is that arrays are typed (i.e. all
 * items must be of the same type), and in this case the type is assumed 
 * to be a character string.
 */

/**
 **     MpArray_FromArray
 **
 *      This routine creates a Python arrayobject given an Apache
 *      array_header pointer.
 *
 */

PyObject * MpArray_FromArray(array_header * ah)
{
    arrayobject *result;

    result = PyMem_NEW(arrayobject, 1);
    if (! result)
	return (arrayobject *) PyErr_NoMemory();
  
    result->ah = ah;
    result->ob_type = &arrayobjecttype;
    result->pool = NULL;
  
    _Py_NewReference(result);
    return (PyObject *)result;
}

/**
 ** array_length
 **
 *      Number of elements in a array. Called
 *      when you do len(array) in Python.
 */

static int array_length(arrayobject *self) 
{ 
    return self->ah->nelts;
}

/**
 ** array_item
 **
 *
 *      Returns an array item.
 */

static PyObject *array_item(arrayobject *self, int i) 
{ 

    char **items;

    if (i < 0 || i >= self->ah->nelts) {
	PyErr_SetString(PyExc_IndexError, "array index out of range");
	return NULL;
    }

    items = (char **) self->ah->elts;
    return PyString_FromString(items[i]);
}

static PySequenceMethods array_mapping = {
    (inquiry)         array_length,      /*sq_length*/
    NULL,
    /*    (binaryfunc)      array_concat,*/      /*sq_concat*/
    NULL,
    /*    (intargfunc)      array_repeat,*/      /*sq_repeat*/
    (intargfunc)      array_item,        /*sq_item*/
    NULL,
    /*    (intintargfunc)   array_slice,  */     /*sq_slice*/
    NULL,
    /*    (intobjargproc)   array_ass_item, */   /*sq_ass_item*/
    NULL,
    /*    (intintobjargproc)array_ass_slice, */  /*sq_ass_slice*/
};


/**
 ** arrayappend
 **
 *
 *      Appends a string to an array.
 */

static PyObject *arrayappend(arrayobject *self, PyObject *args) 
{
    
    char **item;
    PyObject *s;
    
    if (!PyArg_Parse(args, "O", &s))
	return NULL;
    
    if (!PyString_Check(s)) {
	PyErr_SetString(PyExc_TypeError,
			"array items can only be strings");
	return NULL;
    }
    
    item = ap_push_array(self->ah);
    *item = ap_pstrdup(self->ah->pool, PyString_AS_STRING(s));

    Py_INCREF(Py_None);
    return Py_None;
}

/**
 ** arrayinsert
 **
 *
 *      XXX Not implemented
 */
static PyObject *arrayinsert(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "insert not implemented");
    return NULL;
}

/**
 ** arrayextend
 **
 *
 *      Appends another array to this one.
 *      XXX Not Implemented
 */

static PyObject *arrayextend(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "extend not implemented");
    return NULL;
}

/**
 ** arraypop
 **
 *
 *      Get an item and remove it from the list
 *      XXX Not Implemented
 */

static PyObject *arraypop(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "pop not implemented");
    return NULL;
}

/**
 ** arrayremove
 **
 *
 *      Remove an item from the array
 *      XXX Not Implemented
 */

static PyObject *arrayremove(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "remove not implemented");
    return NULL;
}

/**
 ** arrayindex
 **
 *
 *      Find an item in an array
 *      XXX Not Implemented
 */

static PyObject *arrayindex(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "index not implemented");
    return 0;
}

/**
 ** arraycount
 **
 *
 *      Count a particular item in an array
 *      XXX Not Implemented
 */

static PyObject *arraycount(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "count not implemented");
    return NULL;
}

/**
 ** arrayreverse
 **
 *
 *      Reverse the order of items in an array
 *      XXX Not Implemented
 */

static PyObject *arrayreverse(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "reverse not implemented");
    return NULL;
}

/**
 ** arraysort
 **
 *
 *      Sort items in an array
 *      XXX Not Implemented
 */

static PyObject *arraysort(arrayobject *self, PyObject *args) 
{
    PyErr_SetString(PyExc_NotImplementedError, 
		    "sort not implemented");
    return NULL;
}

static PyMethodDef arraymethods[] = {
    {"append",	(PyCFunction)arrayappend,  0},
    {"insert",	(PyCFunction)arrayinsert,  0},
    {"extend",  (PyCFunction)arrayextend,  METH_VARARGS},
    {"pop",	(PyCFunction)arraypop,     METH_VARARGS},
    {"remove",	(PyCFunction)arrayremove,  0},
    {"index",	(PyCFunction)arrayindex,   0},
    {"count",	(PyCFunction)arraycount,   0},
    {"reverse",	(PyCFunction)arrayreverse, 0},
    {"sort",	(PyCFunction)arraysort,    0},
    {NULL, NULL}		/* sentinel */
};

/**
 ** array_dealloc
 **
 *      Frees array's memory
 */

static void array_dealloc(arrayobject *self)
{  

    if (self->pool) 
	ap_destroy_pool(self->pool);

    free(self);
}

/**
 ** array_getattr
 **
 *      Gets array's attributes
 */

static PyObject *array_getattr(PyObject *self, char *name)
{
    return Py_FindMethod(arraymethods, self, name);
}

/**
 ** array_repr
 **
 *      prints array like a list
 */

static PyObject * array_repr(arrayobject *self)
{
    PyObject *s;
    array_header *ah;
    char **elts;
    int i;

    s = PyString_FromString("[");

    ah = self->ah;
    elts = (char **)ah->elts;

    i = ah->nelts;
    if (i == 0)
	PyString_ConcatAndDel(&s, PyString_FromString("]"));

    while (i--) {
	PyString_ConcatAndDel(&s, PyString_FromString("'"));
	PyString_ConcatAndDel(&s, PyString_FromString(elts[i]));
	PyString_ConcatAndDel(&s, PyString_FromString("'"));
	if (i > 0)
	    PyString_ConcatAndDel(&s, PyString_FromString(", "));
	else
	    PyString_ConcatAndDel(&s, PyString_FromString("]"));
    }

    return s;
}

static PyTypeObject arrayobjecttype = {
    PyObject_HEAD_INIT(NULL)
    0,
    "mp_array",
    sizeof(arrayobject),
    0,
    (destructor) array_dealloc,     /*tp_dealloc*/
    0,                              /*tp_print*/
    (getattrfunc) array_getattr,    /*tp_getattr*/
    0,                              /*tp_setattr*/
    0,                              /*tp_compare*/
    (reprfunc) array_repr,          /*tp_repr*/
    0,                              /*tp_as_number*/
    &array_mapping,                 /*tp_as_sequence*/
    0,                              /*tp_as_mapping*/
    0,                              /*tp_hash*/
};

