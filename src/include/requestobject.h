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
 * requestobject.h
 *
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
        PyObject       * headers_in;
        PyObject       * headers_out;
        PyObject       * err_headers_out;
        PyObject       * subprocess_env;
        PyObject       * notes;
        PyObject       * phase;
        PyObject       * config;
        PyObject       * options;
        char           * extension;   /* for | .ext syntax */
        int              content_type_set;
        apr_off_t        bytes_queued;
        hlistobject    * hlo;
        char           * rbuff;       /* read bufer */
        int              rbuff_len;   /* read buffer size */
        int              rbuff_pos;   /* position into the buffer */
        PyObject       * session;

    } requestobject;

    PyAPI_DATA(PyTypeObject) MpRequest_Type;

#define MpRequest_Check(op) (Py_TYPE(op) == &MpRequest_Type)

    PyAPI_FUNC(PyObject *) MpRequest_FromRequest (request_rec *r);

#ifndef ap_is_HTTP_VALID_RESPONSE
#define ap_is_HTTP_VALID_RESPONSE(x) (((x) >= 100)&&((x) < 600))
#endif

#ifdef __cplusplus
}
#endif
#endif /* !Mp_REQUESTOBJECT_H */
