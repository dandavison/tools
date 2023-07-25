#!/usr/bin/env python3
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path == "/favicon.ico":
            if uri := github_to_vscode_link(self.path):
                subprocess.run(["open", uri])
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("Redirected to VSCode", "utf8"))
        return


REPO_PATHS = {
    "sdk-core": "/Users/dan/src/temporalio/sdk-python/temporalio/bridge/sdk-core",
    "tonic": "/Users/dan/tmp/3p/tonic",
}


def github_to_vscode_link(url: str) -> Optional[str]:
    print(url)
    regex = r"/([^/]+)/([^/]+)/blob/([^/]+)/([^?]*)(?:\?line=(\d+))?"
    if match := re.match(regex, url):
        user, repo, _commit, path, line = match.groups()
        print(path, line)
        focus_vscode_workspace(repo)
        repo_path = REPO_PATHS.get(repo, f"/Users/dan/tmp/3p/{repo}")
        url = f"vscode-insiders://file{repo_path}/{path}"
        if line:
            url += f":{line}"
        return url
    else:
        print(f"No match:\n{regex}\n{url}")


def focus_vscode_workspace(workspace: str):
    # GPT
    lua_code = f"""
    print('Searching for window matching "{workspace}"')
    local function is_vscode_with_workspace(window)
        if string.find(window:application():title(), 'Code', 1, true) then
            print(window:title())
            return string.find(window:title(), '{workspace}', 1, true)
        end
    end

    for _, window in pairs(hs.window.allWindows()) do
        if is_vscode_with_workspace(window) then
            print('Found matching window: ' .. window:title())
            window:focus()
            break
        end
    end
    """
    result = subprocess.run(["hs", "-c", lua_code], stdout=subprocess.PIPE)
    print(f"{result.stdout.decode('utf-8')}", file=sys.stderr)


def run():
    [addr] = sys.argv[1:]
    host, port = addr.split(":")
    port = int(port)
    httpd = HTTPServer((host, port), RequestHandler)
    print(f"Running server on http://{host}:{port}")
    httpd.serve_forever()


run()
