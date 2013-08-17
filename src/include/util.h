#ifndef Mp_UTIL_H
#define Mp_UTIL_H

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
 * util.h 
 *
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

PyObject * tuple_from_array_header(const apr_array_header_t *ah);
PyObject * tuple_from_method_list(const ap_method_list_t *l);
PyObject *tuple_from_finfo(apr_finfo_t *f);
PyObject *tuple_from_apr_uri(apr_uri_t *u);
char * get_addhandler_extensions(request_rec *req);
apr_status_t python_decref(void *object);
PyMemberDef *find_memberdef(const PyMemberDef *mlist, const char *name);
PyObject *cfgtree_walk(ap_directive_t *dir);

#endif /* !Mp_UTIL_H */
