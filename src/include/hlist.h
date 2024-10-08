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
 * hlist.h
 *
 *
 * See accompanying documentation and source code comments
 * for details.
 *
 */

#ifndef Mp_HLIST_H
#define Mp_HLIST_H
#ifdef __cplusplus
extern "C" {
#endif

    /* handler list entry */
    typedef struct hl_entry {
        const char *handler;
        const char *directory; /* directory or location */
        ap_regex_t *regex;
        char d_is_fnmatch;
        char d_is_location;
        char silent;  /* 1 for PythonHandlerModule, where
                         if a handler is not found in a module,
                         no error should be reported */
        struct hl_entry *next;
    } hl_entry;

    hl_entry *hlist_new(apr_pool_t *p, const char *h, const char *d,
                        char d_is_fnmatch, char d_is_location,
                        ap_regex_t *regex, const char silent);
    hl_entry *hlist_append(apr_pool_t *p, hl_entry *hle, const char * h,
                           const char *d, char d_is_fnmatch, char d_is_location,
                           ap_regex_t *regex, const char silent);

    hl_entry *hlist_copy(apr_pool_t *p, const hl_entry *hle);
    void hlist_extend(apr_pool_t *p, hl_entry *hle1, const hl_entry *hle2);

#ifdef __cplusplus
}
#endif
#endif /* !Mp_HLIST_H */
