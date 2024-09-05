/*
 * Copyright (C) 2000, 2001, 2013, 2024 Gregory Trubetskoy
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
 *
 */

#ifndef __PSP_STRING_H
#define __PSP_STRING_H

#include <stdlib.h>
#include <string.h>

#ifndef PSP_STRING_BLOCK
#define PSP_STRING_BLOCK 256
#endif

typedef struct {
        size_t allocated;
        size_t length;
        char        *blob;
} psp_string;

void psp_string_0(psp_string *);
void psp_string_appendl(psp_string *, char *, size_t);
void psp_string_append(psp_string *, char *);
void psp_string_appendc(psp_string *, char);
void psp_string_clear(psp_string *);
void psp_string_free(psp_string *);

#endif /* __PSP_STRING_H */
