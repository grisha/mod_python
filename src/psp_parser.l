%{
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
 * $Id: psp_parser.l,v 1.8 2003/05/30 15:10:46 grisha Exp $
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

%x TEXT
%x PYCODE
%x INDENT

%%

[\r\n] {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write(\"\"\"")); 

    yyless(0);
    BEGIN TEXT;
}

. {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write(\"\"\"")); 

    yyless(0);
    BEGIN TEXT;
}

<TEXT>"<%=" {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\"\"\"); req.write(str("));
    PSP_PG(is_psp_echo) = 1;

    BEGIN PYCODE;
}

<TEXT>"<%" {
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\"\"\")")); 
    CLEAR_WHITESPACE(&PSP_PG(whitespace)); 
    PSP_PG(seen_newline) = 0;
    BEGIN PYCODE;
}

<TEXT>[\r\n] {
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
    psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\"\"\")\n"));
    yyterminate();
}

<PYCODE>[\r\n] {
    psp_string_appendc(&PSP_PG(pycode), '\n');
        
    PSP_PG(seen_newline) = 1;
    BEGIN INDENT;
}

<PYCODE>"%>" {

    if (PSP_PG(is_psp_echo)) {
        psp_string_appendl(&PSP_PG(pycode), STATIC_STR(")); req.write(\"\"\""));
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

<INDENT>[\r\n] {
    CLEAR_WHITESPACE(&PSP_PG(whitespace)); 
    yyless(0);
    BEGIN PYCODE;
}

<INDENT>. {
    CLEAR_WHITESPACE(&PSP_PG(whitespace)); 
    yyless(0);
    BEGIN PYCODE;
}

%%

/* this is for emacs
Local Variables:
mode:C
End:
*/
