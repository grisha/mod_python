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
 * $Id: psp_interface.c,v 1.2 2003/05/24 03:55:27 grisha Exp $
 *
 * See accompanying documentation and source code comments 
 * for details.
 *
 */

#include "mod_python.h"
#include "httpd.h"
#include <stdio.h>

static psp_parser_t*
psp_parser_init(void)
{
    psp_parser_t *parser;

    parser = (psp_parser_t *) malloc(sizeof(*parser));

    memset(&parser->ob, 0, sizeof(psp_string));
    memset(&parser->pycode, 0, sizeof(psp_string));
    memset(&parser->whitespace, 0, sizeof(psp_string));
    parser->in_block = 0;
    parser->string_char = 0;
    parser->is_psp_echo = 0;
    parser->is_string_escape = 0;

    return parser;
}

static void
psp_parser_cleanup(psp_parser_t *parser)
{
    if (parser->ob.allocated) {
        free(parser->ob.blob);
    }

    if (parser->pycode.allocated) {
        free(parser->pycode.blob);
    }

    if (parser->whitespace.allocated) {
        free(parser->whitespace.blob);
    }

    free(parser);
}

static char *
psp_parser_gen_pycode(psp_parser_t *parser, char *filename)
{ 
    yyscan_t scanner;
    FILE *f;
     
    f = fopen(filename, "rb");
    if (f == NULL) {
        return NULL;
    }

    yylex_init(&scanner);
    yyset_in(f, scanner);
    yyset_extra(parser, scanner);
    yylex(scanner);
    yylex_destroy(scanner);

    fclose(f);

    psp_string_0(&parser->pycode);

    return parser->pycode.blob;
}

struct psp_object {
	int mtime;
	PyObject *image;
};

static PyObject *
psp_parser_compile_file(char *filename)
{
	PyObject          *compiled = NULL;
	struct psp_object *cached;
	char              *code;
	struct stat        sb;
        psp_parser_t      *parser;

	if (stat(filename, &sb) != 0) {
		return NULL;
	}

/* XXX TODO - Make cache work, but in a thread-safe way
/* 	cached = (struct psp_object *) PyDict_GetItemString(parser->files, filename); */
/* 	if (cached != NULL) { */
/* 		if (sb.st_mtime == cached->mtime) { */
/* 			compiled = cached->image; */
/* 			goto psp_ret; */
/* 		} */
/* 	} */
	
	parser = psp_parser_init();
	code = psp_parser_gen_pycode(parser, filename);
	if (code == NULL) {
		return NULL;
	}
	compiled = Py_CompileString(code, filename, Py_file_input);
	psp_parser_cleanup(parser);

	cached = (struct psp_object *) malloc(sizeof(struct psp_object));
	cached->mtime = sb.st_mtime;
	cached->image = compiled;
	
/*	PyDict_SetItemString(parser->files, filename, (PyObject *) cached); */
psp_ret:
	return compiled;
}

PyObject *
_psp_module_parse(PyObject *self, PyObject *argv)
{
	PyObject *code;
	char     *filename;
	int       len;
	
	if (!PyArg_ParseTuple(argv, "s", &filename, &len)) {
		return;
	}

	code = psp_parser_compile_file(filename);
	if (code == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	}

	return code; 
}

struct PyMethodDef _psp_module_methods[] = {
	{"parse", (PyCFunction) _psp_module_parse, METH_VARARGS},
	{NULL, NULL}
};

void
_psp_module_init(void)
{
	Py_InitModule("_psp", _psp_module_methods);
}
