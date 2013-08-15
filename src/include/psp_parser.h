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
 */

#ifndef __PSP_PARSER_H
#define __PSP_PARSER_H

#include "psp_string.h"
#include <Python.h>

#define STATIC_STR(s) s, sizeof(s)-1

#define PSP_PG(v) (((psp_parser_t*)yyget_extra(yyscanner))->v)

typedef struct {
/*      PyObject   *files;   XXX removed until cache is fixed */
    psp_string  whitespace;     
    psp_string  pycode;
    char *      dir;
    unsigned    is_psp_echo : 1;
    unsigned    after_colon : 1;
    unsigned    seen_newline : 1;
} psp_parser_t;

#endif /* __PSP_PARSER_H */
