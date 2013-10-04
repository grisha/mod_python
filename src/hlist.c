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
 * Originally developed by Gregory Trubetskoy.
 *
 *
 * hlist.c
 *
 *
 * See accompanying documentation and source code comments
 * for details.
 *
 */

#include "mod_python.h"

/**
 ** hlist_new
 **
 *  Start a new list.
 */

hl_entry *hlist_new(apr_pool_t *p, const char *h, const char *d,
                    char d_is_fnmatch, char d_is_location,
                    ap_regex_t *regex, const char silent)

{
    hl_entry *hle;

    hle = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));

    hle->handler = h;
    hle->directory = d;
    hle->d_is_fnmatch = d_is_fnmatch;
    hle->d_is_location = d_is_location;
    hle->regex = regex;
    hle->silent = silent;

    return hle;
}

/**
 ** hlist_append
 **
 *  Appends an hl_entry to a list identified by hle,
 *  and returns the new tail. This func will skip
 *  to the tail of the list.
 *  If hle is NULL, a new list is created.
 */

hl_entry *hlist_append(apr_pool_t *p, hl_entry *hle, const char * h,
                       const char *d, char d_is_fnmatch, char d_is_location,
                       ap_regex_t *regex, const char silent)

{
    hl_entry *nhle;

    /* find tail */
    while (hle && hle->next)
        hle = hle->next;

    nhle = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));

    nhle->handler = h;
    nhle->directory = d;
    nhle->d_is_fnmatch = d_is_fnmatch;
    nhle->d_is_location = d_is_location;
    nhle->regex = regex;
    nhle->silent = silent;

    if (hle)
        hle->next = nhle;

    return nhle;
}

/**
 ** hlist_copy
 **
 */

hl_entry *hlist_copy(apr_pool_t *p, const hl_entry *hle)
{
    hl_entry *nhle;
    hl_entry *head;

    head = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));
    head->handler = hle->handler;
    head->directory = hle->directory;
    head->d_is_fnmatch = hle->d_is_fnmatch;
    head->d_is_location = hle->d_is_location;
    head->regex = hle->regex;
    head->silent = hle->silent;

    hle = hle->next;
    nhle = head;
    while (hle) {
        nhle->next = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));
        nhle = nhle->next;
        nhle->handler = hle->handler;
        nhle->directory = hle->directory;
        nhle->d_is_fnmatch = hle->d_is_fnmatch;
        nhle->d_is_location = hle->d_is_location;
        nhle->regex = hle->regex;
        hle = hle->next;
    }

    return head;
}

/**
 ** hlist_extend
 **
 */

void hlist_extend(apr_pool_t *p, hl_entry *hle1,
                  const hl_entry *hle2)
{
    if (!hle2)
        return;

    /* find tail */
    while (hle1 && hle1->next)
        hle1 = hle1->next;

    while (hle2) {
        hle1->next = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));
        hle1 = hle1->next;
        hle1->handler = hle2->handler;
        hle1->directory = hle2->directory;
        hle1->d_is_fnmatch = hle2->d_is_fnmatch;
        hle1->d_is_location = hle2->d_is_location;
        hle1->regex = hle2->regex;
        hle1->silent = hle2->silent;
        hle2 = hle2->next;
    }
}

