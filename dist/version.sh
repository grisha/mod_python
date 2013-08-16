#!/bin/sh

MPV_PATH="`dirname $0`/../src/include/mp_version.h"

MAJ=`awk '/MP_VERSION_MAJOR/ {print $3}' $MPV_PATH`
MIN=`awk '/MP_VERSION_MINOR/ {print $3}' $MPV_PATH`
PCH=`awk '/MP_VERSION_PATCH/ {print $3}' $MPV_PATH`
GIT=`git describe --dirty --always`

echo $MAJ.$MIN.$PCH-$GIT
