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
 * mod_python.c 
 *
 * $Id: mod_python.c,v 1.99 2003/08/21 18:25:12 grisha Exp $
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

#include "mod_python.h"

/* List of available Python obCallBacks/Interpreters
 * (In a Python dictionary) */
static PyObject * interpreters = NULL;

apr_pool_t *child_init_pool = NULL;

/**
 ** make_interpreter
 **
 *      Creates a new Python interpeter.
 */

static PyInterpreterState *make_interpreter(const char *name, server_rec *srv)
{
    PyThreadState *tstate;
    
    /* create a new interpeter */
    tstate = Py_NewInterpreter();

    if (! tstate) {
        /* couldn't create an interpreter, this is bad */
        ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, srv,
                     "make_interpreter: Py_NewInterpreter() returned NULL. No more memory?");
        return NULL;
    }

    /* release the thread state */
    PyThreadState_Swap(NULL); 

    /* Strictly speaking we don't need that tstate created
     * by Py_NewInterpreter but is preferable to waste it than re-write
     * a cousin to Py_NewInterpreter 
     * XXX (maybe we can destroy it?)
     */
    return tstate->interp;
}

/**
 ** make_obcallback
 **
 *      This function instantiates an obCallBack object. 
 *      NOTE: The obCallBack object is instantiated by Python
 *      code. This C module calls into Python code which returns 
 *      the reference to obCallBack.
 */

static PyObject * make_obcallback(server_rec *s)
{

    PyObject *m;
    PyObject *obCallBack = NULL;

    /* This makes _apache appear imported, and subsequent
     * >>> import _apache 
     * will not give an error.
     */
    /* Py_InitModule("_apache", _apache_module_methods); */
    init_apache();

    /* Now execute the equivalent of
     * >>> import <module>
     * >>> <initstring>
     * in the __main__ module to start up Python.
     */

    if (! ((m = PyImport_ImportModule(MODULENAME)))) {
        ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, s,
                     "make_obcallback: could not import %s.\n", MODULENAME);
        PyErr_Print();
    }
    
    if (m && ! ((obCallBack = PyObject_CallMethod(m, INITFUNC, NULL)))) {
        ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, s,
                     "make_obcallback: could not call %s.\n", INITFUNC);
        PyErr_Print();
    }
    
    return obCallBack;
}

/**
 ** get_interpreter
 **
 *      Get interpreter given its name. 
 *      NOTE: This function will acquire lock
 */

static interpreterdata *get_interpreter(const char *name, server_rec *srv)
{
    PyObject *p;
    PyThreadState *tstate;
    interpreterdata *idata = NULL;
    
    if (! name)
        name = MAIN_INTERPRETER;

#ifdef WITH_THREAD
    PyEval_AcquireLock();
#endif

    if (!interpreters)
        return NULL;

    p = PyDict_GetItemString(interpreters, (char *)name);
    if (!p)
    {
        PyInterpreterState *istate = make_interpreter(name, srv);
        if (istate) {
            idata = (interpreterdata *)malloc(sizeof(interpreterdata));
            idata->istate = istate;
            /* obcallback will be created on first use */
            idata->obcallback = NULL; 
            p = PyCObject_FromVoidPtr((void *) idata, NULL);
            PyDict_SetItemString(interpreters, (char *)name, p);
        }
    }
    else {
        idata = (interpreterdata *)PyCObject_AsVoidPtr(p);
    }

#ifdef WITH_THREAD
    PyEval_ReleaseLock();
#endif

    if (! idata) {
        ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, srv,
                     "get_interpreter: cannot get interpreter data (no more memory?)");
        return NULL;
    }

    /* create thread state and acquire lock */
    tstate = PyThreadState_New(idata->istate);
#ifdef WITH_THREAD
    PyEval_AcquireThread(tstate);
#else
    PyThreadState_Swap(tstate);
#endif

    if (!idata->obcallback) {

        idata->obcallback = make_obcallback(srv);

        if (!idata->obcallback) 
        {
#ifdef WITH_THREAD
            PyEval_ReleaseThread(tstate);
#endif
            PyThreadState_Delete(tstate);
            return NULL;
        }
    }

    return idata;
}


/**
 ** release_interpreter
 **
 *      Release interpreter.
 *      NOTE: This function will release lock
 */

static void release_interpreter(void) 
{
    PyThreadState *tstate = PyThreadState_Get();
#ifdef WITH_THREAD
    PyEval_ReleaseThread(tstate);
#endif
    PyThreadState_Delete(tstate);
}

/**
 ** pytho_cleanup
 **
 *     This function gets called for clean ups registered
 *     with register_cleanup(). Clean ups registered via
 *     PythonCleanupHandler run in python_cleanup_handler()
 *     below.
 */

apr_status_t python_cleanup(void *data)
{
    interpreterdata *idata;

    cleanup_info *ci = (cleanup_info *)data;

    /* get/create interpreter */
    if (ci->request_rec)
        idata = get_interpreter(ci->interpreter, ci->request_rec->server);
    else
        idata = get_interpreter(ci->interpreter, ci->server_rec);

    if (!idata) {
        Py_DECREF(ci->handler);
        Py_XDECREF(ci->data);
        free(ci);
        return APR_SUCCESS; /* this is ignored anyway */
    }
    
    /* 
     * Call the cleanup function.
     */
    if (! PyObject_CallFunction(ci->handler, "O", ci->data)) {
        PyObject *ptype;
        PyObject *pvalue;
        PyObject *ptb;
        PyObject *handler;
        PyObject *stype;
        PyObject *svalue;

        PyErr_Fetch(&ptype, &pvalue, &ptb);
        handler = PyObject_Str(ci->handler);
        stype = PyObject_Str(ptype);
        svalue = PyObject_Str(pvalue);

        Py_XDECREF(ptype);
        Py_XDECREF(pvalue);
        Py_XDECREF(ptb);

        if (ci->request_rec) {
            ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, 
                          ci->request_rec,
                          "python_cleanup: Error calling cleanup object %s", 
                          PyString_AsString(handler));
            ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0,
                          ci->request_rec,
                          "    %s: %s", PyString_AsString(stype), 
                          PyString_AsString(svalue));
        }
        else {
            ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0,
                         ci->server_rec,
                         "python_cleanup: Error calling cleanup object %s", 
                         PyString_AsString(handler));
            ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0,
                         ci->server_rec,
                         "    %s: %s", PyString_AsString(stype), 
                         PyString_AsString(svalue));
        }

        Py_DECREF(handler);
        Py_DECREF(stype);
        Py_DECREF(svalue);
    }

    release_interpreter();

    Py_DECREF(ci->handler);
    Py_DECREF(ci->data);
    free(ci);
    return APR_SUCCESS;
}

static apr_status_t init_mutexes(server_rec *s, apr_pool_t *p, py_global_config *glb)
{
    int max_threads;
    int max_procs;
    int max_clients;
    int locks;
    int n;

    /* figre out maximum possible concurrent connections */
    ap_mpm_query(AP_MPMQ_MAX_THREADS, &max_threads);
    ap_mpm_query(AP_MPMQ_MAX_DAEMONS, &max_procs);
    max_clients = (((!max_threads) ? 1 : max_threads) *
		   ((!max_procs) ? 1 : max_procs));
    locks = max_clients; /* XXX this is completely out of the blue */

    ap_log_error(APLOG_MARK, APLOG_NOTICE, 0, s,
		 "mod_python: Creating %d session mutexes based "
		 "on %d max processes and %d max threads.", 
		 locks, max_procs, max_threads);

    glb->g_locks = (apr_global_mutex_t **) 
	apr_palloc(p, locks * sizeof(apr_global_mutex_t *));
    glb->nlocks = locks;
    glb->parent_pid = getpid();

    for (n=0; n<locks; n++) {
	apr_status_t rc;
	apr_global_mutex_t **mutex = glb->g_locks;

#if !defined(OS2) && !defined(WIN32) && !defined(BEOS) && !defined(NETWARE)
	char fname[255];

	snprintf(fname, 255, "/tmp/mpmtx%d%d", glb->parent_pid, n);
#else
	char *fname = NULL;
#endif
	rc = apr_global_mutex_create(&mutex[n], fname, APR_LOCK_DEFAULT, 
				     p);
	if (rc != APR_SUCCESS) {
	    ap_log_error(APLOG_MARK, APLOG_ERR, rc, s,
			 "mod_python: Failed to create global mutex %d of %d (%s).",
			 n, locks, (!fname) ? "<null>" : fname);
	    if (n > 0) {
		/* we were able to crate at least one, so lets just print a 
		   warning/hint and proceed
		*/
		ap_log_error(APLOG_MARK, APLOG_ERR, 0, s,
			     "mod_python: We can probably continue, but with diminished ability "
			     "to process session locks.");
		ap_log_error(APLOG_MARK, APLOG_ERR, 0, s,
			     "mod_python: Hint: On Linux, the problem may be the number of "
			     "available semaphores, check 'sysctl kernel.sem'");
		glb->nlocks = n;
		break;
		
	    }
	    else {
		return rc;
	    }
	}
	else {
#if !defined(OS2) && !defined(WIN32) && !defined(BEOS) && !defined(NETWARE)
	    chown(fname, unixd_config.user_id, -1);
#endif
	}
    }
    return APR_SUCCESS;
}

static apr_status_t reinit_mutexes(server_rec *s, apr_pool_t *p, py_global_config *glb)
{
    int n;

    for (n=0; n< glb->nlocks; n++) {
	apr_status_t rc;
	apr_global_mutex_t **mutex = glb->g_locks;

#if !defined(OS2) && !defined(WIN32) && !defined(BEOS) && !defined(NETWARE)
        char fname[255];
        snprintf(fname, 255, "/tmp/mpmtx%d%d", glb->parent_pid, n);
#else
        char *fname = NULL;
#endif
	rc = apr_global_mutex_child_init(&mutex[n], fname, p);

	if (rc != APR_SUCCESS) {
	    ap_log_error(APLOG_MARK, APLOG_STARTUP, rc, s,
			 "mod_python: Failed to reinit global mutex %s.",
			 (!fname) ? "<null>" : fname);
	    return rc;
	}
    }
    return APR_SUCCESS;
}

/**
 ** python_create_global_config
 **
 *      This creates the part of config that survives
 *  server restarts
 *
 */

static py_global_config *python_create_global_config(server_rec *s)
{
    apr_pool_t *pool = s->process->pool;
    py_global_config *glb;

    /* do we already have it in s->process->pool? */
    apr_pool_userdata_get((void **)&glb, MP_CONFIG_KEY, pool);

    if (glb) {
        return glb; 
    }

    /* otherwise, create it */

    glb = (py_global_config *)apr_palloc(pool, sizeof(*glb));

    apr_pool_userdata_set(glb, MP_CONFIG_KEY,
                          apr_pool_cleanup_null,
                          pool);

    return glb;
}

/**
 ** python_init()
 **
 *      Called by Apache at mod_python initialization time.
 */

static int python_init(apr_pool_t *p, apr_pool_t *ptemp, 
                       apr_pool_t *plog, server_rec *s)
{
    char buff[255];
    void *data;
    py_global_config *glb;
    const char *userdata_key = "python_init";
    apr_status_t rc;

    apr_pool_userdata_get(&data, userdata_key, s->process->pool);
    if (!data) {
        apr_pool_userdata_set((const void *)1, userdata_key,
                              apr_pool_cleanup_null, s->process->pool);
        return OK;
    }

    /* mod_python version */
    ap_add_version_component(p, VERSION_COMPONENT);
    
    /* Python version */
    sprintf(buff, "Python/%.200s", strtok((char *)Py_GetVersion(), " "));
    ap_add_version_component(p, buff);

    /* global config */
    glb = python_create_global_config(s);
    if ((rc = init_mutexes(s, p, glb)) != APR_SUCCESS) {
	return rc;
    }

    /* initialize global Python interpreter if necessary */
    if (! Py_IsInitialized()) 
    {

        /* initialze the interpreter */
        Py_Initialize();

#ifdef WITH_THREAD
        /* create and acquire the interpreter lock */
        PyEval_InitThreads();
#endif
        /* Release the thread state because we will never use 
         * the main interpreter, only sub interpreters created later. */
        PyThreadState_Swap(NULL); 

        /* create the obCallBack dictionary */
        interpreters = PyDict_New();
        if (! interpreters) {
            ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, s,
                         "python_init: PyDict_New() failed! No more memory?");
            exit(1);
        }
        
#ifdef WITH_THREAD
        /* release the lock; now other threads can run */
        PyEval_ReleaseLock();
#endif

    }
    return OK;
}

/**
 ** python_create_config
 **
 *      Called by create_dir_config and create_srv_config
 */

static py_config *python_create_config(apr_pool_t *p)
{
    py_config *conf = 
        (py_config *) apr_pcalloc(p, sizeof(py_config));

    conf->authoritative = 1;
    conf->options = apr_table_make(p, 4);
    conf->directives = apr_table_make(p, 4);
    conf->hlists = apr_hash_make(p);
    conf->in_filters = apr_hash_make(p);
    conf->out_filters = apr_hash_make(p);

    return conf;
}


/**
 ** python_create_dir_config
 **
 *      Allocate memory and initialize the strucure that will
 *      hold configuration parametes.
 *
 *      This function is called on every hit it seems.
 */

static void *python_create_dir_config(apr_pool_t *p, char *dir)
{

    py_config *conf = python_create_config(p);

    /* make sure directory ends with a slash */
    if (dir && (dir[strlen(dir) - 1] != SLASH))
        conf->config_dir = apr_pstrcat(p, dir, SLASH_S, NULL);
    else
        conf->config_dir = apr_pstrdup(p, dir);

    return conf;
}

/**
 ** python_create_srv_config
 **
 *      Allocate memory and initialize the strucure that will
 *      hold configuration parametes.
 */

static void *python_create_srv_config(apr_pool_t *p, server_rec *srv)
{

    py_config *conf = python_create_config(p);

    return conf;
}

/**
 ** python_merge_dir_config
 **
 */

static void *python_merge_config(apr_pool_t *p, void *current_conf, 
                                 void *new_conf)
{

    py_config *merged_conf = 
        (py_config *) apr_pcalloc(p, sizeof(py_config));
    py_config *cc = (py_config *) current_conf;
    py_config *nc = (py_config *) new_conf;

    apr_hash_index_t *hi;
    char *key;
    apr_ssize_t klen;
    hl_entry *hle;

    /* we basically allow the local configuration to override global,
     * by first copying current values and then new values on top
     */

    /** create **/
    merged_conf->directives = apr_table_make(p, 4);
    merged_conf->options = apr_table_make(p, 4);
    merged_conf->hlists = apr_hash_make(p);
    merged_conf->in_filters = apr_hash_make(p);
    merged_conf->out_filters = apr_hash_make(p);

    /** copy current **/

    merged_conf->authoritative = cc->authoritative;
    merged_conf->config_dir = apr_pstrdup(p, cc->config_dir);
    apr_table_overlap(merged_conf->directives, cc->directives,
                      APR_OVERLAP_TABLES_SET);
    apr_table_overlap(merged_conf->options, cc->options,
                      APR_OVERLAP_TABLES_SET);

    for (hi = apr_hash_first(p, cc->hlists); hi; hi=apr_hash_next(hi)) {
        apr_hash_this(hi, (const void **)&key, &klen, (void **)&hle);
        apr_hash_set(merged_conf->hlists, key, klen, (void *)hle);
    }

    for (hi = apr_hash_first(p, cc->in_filters); hi; hi=apr_hash_next(hi)) {
        apr_hash_this(hi, (const void **)&key, &klen, (void **)&hle);
        apr_hash_set(merged_conf->in_filters, key, klen, (void *)hle);
    }

    for (hi = apr_hash_first(p, cc->out_filters); hi; hi=apr_hash_next(hi)) {
        apr_hash_this(hi, (const void **)&key, &klen, (void **)&hle);
        apr_hash_set(merged_conf->out_filters, key, klen, (void *)hle);
    }

    /** copy new **/

    if (nc->authoritative != merged_conf->authoritative)
        merged_conf->authoritative = nc->authoritative;
    if (nc->config_dir)
        merged_conf->config_dir = apr_pstrdup(p, nc->config_dir);

    apr_table_overlap(merged_conf->directives, nc->directives,
                      APR_OVERLAP_TABLES_SET);
    apr_table_overlap(merged_conf->options, nc->options,
                      APR_OVERLAP_TABLES_SET);

    for (hi = apr_hash_first(p, nc->hlists); hi; hi=apr_hash_next(hi)) {
        apr_hash_this(hi, (const void**)&key, &klen, (void **)&hle);
        apr_hash_set(merged_conf->hlists, key, klen, (void *)hle);
    }

    for (hi = apr_hash_first(p, nc->in_filters); hi; hi=apr_hash_next(hi)) {
        apr_hash_this(hi, (const void**)&key, &klen, (void **)&hle);
        apr_hash_set(merged_conf->in_filters, key, klen, (void *)hle);
    }

    for (hi = apr_hash_first(p, nc->out_filters); hi; hi=apr_hash_next(hi)) {
        apr_hash_this(hi, (const void**)&key, &klen, (void **)&hle);
        apr_hash_set(merged_conf->out_filters, key, klen, (void *)hle);
    }

    return (void *) merged_conf;
}

/**
 ** python_directive
 **
 *  Called by non-handler directives
 *
 */

static const char *python_directive(cmd_parms *cmd, void * mconfig, 
                                    char *key, const char *val)
{
    py_config *conf;
   
    conf = (py_config *) mconfig;
    apr_table_set(conf->directives, key, val);
    
    return NULL;
}

static void python_directive_hl_add(apr_pool_t *p,
                                    apr_hash_t *hlists, 
                                    const char *phase, const char *handler, 
                                    const char *directory, const int silent)
{
    hl_entry *head;
    char *h;

    head = (hl_entry *)apr_hash_get(hlists, phase, APR_HASH_KEY_STRING);

    /* it's possible that handler is multiple handlers separated
       by white space */

    while (*(h = ap_getword_white(p, &handler)) != '\0') {
        if (!head) {
            head = hlist_new(p, h, directory, silent);
            apr_hash_set(hlists, phase, APR_HASH_KEY_STRING, head);
        }
        else {
            hlist_append(p, head, h, directory, silent);
        }
    }
}

/**
 ** python_directive_handler
 **
 *  Called by Python*Handler directives.
 *
 *  When used within the same directory, this will have a
 *  cumulative, rather than overriding effect - i.e. values
 *  from same directives specified multiple times will be appended.
 *
 */

static const char *python_directive_handler(cmd_parms *cmd, py_config* conf, 
                                            char *key, const char *val, int silent)
{
    /* a handler may be restricted to certain file type by 
     * extention using the "| .ext1 .ext2" syntax. When this
     * is the case, we will end up with a directive concatenated
     * with the extension, one per, e.g.
     * "PythonHandler foo | .ext1 .ext2" will result in
     * PythonHandler.ext1 foo
     * PythonHandler.ext2 foo
     */

    const char *exts = val;
    val = ap_getword(cmd->pool, &exts, '|');

    if (*exts == '\0') {
        python_directive_hl_add(cmd->pool, conf->hlists, key, val,
                                conf->config_dir, silent);
    }
    else {

        char *ext;

        /* skip blanks */
        while (apr_isspace(*exts)) exts++;
        
        /* repeat for every extension */
        while (*(ext = ap_getword_white(cmd->pool, &exts)) != '\0') {
            char *s;

            /* append extention to the directive name */
            s = apr_pstrcat(cmd->pool, key, ext, NULL);

            python_directive_hl_add(cmd->pool, conf->hlists, s, val,
                                    conf->config_dir, silent);
        }
    }

    return NULL;
}

/**
 ** python_directive_flag
 **
 *  Called for FLAG directives.
 *
 */

static const char *python_directive_flag(void * mconfig, 
                                         char *key, int val)
{
    py_config *conf;

    conf = (py_config *) mconfig;

    if (val) {
        apr_table_set(conf->directives, key, "1");
    }
    else {
        apr_table_unset(conf->directives, key);
    }

    return NULL;
}

static apr_status_t python_cleanup_handler(void *data);

/**
 ** get_request_object
 **
 *      This creates or retrieves a previously created request object.
 *      The pointer to request object is stored in req->request_config.
 */

static requestobject *get_request_object(request_rec *req, const char *interp_name, char *phase)
{
    py_req_config *req_config;
    requestobject *request_obj = NULL;

    /* see if there is a request object already */
    req_config = (py_req_config *) ap_get_module_config(req->request_config,
                                                        &python_module);

    if (req_config) {
        request_obj = req_config->request_obj;
    }
    else {
/*         if ((req->path_info) &&  */
/*             (req->path_info[strlen(req->path_info) - 1] == SLASH)) */
/*         { */
/*             int i; */
/*             i = strlen(req->path_info); */
/*             /\* take out the slash *\/ */
/*             req->path_info[i - 1] = 0; */

/*             Py_BEGIN_ALLOW_THREADS */
/*             ap_add_cgi_vars(req); */
/*             Py_END_ALLOW_THREADS */

/*             request_obj = (requestobject *)MpRequest_FromRequest(req); */
/*             if (!request_obj) return NULL; */

/*             /\* put the slash back in *\/ */
/*             req->path_info[i - 1] = SLASH;  */
/*             req->path_info[i] = 0; */

/*             /\* and also make PATH_INFO == req->subprocess_env *\/ */
/*             apr_table_set(req->subprocess_env, "PATH_INFO", req->path_info); */
/*         }  */
/*         else  */
/*         {  */
            Py_BEGIN_ALLOW_THREADS
            ap_add_cgi_vars(req);
            Py_END_ALLOW_THREADS

            request_obj = (requestobject *)MpRequest_FromRequest(req);
            if (!request_obj) return NULL;
/*         } */

        /* store the pointer to this object in request_config */
        req_config = apr_pcalloc(req->pool, sizeof(py_req_config));
        req_config->request_obj = request_obj;
        req_config->dynhls = apr_hash_make(req->pool);
        ap_set_module_config(req->request_config, &python_module, req_config);

        /* register the clean up directive handler */
        apr_pool_cleanup_register(req->pool, (void *)req, 
                                  python_cleanup_handler, 
                                  apr_pool_cleanup_null);
    }
    /* make a note of which subinterpreter we're running under */
    if (interp_name)
        request_obj->interpreter = apr_pstrdup(req->pool, interp_name);
    else
        request_obj->interpreter = apr_pstrdup(req->pool, MAIN_INTERPRETER);

    /* make a note of which phase we are in right now */
    Py_XDECREF(request_obj->phase);
    if (phase)
        request_obj->phase = PyString_FromString(phase);
    else
        request_obj->phase = PyString_FromString("");

    return request_obj;
}

/**
 ** select_interpreter_name
 **
 *      (internal)
 *      figure out the name of the interpreter we should be using
 *      If this is for a handler, then hle is required. If this is
 *      for a filter, then fname and is_input are required. If con 
 *      is specified, then its a connection handler.
 */

static const char *select_interp_name(request_rec *req, conn_rec *con, py_config *conf, 
                                      hl_entry *hle, const char *fname, int is_input)
{
    const char *s;

    if ((s = apr_table_get(conf->directives, "PythonInterpreter"))) {
        /* forced by configuration */
        return s;
    }
    else {
        if ((s = apr_table_get(conf->directives, "PythonInterpPerDirectory"))) {
            
            /* base interpreter on directory where the file is found */
            if (req && ap_is_directory(req->pool, req->filename))
                return ap_make_dirstr_parent(req->pool, 
                                             apr_pstrcat(req->pool, req->filename, 
                                                         SLASH_S, NULL ));
            else {
                if (req && req->filename)
                    return ap_make_dirstr_parent(req->pool, req->filename);
                else
                    /* 
                     * In early phases of the request, req->filename is not known,
                     * so this would have to run in the global interpreter.
                     */
                    return NULL;
            }
        }
        else if (apr_table_get(conf->directives, "PythonInterpPerDirective")) {

            /* 
             * base interpreter name on directory where the handler directive
             * was last found. If it was in http.conf, then we will use the 
             * global interpreter.
             */
            
            py_handler *fh;

            if (fname) {
                if (is_input) {
                    fh = (py_handler *)apr_hash_get(conf->in_filters, fname,
                                                           APR_HASH_KEY_STRING);
                }
                else {
                    fh = (py_handler *)apr_hash_get(conf->out_filters, fname,
                                                           APR_HASH_KEY_STRING);
                }
                s = fh->dir;
            }
            else {
                s = hle->directory;
            }

            if (s && (s[0] == '\0'))
                return NULL;
            else
                return s;
        }
        else {
            /* - default: per server - */
            if (con)
                return con->base_server->server_hostname;
            else
                return req->server->server_hostname;
        }
    }
}


/**
 ** python_handler
 **
 *      A generic python handler. Most handlers should use this.
 */

static int python_handler(request_rec *req, char *phase)
{

    PyObject *resultobject = NULL;
    interpreterdata *idata;
    requestobject *request_obj;
    py_config * conf;
    int result;
    const char *interp_name = NULL;
    char *ext = NULL;
    hl_entry *hle = NULL;
    hl_entry *dynhle = NULL;

    py_req_config *req_conf;

    /* get configuration */
    conf = (py_config *) ap_get_module_config(req->per_dir_config, 
                                                  &python_module);
    /* get file extension */
    if (req->filename) {        /* filename is null until after transhandler */
        /* get rid of preceeding path */
        if ((ext = (char *)ap_strrchr_c(req->filename, '/')) == NULL)
            ext = req->filename;
        else 
            ++ext;
        /* get extension */
        ap_getword(req->pool, (const char **)&ext, '.');
        if (*ext != '\0')
            ext = apr_pstrcat(req->pool, ".", ext, NULL);
    }

    /* is there an hlist entry, i.e. a handler? */
    /* try with extension */
    if (ext) {
        hle = (hl_entry *)apr_hash_get(conf->hlists, 
                                       apr_pstrcat(req->pool, phase, ext, NULL),
                                       APR_HASH_KEY_STRING);
    }

    /* try without extension if we don't match */
    if (!hle) {
        hle = (hl_entry *)apr_hash_get(conf->hlists, phase, APR_HASH_KEY_STRING);

        /* also blank out ext since we didn't succeed with it. this is tested
           further below */
        ext = NULL;
    }
    
    req_conf = (py_req_config *) ap_get_module_config(req->request_config,
                                                      &python_module);
    if (req_conf) {
        dynhle = (hl_entry *)apr_hash_get(req_conf->dynhls, phase, 
                                          APR_HASH_KEY_STRING);
    }

    if (! (hle || dynhle)) {
        /* nothing to do here */
        return DECLINED;
    }
    
    /* determine interpreter to use */
    interp_name = select_interp_name(req, NULL, conf, hle, NULL, 0);

    /* get/create interpreter */
    idata = get_interpreter(interp_name, req->server);

    if (!idata)
        return HTTP_INTERNAL_SERVER_ERROR;
    
    /* create/acquire request object */
    request_obj = get_request_object(req, interp_name, phase);

    /* remember the extension if any. used by publisher */
    if (ext) 
        request_obj->extension = apr_pstrdup(req->pool, ext);

    /* create a hahdler list object */
    request_obj->hlo = (hlistobject *)MpHList_FromHLEntry(hle);

    /* add dynamically registered handlers, if any */
    if (dynhle) {
        MpHList_Append(request_obj->hlo, dynhle);
    }

    /* 
     * Here is where we call into Python!
     * This is the C equivalent of
     * >>> resultobject = obCallBack.Dispatch(request_object, phase)
     */
    resultobject = PyObject_CallMethod(idata->obcallback, "HandlerDispatch", "O", 
                                       request_obj);
     
    /* release the lock and destroy tstate*/
    release_interpreter();

    if (! resultobject) {
        ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req, 
                      "python_handler: Dispatch() returned nothing.");
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    else {
        /* Attempt to analyze the result as a string indicating which
           result to return */
        if (! PyInt_Check(resultobject)) {
            ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req, 
                          "python_handler: Dispatch() returned non-integer.");
            return HTTP_INTERNAL_SERVER_ERROR;
        }
        else {
            result = PyInt_AsLong(resultobject);

            /* authen handlers need one more thing
             * if authentication failed and this handler is not
             * authoritative, let the others handle it
             */
            if (strcmp(phase, "PythonAuthenHandler") == 0) {
                if (result == HTTP_UNAUTHORIZED)
                {
                    if   (! conf->authoritative)
                        result = DECLINED;
                    else {
                        /*
                         * This will insert a WWW-Authenticate header
                         * to let the browser know that we are using
                         * Basic authentication. This function does check
                         * to make sure that auth is indeed Basic, no
                         * need to do that here.
                         */
                        ap_note_basic_auth_failure(req);
                    }
                }
            }
        }
    } 

    /* When the script sets an error status by using req.status,
     * it can then either provide its own HTML error message or have
     * Apache provide one. To have Apache provide one, you need to send
     * no output and return the error from the handler function. However,
     * if the script is providing HTML, then the return value of the 
     * handler should be OK, else the user will get both the script
     * output and the Apache output.
     */

    /* Another note on status. req->status is used to build req->status_line
     * unless status_line is not NULL. req->status has no effect on how the
     * server will behave. The error behaviour is dictated by the return 
     * value of this handler. When the handler returns anything other than OK,
     * the server will display the error that matches req->status, unless it is
     * 200 (HTTP_OK), in which case it will just show the error matching the return
     * value. If the req->status and the return of the handle do not match,
     * then the server will first show what req->status shows, then it will
     * print "Additionally, X error was recieved", where X is the return code
     * of the handle. If the req->status or return code is a weird number that the 
     * server doesn't know, it will default to 500 Internal Server Error.
     */

    /* clean up */
    Py_XDECREF(resultobject);

    /* return the translated result (or default result) to the Server. */
    return result;

}

/**
 ** python_cleanup_handler
 **
 *    Runs handler registered via PythonCleanupHandler. Clean ups
 *    registered via register_cleanup() run in python_cleanup() above.
 */

static apr_status_t python_cleanup_handler(void *data)
{

    apr_status_t rc;
    py_req_config *req_config;
    request_rec *req = (request_rec *)data;

    rc = python_handler((request_rec *)data, "PythonCleanupHandler");

    req_config = (py_req_config *) ap_get_module_config(req->request_config,
                                                        &python_module);

    if (req_config && req_config->request_obj) {

        interpreterdata *idata;
        requestobject *request_obj = req_config->request_obj;

        /* get interpreter */
        idata = get_interpreter(NULL, req->server);
        if (!idata)
            return APR_SUCCESS; /* this return code is ignored by httpd anyway */

        Py_XDECREF(request_obj);

        /* release interpreter */
        release_interpreter();
    }

    return rc;
}


/**
 ** python_connection
 **
 *    connection handler
 */

static apr_status_t python_connection(conn_rec *con)
{

    PyObject *resultobject = NULL;
    interpreterdata *idata;
    connobject *conn_obj;
    py_config * conf;
    int result;
    const char *interp_name = NULL;
    hl_entry *hle = NULL;

    /* get configuration */
    conf = (py_config *) ap_get_module_config(con->base_server->module_config, 
                                                  &python_module);

    /* is there a handler? */
    hle = (hl_entry *)apr_hash_get(conf->hlists, "PythonConnectionHandler", 
                                   APR_HASH_KEY_STRING);

    if (! hle) {
        /* nothing to do here */
        return DECLINED;
    }
    
    /* determine interpreter to use */
    interp_name = select_interp_name(NULL, con, conf, hle, NULL, 0);

    /* get/create interpreter */
    idata = get_interpreter(interp_name, con->base_server);

    if (!idata)
        return HTTP_INTERNAL_SERVER_ERROR;
    
    /* create connection object */
    conn_obj = (connobject*) MpConn_FromConn(con);

    /* create a hahdler list object */
    conn_obj->hlo = (hlistobject *)MpHList_FromHLEntry(hle);

    /* 
     * Here is where we call into Python!
     * This is the C equivalent of
     * >>> resultobject = obCallBack.Dispatch(request_object, phase)
     */
    resultobject = PyObject_CallMethod(idata->obcallback, "ConnectionDispatch", "O", 
                                       conn_obj);
     
    /* release the lock and destroy tstate*/
    release_interpreter();

    if (! resultobject) {
        ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, con->base_server, 
                     "python_connection: ConnectionDispatch() returned nothing.");
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    else {
        /* Attempt to analyze the result as a string indicating which
           result to return */
        if (! PyInt_Check(resultobject)) {
            ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, con->base_server, 
                         "python_connection: ConnectionDispatch() returned non-integer.");
            return HTTP_INTERNAL_SERVER_ERROR;
        }
        else 
            result = PyInt_AsLong(resultobject);
    } 

    /* clean up */
    Py_XDECREF(resultobject);

    /* return the translated result (or default result) to the Server. */
    return result;
}

/**
 ** python_filter
 **
 *    filter
 */

static apr_status_t python_filter(int is_input, ap_filter_t *f, 
                                  apr_bucket_brigade *bb,
                                  ap_input_mode_t mode,
                                  apr_read_type_e block,
                                  apr_size_t readbytes) {

    PyObject *resultobject = NULL;
    interpreterdata *idata;
    requestobject *request_obj;
    py_config * conf;
    const char * interp_name = NULL;
    request_rec *req;
    filterobject *filter;
    python_filter_ctx *ctx;
    py_handler *fh;

    /* we only allow request level filters so far */
    req = f->r;

    /* create ctx if not there yet */
    if (!f->ctx) {
        ctx = (python_filter_ctx *) apr_pcalloc(req->pool, sizeof(python_filter_ctx));
        f->ctx = (void *)ctx;
    }
    else {
        ctx = (python_filter_ctx *) f->ctx;
    }
        
    /* are we in transparent mode? transparent mode is on after an error,
       so a fitler can spit out an error without causing infinite loop */
    if (ctx->transparent) {
        if (is_input) 
            return ap_get_brigade(f->next, bb, mode, block, readbytes);
        else
            return ap_pass_brigade(f->next, bb);
    }
        
    /* get configuration */
    conf = (py_config *) ap_get_module_config(req->per_dir_config, 
                                                  &python_module);

    /* determine interpreter to use */
    interp_name = select_interp_name(req, NULL, conf, NULL, f->frec->name, is_input);

    /* get/create interpreter */
    idata = get_interpreter(interp_name, req->server);
   
    if (!idata)
        return HTTP_INTERNAL_SERVER_ERROR;

    /* create/acquire request object */
    request_obj = get_request_object(req, interp_name, 
                                     is_input?"PythonInputFilter":"PythonOutputFilter");
    
    /* the name of python function to call */
    if (is_input)
        fh = apr_hash_get(conf->in_filters, f->frec->name, APR_HASH_KEY_STRING);
    else
        fh = apr_hash_get(conf->out_filters, f->frec->name, APR_HASH_KEY_STRING);

    /* create filter */
    filter = (filterobject *)MpFilter_FromFilter(f, bb, is_input, mode, readbytes,
                                                 fh->handler, fh->dir);

    Py_INCREF(request_obj);
    filter->request_obj = request_obj;

    /* 
     * Here is where we call into Python!
     * This is the C equivalent of
     * >>> resultobject = obCallBack.FilterDispatch(filter_object)
     */
    resultobject = PyObject_CallMethod(idata->obcallback, "FilterDispatch", "O", 
                                       filter);

    /* clean up */
    Py_XDECREF(resultobject);

    /* release interpreter */
    release_interpreter();
    
    return filter->rc;
}

/**
 ** python_input_filter
 **
 *    input filter
 */

static apr_status_t python_input_filter(ap_filter_t *f, 
                                        apr_bucket_brigade *bb,
                                        ap_input_mode_t mode,
                                        apr_read_type_e block,
                                        apr_off_t readbytes)
{
    return python_filter(1, f, bb, mode, block, readbytes);
}


/**
 ** python_output_filter
 **
 *    output filter
 */

static apr_status_t python_output_filter(ap_filter_t *f, 
                                         apr_bucket_brigade *bb)
{
    return python_filter(0, f, bb, 0, 0, 0);
}


/**
 ** directive_PythonImport
 **
 *      This function called whenever PythonImport directive
 *      is encountered. Note that this function does not actually
 *      import anything, it just remembers what needs to be imported.
 *      The actual importing is done later
 *      in the ChildInitHandler. This is because this function here
 *      is called before the python_init and before the suid and fork.
 *
 */
static const char *directive_PythonImport(cmd_parms *cmd, void *mconfig, 
                                          const char *module, const char *interp_name) 
{
    py_config *conf = ap_get_module_config(cmd->server->module_config,
                                           &python_module);

    if (!conf->imports)
        conf->imports = hlist_new(cmd->pool, module, interp_name, 0);
    else 
        hlist_append(cmd->pool, conf->imports, module, interp_name, 0);

    return NULL;

}

/**
 ** directive_PythonPath
 **
 *      This function called whenever PythonPath directive
 *      is encountered.
 */
static const char *directive_PythonPath(cmd_parms *cmd, void *mconfig, 
                                        const char *val) {

    const char *rc = python_directive(cmd, mconfig, "PythonPath", val);

    if (!rc) {
        py_config *conf = ap_get_module_config(cmd->server->module_config,
                                               &python_module);
        return python_directive(cmd, conf, "PythonPath", val);
    }
    return rc;
}

/**
 ** directive_PythonInterpreter
 **
 *      This function called whenever PythonInterpreter directive
 *      is encountered.
 */
static const char *directive_PythonInterpreter(cmd_parms *cmd, void *mconfig, 
                                               const char *val) {
    const char *rc = python_directive(cmd, mconfig, "PythonInterpreter", val);

    if (!rc) {
        py_config *conf = ap_get_module_config(cmd->server->module_config,
                                               &python_module);
        return python_directive(cmd, conf, "PythonInterpreter", val);
    }
    return rc;
}

/**
 ** directive_PythonDebug
 **
 *      This function called whenever PythonDebug directive
 *      is encountered.
 */
static const char *directive_PythonDebug(cmd_parms *cmd, void *mconfig,
                                         int val) {
    const char *rc = python_directive_flag(mconfig, "PythonDebug", val);

    if (!rc) {
        py_config *conf = ap_get_module_config(cmd->server->module_config,
                                               &python_module);

        return python_directive_flag(conf, "PythonDebug", val);
    }
    return rc;
}

/**
 ** directive_PythonEnablePdb
 **
 *      This function called whenever PythonEnablePdb directive
 *      is encountered.
 */
static const char *directive_PythonEnablePdb(cmd_parms *cmd, void *mconfig,
                                             int val) {
    const char *rc = python_directive_flag(mconfig, "PythonEnablePdb", val);

    if (!rc) {
        py_config *conf = ap_get_module_config(cmd->server->module_config,
                                               &python_module);
        return python_directive_flag(conf, "PythonEnablePdb", val);
    }
    return rc;
}

/**
 ** directive_PythonInterpPerDirective
 **
 *      This function called whenever PythonInterpPerDirective directive
 *      is encountered.
 */

static const char *directive_PythonInterpPerDirective(cmd_parms *cmd, 
                                                      void *mconfig, int val) {
    const char *rc = python_directive_flag(mconfig, "PythonInterpPerDirective", val);

    if (!rc) {
        py_config *conf = ap_get_module_config(cmd->server->module_config,
                                               &python_module);
        return python_directive_flag(conf, "PythonInterpPerDirective", val);
    }
    return rc;
}

/**
 ** directive_PythonInterpPerDirectory
 **
 *      This function called whenever PythonInterpPerDirectory directive
 *      is encountered.
 */

static const char *directive_PythonInterpPerDirectory(cmd_parms *cmd, 
                                                      void *mconfig, int val) {
    return python_directive_flag(mconfig, "PythonInterpPerDirectory", val);
}

/**
 ** directive_PythonAutoReload
 **
 *      This function called whenever PythonAutoReload directive
 *      is encountered.
 */

static const char *directive_PythonAutoReload(cmd_parms *cmd, 
                                              void *mconfig, int val) {
    const char *rc = python_directive_flag(mconfig, "PythonAutoReload", val);

    if (!rc) {
        py_config *conf = ap_get_module_config(cmd->server->module_config,
                                               &python_module);
        return python_directive_flag(conf, "PythonAutoReload", val);
    }
    return rc;
}

/**
 ** directive_PythonOption
 **
 *       This function is called every time PythonOption directive
 *       is encountered. It sticks the option into a table containing
 *       a list of options. This table is part of the local config structure.
 */

static const char *directive_PythonOption(cmd_parms *cmd, void * mconfig, 
                                          const char *key, const char *val)
{

    py_config *conf;

    conf = (py_config *) mconfig;
    apr_table_set(conf->options, key, val);

    conf = ap_get_module_config(cmd->server->module_config,
                                &python_module);
    apr_table_set(conf->options, key, val);

    return NULL;
}

/**
 ** directive_PythonOptimize
 **
 *      This function called whenever PythonOptimize directive
 *      is encountered.
 */

static const char *directive_PythonOptimize(cmd_parms *cmd, void *mconfig,
                                            int val) {
    if ((val) && (Py_OptimizeFlag != 2))
        Py_OptimizeFlag = 2;
    return NULL;
}

/**
 ** Python*Handler directives
 **
 */

static const char *directive_PythonAccessHandler(cmd_parms *cmd, void *mconfig, 
                                                 const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonAccessHandler", val, NOTSILENT);
}
static const char *directive_PythonAuthenHandler(cmd_parms *cmd, void *mconfig, 
                                                 const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonAuthenHandler", val, NOTSILENT);
}
static const char *directive_PythonAuthzHandler(cmd_parms *cmd, void *mconfig, 
                                                const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonAuthzHandler", val, NOTSILENT);
}
static const char *directive_PythonCleanupHandler(cmd_parms *cmd, void *mconfig, 
                                                  const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonCleanupHandler", val, NOTSILENT);
}
static const char *directive_PythonConnectionHandler(cmd_parms *cmd, void *mconfig, 
                                                     const char *val) {
    py_config *conf = ap_get_module_config(cmd->server->module_config,
                                           &python_module);
    return python_directive_handler(cmd, conf, "PythonConnectionHandler", val, NOTSILENT);
}
static const char *directive_PythonFixupHandler(cmd_parms *cmd, void *mconfig, 
                                                const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonFixupHandler", val, NOTSILENT);
}
static const char *directive_PythonHandler(cmd_parms *cmd, void *mconfig, 
                                           const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonHandler", val, NOTSILENT);
}
static const char *directive_PythonHeaderParserHandler(cmd_parms *cmd, void *mconfig, 
                                                       const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonHeaderParserHandler", val, NOTSILENT);
}
static const char *directive_PythonInitHandler(cmd_parms *cmd, void *mconfig,
                                               const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonInitHandler", val, NOTSILENT);
}
static const char *directive_PythonHandlerModule(cmd_parms *cmd, void *mconfig,
                                                 const char *val) {

    /* 
     * This handler explodes into all other handlers, but their absense will be
     * silently ignored.
     */
    py_config *srv_conf = ap_get_module_config(cmd->server->module_config,
                                               &python_module);

    python_directive_handler(cmd, mconfig, "PythonPostReadRequestHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonTransHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonHeaderParserHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonAccessHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonAuthzHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonTypeHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonInitHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonLogHandler", val, SILENT);
    python_directive_handler(cmd, mconfig, "PythonCleanupHandler", val, SILENT);

    python_directive_handler(cmd, srv_conf, "PythonConnectionHandler", val, SILENT);

    return NULL;
}
static const char *directive_PythonPostReadRequestHandler(cmd_parms *cmd, 
                                                          void * mconfig, 
                                                          const char *val) {

    if (strchr((char *)val, '|'))
        return "PythonPostReadRequestHandler does not accept \"| .ext\" syntax.";

    return python_directive_handler(cmd, mconfig, "PythonPostReadRequestHandler", val,NOTSILENT);
}

static const char *directive_PythonTransHandler(cmd_parms *cmd, void *mconfig, 
                                                const char *val) {
    if (strchr((char *)val, '|'))
        return "PythonTransHandler does not accept \"| .ext\" syntax.";

    return python_directive_handler(cmd, mconfig, "PythonTransHandler", val, NOTSILENT);
}
static const char *directive_PythonTypeHandler(cmd_parms *cmd, void *mconfig, 
                                               const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonTypeHandler", val, NOTSILENT);
}
static const char *directive_PythonLogHandler(cmd_parms *cmd, void *mconfig, 
                                              const char *val) {
    return python_directive_handler(cmd, mconfig, "PythonLogHandler", val, NOTSILENT);
}
static const char *directive_PythonInputFilter(cmd_parms *cmd, void *mconfig, 
                                               const char *handler, const char *name) {

    py_config *conf;
    py_handler *fh;
    ap_filter_rec_t *frec;

    if (!name)
        name = apr_pstrdup(cmd->pool, handler);

    /* register the filter NOTE - this only works so long as the
       directive is only allowed in the main config. For .htaccess we
       would have to make sure not to duplicate this */
    frec = ap_register_input_filter(name, python_input_filter, NULL, AP_FTYPE_CONNECTION);
 
    conf = (py_config *) mconfig;

    fh = (py_handler *) apr_pcalloc(cmd->pool, sizeof(py_handler));
    fh->handler = (char *)handler;
    fh->dir = conf->config_dir;

    apr_hash_set(conf->in_filters, frec->name, APR_HASH_KEY_STRING, fh);

    return NULL;
}

static const char *directive_PythonOutputFilter(cmd_parms *cmd, void *mconfig, 
                                                const char *handler, const char *name) {
    py_config *conf;
    py_handler *fh;
    ap_filter_rec_t *frec;
 
    if (!name)
        name = apr_pstrdup(cmd->pool, handler);

    /* register the filter NOTE - this only works so long as the
       directive is only allowed in the main config. For .htaccess we
       would have to make sure not to duplicate this */
    frec = ap_register_output_filter(name, python_output_filter, NULL, AP_FTYPE_RESOURCE);
 
    conf = (py_config *) mconfig;
    
    fh = (py_handler *) apr_pcalloc(cmd->pool, sizeof(py_handler));
    fh->handler = (char *)handler;
    fh->dir = conf->config_dir;

    apr_hash_set(conf->out_filters, frec->name, APR_HASH_KEY_STRING, fh);

    return NULL;
}

/**
 ** python_finalize
 **
 *  We create a thread state just so we can run Py_Finalize()
 */

static apr_status_t python_finalize(void *data)
{
    interpreterdata *idata;

    idata = get_interpreter(NULL, NULL);

    if (idata) {

        Py_Finalize();

#ifdef WITH_THREAD
        PyEval_ReleaseLock();
#endif

    }

    return APR_SUCCESS;

}

/**
 ** Handlers
 **
 */

static void PythonChildInitHandler(apr_pool_t *p, server_rec *s)
{


    hl_entry *hle;
    py_config *conf = ap_get_module_config(s->module_config, &python_module);
    py_global_config *glb;

    /* accordig Py C Docs we must do this after forking */

#ifdef WITH_THREAD
    PyEval_AcquireLock();
#endif
    PyOS_AfterFork();
#ifdef WITH_THREAD
    PyEval_ReleaseLock();
#endif

    /*
     * Cleanups registered first will be called last. This will
     * end the Python interpreter *after* all other cleanups.
     */

    apr_pool_cleanup_register(p, NULL, python_finalize, apr_pool_cleanup_null);

    /*
     * Reinit mutexes
     */

    /* this will return it if it already exists */
    glb = python_create_global_config(s);

    reinit_mutexes(s, p, glb);

    /*
     * remember the pool in a global var. we may use it
     * later in server.register_cleanup()
     */
    child_init_pool = p;

    /*
     * Now run PythonImports
     */

    hle = conf->imports;
    while(hle) {

        interpreterdata *idata;
        const char *module_name = hle->handler;
        const char *interp_name = hle->directory;
        const char *ppath;

        /* get interpreter */
        idata = get_interpreter(interp_name, s);
        if (!idata)
            return;

        /* set up PythonPath */
        ppath = apr_table_get(conf->directives, "PythonPath");
        if (ppath) {

            PyObject *globals, *locals, *newpath, *sys;
            
            globals = PyDict_New();
            locals = PyDict_New();
            
            sys = PyImport_ImportModuleEx("sys", globals, locals, NULL);
            if (!sys)
                goto err;

            PyDict_SetItemString(globals, "sys", sys);
            newpath = PyRun_String((char *)ppath, Py_eval_input, globals, locals);
            if (!newpath)
                goto err;

            if (PyObject_SetAttrString(sys, "path", newpath) == -1)
                goto err;

            Py_XDECREF(sys);
            Py_XDECREF(newpath);
            Py_XDECREF(globals);
            Py_XDECREF(locals);
            goto success;

        err:
            PyErr_Print();
            release_interpreter();
            return;
        }

    success:
        /* now import the specified module */
        if (! PyImport_ImportModule((char *)module_name)) {
            if (PyErr_Occurred())
                PyErr_Print();
            ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, s,
                         "directive_PythonImport: error importing %s", module_name);
        }

        /* release interpreter */
        release_interpreter();

        /* next module */
        hle = hle->next;
    }
}

static int PythonConnectionHandler(conn_rec *con) {
    return python_connection(con);
}
static int PythonAccessHandler(request_rec *req) {
    return python_handler(req, "PythonAccessHandler");
}
static int PythonAuthenHandler(request_rec *req) {
    return python_handler(req, "PythonAuthenHandler");
}
static int PythonAuthzHandler(request_rec *req) {
    return python_handler(req, "PythonAuthzHandler");
}
static int PythonFixupHandler(request_rec *req) {
    return python_handler(req, "PythonFixupHandler");
}
static int PythonHandler(request_rec *req) {
    /*
     * In Apache 2.0, all handlers receive a request and have
     * a chance to process them.  Therefore, we need to only
     * handle those that we explicitly agreed to handle (see 
     * above).
     */
    if (!req->handler || (strcmp(req->handler, "mod_python") &&
			  strcmp(req->handler, "python-program")))
        return DECLINED;

    return python_handler(req, "PythonHandler");
}
static int PythonHeaderParserHandler(request_rec *req) {
    int rc;
    
    /* run PythonInitHandler, if not already */
    if (! apr_table_get(req->notes, "python_init_ran")) {
        rc = python_handler(req, "PythonInitHandler");
        if ((rc != OK) && (rc != DECLINED))
            return rc;
    }
    return python_handler(req, "PythonHeaderParserHandler");
}
static int PythonLogHandler(request_rec *req) {
    return python_handler(req, "PythonLogHandler");
}
static int PythonPostReadRequestHandler(request_rec *req) {
    int rc;

    /* run PythonInitHandler */
    rc = python_handler(req, "PythonInitHandler");
    apr_table_set(req->notes, "python_init_ran", "1");
    if ((rc != OK) && (rc != DECLINED))
        return rc;

    return python_handler(req, "PythonPostReadRequestHandler");
}
static int PythonTransHandler(request_rec *req) {
    return python_handler(req, "PythonTransHandler");
}
static int PythonTypeHandler(request_rec *req) {
    return python_handler(req, "PythonTypeHandler");
}

static void python_register_hooks(apr_pool_t *p)
{

    /* module initializer */ 
    ap_hook_post_config(python_init, 
                        NULL, NULL, APR_HOOK_MIDDLE);

    /* [0] raw connection handling */ 
    ap_hook_process_connection(PythonConnectionHandler, 
                               NULL, NULL, APR_HOOK_MIDDLE);

    /* [1] post read_request handling */ 
    ap_hook_post_read_request(PythonPostReadRequestHandler, 
                              NULL, NULL, APR_HOOK_MIDDLE);

    /* [2] filename-to-URI translation */ 
    ap_hook_translate_name(PythonTransHandler,
                           NULL, NULL, APR_HOOK_MIDDLE);

    /* [3] header parser */ 
    ap_hook_header_parser(PythonHeaderParserHandler,
                          NULL, NULL, APR_HOOK_MIDDLE); 

    /* [4] check access by host address */ 
    ap_hook_access_checker(PythonAccessHandler,
                           NULL, NULL, APR_HOOK_MIDDLE);

    /* [5] check/validate user_id */ 
    ap_hook_check_user_id(PythonAuthenHandler,
                          NULL, NULL, APR_HOOK_MIDDLE);

    /* [6] check user_id is valid *here* */ 
    ap_hook_auth_checker(PythonAuthzHandler,
                         NULL, NULL, APR_HOOK_MIDDLE); 

    /* [7] MIME type checker/setter */ 
    ap_hook_type_checker(PythonTypeHandler,
                         NULL, NULL, APR_HOOK_MIDDLE);

    /* [8] fixups */ 
    ap_hook_fixups(PythonFixupHandler,
                   NULL, NULL, APR_HOOK_MIDDLE);

    /* [9] filter insert opportunity */
    /* ap_hook_insert_filter(PythonInsertFilter,
       NULL, NULL, APR_HOOK_MIDDLE); */

    /* [10] is for the handlers; see below */
    ap_hook_handler(PythonHandler, NULL, NULL, APR_HOOK_MIDDLE);

    /* [11] logger */ 
    ap_hook_log_transaction(PythonLogHandler,
                            NULL, NULL, APR_HOOK_MIDDLE);

    /* process initializer */ 
    ap_hook_child_init(PythonChildInitHandler,
                       NULL, NULL, APR_HOOK_MIDDLE);

}

/* command table */
command_rec python_commands[] =
{
    AP_INIT_RAW_ARGS(
        "PythonAccessHandler", directive_PythonAccessHandler, NULL, OR_ALL,
        "Python access by host address handlers."),
    AP_INIT_RAW_ARGS(
        "PythonAuthenHandler", directive_PythonAuthenHandler, NULL, OR_ALL,
        "Python authentication handlers."),
    AP_INIT_FLAG(
        "PythonAutoReload", directive_PythonAutoReload, NULL, OR_ALL,
        "Set to Off if you don't want changed modules to reload."),
    AP_INIT_RAW_ARGS(
        "PythonAuthzHandler", directive_PythonAuthzHandler, NULL, OR_ALL,
        "Python authorization handlers."),
    AP_INIT_RAW_ARGS(
        "PythonCleanupHandler", directive_PythonCleanupHandler, NULL, OR_ALL,
        "Python clean up handlers."),
    AP_INIT_RAW_ARGS(
        "PythonConnectionHandler", directive_PythonConnectionHandler, NULL, RSRC_CONF,
        "Python connection handlers."),
    AP_INIT_FLAG(
        "PythonDebug", directive_PythonDebug, NULL, OR_ALL,
        "Send (most) Python error output to the client rather than logfile."),
    AP_INIT_FLAG(
        "PythonEnablePdb", directive_PythonEnablePdb, NULL, OR_ALL,
        "Run handlers in PDB (Python Debugger). Use with -DONE_PROCESS."),
    AP_INIT_RAW_ARGS(
        "PythonFixupHandler", directive_PythonFixupHandler, NULL, OR_ALL,
        "Python fixups handlers."),
    AP_INIT_RAW_ARGS(
        "PythonHandler", directive_PythonHandler, NULL, OR_ALL,
        "Python request handlers."),
    AP_INIT_RAW_ARGS(
        "PythonHeaderParserHandler", directive_PythonHeaderParserHandler, NULL, OR_ALL,
        "Python header parser handlers."),
    AP_INIT_TAKE2(
        "PythonImport", directive_PythonImport, NULL, RSRC_CONF,
        "Module and interpreter name to be imported at server/child init time."),
    AP_INIT_RAW_ARGS(
        "PythonInitHandler", directive_PythonInitHandler, NULL, OR_ALL,
        "Python request initialization handler."),
    AP_INIT_FLAG(
        "PythonInterpPerDirective", directive_PythonInterpPerDirective, NULL, OR_ALL,
        "Create subinterpreters per directive."),
    AP_INIT_FLAG(
        "PythonInterpPerDirectory", directive_PythonInterpPerDirectory, NULL, OR_ALL,
        "Create subinterpreters per directory."),
    AP_INIT_TAKE1(
        "PythonInterpreter", directive_PythonInterpreter, NULL, OR_ALL,
        "Forces a specific Python interpreter name to be used here."),
    AP_INIT_RAW_ARGS(
        "PythonLogHandler", directive_PythonLogHandler, NULL, OR_ALL,
        "Python logger handlers."),
    AP_INIT_RAW_ARGS(
        "PythonHandlerModule", directive_PythonHandlerModule, NULL, OR_ALL,
        "A Python module containing handlers to be executed."),
    AP_INIT_FLAG(
        "PythonOptimize", directive_PythonOptimize, NULL, RSRC_CONF,
        "Set the equivalent of the -O command-line flag on the interpreter."),
    AP_INIT_TAKE2(
        "PythonOption", directive_PythonOption, NULL, OR_ALL,
        "Useful to pass custom configuration information to scripts."),
    AP_INIT_TAKE1(
        "PythonPath", directive_PythonPath, NULL, OR_ALL,
        "Python path, specified in Python list syntax."),
    AP_INIT_RAW_ARGS(
        "PythonPostReadRequestHandler", directive_PythonPostReadRequestHandler, 
        NULL, RSRC_CONF,
        "Python post read-request handlers."),
    AP_INIT_RAW_ARGS(
        "PythonTransHandler", directive_PythonTransHandler, NULL, RSRC_CONF,
        "Python filename to URI translation handlers."),
    AP_INIT_RAW_ARGS(
        "PythonTypeHandler", directive_PythonTypeHandler, NULL, OR_ALL,
        "Python MIME type checker/setter handlers."),
    AP_INIT_TAKE12(
        "PythonInputFilter", directive_PythonInputFilter, NULL, RSRC_CONF|ACCESS_CONF,
        "Python input filter."),
    AP_INIT_TAKE12(
        "PythonOutputFilter", directive_PythonOutputFilter, NULL, RSRC_CONF|ACCESS_CONF,
        "Python output filter."),
    {NULL}
};


module python_module =
{
    STANDARD20_MODULE_STUFF,
    python_create_dir_config,      /* per-directory config creator */
    python_merge_config,           /* dir config merger */ 
    python_create_srv_config,      /* server config creator */ 
    python_merge_config,           /* server config merger */ 
    python_commands,               /* command table */ 
    python_register_hooks          /* register hooks */
};
    







