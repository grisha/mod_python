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
 * This file originally written by Stering Hughes
 * 
 * $Id: _pspmodule.c,v 1.2 2003/05/29 20:52:25 grisha Exp $
 *
 * See accompanying documentation and source code comments for
 * details.
 *
 */

#include "psp_flex.h"
#include "psp_parser.h"
#include "psp_string.h"
#include "_pspmodule.h"
#include "Python.h"

/* calm down compile warning from psp_flex.h*/
static int yy_init_globals (yyscan_t yyscanner ) {return 0;};

static psp_parser_t *psp_parser_init(void)
{
    psp_parser_t *parser;

    parser = (psp_parser_t *) malloc(sizeof(*parser));

    memset(&parser->pycode, 0, sizeof(psp_string));
    memset(&parser->whitespace, 0, sizeof(psp_string));
    parser->is_psp_echo = 0;
    parser->after_colon = 0;
    parser->seen_newline = 0;

    return parser;
}

static void psp_parser_cleanup(psp_parser_t *parser)
{
    if (parser->pycode.allocated) {
        free(parser->pycode.blob);
    }
    
    if (parser->whitespace.allocated) {
        free(parser->whitespace.blob);
    }
    
    free(parser);
}

static PyObject * _psp_module_parse(PyObject *self, PyObject *argv)
{
    PyObject *code;
    char     *filename;
    psp_parser_t  *parser;
    yyscan_t scanner;
    FILE *f;
    
    if (!PyArg_ParseTuple(argv, "s", &filename)) {
        return NULL;
    }
    
    f = fopen(filename, "rb");
    
    if (f == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return NULL;
    }

    parser = psp_parser_init();

    yylex_init(&scanner);
    yyset_in(f, scanner);
    yyset_extra(parser, scanner);
    yylex(scanner);
    yylex_destroy(scanner);
    
    fclose(f);

    psp_string_0(&parser->pycode);
    code = PyString_FromString(parser->pycode.blob);

    psp_parser_cleanup(parser);
    
    return code; 
}

static PyObject * _psp_module_parsestring(PyObject *self, PyObject *argv)
{
    PyObject *code;
    PyObject *str;
    yyscan_t scanner;
    psp_parser_t  *parser;
    YY_BUFFER_STATE bs;

    if (!PyArg_ParseTuple(argv, "S", &str)) {
        return NULL;
    }

    parser = psp_parser_init();
    yylex_init(&scanner);
    yyset_extra(parser, scanner);

    bs = yy_scan_string(PyString_AsString(str), scanner);
    yylex(scanner);

    yy_delete_buffer(bs, scanner);
    yylex_destroy(scanner);
    
    psp_string_0(&parser->pycode);
    code = PyString_FromString(parser->pycode.blob);

    psp_parser_cleanup(parser);
    
    return code; 
}

struct PyMethodDef _psp_module_methods[] = {
    {"parse",       (PyCFunction) _psp_module_parse,       METH_VARARGS},
    {"parsestring", (PyCFunction) _psp_module_parsestring, METH_VARARGS},
    {NULL, NULL}
};

void init_psp(void)
{
    Py_InitModule("_psp", _psp_module_methods);
}
