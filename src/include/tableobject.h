#ifndef Mp_TABLEOBJECT_H
#define Mp_TABLEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

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
 * tableobject.h
 *
 * $Id: tableobject.h,v 1.4 2002/08/09 21:40:57 gtrubetskoy Exp $
 *
 */

/*
 * This is a mapping of a Python object to an Apache table.
 *
 * This object behaves like a dictionary. Note that the
 * underlying table can have duplicate keys, which can never
 * happen to a Python dictionary. But this is such a rare thing 
 * that I can't even think of a possible scenario or implications.
 *
 */

    typedef struct tableobject {
	PyObject_VAR_HEAD
	apr_table_t     *table;
	apr_pool_t      *pool;
    } tableobject;
    
    extern DL_IMPORT(PyTypeObject) MpTable_Type;
    extern DL_IMPORT(PyTypeObject) MpTableIter_Type;
    
#define MpTable_Check(op) ((op)->ob_type == &MpTable_Type)
    
    extern DL_IMPORT(PyObject *) MpTable_FromTable Py_PROTO((apr_table_t *t));
    extern DL_IMPORT(PyObject *) MpTable_New Py_PROTO((void));

#ifdef __cplusplus
}
#endif
#endif /* !Mp_TABLEOBJECT_H */
