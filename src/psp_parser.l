%{
/*
 * Copyright 2004 Apache Software Foundation 
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
 * $Id$
 *
 * This file originally written by Sterling Hughes.
 * 
 */

/* NOTE The seemingly unusual generated Python code (sometime using
 * ";" to separate statements, newline placement, etc) is such that
 * for vast majority of cases the line number of the input file will
 * match the line number of the output!
 */

#include "psp_parser.h"

#define OUTPUT_WHITESPACE(__wsstring) \
        psp_string_0((__wsstring)); \
        psp_string_append(&PSP_PG(pycode), (__wsstring)->blob)

#define CLEAR_WHITESPACE(__wsstring) psp_string_clear((__wsstring));

%}

%option noyywrap nounistd

%x TEXT
%x PYCODE
%x INDENT
%x DIR
%x COMMENT

%%

\r\n|\n {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write(\"\"\"")); 

    yyless(0);
    BEGIN TEXT;
}

. {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write(\"\"\"")); 

    yyless(0);
    BEGIN TEXT;
}

<TEXT>"\\n" {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\\\\n"));
}

<TEXT>"\\r" {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\\\\r"));
}

<TEXT>"\\t" {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\\\\t"));
}

<TEXT>"<%=" {    /* expression */
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\"\"\",0); req.write(str("));
    PSP_PG(is_psp_echo) = 1;

    BEGIN PYCODE;
}

<TEXT>"<%" {     /* python code */
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\"\"\",0);")); 
    CLEAR_WHITESPACE(&PSP_PG(whitespace)); 
    PSP_PG(seen_newline) = 0;
    BEGIN PYCODE;
}

<TEXT>"<%@" {     /* directive */
    BEGIN DIR;
}

<TEXT>"<%--" {    /* comment */
    BEGIN COMMENT;
}

<TEXT>\r\n|\n {
    psp_string_appendc(&PSP_PG(pycode), '\n');
}

<TEXT>. {
    if (yytext[0] == '"') {
        psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\\\""));
    } else {
        psp_string_appendc(&PSP_PG(pycode), yytext[0]);
    }
}

<TEXT><<EOF>> {
    yypop_buffer_state(yyscanner);
    if (!YY_CURRENT_BUFFER) {
        /* this is really the end */
        psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\"\"\",0)\n"));
        yyterminate();
    }
    else {
        /* we are inside include, continue scanning */
        BEGIN DIR;
    }
}

<PYCODE>\r\n|\n|\r {
    psp_string_appendc(&PSP_PG(pycode), '\n');
        
    PSP_PG(seen_newline) = 1;
    BEGIN INDENT;
}

<PYCODE>"%>" {

    if (PSP_PG(is_psp_echo)) {
        psp_string_appendl(&PSP_PG(pycode), STATIC_STR("),0); req.write(\"\"\""));
        PSP_PG(is_psp_echo) = 0;
    } 
    else {
        if (!PSP_PG(seen_newline)) {
            /* this will happen is you have <%%> */
            psp_string_appendc(&PSP_PG(pycode), ';');
        }

        if (PSP_PG(after_colon)) {
            /* this is dumb mistake-proof measure, if %> 
               is immediately following where there should be an indent */
            psp_string_appendc(&PSP_PG(whitespace), '\t');
            PSP_PG(after_colon) = 0;
        }
        OUTPUT_WHITESPACE(&PSP_PG(whitespace));
        psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write(\"\"\""));
    }
    
    BEGIN TEXT;
}

<PYCODE>":" {
    psp_string_appendc(&PSP_PG(pycode), yytext[0]);
    PSP_PG(after_colon) = 1;
}

<PYCODE>. {
    psp_string_appendc(&PSP_PG(pycode), yytext[0]);
    PSP_PG(after_colon) = 0;
}

<INDENT>^[\t ]* {

    CLEAR_WHITESPACE(&PSP_PG(whitespace)); 
    psp_string_appendl(&PSP_PG(whitespace), yytext, yyleng);
    psp_string_appendl(&PSP_PG(pycode), yytext, yyleng);

    BEGIN PYCODE;
}

<INDENT>"%>" {
    yyless(0);
    BEGIN PYCODE;
}

<INDENT>\r\n|\n {
    CLEAR_WHITESPACE(&PSP_PG(whitespace)); 
    yyless(0);
    BEGIN PYCODE;
}

<INDENT>. {
    CLEAR_WHITESPACE(&PSP_PG(whitespace)); 
    yyless(0);
    BEGIN PYCODE;
}

<DIR>"include"[ ]+"file"[ ]?=[ ]?"\""[^ ]+"\"" {

    char *filename;
    char *path;
    FILE *f;

    /* find a quote */
    filename = strchr(yytext, '"') + 1;
    filename[strchr(filename, '"')-filename] = '\0';

    /* XXX The absolute path check won't work on Windows,
     * needs to be corrected
     */

    if (PSP_PG(dir) && filename[0] != '/') {
        path = malloc(strlen(filename)+strlen(PSP_PG(dir))+1);
        if (path == NULL) {
            PyErr_NoMemory();
            yyterminate();
        }
        strcpy(path, PSP_PG(dir));
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
    }
    else {
        yypush_buffer_state(yy_create_buffer(f, YY_BUF_SIZE, yyscanner), 
                            yyscanner);
        BEGIN(TEXT);
    }

    if (PSP_PG(dir)) free(path);
}

<DIR>"%>" {
    BEGIN TEXT;
}

<COMMENT>"--%>" {
    BEGIN TEXT;
}

%%

/* this is for emacs
Local Variables:
mode:C
End:
*/
