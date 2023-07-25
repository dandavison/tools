#!/usr/bin/env python3
import re
import ssl
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        uri = github_to_vscode_link(self.path)
        subprocess.run(["open", uri])
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # self.wfile.write(bytes("Redirected to VSCode", "utf8"))
        return


REPO_PATHS = {
    "sdk-core": "/Users/dan/src/temporalio/sdk-python/temporalio/bridge/sdk-core"
}


def github_to_vscode_link(url: str):
    print(url)
    regex = r"/([^/]+)/([^/]+)/blob/([^/]+)/(.*)#L(\d+)"
    assert (match := re.match(regex, url)), url
    user, repo, _commit, path, line = match.groups()
    repo_path = REPO_PATHS.get(repo, f"/Users/dan/src/{user}/{repo}")
    return f"vscode-insiders://file{repo_path}/{path}:{line}"


def run():
    [addr] = sys.argv[1:]
    host, port = addr.split(":")
    port = int(port)
    httpd = HTTPServer((host, port), RequestHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(
        "/Users/dan/.ssh/cert.pem",
        "/Users/dan/.ssh/key.pem",
    )
    httpd.socket = context.wrap_socket(
        httpd.socket,
        server_side=True,
    )
    print(f"Running server on http://{host}:{port}")
    httpd.serve_forever()


run()
