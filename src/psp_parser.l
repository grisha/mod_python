%{
/*
 +----------------------------------------------------------------------------+
 | mod_psp - A python server pages preprocessor                               |
 +----------------------------------------------------------------------------+
 | Copyright (c) 2003 Sterling Hughes <sterling@php.net>                      |
 | Permission is hereby granted, free of charge, to any person obtaining a    |
 | copy of this software and associated documentation files (the "Software"), |
 | to deal in the Software without restriction, including without limitation  |
 | the rights to use, copy, modify, merge, publish, distribute, sublicense,   |
 | and/or sell copies of the Software, and to permit persons to whom the      |
 | Software is furnished to do so, subject to the following conditions:       |
 |                                                                            |
 | The above copyright notice and this permission notice shall be included in |
 | all copies or substantial portions of the Software.                        |
 |                                                                            |
 | THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR |
 | IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,   |
 | FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL    |
 | THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER |
 | LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING    |
 | FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER        |
 | DEALINGS IN THE SOFTWARE.                                                  |
 +----------------------------------------------------------------------------+
 | Authors: Sterling Hughes <sterling@php.net>                                |
 +----------------------------------------------------------------------------+
*/

#include "psp_parser.h"
#include <stdio.h>

#define OUTPUT_WHITESPACE(__wsstring) \
	psp_string_0((__wsstring)); \
	psp_string_append(&PSP_PG(pycode), (__wsstring)->blob)

#define CLEAR_WHITESPACE(__wsstring) psp_string_clear((__wsstring));

%}

%x IN_PYCODE
%x IN_STRING

%%

<IN_STRING>. {
	if (yytext[0] == '\\') {
		PSP_PG(is_string_escape) = 1;
	} else {
		if (yytext[0] == PSP_PG(string_char)) {
			if (!PSP_PG(is_string_escape)) {
				BEGIN IN_PYCODE;
			}
		}
		PSP_PG(is_string_escape) = 0;
	}
	
	psp_string_appendc(&PSP_PG(pycode), yytext[0]);
}

<IN_PYCODE>[\r\n] {
	psp_string_appendc(&PSP_PG(pycode), '\n');
}

<IN_PYCODE>"{" {
	psp_string_appendc(&PSP_PG(whitespace), '\t');
	psp_string_appendc(&PSP_PG(pycode), '\n');
	PSP_PG(in_block)++;
}

<IN_PYCODE>"}"([ ])* {
	CLEAR_WHITESPACE(&PSP_PG(whitespace));
	PSP_PG(in_block)--;
	if (PSP_PG(in_block) < 0) {
		PSP_PG(in_block) = 0;
	}
}

<IN_PYCODE>. {
	if (yytext[0] == '"' || yytext[0] == '\'') {
		PSP_PG(string_char) = yytext[0];
		BEGIN IN_STRING;
	}
	psp_string_appendc(&PSP_PG(pycode), yytext[0]);
}

<IN_PYCODE>"?>" {
	if (PSP_PG(is_psp_echo)) {
		psp_string_appendl(&PSP_PG(pycode), STATIC_STR(")\n"));
		PSP_PG(is_psp_echo) = 0;
	} else {
		psp_string_appendc(&PSP_PG(pycode), '\n');
	}

	BEGIN 0;
}

"<?=" {
	if (PSP_PG(ob).length) {
		psp_string_0(&PSP_PG(ob));
		OUTPUT_WHITESPACE(&PSP_PG(whitespace));
		psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write(\""));
		psp_string_appendl(&PSP_PG(pycode), PSP_PG(ob).blob, PSP_PG(ob).length);
		psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\")\n"));
		psp_string_free(&PSP_PG(ob));
	}

	OUTPUT_WHITESPACE(&PSP_PG(whitespace));
	psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write("));
	PSP_PG(is_psp_echo) = 1;

	BEGIN IN_PYCODE;
}

("<?psp"|"<?")([ \t]|[\n\r]) {
	if (PSP_PG(ob).length) {
		psp_string_0(&PSP_PG(ob));
		OUTPUT_WHITESPACE(&PSP_PG(whitespace));
		psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write(\""));
		psp_string_appendl(&PSP_PG(pycode), PSP_PG(ob).blob, PSP_PG(ob).length);
		psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\")\n"));
		psp_string_free(&PSP_PG(ob));
	} 
	
	CLEAR_WHITESPACE(&PSP_PG(whitespace));

	BEGIN IN_PYCODE;
}

^[\t ]* {
	if (!PSP_PG(in_block)) {
		psp_string_clear(&PSP_PG(whitespace));
		psp_string_appendl(&PSP_PG(whitespace), yytext, yyleng);
	}
}

[\r\n] {
	if (PSP_PG(ob).length) {
		psp_string_0(&PSP_PG(ob));
		OUTPUT_WHITESPACE(&PSP_PG(whitespace));
		psp_string_appendl(&PSP_PG(pycode), STATIC_STR("req.write(\""));
		psp_string_appendl(&PSP_PG(pycode), PSP_PG(ob).blob, PSP_PG(ob).length);
		psp_string_appendl(&PSP_PG(pycode), STATIC_STR("\")\n"));
		psp_string_free(&PSP_PG(ob));
	} 

	if (!PSP_PG(in_block)) {
		CLEAR_WHITESPACE(&PSP_PG(whitespace));
	}
}

. {
	if (yytext[0] == '"') {
		psp_string_appendl(&PSP_PG(ob), STATIC_STR("\\\""));
	} else {
		psp_string_appendc(&PSP_PG(ob), yytext[0]);
	}
}

%%
