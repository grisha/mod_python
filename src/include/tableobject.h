#ifndef Mp_TABLEOBJECT_H
#define Mp_TABLEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

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

    PyAPI_DATA(PyTypeObject) MpTable_Type;
    PyAPI_DATA(PyTypeObject) MpTableIter_Type;

#define MpTable_Check(op) (Py_TYPE(op) == &MpTable_Type)

    PyAPI_FUNC(PyObject *) MpTable_FromTable (apr_table_t *t);
    PyAPI_FUNC(PyObject *) MpTable_New (void);

/* #define DEBUG_TABLES 1 */
#ifdef DEBUG_TABLES
#define TABLE_DEBUG(str) printf("mp_table: %s\n", str)
#else
#define TABLE_DEBUG(str)
#endif

#ifdef __cplusplus
}
#endif
#endif /* !Mp_TABLEOBJECT_H */
