
# mod_python tests

from mod_python import apache

TestFailed = "TestFailed"

def apache_log_error(req):

    apache.log_error("This is a test message")
    req.write("Just wrote something to log\n")

    return apache.OK

def apache_table(req):

    # tests borrowed from Python test quite for dict
    _test_table()

    # inheritance
    class mytable(apache.table):
        def __str__(self):
            return "str() from mytable"
    mt = mytable({'a':'b'})

    # add()
    a = apache.table({'a':'b'})
    a.add('a', 'c')
    if a['a'] != ['b', 'c']: raise TestFailed, 'table.add() broken: a["a"] is %s' % `a["a"]`

    req.write("test ok")
    return apache.OK

def req_add_common_vars(req):

    a = len(req.subprocess_env)
    req.add_common_vars()
    b = len(req.subprocess_env)
    if a >= b: raise TestFailed, 'req.subprocess_env() is same size before and after'
    
    req.write("test ok")
    return apache.OK

def req_add_handler(req):

    req.secret_message = "foo"
    req.add_handler("PythonHandler", "tests::simple_handler")

    return apache.OK

def simple_handler(req):
    # for req_add_handler()
    if (req.secret_message == "foo"):
        req.write("test ok")
        
    return apache.OK

def req_allow_methods(req):

    req.allow_methods(["PYTHONIZE"])
    return apache.HTTP_METHOD_NOT_ALLOWED

def req_get_basic_auth_pw(req):

    if (req.phase == "PythonAuthenHandler"):
        if req.user != "spam":
            return apache.HTTP_UNAUTHORIZED
    else:
        req.write("test ok")

    return apache.OK

def req_get_config(req):


    if req.get_config() == apache.table({"PythonDebug":"1"}) and \
       req.get_options() == apache.table({"secret":"sauce"}):
        req.write("test ok")

    return apache.OK

def req_get_remote_host(req):

    # simulating this test for real is too complex...

    if (req.get_remote_host(apache.REMOTE_HOST) == None) and \
       (req.get_remote_host() != ""):
        req.write("test ok")

    return apache.OK

def req_read(req):

    s = req.read()
    req.write(s)

    return apache.OK

def req_readline(req):

    s = req.readline()
    while s:
        req.write(s)
        s = req.readline()

    return apache.OK

def req_register_cleanup(req):

    req.cleanup_data = "test ok"
    req.register_cleanup(cleanup, req)
    req.write("registered cleanup that will write to log")

    return apache.OK

def cleanup(data):
    # for req_register_cleanup above

    data.log_error(data.cleanup_data)
    

def _test_table():

    d = apache.table()
    if d.keys() != []: raise TestFailed, '{}.keys()'
    if d.has_key('a') != 0: raise TestFailed, '{}.has_key(\'a\')'
    if ('a' in d) != 0: raise TestFailed, "'a' in {}"
    if ('a' not in d) != 1: raise TestFailed, "'a' not in {}"
    if len(d) != 0: raise TestFailed, 'len({})'
    d = {'a': 1, 'b': 2}
    if len(d) != 2: raise TestFailed, 'len(dict)'
    k = d.keys()
    k.sort()
    if k != ['a', 'b']: raise TestFailed, 'dict keys()'
    if d.has_key('a') and d.has_key('b') and not d.has_key('c'): pass
    else: raise TestFailed, 'dict keys()'
    if 'a' in d and 'b' in d and 'c' not in d: pass
    else: raise TestFailed, 'dict keys() # in/not in version'
    if d['a'] != 1 or d['b'] != 2: raise TestFailed, 'dict item'
    d['c'] = 3
    d['a'] = 4
    if d['c'] != 3 or d['a'] != 4: raise TestFailed, 'dict item assignment'
    del d['b']
    if d != {'a': 4, 'c': 3}: raise TestFailed, 'dict item deletion'
    # dict.clear()
    d = apache.table()
    d['1'] = '1'
    d['2'] = '2'
    d['3'] = '3'
    d.clear()
    if d != apache.table(): raise TestFailed, 'dict clear'
    # dict.update()
    d.update({'1':'100'})
    d.update({'2':'20'})
    d.update({'1':'1', '2':'2', '3':'3'})
    if d != apache.table({'1':'1', '2':'2', '3':'3'}): raise TestFailed, 'dict update'
    d.clear()
    try: d.update(None)
    except AttributeError: pass
    else: raise TestFailed, 'dict.update(None), AttributeError expected'
    class SimpleUserDict:
        def __init__(self):
            self.d = {1:1, 2:2, 3:3}
        def keys(self):
            return self.d.keys()
        def __getitem__(self, i):
            return self.d[i]
    d.update(SimpleUserDict())
    if d != apache.table({1:1, 2:2, 3:3}): raise TestFailed, 'dict.update(instance)'
    d.clear()
    class FailingUserDict:
        def keys(self):
            raise ValueError
    try: d.update(FailingUserDict())
    except ValueError: pass
    else: raise TestFailed, 'dict.keys() expected ValueError'
    class FailingUserDict:
        def keys(self):
            class BogonIter:
                def __iter__(self):
                    raise ValueError
            return BogonIter()
    try: d.update(FailingUserDict())
    except ValueError: pass
    else: raise TestFailed, 'iter(dict.keys()) expected ValueError'
    class FailingUserDict:
        def keys(self):
            class BogonIter:
                def __init__(self):
                    self.i = 1
                def __iter__(self):
                    return self
                def next(self):
                    if self.i:
                        self.i = 0
                        return 'a'
                    raise ValueError
            return BogonIter()
        def __getitem__(self, key):
            return key
    try: d.update(FailingUserDict())
    except ValueError: pass
    else: raise TestFailed, 'iter(dict.keys()).next() expected ValueError'
    class FailingUserDict:
        def keys(self):
            class BogonIter:
                def __init__(self):
                    self.i = ord('a')
                def __iter__(self):
                    return self
                def next(self):
                    if self.i <= ord('z'):
                        rtn = chr(self.i)
                        self.i += 1
                        return rtn
                    raise StopIteration
            return BogonIter()
        def __getitem__(self, key):
            raise ValueError
    try: d.update(FailingUserDict())
    except ValueError: pass
    else: raise TestFailed, 'dict.update(), __getitem__ expected ValueError'
    # dict.copy()
    d = {1:1, 2:2, 3:3}
    if d.copy() != {1:1, 2:2, 3:3}: raise TestFailed, 'dict copy'
    if apache.table().copy() != apache.table(): raise TestFailed, 'empty dict copy'
    # dict.get()
    d = apache.table()
    if d.get('c') is not None: raise TestFailed, 'missing {} get, no 2nd arg'
    if d.get('c', '3') != '3': raise TestFailed, 'missing {} get, w/ 2nd arg'
    d = apache.table({'a' : '1', 'b' : '2'})
    if d.get('c') is not None: raise TestFailed, 'missing dict get, no 2nd arg'
    if d.get('c', '3') != '3': raise TestFailed, 'missing dict get, w/ 2nd arg'
    if d.get('a') != '1': raise TestFailed, 'present dict get, no 2nd arg'
    if d.get('a', '3') != '1': raise TestFailed, 'present dict get, w/ 2nd arg'
    # dict.setdefault()
    d = apache.table()
    d.setdefault('key0')
    if d.setdefault('key0') is not "":
        raise TestFailed, 'missing {} setdefault, no 2nd arg'
    if d.setdefault('key0') is not "":
        raise TestFailed, 'present {} setdefault, no 2nd arg'
    # dict.popitem()
    for copymode in -1, +1:
        # -1: b has same structure as a
        # +1: b is a.copy()
        for log2size in range(12):
            size = 2**log2size
            a = apache.table()
            b = apache.table()
            for i in range(size):
                a[`i`] = str(i)
                if copymode < 0:
                    b[`i`] = str(i)
            if copymode > 0:
                b = a.copy()
            for i in range(size):
                ka, va = ta = a.popitem()
                if va != ka: raise TestFailed, "a.popitem: %s" % str(ta)
                kb, vb = tb = b.popitem()
                if vb != kb: raise TestFailed, "b.popitem: %s" % str(tb)
                if copymode < 0 and ta != tb:
                    raise TestFailed, "a.popitem != b.popitem: %s, %s" % (
                        str(ta), str(tb))
            if a: raise TestFailed, 'a not empty after popitems: %s' % str(a)
            if b: raise TestFailed, 'b not empty after popitems: %s' % str(b)

