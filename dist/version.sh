#!/bin/sh

MPV_PATH="`dirname $0`/../src/include/mp_version.h"

MAJ=`awk '/MP_VERSION_MAJOR/ {print $3}' $MPV_PATH`
MIN=`awk '/MP_VERSION_MINOR/ {print $3}' $MPV_PATH`
PCH=`awk '/MP_VERSION_PATCH/ {print $3}' $MPV_PATH`

# if git exists in path
if type git >/dev/null 2>&1; then
    # and we are in a checkout
    if git rev-parse 2>/dev/null; then
        # but not on a tag (which means this is a release)
        if test -z "`git log 'HEAD^!' --format=%d 2>/dev/null | grep 'tag: '`"; then
            # append git revision hash to version
            GIT="-`git describe --always`"
        fi
    fi
fi

echo $MAJ.$MIN.$PCH$GIT
