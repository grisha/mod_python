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
 * filterobject.h 
 *
 * $Id$
 *
 */

#ifndef Mp_FILTEROBJECT_H
#define Mp_FILTEROBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

    typedef struct filterobject {
        PyObject_HEAD
        ap_filter_t        *f;

        /* in out refers to the dircetion of data with respect to
           filter, not the filter type */
        apr_bucket_brigade *bb_in; 
        apr_bucket_brigade *bb_out;

        apr_status_t rc;

        int is_input;
        ap_input_mode_t mode;
        apr_size_t readbytes;

        int closed;
        int softspace;
        int bytes_written;

        char *handler;
        char *dir;

        requestobject *request_obj;

    } filterobject;

    extern DL_IMPORT(PyTypeObject) MpFilter_Type;
    
#define MpFilter_Check(op) ((op)->ob_type == &MpFilter_Type)
    
    extern DL_IMPORT(PyObject *) 
        MpFilter_FromFilter Py_PROTO((ap_filter_t *f, apr_bucket_brigade *bb_in, 
                                      int is_input, ap_input_mode_t mode, 
                                      apr_size_t readbytes, char *hadler, char *dir));

#ifdef __cplusplus
}
#endif
#endif /* !Mp_FILTEROBJECT_H */
