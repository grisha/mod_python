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
 * Originally developed by Gregory Trubetskoy.
 *
 *
 * hlist.c 
 *
 * $Id: hlist.c,v 1.4 2003/09/10 02:11:22 grisha Exp $
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
                    const int s)
{
    hl_entry *hle;

    hle = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));

    hle->handler = apr_pstrdup(p, h);
    hle->directory = apr_pstrdup(p, d);
    hle->silent = s;

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
                       const char *d, const int s)
{
    hl_entry *nhle;

    /* find tail */
    while (hle && hle->next)
        hle = hle->next;

    nhle = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));

    nhle->handler = apr_pstrdup(p, h);
    nhle->directory = apr_pstrdup(p, d);
    nhle->silent = s;

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
    head->directory = apr_pstrdup(p, hle->directory);
    head->silent = hle->silent;

    hle = hle->next;
    nhle = head;
    while (hle) {
        nhle->next = (hl_entry *)apr_pcalloc(p, sizeof(hl_entry));
        nhle = nhle->next;
        nhle->handler = apr_pstrdup(p, hle->handler);
        nhle->directory = apr_pstrdup(p, hle->directory);
        nhle->silent = hle->silent;
        hle = hle->next;
    }

    return head;
}

