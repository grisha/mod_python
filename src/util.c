/* ====================================================================
 * Copyright (c) 2000 Gregory Trubetskoy.  All rights reserved.
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
 * util.c 
 *
 * $Id: util.c,v 1.6 2002/08/15 21:46:35 gtrubetskoy Exp $
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

#include "mod_python.h"

/**
 ** tuple_from_array_header
 **
 *   Given an array header return a tuple. The array elements
 *   assumed to be strings.
 */

PyObject * tuple_from_array_header(const apr_array_header_t *ah)
{

    PyObject *t;
    int i;
    char **s;

    if (ah == NULL)
    {
	Py_INCREF(Py_None);
	return Py_None;
    }
    else
    {
	t = PyTuple_New(ah->nelts);

	s = (char **) ah->elts;
	for (i = 0; i < ah->nelts; i++) {
	    PyTuple_SetItem(t, i, PyString_FromString(s[i]));
	}
	return t;
    }
}

/**
 ** tuple_from_method_list
 **
 *   Given an apr_method_list_t return a tuple. 
 */

PyObject * tuple_from_method_list(const ap_method_list_t *l)
{

    PyObject *t;
    int i;
    char **methods;

    if ((l->method_list == NULL) || (l->method_list->nelts == 0)) {
	Py_INCREF(Py_None);
	return Py_None;
    }
    else {
	t = PyTuple_New(l->method_list->nelts);
	
	methods = (char **)l->method_list->elts;
	for (i = 0; i < l->method_list->nelts; ++i) {
	    PyTuple_SetItem(t, i, PyString_FromString(methods[i]));
	}
	return t;
    }
}

/**
 ** tuple_from_finfo
 **
 *  makes a tuple similar to return of os.stat() from apr_finfo_t
 *
 */

PyObject *tuple_from_finfo(apr_finfo_t *f)
{
    PyObject *t;

    if (f->filetype == APR_NOFILE) {
	Py_INCREF(Py_None);
	return Py_None;
    }
      
    t = PyTuple_New(12);

    if (f->valid & APR_FINFO_PROT) {
	PyTuple_SET_ITEM(t, 0, PyInt_FromLong(f->protection));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 0, Py_None);
    }
    if (f->valid & APR_FINFO_INODE) {
	PyTuple_SET_ITEM(t, 1, PyInt_FromLong(f->inode));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 1, Py_None);
    }
    if (f->valid & APR_FINFO_DEV) {
	PyTuple_SET_ITEM(t, 2, PyInt_FromLong(f->device));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 2, Py_None);
    }
    if (f->valid & APR_FINFO_NLINK) {
	PyTuple_SET_ITEM(t, 3, PyInt_FromLong(f->nlink));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 3, Py_None);
    }
    if (f->valid & APR_FINFO_USER) {
	PyTuple_SET_ITEM(t, 4, PyInt_FromLong(f->user));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 4, Py_None);
    }
    if (f->valid & APR_FINFO_GROUP) {
	PyTuple_SET_ITEM(t, 5, PyInt_FromLong(f->group));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 5, Py_None);
    }
    if (f->valid & APR_FINFO_SIZE) {
	PyTuple_SET_ITEM(t, 6, PyInt_FromLong(f->size));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 6, Py_None);
    }
    if (f->valid & APR_FINFO_ATIME) {
	PyTuple_SET_ITEM(t, 7, PyInt_FromLong(f->atime/1000000));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 7, Py_None);
    }
    if (f->valid & APR_FINFO_MTIME) {
	PyTuple_SET_ITEM(t, 8, PyInt_FromLong(f->mtime/1000000));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 8, Py_None);
    }
    if (f->valid & APR_FINFO_CTIME) {
	PyTuple_SET_ITEM(t, 9, PyInt_FromLong(f->ctime/10000000));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 9, Py_None);
    }
    if (f->fname) {
	PyTuple_SET_ITEM(t, 10, PyString_FromString(f->fname));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 10, Py_None);
    }
    if (f->valid & APR_FINFO_NAME) {
	PyTuple_SET_ITEM(t, 11, PyString_FromString(f->name));
    } else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 11, Py_None);
    }
    /* it'd be nice to also return the file dscriptor, 
       f->filehand->filedes, but it's platform dependent,
       so may be later... */

    return t;
}

/**
 ** tuple_from_apr_uri
 **
 *  makes a tuple from uri_components
 *
 */

PyObject *tuple_from_apr_uri(apr_uri_t *u)
{
    PyObject *t;

    t = PyTuple_New(9);

    if (u->scheme) {
	PyTuple_SET_ITEM(t, 0, PyString_FromString(u->scheme));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 0, Py_None);
    }
    if (u->hostinfo) {
	PyTuple_SET_ITEM(t, 1, PyString_FromString(u->hostinfo));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 1, Py_None);
    }
    if (u->user) {
	PyTuple_SET_ITEM(t, 2, PyString_FromString(u->user));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 2, Py_None);
    }
    if (u->password) {
	PyTuple_SET_ITEM(t, 3, PyString_FromString(u->password));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 3, Py_None);
    }
    if (u->hostname) {
	PyTuple_SET_ITEM(t, 4, PyString_FromString(u->hostname));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 4, Py_None);
    }
    if (u->port_str) {
	PyTuple_SET_ITEM(t, 5, PyInt_FromLong(u->port));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 5, Py_None);
    }
    if (u->path) {
	PyTuple_SET_ITEM(t, 6, PyString_FromString(u->path));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 6, Py_None);
    }
    if (u->query) {
	PyTuple_SET_ITEM(t, 7, PyString_FromString(u->query));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 7, Py_None);
    }
    if (u->fragment) {
	PyTuple_SET_ITEM(t, 8, PyString_FromString(u->fragment));
    }
    else {
	Py_INCREF(Py_None);
	PyTuple_SET_ITEM(t, 8, Py_None);
    }
    // XXX hostent, is_initialized, dns_*

    return t;
}


/**
 ** python_decref
 ** 
 *   This helper function is used with apr_pool_cleanup_register to destroy
 *   python objects when a certain pool is destroyed.
 */

apr_status_t python_decref(void *object)
{
    Py_XDECREF((PyObject *) object);
    return 0;
}

/**
 ** find_module
 ** 
 *   Find an Apache module by name, used by get_addhandler_extensions
 */

module *find_module(char *name)
{
    int n; 
    for (n = 0; ap_loaded_modules[n]; ++n) {

	if (strcmp(name, ap_loaded_modules[n]->name) == 0)
	    return ap_loaded_modules[n];

    }
    return NULL;
}
 
/**
 ** get_addhandler_extensions
 ** 
 *   Get extensions specified for AddHandler, if any. To do this we
 *   retrieve mod_mime's config. This is used by the publisher to strip
 *   file extentions from modules in the most meaningful way.
 *
 *   XXX This function is a hack and will stop working if mod_mime people
 *   decide to change their code. A better way to implement this would
 *   be via the config tree, but it doesn't seem to be quite there just
 *   yet, because it doesn't have .htaccess directives.
 */

char * get_addhandler_extensions(request_rec *req)
{

    /* these typedefs are copied from mod_mime.c */

    typedef struct {
	apr_hash_t  *extension_mappings;  
	apr_array_header_t *remove_mappings; 
	char *default_language;
	int multimatch;
    } mime_dir_config;

    typedef struct extension_info {
	char *forced_type;                /* Additional AddTyped stuff */
	char *encoding_type;              /* Added with AddEncoding... */
	char *language_type;              /* Added with AddLanguage... */
	char *handler;                    /* Added with AddHandler... */
	char *charset_type;               /* Added with AddCharset... */
	char *input_filters;              /* Added with AddInputFilter... */
	char *output_filters;             /* Added with AddOutputFilter... */
    } extension_info;

    mime_dir_config *mconf;

    apr_hash_index_t *hi;
    void *val;
    void *key;
    extension_info *ei;
    char *result = NULL;

    module *mod_mime = find_module("mod_mime.c");
    mconf = (mime_dir_config *) ap_get_module_config(req->per_dir_config, mod_mime);

    for (hi = apr_hash_first(req->pool, mconf->extension_mappings); hi; hi = apr_hash_next(hi)) {
	apr_hash_this(hi, &key, NULL, &val);
	ei = (extension_info *)val;
	if (ei->handler) 
	    if (strcmp("python-program", ei->handler) == 0) 
		result = apr_pstrcat(req->pool, (char *)key, " ", result, NULL);
    }

    return result;
}

/**
 ** find_memberdef
 ** 
 *   Find a memberdef in a PyMemberDef array
 */
const PyMemberDef *find_memberdef(const PyMemberDef *mlist, const char *name)
{
    PyMemberDef *md;

    for (md = mlist; md->name != NULL; md++)
	if (strcmp(md->name, name) == 0)
	    return md;

    /* this should never happen or the mlist is screwed up */
    return NULL;
}
