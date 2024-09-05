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
 * Originally developed by Gregory Trubetskoy.
 *
 *
 *
 * See accompanying documentation and source code comments
 * for details.
 *
 */

#include "psp_string.h"

#define psp_string_alloc(__pspstring, __length) \
        if ((__length) > (__pspstring)->allocated) { \
                (__pspstring)->blob = realloc((__pspstring)->blob, (__length) + PSP_STRING_BLOCK); \
                (__pspstring)->allocated = (__length) + PSP_STRING_BLOCK; \
        }

void
psp_string_0(psp_string *s)
{
        if (!s->length) {
                return;
        }

        s->blob[s->length] = '\0';
}

void
psp_string_appendl(psp_string *s, char *text, size_t length)
{
        int newlen = s->length + length;

        if (text == NULL) {
                return;
        }

        psp_string_alloc(s, newlen);
        memcpy(s->blob + s->length, text, length);
        s->length = newlen;
}

void
psp_string_append(psp_string *s, char *text)
{
        if (text == NULL) {
                return;
        }
        psp_string_appendl(s, text, strlen(text));
}

void
psp_string_appendc(psp_string *s, char c)
{
        int newlen = s->length + 1;

        psp_string_alloc(s, newlen);
        s->blob[s->length] = c;
        s->length = newlen;
}

void
psp_string_clear(psp_string *s)
{
        memset(s->blob, 0, s->length);
        s->length = 0;
}

void
psp_string_free(psp_string *s)
{
        free(s->blob);
        s->blob = NULL;
        s->length = 0;
        s->allocated = 0;
}
