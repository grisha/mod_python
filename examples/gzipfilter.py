#
# Usage:
#   <Directory /where/ever>
#     PythonOutputFilter gzipfilter
#     SetOutputFilter gzipfilter
#   </Directory>

from mod_python import apache

import os
import sys
import gzip
import cStringIO
from   mod_python import apache

def compress(s):
    sio = cStringIO.StringIO()
    f = gzip.GzipFile(mode='wb',  fileobj=sio)
    f.write(s)
    f.close()
    return sio.getvalue()

def accepts_gzip(req):
    if req.headers_in.has_key('accept-encoding'):
        encodings = req.headers_in['accept-encoding']
        return (encodings.find("gzip") != -1)
    return 0

###
### main filter function
###
def outputfilter(filter):

    if (filter.req.main or
        not accepts_gzip(filter.req)):
        
        # Presense of filter.req.main tells us that
        # we are in a subrequest. We don't want to compress
        # the data more than once, so we pass_on() in
        # subrequests. We also pass_on() if the client
        # does not accept gzip encoding, of course.

        filter.pass_on()
    else:
        
        if not filter.req.sent_bodyct:

            # the above test allows us to set the encoding once
            # rather than every time the filter is invoked
            
            filter.req.headers_out['content-encoding'] = 'gzip'

        # loop through content, compressing

        s = filter.read()

        while s:
            s = compress(s)
            filter.write(s)
            s = filter.read()

        if s is None:

            # this means we received an EOS, so we pass it on
            # by closing the filter
            
            filter.close()




