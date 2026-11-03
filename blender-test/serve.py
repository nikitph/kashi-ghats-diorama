import http.server, os, sys, urllib.parse
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.dirname(os.path.abspath(__file__))
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s,*a,**k): super().__init__(*a,directory=ROOT,**k)
    def do_POST(s):
        q=urllib.parse.parse_qs(urllib.parse.urlparse(s.path).query); name=os.path.basename(q['name'][0])
        n=int(s.headers['Content-Length']); open(os.path.join(OUT,name),'wb').write(s.rfile.read(n))
        s.send_response(200); s.end_headers(); s.wfile.write(b'ok')
http.server.ThreadingHTTPServer(('127.0.0.1',int(sys.argv[1]) if len(sys.argv)>1 else 8766),H).serve_forever()
