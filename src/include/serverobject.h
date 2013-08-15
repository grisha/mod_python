#ifndef Mp_SERVEROBJECT_H
#define Mp_SERVEROBJECT_H
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
 * serverobject.h
 *
 *
 */

    typedef struct serverobject {
        PyObject_HEAD
        PyObject       *dict;
        server_rec     *server;
        PyObject       *next;
    } serverobject;
    
    extern DL_IMPORT(PyTypeObject) MpServer_Type;
    
#define MpServer_Check(op) ((op)->ob_type == &MpServer_Type)
    
    extern DL_IMPORT(PyObject *) MpServer_FromServer Py_PROTO((server_rec *s));

#ifdef __cplusplus
}
#endif
#endif /* !Mp_SERVEROBJECT_H */
