def application(environ, start_response):
    """WSGI Application"""
    start_response('200 OK', [('Content-type','text/html')])
    yield '<h2>WSGI environment variables</h2>\n<pre><code>'
    sorted_envs = environ.keys()[:]
    sorted_envs.sort()
    for k in sorted_envs:
        yield '{0:<24}: {1}\n'.format(k, environ[k])
    yield '</code></pre>'