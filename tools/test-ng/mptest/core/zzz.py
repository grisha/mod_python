"""This module contains tests which should be run after all other tests.
Typically this might be done to examine the error log for evidence
of error conditions such as segmentation faults.

We want these tests to run after all other tests, hence the name zzz.py

"""

import os

from mptest.httpdconf import *
from mptest.testconf import * 
from mptest.testsetup import register, apache_version
from mptest.util import findUnusedPort

class SegmentationFaultTest(PerRequestTestBase):
    """Scans the error log and looks for evidence of a segmentation fault.
    This test does not make an http request, and does not require httpd 
    to be running."""
    
    disable = False # set disable = True to disable this test

    def runTest(self):
        """SegmentationFaultTest: scan log for 'Segmentation fault'"""
         #'child pid 2711 exit signal Segmentation fault (11)'
        
        error_log = os.path.join(self.httpd.server_root,self.httpd.error_log)

        print "\n  * Testing", self.shortDescription()


        f = open(error_log)
        # for some reason re doesn't like \n, why?
        import string
        log = "".join(map(string.strip, f.readlines()))
        f.close()

        if re.search("Segmentation fault", log):
            self.fail("'Segmentation fault' found in error_log")    

register(SegmentationFaultTest)


