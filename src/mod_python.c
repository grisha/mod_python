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
 * mod_python.c 
 *
 * $Id: mod_python.c,v 1.53 2001/08/18 22:43:45 gtrubetskoy Exp $
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

#include "mod_python.h"

/* List of available Python obCallBacks/Interpreters
 * (In a Python dictionary) */
static PyObject * interpreters = NULL;

/* list of modules to be imported from PythonImport */
static apr_table_t *python_imports = NULL;

apr_pool_t *child_init_pool = NULL;

/**
 ** make_interpreter
 **
 *      Creates a new Python interpeter.
 */

PyInterpreterState *make_interpreter(const char *name, server_rec *srv)
{
    PyThreadState *tstate;
    
    /* create a new interpeter */
    tstate = Py_NewInterpreter();

    if (! tstate) {
	if (srv) {

	    /* couldn't create an interpreter, this is bad */
	    ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, srv,
		 "make_interpreter: Py_NewInterpreter() returned NULL. No more memory?");
	}
       return NULL;
    }
    else {

        /* release the thread state */
        PyThreadState_Swap(NULL); 

        /* Strictly speaking we don't need that tstate created
	 * by Py_NewInterpreter but is preferable to waste it than re-write
	 * a cousin to Py_NewInterpreter 
	 * XXX (maybe we can destroy it?)
	 */
        return tstate->interp;
    }
    
}

/**
 ** get_interpreter_data
 **
 *      Get interpreter given its name. 
 *      NOTE: Lock must be acquired prior to entering this function.
 */

interpreterdata *get_interpreter_data(const char *name, server_rec *srv)
{
    PyObject *p;
    interpreterdata *idata = NULL;
    
    if (! name)
	name = MAIN_INTERPRETER;

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

    return idata;
}


/**
 ** python_cleanup
 **
 *     This function gets called for clean ups registered
 *     with register_cleanup(). Clean ups registered via
 *     PythonCleanupHandler run in python_cleanup_handler()
 *     below.
 */

apr_status_t python_cleanup(void *data)
{
    interpreterdata *idata;
    PyThreadState *tstate;

    cleanup_info *ci = (cleanup_info *)data;

#ifdef WITH_THREAD  
    /* acquire lock (to protect the interpreters dictionary) */
    PyEval_AcquireLock();
#endif

    /* get/create interpreter */
    if (ci->request_rec)
	idata = get_interpreter_data(ci->interpreter, ci->request_rec->server);
    else
	idata = get_interpreter_data(ci->interpreter, ci->server_rec);

#ifdef WITH_THREAD
    /* release the lock */
    PyEval_ReleaseLock();
#endif

    if (!idata) {
	if (ci->request_rec)
	    ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, 
			  ci->request_rec,
			  "python_cleanup: get_interpreter_data returned NULL!");
	else
	    ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, 
			 ci->server_rec,
			 "python_cleanup: get_interpreter_data returned NULL!");
	Py_DECREF(ci->handler);
	Py_XDECREF(ci->data);
	free(ci);
        return APR_SUCCESS;
    }
    
    /* create thread state and acquire lock */
    tstate = PyThreadState_New(idata->istate);
#ifdef WITH_THREAD  
    PyEval_AcquireThread(tstate);
#else
    PyThreadState_Swap(tstate);
#endif

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
     
    /* release the lock and destroy tstate*/
    /* XXX Do not use 
     * . PyEval_ReleaseThread(tstate); 
     * . PyThreadState_Delete(tstate);
     * because PyThreadState_delete should be done under 
     * interpreter lock to work around a bug in 1.5.2 (see patch to pystate.c 2.8->2.9) 
     */
    PyThreadState_Swap(NULL);
    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
    PyEval_ReleaseLock();
#endif

    Py_DECREF(ci->handler);
    Py_DECREF(ci->data);
    free(ci);
    return APR_SUCCESS;
}

/**
 ** python_init()
 **
 *      Called at Apache mod_python initialization time.
 */

static void python_init(apr_pool_t *p, apr_pool_t *ptemp, 
			apr_pool_t *plog, server_rec *s)
{

    char buff[255];

    /* mod_python version */
    ap_add_version_component(p, VERSION_COMPONENT);
    
    /* Python version */
    sprintf(buff, "Python/%s", strtok((char *)Py_GetVersion(), " "));
    ap_add_version_component(p, buff);

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

    py_dir_config *conf = 
	(py_dir_config *) apr_pcalloc(p, sizeof(py_dir_config));

    conf->authoritative = 1;
    /* make sure directory ends with a slash */
    if (dir && (dir[strlen(dir) - 1] != SLASH))
	conf->config_dir = apr_pstrcat(p, dir, SLASH_S, NULL);
    else
	conf->config_dir = apr_pstrdup(p, dir);
    conf->options = apr_table_make(p, 4);
    conf->directives = apr_table_make(p, 4);
    conf->dirs = apr_table_make(p, 4);
    conf->input_filters = apr_table_make(p, 4);
    conf->input_filter_dirs = apr_table_make(p, 4);
    conf->output_filters = apr_table_make(p, 4);
    conf->output_filter_dirs = apr_table_make(p, 4);

    return conf;
}

/**
 ** mp_copy_table
 **
 *   Merge two tables into one. Matching key values 
 *   in second overlay the first.
 */

void mp_copy_table(apr_table_t *t1, apr_table_t *t2)
{

    apr_array_header_t *ah;
    apr_table_entry_t *elts;
    int i;

    ah = apr_table_elts(t2);
    elts = (apr_table_entry_t *)ah->elts;
    i = ah->nelts;

    while (i--)
	if (elts[i].key)
	    apr_table_set(t1, elts[i].key, elts[i].val);
}

/**
 ** python_merge_dir_config
 **
 */

static void *python_merge_dir_config(apr_pool_t *p, void *cc, void *nc)
{

    py_dir_config *merged_conf = 
	(py_dir_config *) apr_pcalloc(p, sizeof(py_dir_config));
    py_dir_config *current_conf = (py_dir_config *) cc;
    py_dir_config *new_conf = (py_dir_config *) nc;

    /* we basically allow the local configuration to override global,
     * by first copying current values and then new values on top
     */

    /** create **/
    merged_conf->directives = apr_table_make(p, 4);
    merged_conf->dirs = apr_table_make(p, 4);
    merged_conf->options = apr_table_make(p, 4);
    merged_conf->input_filters = apr_table_make(p, 4);
    merged_conf->input_filter_dirs = apr_table_make(p, 4);
    merged_conf->output_filters = apr_table_make(p, 4);
    merged_conf->output_filter_dirs = apr_table_make(p, 4);

    /** copy current **/
    merged_conf->authoritative = current_conf->authoritative;
    merged_conf->config_dir = apr_pstrdup(p, current_conf->config_dir);

    mp_copy_table(merged_conf->directives, current_conf->directives);
    mp_copy_table(merged_conf->dirs, current_conf->dirs);
    mp_copy_table(merged_conf->options, current_conf->options);
    mp_copy_table(merged_conf->input_filters, current_conf->input_filters);
    mp_copy_table(merged_conf->input_filter_dirs, current_conf->input_filter_dirs);
    mp_copy_table(merged_conf->output_filters, current_conf->output_filters);
    mp_copy_table(merged_conf->output_filter_dirs, current_conf->output_filter_dirs);


    /** copy new **/

    if (new_conf->authoritative != merged_conf->authoritative)
	merged_conf->authoritative = new_conf->authoritative;
    if (new_conf->config_dir)
	merged_conf->config_dir = apr_pstrdup(p, new_conf->config_dir);

    mp_copy_table(merged_conf->directives, new_conf->directives);
    mp_copy_table(merged_conf->dirs, new_conf->dirs);
    mp_copy_table(merged_conf->options, new_conf->options);
    mp_copy_table(merged_conf->input_filters, new_conf->input_filters);
    mp_copy_table(merged_conf->input_filter_dirs, new_conf->input_filter_dirs);
    mp_copy_table(merged_conf->output_filters, new_conf->output_filters);
    mp_copy_table(merged_conf->output_filter_dirs, new_conf->output_filter_dirs);

    return (void *) merged_conf;
}

/**
 ** python_directive
 **
 *  Called by Python*Handler directives.
 *
 *  When used within the same directory, this will have a
 *  cumulative, rather than overriding effect - i.e. values
 *  from same directives specified multiple times will be appended
 *  with a space in between.
 *
 */

static const char *python_directive(cmd_parms *cmd, void * mconfig, 
				    char *key, const char *val)
{
    py_dir_config *conf;
    const char *s;
    
    conf = (py_dir_config *) mconfig;
    
    if (! val) {
	/*  If the value is NULL, then assume this is an "Off" FLAG
	    and erase the directive from the config. */
	apr_table_unset(conf->directives, key);
	apr_table_unset(conf->dirs, key);
    }
    else {

	/* something there already? */
	s = apr_table_get(conf->directives, key);
	if (s)
	    val = apr_pstrcat(cmd->pool, s, " ", val, NULL);
    
	apr_table_set(conf->directives, key, val);
    
	/* remember the directory where the directive was found */
	if (conf->config_dir) {
	    apr_table_set(conf->dirs, key, conf->config_dir);
	}
	else {
	    apr_table_set(conf->dirs, key, "");
	}
    }
    return NULL;
}


/**
 ** make_obcallback
 **
 *      This function instantiates an obCallBack object. 
 *      NOTE: The obCallBack object is instantiated by Python
 *      code. This C module calls into Python code which returns 
 *      the reference to obCallBack.
 */

PyObject * make_obcallback()
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
	fprintf(stderr, "make_obcallback(): could not import %s.\n", MODULENAME);
    }
    
    if (! ((obCallBack = PyObject_CallMethod(m, INITFUNC, NULL)))) {
	fprintf(stderr, "make_obcallback(): could not call %s.\n",
		INITFUNC);
    }
    
    return obCallBack;

}

/**
 ** get_request_object
 **
 *      This creates or retrieves a previously created request object.
 *      The pointer to request object is stored in req->request_config.
 */

static requestobject *get_request_object(request_rec *req)
{
    requestobject *request_obj;
    PyThreadState *_save;

    /* see if there is a request object already */
    request_obj = (requestobject *) ap_get_module_config(req->request_config,
							 &python_module);
    if (request_obj) {
	return request_obj;
    }
    else {
	if ((req->path_info) && 
	    (req->path_info[strlen(req->path_info) - 1] == SLASH))
	{
	    int i;
	    i = strlen(req->path_info);
	    /* take out the slash */
	    req->path_info[i - 1] = 0;

	    _save = PyEval_SaveThread();
	    ap_add_cgi_vars(req);
	    PyEval_RestoreThread(_save);
	    request_obj = (requestobject *)MpRequest_FromRequest(req);

	    /* put the slash back in */
	    req->path_info[i - 1] = SLASH; 
	    req->path_info[i] = 0;

	    /* and also make PATH_INFO == req->subprocess_env */
	    apr_table_set(req->subprocess_env, "PATH_INFO", req->path_info);
	} 
	else 
	{ 
	    _save = PyEval_SaveThread();
	    ap_add_cgi_vars(req);
	    PyEval_RestoreThread(_save);
	    request_obj = (requestobject *)MpRequest_FromRequest(req);
	}

	/* store the pointer to this object in request_config */
	ap_set_module_config(req->request_config, &python_module, request_obj);
	return request_obj;
    }
}

/**
 ** select_interpreter_name
 **
 *      (internal)
 *      figure out the name of the interpreter we should be using
 */

static const char *select_interp_name(request_rec *req, py_dir_config *conf, 
				      char *handler, const char *fname)
{
    const char *s;

    if ((s = apr_table_get(conf->directives, "PythonInterpreter"))) {
	/* forced by configuration */
	return s;
    }
    else {
	if ((s = apr_table_get(conf->directives, "PythonInterpPerDirectory"))) {
	    
	    /* base interpreter on directory where the file is found */
	    if (ap_is_directory(req->pool, req->filename))
		return ap_make_dirstr_parent(req->pool, 
					     apr_pstrcat(req->pool, req->filename, 
							 SLASH_S, NULL ));
	    else {
		if (req->filename)
		    return ap_make_dirstr_parent(req->pool, req->filename);
		else
		    /* 
		     * In early stages of the request, req->filename is not known,
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
	    
	    if (strcmp("PythonInputHandler", handler) == 0) {
		s = apr_table_get(conf->input_filter_dirs, fname);
	    }
	    else if (strcmp("PythonOutputHandler", handler) == 0) {
		s = apr_table_get(conf->output_filter_dirs, fname);
	    }
	    else {
		s = apr_table_get(conf->dirs, handler);
		if (! s) {

		    /* are we using PythonHandlerModule? */
		    s = apr_table_get(conf->dirs, "PythonHandlerModule");
		
		    if (! s) {
			/* this one must have been added via req.add_handler() */
			char * ss = apr_pstrcat(req->pool, handler, "_dir", NULL);
			s = apr_table_get(req->notes, ss);
		    }
		}
	    }
	    if (strcmp(s, "") == 0)
		return NULL;
	    else
		return s;
	}
	else {
	    /* - default per server - */
	    return req->server->server_hostname;
	}
    }
}


/**
 ** python_handler
 **
 *      A generic python handler. Most handlers should use this.
 */

static int python_handler(request_rec *req, char *handler)
{

    PyObject *resultobject = NULL;
    interpreterdata *idata;
    requestobject *request_obj;
    const char *s;
    py_dir_config * conf;
    int result;
    const char * interpreter = NULL;
    PyThreadState *tstate;

    /*
     * In Apache 2.0, all handlers receive a request and have
     * a chance to process them.  Therefore, we need to only
     * handle those that we explicitly agreed to handle (see 
     * above).
     */
    if (!req->handler || strcmp(req->handler, "python-program"))
        return DECLINED;

    /* get configuration */
    conf = (py_dir_config *) ap_get_module_config(req->per_dir_config, 
						  &python_module);

    /* is there a handler? */
    if (! apr_table_get(conf->directives, "PythonHandlerModule")) {
	if (! apr_table_get(conf->directives, handler)) {
	    if (! apr_table_get(req->notes, handler))
	    return DECLINED;
	}
    }

    /* determine interpreter to use */
    interpreter = select_interp_name(req, conf, handler, NULL);

#ifdef WITH_THREAD  
    /* acquire lock (to protect the interpreters dictionary) */
    PyEval_AcquireLock();
#endif

    /* get/create interpreter */
    idata = get_interpreter_data(interpreter, req->server);
   
#ifdef WITH_THREAD
    /* release the lock */
    PyEval_ReleaseLock();
#endif

    if (!idata) {
        ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req,
		      "python_handler: get_interpreter_data returned NULL!");
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    
    /* create thread state and acquire lock */
    tstate = PyThreadState_New(idata->istate);
#ifdef WITH_THREAD 
    PyEval_AcquireThread(tstate);
#else
    PyThreadState_Swap(tstate);
#endif

    if (!idata->obcallback) {

        idata->obcallback = make_obcallback();
        /* we must have a callback object to succeed! */
        if (!idata->obcallback) 
        {
	    ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req,
			  "python_handler: make_obcallback returned no obCallBack!");

	    PyThreadState_Swap(NULL);
	    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
	    PyEval_ReleaseLock();
#endif
	    return HTTP_INTERNAL_SERVER_ERROR;
        }
    }

    /* 
     * make a note of which subinterpreter we're running under.
     * this information is used by register_cleanup()
     */
    if (interpreter)
	apr_table_set(req->notes, "python_interpreter", interpreter);
    else
	apr_table_set(req->notes, "python_interpreter", MAIN_INTERPRETER);
    
    /* create/acquire request object */
    request_obj = get_request_object(req);

    /* make a note of which handler we are in right now */
    apr_table_set(req->notes, "python_handler", handler);

    /* put the list of handlers on the hstack */
    if ((s = apr_table_get(conf->directives, handler))) {
	request_obj->hstack = apr_pstrdup(req->pool, apr_table_get(conf->directives,
								 handler));
    }
    if ((s = apr_table_get(conf->directives, "PythonHandlerModule"))) {
	if (request_obj->hstack)
	    request_obj->hstack = apr_pstrcat(req->pool, request_obj->hstack,
					     " ", s, NULL);
	else 
	    request_obj->hstack = apr_pstrdup(req->pool, s);
    }	
    if ((s = apr_table_get(req->notes, handler))) {
	if (request_obj->hstack)
	    request_obj->hstack = apr_pstrcat(req->pool, request_obj->hstack,
					     " ", s, NULL);
	else
	    request_obj->hstack = apr_pstrdup(req->pool, s);
    }

    /* 
     * Here is where we call into Python!
     * This is the C equivalent of
     * >>> resultobject = obCallBack.Dispatch(request_object, handler)
     */
    resultobject = PyObject_CallMethod(idata->obcallback, "HandlerDispatch", "Os", 
				       request_obj, handler);
     
    /* release the lock and destroy tstate*/
    /* XXX Do not use 
     * . PyEval_ReleaseThread(tstate); 
     * . PyThreadState_Delete(tstate);
     * because PyThreadState_delete should be done under 
     * interpreter lock to work around a bug in 1.5.2 (see patch to pystate.c 2.8->2.9) 
     */
    PyThreadState_Swap(NULL);
    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
    PyEval_ReleaseLock();
#endif

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
	    if (strcmp(handler, "PythonAuthenHandler") == 0) {
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
 *
 *    This is a little too similar to python_handler, except the
 *    return of the function doesn't matter.
 */

static apr_status_t python_cleanup_handler(void *data)
{

    request_rec *req = (request_rec *)data;
    char *handler = "PythonCleanupHandler";
    interpreterdata *idata;
    requestobject *request_obj;
    const char *s;
    py_dir_config * conf;
    const char * interpreter = NULL;
    PyThreadState *tstate;
    
    /* get configuration */
    conf = (py_dir_config *) ap_get_module_config(req->per_dir_config, &python_module);

    /* is there a handler? */
    if (! apr_table_get(conf->directives, handler)) {
	return APR_SUCCESS;
    }

    /* determine interpreter to use */
    interpreter = select_interp_name(req, conf, handler, NULL);

#ifdef WITH_THREAD  
    /* acquire lock (to protect the interpreters dictionary) */
    PyEval_AcquireLock();
#endif

    /* get/create interpreter */
    idata = get_interpreter_data(interpreter, req->server);
   
#ifdef WITH_THREAD
    /* release the lock */
    PyEval_ReleaseLock();
#endif

    if (!idata) {
        ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req,
		      "python_cleanup_handler: get_interpreter_data returned NULL!");
        return APR_SUCCESS;
    }
    
    /* create thread state and acquire lock */
    tstate = PyThreadState_New(idata->istate);
#ifdef WITH_THREAD  
    PyEval_AcquireThread(tstate);
#else
    PyThreadState_Swap(tstate);
#endif

    if (!idata->obcallback) {

        idata->obcallback = make_obcallback();
        /* we must have a callback object to succeed! */
        if (!idata->obcallback) 
        {
	    ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req,
			  "python_cleanup_handler: make_obcallback returned no obCallBack!");
	    PyThreadState_Swap(NULL);
	    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
	    PyEval_ReleaseLock();
#endif
	    return APR_SUCCESS;
        }
    }

    /* 
     * make a note of which subinterpreter we're running under.
     * this information is used by register_cleanup()
     */
    if (interpreter)
	apr_table_set(req->notes, "python_interpreter", interpreter);
    else
	apr_table_set(req->notes, "python_interpreter", MAIN_INTERPRETER);
    
    /* create/acquire request object */
    request_obj = get_request_object(req);

    /* make a note of which handler we are in right now */
    apr_table_set(req->notes, "python_handler", handler);

    /* put the list of handlers on the hstack */
    if ((s = apr_table_get(conf->directives, handler))) {
	request_obj->hstack = apr_pstrdup(req->pool, apr_table_get(conf->directives,
								 handler));
    }
    if ((s = apr_table_get(req->notes, handler))) {
	if (request_obj->hstack) {
	    request_obj->hstack = apr_pstrcat(req->pool, request_obj->hstack,
					     " ", s, NULL);
	}
	else {
	    request_obj->hstack = apr_pstrdup(req->pool, s);
	}
    }
    /* 
     * Here is where we call into Python!
     * This is the C equivalent of
     * >>> obCallBack.Dispatch(request_object, handler)
     */
    PyObject_CallMethod(idata->obcallback, "Dispatch", "Os", 
			request_obj, handler);
     
    /* release the lock and destroy tstate*/
    /* XXX Do not use 
     * . PyEval_ReleaseThread(tstate); 
     * . PyThreadState_Delete(tstate);
     * because PyThreadState_delete should be done under 
     * interpreter lock to work around a bug in 1.5.2 (see patch to pystate.c 2.8->2.9) 
     */
    PyThreadState_Swap(NULL);
    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
    PyEval_ReleaseLock();
#endif

    /* unlike python_handler, there is nothing to return */
    return APR_SUCCESS;
}


/**
 ** python_filter
 **
 *    filter
 */

static apr_status_t python_filter(int is_input, ap_filter_t *f, 
				  apr_bucket_brigade *bb,
				  ap_input_mode_t mode,
				  apr_size_t *readbytes) {
    
    PyObject *resultobject = NULL;
    interpreterdata *idata;
    requestobject *request_obj;
    py_dir_config * conf;
    const char * interpreter = NULL;
    PyThreadState *tstate;
    request_rec *req;
    filterobject *filter;
    const char *func;
    python_filter_ctx *ctx;

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
	    return ap_get_brigade(f->next, bb, mode, readbytes);
	else
	    return ap_pass_brigade(f->next, bb);
    }
	
    /* get configuration */
    conf = (py_dir_config *) ap_get_module_config(req->per_dir_config, 
						  &python_module);

    /* determine interpreter to use */
    if (is_input)
	interpreter = select_interp_name(req, conf, "PythonInputFilter", f->frec->name);
    else
	interpreter = select_interp_name(req, conf, "PythonOutputFilter", f->frec->name);

#ifdef WITH_THREAD  
    /* acquire lock (to protect the interpreters dictionary) */
    PyEval_AcquireLock();
#endif

    /* get/create interpreter */
    idata = get_interpreter_data(interpreter, req->server);
   
#ifdef WITH_THREAD
    /* release the lock */
    PyEval_ReleaseLock();
#endif

    if (!idata) {
        ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req,
		      "python_filter: get_interpreter_data returned NULL!");
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    
    /* create thread state and acquire lock */
    tstate = PyThreadState_New(idata->istate);
#ifdef WITH_THREAD 
    PyEval_AcquireThread(tstate);
#else
    PyThreadState_Swap(tstate);
#endif

    if (!idata->obcallback) {

        idata->obcallback = make_obcallback();
        /* we must have a callback object to succeed! */
        if (!idata->obcallback) 
        {
	    ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req,
			  "python_filter: make_obcallback returned no obCallBack!");

	    PyThreadState_Swap(NULL);
	    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
	    PyEval_ReleaseLock();
#endif
	    return HTTP_INTERNAL_SERVER_ERROR;
        }
    }

    /* 
     * make a note of which subinterpreter we're running under.
     * this information is used by register_cleanup()
     */
    if (interpreter)
	apr_table_set(req->notes, "python_interpreter", interpreter);
    else
	apr_table_set(req->notes, "python_interpreter", MAIN_INTERPRETER);
    
    /* create/acquire request object */
    request_obj = get_request_object(req);

    /* create filter */
    filter = (filterobject *)MpFilter_FromFilter(f, bb, is_input, mode, readbytes);
    Py_INCREF(request_obj);
    filter->request_obj = request_obj;

    /* the name of python function to call */
    if (is_input)
	func = apr_table_get(conf->input_filters, f->frec->name);
    else
	func = apr_table_get(conf->output_filters, f->frec->name);

    /* 
     * Here is where we call into Python!
     * This is the C equivalent of
     * >>> resultobject = obCallBack.FilterDispatch(filter_object, handler)
     */
    resultobject = PyObject_CallMethod(idata->obcallback, "FilterDispatch", "Os", 
				       filter, func);
     
    /* release the lock and destroy tstate*/
    /* XXX Do not use 
     * . PyEval_ReleaseThread(tstate); 
     * . PyThreadState_Delete(tstate);
     * because PyThreadState_delete should be done under 
     * interpreter lock to work around a bug in 1.5.2 (see patch to pystate.c 2.8->2.9) 
     */
    PyThreadState_Swap(NULL);
    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
    PyEval_ReleaseLock();
#endif
    
    if (! resultobject) {
	ap_log_rerror(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, req, 
		      "python_filter: FilterDispatch() returned NULL");
	if (APR_STATUS_IS_SUCCESS(filter->rc))
	    /* this means it's a Python error not caused by Apache */
	    return APR_EGENERAL;
    }
    else {
	/* clean up */
	Py_XDECREF(resultobject);

	/* if this is a PEEK */
	if (mode == AP_MODE_PEEK) {
	    if (APR_STATUS_IS_SUCCESS(filter->rc) && 
		filter->bytes_written == 0) {
		/* if the filter wrote no data, 
		   there must not be any left */
		return APR_EOF;
	    }
	}
    }
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
					apr_size_t *readbytes) 
{
    return python_filter(1, f, bb, mode, readbytes);
}


/**
 ** python_output_filter
 **
 *    output filter
 */

static apr_status_t python_output_filter(ap_filter_t *f, 
					 apr_bucket_brigade *bb)
{
    return python_filter(0, f, bb, 0, NULL);
}


/**
 ** directive_PythonImport
 **
 *      This function called whenever PythonImport directive
 *      is encountered. Note that this function does not actually
 *      import anything, it just remembers what needs to be imported
 *      in the python_imports table. The actual importing is done later
 *      in the ChildInitHandler. This is because this function here
 *      is called before the python_init and before the suid and fork.
 *
 *      The reason why this infor stored in a global variable as opposed
 *      to the actual config, is that the config info doesn't seem to
 *      be available within the ChildInit handler.
 */
static const char *directive_PythonImport(cmd_parms *cmd, void *mconfig, 
					  const char *module) 
{
    const char *s = NULL; /* general purpose string */
    py_dir_config *conf;
    const char *key = "PythonImport";

    /* get config */
    conf = (py_dir_config *) mconfig;

#ifdef WITH_THREAD  
    PyEval_AcquireLock();
#endif

    /* make the table if not yet */
    if (! python_imports)
	python_imports = apr_table_make(cmd->pool, 4);
    
    /* remember the module name and the directory in which to
       import it (this is for ChildInit) */
    apr_table_add(python_imports, module, conf->config_dir);

#ifdef WITH_THREAD  
    PyEval_ReleaseLock();
#endif

    /* the rest is basically for consistency */

    /* Append the module to the directive. (this is ITERATE) */
    if ((s = apr_table_get(conf->directives, key))) {
	apr_pstrcat(cmd->pool, s, " ", module, NULL);
    }
    else {
	apr_table_set(conf->directives, key, module);
    }

    /* remember the directory where the directive was found */
    if (conf->config_dir) {
	apr_table_set(conf->dirs, key, conf->config_dir);
    }
    else {
	apr_table_set(conf->dirs, key, "");
    }

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
    return python_directive(cmd, mconfig, "PythonPath", val);
}

/**
 ** directive_PythonInterpreter
 **
 *      This function called whenever PythonInterpreter directive
 *      is encountered.
 */
static const char *directive_PythonInterpreter(cmd_parms *cmd, void *mconfig, 
				       const char *val) {
    return python_directive(cmd, mconfig, "PythonInterpreter", val);
}

/**
 ** directive_PythonDebug
 **
 *      This function called whenever PythonDebug directive
 *      is encountered.
 */
static const char *directive_PythonDebug(cmd_parms *cmd, void *mconfig,
					 int val) {
    if (val)
	return python_directive(cmd, mconfig, "PythonDebug", "1");
    else
	return python_directive(cmd, mconfig, "PythonDebug", NULL);
}

/**
 ** directive_PythonEnablePdb
 **
 *      This function called whenever PythonEnablePdb
 *      is encountered.
 */
static const char *directive_PythonEnablePdb(cmd_parms *cmd, void *mconfig,
					     int val) {
    if (val)
	return python_directive(cmd, mconfig, "PythonEnablePdb", "1");
    else
	return python_directive(cmd, mconfig, "PythonEnablePdb", NULL);
}

/**
 ** directive_PythonInterpPerDirective
 **
 *      This function called whenever PythonInterpPerDirective directive
 *      is encountered.
 */

static const char *directive_PythonInterpPerDirective(cmd_parms *cmd, 
						      void *mconfig, int val) {
    py_dir_config *conf;
    const char *key = "PythonInterpPerDirective";

    conf = (py_dir_config *) mconfig;

    if (val) {
	apr_table_set(conf->directives, key, "1");

	/* remember the directory where the directive was found */
	if (conf->config_dir) {
	    apr_table_set(conf->dirs, key, conf->config_dir);
	}
	else {
	    apr_table_set(conf->dirs, key, "");
	}
    }
    else {
	apr_table_unset(conf->directives, key);
	apr_table_unset(conf->dirs, key);
    }

    return NULL;
}

/**
 ** directive_PythonInterpPerDirectory
 **
 *      This function called whenever PythonInterpPerDirectory directive
 *      is encountered.
 */

static const char *directive_PythonInterpPerDirectory(cmd_parms *cmd, 
						      void *mconfig, int val) {
    py_dir_config *conf;
    const char *key = "PythonInterpPerDirectory";

    conf = (py_dir_config *) mconfig;

    if (val) {
	apr_table_set(conf->directives, key, "1");

	/* remember the directory where the directive was found */
	if (conf->config_dir) {
	    apr_table_set(conf->dirs, key, conf->config_dir);
	}
	else {
	    apr_table_set(conf->dirs, key, "");
	}
    }
    else {
	apr_table_unset(conf->directives, key);
	apr_table_unset(conf->dirs, key);
    }

    return NULL;
}

/**
 ** directive_PythonAutoReload
 **
 *      This function called whenever PythonAutoReload directive
 *      is encountered.
 */

static const char *directive_PythonAutoReload(cmd_parms *cmd, 
					    void *mconfig, int val) {
    if (val)
	return python_directive(cmd, mconfig, "PythonAutoReload", "1");
    else
	return python_directive(cmd, mconfig, "PythonAutoReload", "0");
}

/**
 **
 *       This function is called every time PythonOption directive
 *       is encountered. It sticks the option into a table containing
 *       a list of options. This table is part of the local config structure.
 */

static const char *directive_PythonOption(cmd_parms *cmd, void * mconfig, 
				       const char *key, const char *val)
{

    py_dir_config *conf;

    conf = (py_dir_config *) mconfig;
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
    return python_directive(cmd, mconfig, "PythonAccessHandler", val);
}
static const char *directive_PythonAuthenHandler(cmd_parms *cmd, void *mconfig, 
						 const char *val) {
    return python_directive(cmd, mconfig, "PythonAuthenHandler", val);
}
static const char *directive_PythonAuthzHandler(cmd_parms *cmd, void *mconfig, 
						const char *val) {
    return python_directive(cmd, mconfig, "PythonAuthzHandler", val);
}
static const char *directive_PythonCleanupHandler(cmd_parms *cmd, void *mconfig, 
						  const char *val) {
    return python_directive(cmd, mconfig, "PythonCleanupHandler", val);
}
static const char *directive_PythonFixupHandler(cmd_parms *cmd, void *mconfig, 
						const char *val) {
    return python_directive(cmd, mconfig, "PythonFixupHandler", val);
}
static const char *directive_PythonHandler(cmd_parms *cmd, void *mconfig, 
					   const char *val) {
    return python_directive(cmd, mconfig, "PythonHandler", val);
}
static const char *directive_PythonHeaderParserHandler(cmd_parms *cmd, void *mconfig, 
						       const char *val) {
    return python_directive(cmd, mconfig, "PythonHeaderParserHandler", val);
}
static const char *directive_PythonInitHandler(cmd_parms *cmd, void *mconfig,
					       const char *val) {
    return python_directive(cmd, mconfig, "PythonInitHandler", val);
}
static const char *directive_PythonHandlerModule(cmd_parms *cmd, void *mconfig,
					  const char *val) {
    return python_directive(cmd, mconfig, "PythonHandlerModule", val);
}
static const char *directive_PythonPostReadRequestHandler(cmd_parms *cmd, 
							  void * mconfig, 
							  const char *val) {
    return python_directive(cmd, mconfig, "PythonPostReadRequestHandler", val);
}
static const char *directive_PythonTransHandler(cmd_parms *cmd, void *mconfig, 
						const char *val) {
    return python_directive(cmd, mconfig, "PythonTransHandler", val);
}
static const char *directive_PythonTypeHandler(cmd_parms *cmd, void *mconfig, 
					       const char *val) {
    return python_directive(cmd, mconfig, "PythonTypeHandler", val);
}
static const char *directive_PythonLogHandler(cmd_parms *cmd, void *mconfig, 
					      const char *val) {
    return python_directive(cmd, mconfig, "PythonLogHandler", val);
}
static const char *directive_PythonInputFilter(cmd_parms *cmd, void *mconfig, 
					       const char *func, const char *name) {
    py_dir_config *conf;
 
    if (!name)
	name = apr_pstrdup(cmd->pool, func);

    conf = (py_dir_config *) mconfig;
    
    apr_table_set(conf->input_filters, name, func);
    
    /* remember the directory where the directive was found */
    if (conf->config_dir)
	apr_table_set(conf->input_filter_dirs, name, conf->config_dir);
    else 
	apr_table_set(conf->input_filter_dirs, name, "");

    /* register the filter NOTE - this only works so long as the
       directive is only allowed in the main config. For .htaccess we
       would have to make sure not to duplicate this */
    ap_register_input_filter(name, python_input_filter, AP_FTYPE_CONTENT);
 
    return NULL;
}

static const char *directive_PythonOutputFilter(cmd_parms *cmd, void *mconfig, 
						const char *func, const char *name) {
    py_dir_config *conf;
 
    if (!name)
	name = apr_pstrdup(cmd->pool, func);

    conf = (py_dir_config *) mconfig;
    
    apr_table_set(conf->output_filters, name, func);
    
    /* remember the directory where the directive was found */
    if (conf->config_dir)
	apr_table_set(conf->output_filter_dirs, name, conf->config_dir);
    else 
	apr_table_set(conf->output_filter_dirs, name, "");

    /* register the filter NOTE - this only works so long as the
       directive is only allowed in the main config. For .htaccess we
       would have to make sure not to duplicate this */
    ap_register_output_filter(name, python_output_filter, AP_FTYPE_CONTENT);
 
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
    PyThreadState *tstate;


#ifdef WITH_THREAD  
    PyEval_AcquireLock();
#endif
    
    idata = get_interpreter_data(NULL, NULL);

#ifdef WITH_THREAD
    PyEval_ReleaseLock();
#endif

    /* create thread state and acquire lock */
    tstate = PyThreadState_New(idata->istate);
#ifdef WITH_THREAD
    PyEval_AcquireThread(tstate);
#else
    PyThreadState_Swap(tstate);
#endif

    Py_Finalize();

#ifdef WITH_THREAD
    PyEval_ReleaseLock();
#endif

    return APR_SUCCESS;

}

/**
 ** Handlers
 **
 */

static void PythonChildInitHandler(apr_pool_t *p, server_rec *s)
{

    apr_array_header_t *ah;
    apr_table_entry_t *elts;
    PyObject *sys, *path, *dirstr;
    interpreterdata *idata;
    int i;
    const char *interpreter;
    PyThreadState *tstate;

    /*
     * Cleanups registered first will be called last. This will
     * end the Python enterpreter *after* all other cleanups.
     */

    apr_pool_cleanup_register(p, NULL, python_finalize, apr_pool_cleanup_null);

    /*
     * remember the pool in a global var. we may use it
     * later in server.register_cleanup()
     */
    child_init_pool = p;

    if (python_imports) {

	/* iterate throught the python_imports table and import all
	   modules specified by PythonImport */

	ah = apr_table_elts(python_imports);
	elts = (apr_table_entry_t *)ah->elts;
	for (i = 0; i < ah->nelts; i++) {
	
	    char *module = elts[i].key;
	    char *dir = elts[i].val;

	    /* Note: PythonInterpreter has no effect */
	    interpreter = dir;

#ifdef WITH_THREAD  
	    PyEval_AcquireLock();
#endif
    
	    idata = get_interpreter_data(interpreter, s);

#ifdef WITH_THREAD
	    PyEval_ReleaseLock();
#endif

	    if (!idata) {
		ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, s,
			     "ChildInitHandler: (PythonImport) get_interpreter_data returned NULL!");
		return;
	    }

	    /* create thread state and acquire lock */
	    tstate = PyThreadState_New(idata->istate);
#ifdef WITH_THREAD  
	    PyEval_AcquireThread(tstate);
#else
	    PyThreadState_Swap(tstate);
#endif

	    if (!idata->obcallback) {
		idata->obcallback = make_obcallback();
		/* we must have a callback object to succeed! */
		if (!idata->obcallback) {
		    ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, s,
				 "python_handler: get_obcallback returned no obCallBack!");

		    PyThreadState_Swap(NULL);
		    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
		    PyEval_ReleaseLock();
#endif
		    return;
		}
	    }
	
	    /* add dir to pythonpath if not in there already */
	    if (dir) {
		sys = PyImport_ImportModule("sys");
		path = PyObject_GetAttrString(sys, "path");
		dirstr = PyString_FromString(dir);
		if (PySequence_Index(path, dirstr) == -1) {
		    PyObject *list;
		    PyErr_Clear();
		    list = Py_BuildValue("[O]", dirstr);
		    PyList_SetSlice(path, 0, 0, list);
		    Py_DECREF(list);
		}
		Py_DECREF(dirstr);
		Py_DECREF(path);
		Py_DECREF(sys);
	    }

	    /* now import the specified module */
	    if (! PyImport_ImportModule(module)) {
		if (PyErr_Occurred())
		    PyErr_Print();
		ap_log_error(APLOG_MARK, APLOG_NOERRNO|APLOG_ERR, 0, s,
			     "directive_PythonImport: error importing %s", module);
	    }

	    PyThreadState_Swap(NULL);
	    PyThreadState_Delete(tstate);
#ifdef WITH_THREAD
	    PyEval_ReleaseLock();
#endif

	}
    }
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

    /* register the clean up directive handler */
    apr_pool_cleanup_register(req->pool, (void *)req, python_cleanup_handler, 
			      apr_pool_cleanup_null);

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
    AP_INIT_FLAG(
	"PythonDebug", directive_PythonDebug, NULL, OR_ALL,
	"Send (most) Python error output to the client rather than logfile."),
    AP_INIT_FLAG(
	"PythonEnablePdb", directive_PythonEnablePdb, NULL, OR_ALL,
	"Run handlers in pdb (Python Debugger). Use with -X."),
    AP_INIT_RAW_ARGS(
	"PythonFixupHandler", directive_PythonFixupHandler, NULL, OR_ALL,
	"Python fixups handlers."),
    AP_INIT_RAW_ARGS(
	"PythonHandler", directive_PythonHandler, NULL, OR_ALL,
	"Python request handlers."),
    AP_INIT_RAW_ARGS(
	"PythonHeaderParserHandler", directive_PythonHeaderParserHandler, NULL, OR_ALL,
	"Python header parser handlers."),
    AP_INIT_ITERATE(
	"PythonImport", directive_PythonImport, NULL, ACCESS_CONF,
	"Modules to be imported when this directive is processed."),
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
	"PythonTypeHandler", directive_PythonTypeHandler, NULL,	OR_ALL,
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
    python_merge_dir_config,       /* dir config merger */ 
    NULL,                          /* server config creator */ 
    NULL,                          /* server config merger */ 
    python_commands,               /* command table */ 
    python_register_hooks          /* register hooks */
};
    







