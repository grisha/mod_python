/* ====================================================================
 * Copyright (c) 2001 Gregory Trubetskoy.  All rights reserved.
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
 *    contact grisha@modpython.org.
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
 * filterobject.h 
 *
 * $Id: filterobject.h,v 1.2 2001/11/03 04:24:30 gtrubetskoy Exp $
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
	apr_size_t *readbytes;

	int closed;
	int softspace;
	int bytes_written;

	char *handler;
	char *dir;

	requestobject *request_obj;
	PyObject *Request;

    } filterobject;

    extern DL_IMPORT(PyTypeObject) MpFilter_Type;
    
#define MpFilter_Check(op) ((op)->ob_type == &MpFilter_Type)
    
    extern DL_IMPORT(PyObject *) 
	MpFilter_FromFilter Py_PROTO((ap_filter_t *f, apr_bucket_brigade *bb_in, 
				      int is_input, ap_input_mode_t mode, 
				      apr_size_t *readbytes, char *hadler, char *dir));

#ifdef __cplusplus
}
#endif
#endif /* !Mp_FILTEROBJECT_H */
