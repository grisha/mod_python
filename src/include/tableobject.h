#ifndef Mp_TABLEOBJECT_H
#define Mp_TABLEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

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
 * tableobject.h
 *
 *
 */

/*
 * This is a mapping of a Python object to an Apache table.
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
