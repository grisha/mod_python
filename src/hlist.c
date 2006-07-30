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
 * Originally developed by Gregory Trubetskoy.
 *
 *
 * hlist.c 
 *
 * $Id$
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

hl_entry *hlist_new(apr_pool_t *p, const char *h, PyObject *o, const char *d, 
                    int d_is_fnmatch, ap_regex_t *regex, const int s,
                    hl_entry* parent)
{
    hl_entry *hle;

    hle = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));

    hle->handler = apr_pstrdup(p, h);
    hle->callable = o;
    hle->directory = apr_pstrdup(p, d);
    hle->d_is_fnmatch = d_is_fnmatch;
    hle->regex = regex;
    hle->silent = s;
    hle->parent = parent;

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
                       PyObject *o, const char *d, int d_is_fnmatch,
                       ap_regex_t *regex, const int s, hl_entry *parent)
{
    hl_entry *nhle;

    /* find tail */
    while (hle && hle->next)
        hle = hle->next;

    nhle = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));

    nhle->handler = apr_pstrdup(p, h);
    nhle->callable = o;
    nhle->directory = apr_pstrdup(p, d);
    nhle->d_is_fnmatch = d_is_fnmatch;
    nhle->regex = regex;
    nhle->silent = s;
    nhle->parent = parent;

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
    head->handler = apr_pstrdup(p, hle->handler);
    head->callable = hle->callable;
    head->directory = apr_pstrdup(p, hle->directory);
    head->d_is_fnmatch = hle->d_is_fnmatch;
    head->regex = hle->regex;
    head->silent = hle->silent;
    head->parent = hle->parent;

    hle = hle->next;
    nhle = head;
    while (hle) {
        nhle->next = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));
        nhle = nhle->next;
        nhle->handler = apr_pstrdup(p, hle->handler);
        nhle->callable = hle->callable;
        nhle->directory = apr_pstrdup(p, hle->directory);
        nhle->d_is_fnmatch = hle->d_is_fnmatch;
        nhle->regex = hle->regex;
        nhle->silent = hle->silent;
        nhle->parent = hle->parent;
        hle = hle->next;
    }

    return head;
}

