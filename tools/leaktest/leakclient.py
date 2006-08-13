#!/usr/bin/env python

import sys
import os
import time
import commands
import urllib
import httplib
from optparse import OptionParser
import ConfigParser


__version__ = '0.0.1'

class StopTest(Exception): pass
class HandlerError(Exception): pass

def leaktest(test_name, test_method,
             count=1000, log_dir='/tmp/leaktest',
             sleep=6, host='localhost',
             mem_limit=10.0, pmap=0,
             verbose=0):

    log_msg(log_dir, 'TEST %s: START;' % test_name)
    log_memory_usage(log_dir, test_name, 0)
    
    try:
        print >>sys.stderr, '%s leaktest' % name
        print >>sys.stderr, '    running ',
        for i in xrange(0, count):
            rsp = test_method(host)
            if verbose == 3:
                print >>sys.stderr, '\nRESPONSE:\n\n', rsp, '\n\nEND RESPONSE'
            if not rsp.startswith('ok %s:' % test_name):
                print >>sys.stderr,  i, 'error', rsp
                raise HandlerError, 'a problem occured with handler for %s' % test_name
            if (i % 100) == 0:
                sys.stderr.write('=')
                sys.stderr.flush()
            if (i % 1000) == 999:
                if pmap:
                    dump_memory_map(log_dir, test_name, i, verbose, detail=pmap)
                # check and make sure we are not exceeding 20% memory usage
                # as we don't want to crash the host
                mem_usage = get_memory_usage()
                log_memory_usage(log_dir, test_name, i + 1, mem_usage)
                if max(mem_usage.values()) > mem_limit:
                    log_msg('/tmp/leaktest',
                            'TEST %s: ERROR LEAK_DETECTED: memory limit (%0.2f %%) exceeded' % (test_name, mem_limit))

                    raise StopTest, 'apache memory limit exceeded'
                print >>sys.stderr, '    sleeping ',
                count_down = sleep
                while (count_down > 0):
                    time.sleep(2)
                    count_down = count_down - 2
                    sys.stderr.write('. ')
                    sys.stderr.flush()
                print >>sys.stderr, '\n    running ',
        status = 'PASS'
    except StopTest:
        print >>sys.stderr, ''
        print >>sys.stderr, 'Stopping test: memory limit %0.2f exceeded: completed %d requests' % (mem_limit, i + 1)
        print >>sys.stderr, ''
        status = 'FAIL'

    mem_usage = get_memory_usage()
    log_memory_usage(log_dir, test_name, i + 1, mem_usage)
    log_msg('/tmp/leaktest', 'TEST %s: END; REQUEST %d;' % (test_name, i + 1))
    print >>sys.stderr, '\n    completed', count, 'requests'
    return (status, i + 1, count, mem_usage)


def fieldstorage_leaktest(host='localhost'):
    body = urllib.urlencode([('spam', 'spam'*100), ('spam', 'spam'*100), ('eggs', 'eggs'*100), ('bacon', 'bacon'*100)])
    headers = {"Host": host,
               "Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}
    return request(host, "POST", "/mod_python/leaktests/fieldstorage/mptest.py", body)

def allow_methods_leaktest(host='localhost'):
    """ req.allow_methods 
    """
    return request(host, "GET", "/mod_python/leaktests/allow_methods/mptest.py")


def cfgtree_walk_leaktest(host='localhost'):
    return request(host, "GET", "/mod_python/leaktests/cfgtree_walk/mptest.py")

def fixup_leaktest(host='localhost'):
    """MODPYTHON-181
    """
    rsp = request(host, "GET", "/mod_python/leaktests/MODPYTHON-181/hello.py")
    return 'ok 181:'


def get_config_leaktest(host='localhost'):
    """Tests req.get_config() 
    """
    return request(host, "GET", "/mod_python/leaktests/get_config/mptest.py")


def get_options_leaktest(host='localhost'):
    """Tests req.get_options() 
    """
    return request(host, "GET", "/mod_python/leaktests/get_options/mptest.py")


def parse_qsl_leaktest(host='localhost'):
    params = urllib.urlencode([('spam', 'spam'*250), ('spam', 'spam'*250), ('eggs', 'eggs'*250), ('bacon', 'bacon'*250)])
    headers = {"Host": host,
               "Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}
    return request(host, "GET", "/mod_python/leaktests/parse_qsl/mptest.py?%s" % params, '', headers)

def parse_qs_leaktest(host='localhost'):
    params = urllib.urlencode([('spam', 'spam'*250), ('spam', 'spam'*250), ('eggs', 'eggs'*250), ('bacon', 'bacon'*250)])
    headers = {"Host": host,
               "Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}
    return request(host, "GET", "/mod_python/leaktests/parse_qs/mptest.py?%s" % params, '', headers)

def readline_leaktest(host='localhost'):
    """ This test is similar to readlines_leaktest, but the handler interates
    over the request body using req.readline instead of req.readlines().
    """
    
    body = []
    for i in xrange(0,1000):
        body.append('a'*1000)
    return request(host, "POST", "/mod_python/leaktests/readline/mptest.py", '\n'.join(body))

def readline_partial_leaktest(host='localhost'):
    """ This test is similar to readline_leaktest, but the does not read
    the whole request body.
    """
    
    body = []
    for i in xrange(0,100):
        body.append('a'*100)
    return request(host, "POST", "/mod_python/leaktests/readline_partial/mptest.py", '\n'.join(body))

def readlines_leaktest(host='localhost'):
    body = []
    for i in xrange(0,1000):
        body.append('a'*100)

    return request(host, "POST", "/mod_python/leaktests/readlines/mptest.py", '\n'.join(body))


def requires_leaktest(host='localhost'):
    """Tests req.requires() 
    """
    return request(host, "GET", "/mod_python/leaktests/requires/mptest.py")

def table_leaktest(host='localhost'):
    """Test apache.make_table()
    """
    return request(host, "GET", "/mod_python/leaktests/table/mptest.py")

def baseline_leaktest(host='localhost'):
    """ This is a simple request which should not leak and can be used
    to determine a memory baseline. The hander simply consists of
        def handler(req):
            req.content_type = 'text/plain'
            req.write('ok')
            return apache.OK
    """
    return request(host, "GET", "/mod_python/leaktests/baseline/mptest.py")

def debug_leaktest(host='localhost'):
    """This is used to debug the leaktest framework. It is not used
    to actually detect any memory leaks.
    """
    return request(host, "GET", "/mod_python/leaktests/debug/mptest.py")

def request(host, method='GET', url=None, body='', headers=None):
    req_headers = {"Host": host,
               "Accept": "text/plain"}

    if headers is not None:
        req_headers.update(headers)

    if url is None:
        raise Exception, 'url cannot be none'
        
    conn = httplib.HTTPConnection(host)
    conn.request(method, url, body, req_headers)
    response = conn.getresponse()
    rsp = response.read()
    conn.close()
    return rsp


def log_msg(path, msg):
    fout = open('%s/leaktest.log' % (path), 'a+')
    fout.write(str(msg))
    fout.write('\n')
    fout.close()

def log_memory_usage(path, test_name, count, mem_usage=None):
    if mem_usage is None:
        mem_usage = get_memory_usage()
    msg_parts = []
    processes = mem_usage.items()
    processes.sort()
    for pid,mem in processes:
        msg_parts.append('(%d, %0.1f)' % (pid, mem))
        
    msg = 'name: %s; requests: %d; memory: %s;' % (test_name, count, ', '.join(msg_parts))

    fout = open('%s/memory.log' % (path), 'a+')
    fout.write(str(msg))
    fout.write('\n')
    fout.close()



def dump_memory_map(log_dir, test_name, count, verbose=False, detail=0):

    if detail < 1:
        return

    if verbose:
        print >>sys.stderr, '\n    dumping memory (%d requests completed)...' % (count + 1)

    log_dir = '%s/%s'  % (log_dir, test_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    output = commands.getoutput('ps -u www-data')
    pid_list = []
    lines = [ line.strip() for line  in output.split('\n') ]
    for line in lines:
        pid = line.split()[0] 
        try:
            pid = int(pid)
            pid_list.append(pid)
        except:
            pass


    if detail == 1:
            cmd = r'pmap -d %d | grep "^mapped"'
    elif detail == 2:
            cmd = r'pmap -d %d | grep "python\|apache\|^mapped"'
    elif detail > 2:
            cmd = r'pmap -d %d'
     
    label = '%s: %d' % (test_name, count)
    for pid in pid_list:
        fout = open('%s/%d' % (log_dir, pid), 'a+')
        pmap = commands.getoutput(cmd % pid)

        if detail == 1:
            print >>fout, test_name, count, pmap 
        else:
            print >>fout, '-' * 60
            print >>fout,  label
            print >>fout, '-' * 60
            print >>fout, pmap
            print >>fout, ''
        
        fout.close()


def apache_restart(verbose=False):
    output = commands.getoutput('sudo /etc/init.d/apache2 restart')
    if verbose:
        print output
    else:
        print 'Restarting Apache'

def get_mp_version(host='127.0.0.1', port=80):
    headers = {"Host": host,
               "Accept": "text/plain"}
    conn = httplib.HTTPConnection(host)
    conn.request("GET", "/mod_python/leaktests/version/mptest.py", '', headers)
    response = conn.getresponse()
    rsp = response.read()
    conn.close()
    return rsp



def max_mem(src):
    mem = src.values()
    return max(mem)

def print_report_header(fout, mp_version, mem_limit, requests):
    print >>fout, '=' * 60
    print >>fout, 'Mod_python Memory Leak Test'
    print >>fout, '  mod_python version: %s' % mp_version
    print >>fout, '  requests attempted: %d' % requests
    print >>fout, '  memory maximum for failure condition: %0.1f%%' % mem_limit
    print >>fout, '=' * 60
    print >>fout, 'Test Name       Status   Requests      %Mem'
    print >>fout, '-' * 60


def print_result(fout, test_name, result):
    status, completed, desired, mem = result
    print >>fout, '%s %s %10d %10.1f' % (test_name.ljust(16), status, completed, max_mem(mem))

def get_memory_usage(pid=None):
    if not pid:
        cmd = 'top -b -u www-data -n 1 -d 1'
    else:
        cmd = 'top -b -u www-data -n 1 -d 1 -p%s' % pid

    output = commands.getoutput(cmd)
    lines = output.split('\n')
    data = [ line.split() for line in lines if line ]
    mem_usage = {} 
    for line in data:
        try:
            pid = int(line[0])
            mem = line[9]
            mem_usage[pid] =  float(mem)
        except:
            pass
    return mem_usage

if __name__ == '__main__':
    
    usage = "usage: %prog [options] [tests]"
    parser = OptionParser(usage=usage, version="%s" % __version__)
   
    # no config file handling just yet.
    # parser.add_option("-c", "--config", dest="config_file",
                      # metavar="FILE",
                      # help="Configuration file")

    parser.add_option("-a", 
                      action="store_true", dest="all_tests", default=False,
                      help="Run all tests (implies the -b option).")

    parser.add_option("-b", 
                      action="store_true", dest="do_baseline", default=False,
                      help="Run baseline test. The baseline test should not leak memory, "\
                           "so it is a useful for benchmark to compare with other tests.")

    parser.add_option("--host", 
                      dest="host", type="string", default='127.0.0.1',
                      help="Host name or ip address. Default is 127.0.0.1")


    parser.add_option("--port", 
                      dest="port", type="string", default='80',
                      help="Port. Default is 80. (Not currently implemented).")

    parser.add_option("--memory-limit", 
                      dest="mem_limit", type="float", default=10.0,
                      help="Memory (as % of total memory) which when reached "\
                           "will be considered a test failure. Default is 10.0%. "\
                           "The test will be terminated once any apache process "\
                           "reaches this limit. The default value of 10% assumes "\
                           "the initial mod_python memory footprint is < 2%. "\
                           "To determine a suitable value for --memory-limit run "\
                           "the baseline test first: "\
                           "  leaktest.py -b -n 100 " 
                      )

    parser.add_option("-n", 
                      dest="count", type="int", default=1000,
                      help="Number of requests to perform for benchmarking.")

    parser.add_option("-m", 
                      action="count", dest="pmap", default=0,
                      help="Dump memory map to log after every 1000 requests. "\
                           "Each Apache process gets it's own logfile. "\
                           "Requires the pmap program. Default is no logging. "\
                           "You can specify -m upto 3 times to get a greater level of detail. "\
                           "The informtion will be dumped to file 'log_dir/test_name/pid'")

    parser.add_option("-l", '--log-dir', 
                      dest="log_dir", type="string", default='/tmp/leaktest',
                      metavar="DIR",
                      help="Log directory for benchmark output. Default is /tmp/leaktest")

    parser.add_option("-r", "--report", 
                      dest="report_output", default=None,
                      metavar="FILE",
                      help="Output leaktest results to FILE. Default is to print to stdout. ")

    # parser.add_option("-o", "--output", 
                      # dest="output_report", default='leaktest-results.txt',
                      # metavar="FILE",
                      # help="Output leaktest results to FILE. Default is leaktest-results.txt")


    parser.add_option("--no-restart",
                      action="store_false", dest="restart", default=True,
                      help="Keeps Apache from restarting after each test. "\
                           "Generally you should let Apache restart, but you "\
                           "can suppress the normal behaviour with this option.")

    parser.add_option("-t", "--test-list",
                      action="store_true", dest="show_tests", default=False,
                      help="List available leak tests and exit.")

    parser.add_option("-s", "--sleep",
                      dest="sleep", type="int", default=2,
                      help="Sleep for SLEEP seconds after every 1000 requests."\
                           " Default is 2 seconds.")

 
    parser.add_option("-v", "--verbose", 
                      action="count", dest="verbose", default=0,
                      help="Increase verbosity. "\
                           "You can specify -v up to 3 times to get a greater level of detail. "\
                           "Using -v -v -v will cause the http response to be printed to stderr. "\
                           "The most verbose setting could result in a large amount of output and should "\
                           "likely be used in conjuction with -n 1.")

   

    # parser.add_option("-q", "--quiet",
                      # action="store_false", dest="verbose", default=True,
                      # help="don't print status messages to stdout")

    (options, args) = parser.parse_args()


    mem_limit = options.mem_limit
    sleep = options.sleep
    count = options.count
    
    host = options.host
    port = options.port

    mp_version = get_mp_version(host)

    tests = {'debug': (debug_leaktest, 'useful for debugging leakclient.py. Should not leak.'),
             'baseline': (baseline_leaktest, 'Establish a memory consumption baseline. This should not leak.'),  # This one should NOT leak
             'allow_methods': (allow_methods_leaktest, 'req.allow_methods()'),
             'cfgtree_walk': (cfgtree_walk_leaktest, 'apache.config_tree()'),
             'get_config': (get_config_leaktest, 'req.get_config()'),
             'get_options': (get_options_leaktest, 'req.get_options()'),
             'fieldstorage': (fieldstorage_leaktest, 'util.FieldStorage()'),
             '181': (fixup_leaktest, 'fixuphandler MODPYTHON-181'),
             'parse_qs': (parse_qs_leaktest,  '_apache.parse_qs()'),
             'parse_qsl': (parse_qsl_leaktest, '_apache.parse_qsl()'),
             'readline': (readline_leaktest, 'req.readline()'),
             'readline_partial': (readline_partial_leaktest, 'use req.readline() to read only part of the request'),
             'readlines': (readlines_leaktest, 'req.readlines()'),
             'table': (table_leaktest, 'apache.make_table()'),
            }

    if options.show_tests:
        # show the available tests and exit.
        test_list = tests.keys()
        test_list.sort()
        for t in test_list:
            print t.ljust(12), tests[t][1] 
        sys.exit()

    test_list = []
    if options.all_tests:
        test_list = tests.keys()
        test_list.remove('debug')

        # We want to run the baseline test first
        # The baseline request should NOT leak.
        test_list.remove('baseline')
        test_list.sort()
        test_list.insert(0, 'baseline')
    elif options.do_baseline:
        test_list = ['baseline', ]

    for arg in args:
        if arg not in tests:
            print 'unknown test', test_name
            sys.exit()
        elif arg not in test_list:
            test_list.append(arg)

    results = {}
    log_dir = options.log_dir
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    for name in test_list:
        if options.restart:
            apache_restart()
            log_msg(log_dir, 'APACHE RESTART')
        status = leaktest(name, tests[name][0], count, log_dir,
                          sleep=sleep, host=host, mem_limit=mem_limit, 
                          pmap=options.pmap, verbose=options.verbose)
        results[name] = status
    
    # restart apache in case the last test leaked.
    if options.restart:
        apache_restart()
        log_msg(log_dir, 'APACHE RESTART')

    tests_run = results.keys()

    
    if options.report_output:
        freport = open(options.report_output, 'w')
    else:
        freport = sys.stdout

    print_report_header(freport, mp_version, mem_limit, count)
        
    if 'baseline' in tests_run:
        tests_run.remove('baseline')
        print_result(freport, 'baseline', results['baseline'])

    tests_run.sort()
    for t in tests_run:
        print_result(freport, t, results[t])

    if options.report_output:
        # we don't want to close sys.stdout!
        freport.close()
