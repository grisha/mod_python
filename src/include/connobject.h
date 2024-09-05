#ifndef Mp_CONNOBJECT_H
#define Mp_CONNOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

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
 * connobject.h
 *
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

    typedef struct connobject {
        PyObject_HEAD
        conn_rec     *conn;
        PyObject     *base_server;
        PyObject     *notes;
        hlistobject  *hlo;
    } connobject;

    PyAPI_DATA(PyTypeObject) MpConn_Type;

#define MpConn_Check(op) (Py_TYPE(op) == &MpConn_Type)

    PyAPI_FUNC(PyObject *) MpConn_FromConn (conn_rec *c);

#ifdef __cplusplus
}
#endif
#endif /* !Mp_CONNOBJECT_H */
