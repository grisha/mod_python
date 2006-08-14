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
 * hlistobject.h 
 *
 * $Id$
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

#ifndef Mp_HLISTOBJECT_H
#define Mp_HLISTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

    typedef struct hlist {
        PyObject_HEAD
        struct hl_entry *head;
    } hlistobject;

    extern DL_IMPORT(PyTypeObject) MpHList_Type;
    
#define MpHList_Check(op) ((op)->ob_type == &MpHList_Type)

    extern DL_IMPORT(PyObject *)MpHList_FromHLEntry Py_PROTO((hl_entry *hle));
    
#ifdef __cplusplus
}
#endif
#endif /* !Mp_HLISTOBJECT_H */
