/*
 * Copyright (C) 2000, 2001, 2013, 2024 Gregory Trubetskoy
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
 * hlistobject.h
 *
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

    PyAPI_DATA(PyTypeObject) MpHList_Type;

#define MpHList_Check(op) (Py_TYPE(op) == &MpHList_Type)

    PyAPI_FUNC(PyObject *)MpHList_FromHLEntry (hl_entry *hle);

#ifdef __cplusplus
}
#endif
#endif /* !Mp_HLISTOBJECT_H */
