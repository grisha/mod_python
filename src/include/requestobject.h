/* ====================================================================
 * The Apache Software License, Version 1.1
 *
 * Copyright (c) 2000-2002 The Apache Software Foundation.  All rights
 * reserved.
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
 * 3. The end-user documentation included with the redistribution,
 *    if any, must include the following acknowledgment:
 *       "This product includes software developed by the
 *        Apache Software Foundation (http://www.apache.org/)."
 *    Alternately, this acknowledgment may appear in the software itself,
 *    if and wherever such third-party acknowledgments normally appear.
 *
 * 4. The names "Apache" and "Apache Software Foundation" must
 *    not be used to endorse or promote products derived from this
 *    software without prior written permission. For written
 *    permission, please contact apache@apache.org.
 *
 * 5. Products derived from this software may not be called "Apache",
 *    "mod_python", or "modpython", nor may these terms appear in their
 *    name, without prior written permission of the Apache Software
 *    Foundation.
 *
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED.  IN NO EVENT SHALL THE APACHE SOFTWARE FOUNDATION OR
 * ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 * USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 * ====================================================================
 *
 * This software consists of voluntary contributions made by many
 * individuals on behalf of the Apache Software Foundation.  For more
 * information on the Apache Software Foundation, please see
 * <http://www.apache.org/>.
 *
 * Originally developed by Gregory Trubetskoy.
 *
 *
 * requestobject.h
 *
 * $Id: requestobject.h,v 1.14 2002/12/18 20:47:02 grisha Exp $
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
