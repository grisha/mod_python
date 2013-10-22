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
 * util.c
 *
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
        t = PyTuple_New(0);
    else {
        t = PyTuple_New(ah->nelts);

        s = (char **) ah->elts;
        for (i = 0; i < ah->nelts; i++)
            PyTuple_SetItem(t, i, MpBytesOrUnicode_FromString(s[i]));
    }
    return t;
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

    if ((l->method_list == NULL) || (l->method_list->nelts == 0))
        t = PyTuple_New(0);
    else {
        t = PyTuple_New(l->method_list->nelts);

        methods = (char **)l->method_list->elts;
        for (i = 0; i < l->method_list->nelts; ++i)
            PyTuple_SetItem(t, i, MpBytesOrUnicode_FromString(methods[i]));
    }
    return t;
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

    t = PyTuple_New(13);

    /* this should have been first, but was added later */
    PyTuple_SET_ITEM(t, 12, PyLong_FromLong(f->filetype));

    if (f->valid & APR_FINFO_PROT) {
        PyTuple_SET_ITEM(t, 0, PyLong_FromLong(f->protection));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 0, Py_None);
    }
    if (f->valid & APR_FINFO_INODE) {
        PyTuple_SET_ITEM(t, 1, PyLong_FromLong(f->inode));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 1, Py_None);
    }
    if (f->valid & APR_FINFO_DEV) {
        PyTuple_SET_ITEM(t, 2, PyLong_FromLong(f->device));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 2, Py_None);
    }
    if (f->valid & APR_FINFO_NLINK) {
        PyTuple_SET_ITEM(t, 3, PyLong_FromLong(f->nlink));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 3, Py_None);
    }
    if (f->valid & APR_FINFO_USER) {
        PyTuple_SET_ITEM(t, 4, PyLong_FromLong(f->user));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 4, Py_None);
    }
    if (f->valid & APR_FINFO_GROUP) {
        PyTuple_SET_ITEM(t, 5, PyLong_FromLong(f->group));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 5, Py_None);
    }
    if (f->valid & APR_FINFO_SIZE) {
        PyTuple_SET_ITEM(t, 6, PyLong_FromLong(f->size));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 6, Py_None);
    }
    if (f->valid & APR_FINFO_ATIME) {
        PyTuple_SET_ITEM(t, 7, PyLong_FromLong(f->atime*0.000001));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 7, Py_None);
    }
    if (f->valid & APR_FINFO_MTIME) {
        PyTuple_SET_ITEM(t, 8, PyLong_FromLong(f->mtime*0.000001));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 8, Py_None);
    }
    if (f->valid & APR_FINFO_CTIME) {
        PyTuple_SET_ITEM(t, 9, PyLong_FromLong(f->ctime*0.000001));
    } else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 9, Py_None);
    }
    if (f->fname) {
        PyTuple_SET_ITEM(t, 10, MpBytesOrUnicode_FromString(f->fname));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 10, Py_None);
    }
    if (f->valid & APR_FINFO_NAME) {
        PyTuple_SET_ITEM(t, 11, MpBytesOrUnicode_FromString(f->name));
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
        PyTuple_SET_ITEM(t, 0, MpBytesOrUnicode_FromString(u->scheme));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 0, Py_None);
    }
    if (u->hostinfo) {
        PyTuple_SET_ITEM(t, 1, MpBytesOrUnicode_FromString(u->hostinfo));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 1, Py_None);
    }
    if (u->user) {
        PyTuple_SET_ITEM(t, 2, MpBytesOrUnicode_FromString(u->user));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 2, Py_None);
    }
    if (u->password) {
        PyTuple_SET_ITEM(t, 3, MpBytesOrUnicode_FromString(u->password));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 3, Py_None);
    }
    if (u->hostname) {
        PyTuple_SET_ITEM(t, 4, MpBytesOrUnicode_FromString(u->hostname));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 4, Py_None);
    }
    if (u->port_str) {
        PyTuple_SET_ITEM(t, 5, PyLong_FromLong(u->port));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 5, Py_None);
    }
    if (u->path) {
        PyTuple_SET_ITEM(t, 6, MpBytesOrUnicode_FromString(u->path));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 6, Py_None);
    }
    if (u->query) {
        PyTuple_SET_ITEM(t, 7, MpBytesOrUnicode_FromString(u->query));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 7, Py_None);
    }
    if (u->fragment) {
        PyTuple_SET_ITEM(t, 8, MpBytesOrUnicode_FromString(u->fragment));
    }
    else {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 8, Py_None);
    }
    /* XXX hostent, is_initialized, dns_* */

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

static module *find_module(char *name)
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

    if (mconf->extension_mappings) {

        for (hi = apr_hash_first(req->pool, mconf->extension_mappings); hi; hi = apr_hash_next(hi)) {
            apr_hash_this(hi, (const void **)&key, NULL, &val);
            ei = (extension_info *)val;
            if (ei->handler)
                if (strcmp("mod_python", ei->handler) == 0 ||
                    strcmp("python-program", ei->handler) == 0)
                    result = apr_pstrcat(req->pool, (char *)key, " ", result, NULL);
        }
    }

    return result;
}

/**
 ** find_memberdef
 **
 *   Find a memberdef in a PyMemberDef array
 */

PyMemberDef *find_memberdef(const PyMemberDef *mlist, const char *name)
{
    const PyMemberDef *md;

    for (md = mlist; md->name != NULL; md++)
        if (name[0] == md->name[0] &&
            strcmp(md->name+1, name+1) == 0)
            return (PyMemberDef *)md;

    /* this should never happen or the mlist is screwed up */
    return NULL;
}

/**
 ** cfgtree_walk
 **
 *  walks ap_directive_t tree returning a list of
 *  tuples and lists
 */

PyObject *cfgtree_walk(ap_directive_t *dir)
{

    PyObject *list = PyList_New(0);
    if (!list)
        return PyErr_NoMemory();

    while (dir) {

        PyObject *t = Py_BuildValue("(s, s)", dir->directive, dir->args);
        if (!t)
            return PyErr_NoMemory();

        PyList_Append(list, t);

        Py_DECREF(t);

        if (dir->first_child) {

            PyObject *child = cfgtree_walk(dir->first_child);
            if (!child)
                return PyErr_NoMemory();

            PyList_Append(list, child);

            Py_DECREF(child);

        }

        dir = dir->next;
    }

    return list;
}

/**
 ** makeipaddr
 **
 *  utility func to make an ip address
 */

static PyObject *makeipaddr(struct apr_sockaddr_t *addr)
{
    char *str = NULL;
    apr_status_t rc;
    PyObject *ret = NULL;

    rc = apr_sockaddr_ip_get(&str, addr);
    if (rc==APR_SUCCESS) {
        ret = MpBytesOrUnicode_FromString(str);
    }
    else {
        PyErr_SetString(PyExc_SystemError,"apr_sockaddr_ip_get failure");
    }
    return ret;
}

/**
 ** makesockaddr
 **
 *  utility func to make a socket address
 */

PyObject *makesockaddr(struct apr_sockaddr_t *addr)
{
    PyObject *addrobj = makeipaddr(addr);
    PyObject *ret = NULL;

    if (addrobj) {
        apr_port_t port;
        port = addr->port;
        ret = Py_BuildValue("Oi", addrobj, port );
        Py_DECREF(addrobj);
    }
    return ret;
}
