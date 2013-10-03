
import sys

def application(env, start_response):
   status = '200 OK'
   output = 'test fail\n'

   try:
      assert(env['wsgi.input'].__class__.__name__ == 'mp_request')
      assert(env['wsgi.errors'] == sys.stderr)
      assert(env['wsgi.version'] == (1,0))
      assert(env['wsgi.multithread'] in (True, False))
      assert(env['wsgi.multiprocess'] in (True, False))
      assert(env['wsgi.url_scheme'] == 'http')
      assert(env['SCRIPT_NAME'] == '')
      assert(env['PATH_INFO'] == '/tests.py')
      output = 'test ok\n'
   except:
      pass

   env['wsgi.errors'].write('written_from_wsgi_test\n')
   env['wsgi.errors'].flush()

   response_headers = [('Content-type', 'text/plain'),
                       ('Content-Length', str(len(output)))]
   start_response(status, response_headers)

   return [output]


