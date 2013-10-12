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
 * This file originally written by Stering Hughes
 *
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
    parser->dir = NULL;
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
    char     *dir = NULL;
    char     *path;
    psp_parser_t  *parser;
    yyscan_t scanner;
    FILE *f;

    if (!PyArg_ParseTuple(argv, "s|s", &filename, &dir)) {
        return NULL;
    }

    if (dir) {
        path = malloc(strlen(filename)+strlen(dir)+1);
        if (!path)
            return PyErr_NoMemory();
        strcpy(path, dir);
        strcat(path, filename);
    }
    else {
        path = filename;
    }

    Py_BEGIN_ALLOW_THREADS
    f = fopen(path, "rb");
    Py_END_ALLOW_THREADS

    if (f == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, path);
        if (dir) free(path);
        return NULL;
    }
    if (dir) free(path);

    parser = psp_parser_init();
    if (dir)
        parser->dir = dir;

    yylex_init(&scanner);
    yyset_in(f, scanner);
    yyset_extra(parser, scanner);
    yylex(scanner);
    yylex_destroy(scanner);

    fclose(f);
    psp_string_0(&parser->pycode);

    if (PyErr_Occurred()) {
        psp_parser_cleanup(parser);
        return NULL;
    }

    if (parser->pycode.blob) {
        code = PyBytes_FromString(parser->pycode.blob);
    }
    else {
        code = PyBytes_FromString("");
    }

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

    Py_BEGIN_ALLOW_THREADS
    parser = psp_parser_init();
    yylex_init(&scanner);
    yyset_extra(parser, scanner);

    bs = yy_scan_string(PyBytes_AsString(str), scanner);
    yylex(scanner);

    /* yy_delete_buffer(bs, scanner); */
    yylex_destroy(scanner);

    psp_string_0(&parser->pycode);
    Py_END_ALLOW_THREADS

    if (parser->pycode.blob) {
        code = PyBytes_FromString(parser->pycode.blob);
    }
    else {
        code = PyBytes_FromString("");
    }

    psp_parser_cleanup(parser);

    return code;
}

static PyMethodDef _psp_module_methods[] = {
    {"parse",       (PyCFunction) _psp_module_parse,       METH_VARARGS},
    {"parsestring", (PyCFunction) _psp_module_parsestring, METH_VARARGS},
    {NULL, NULL}
};

void init_psp(void)
{
    Py_InitModule("_psp", _psp_module_methods);
}
