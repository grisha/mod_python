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
 * requestobject.h
 *
 * $Id$
 *
 */

#ifndef Mp_REQUESTOBJECT_H
#define Mp_REQUESTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

    typedef struct requestobject {
        PyObject_HEAD
        PyObject       * dict;
        request_rec    * request_rec;
        PyObject       * connection;
        PyObject       * server;
        PyObject       * next;
        PyObject       * prev;
        PyObject       * main;
        PyObject       * headers_in;
        PyObject       * headers_out;
        PyObject       * err_headers_out;
        PyObject       * subprocess_env;
        PyObject       * notes;
        PyObject       * phase;
        char           * extension;   /* for | .ext syntax */
        char           * interpreter; 
        int              content_type_set;
        hlistobject    * hlo;
        char           * rbuff;       /* read bufer */
        int              rbuff_len;   /* read buffer size */
        int              rbuff_pos;   /* position into the buffer */
    } requestobject;

    extern DL_IMPORT(PyTypeObject) MpRequest_Type;
    
#define MpRequest_Check(op) ((op)->ob_type == &MpRequest_Type)
    
    extern DL_IMPORT(PyObject *) MpRequest_FromRequest Py_PROTO((request_rec *r));

#ifdef __cplusplus
}
#endif
#endif /* !Mp_REQUESTOBJECT_H */
