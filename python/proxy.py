#!/usr/bin/env python3
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path == "/favicon.ico":
            print(self.path)
            if uri := file_to_vscode_link(self.path):
                subprocess.run(["open", uri])
            elif uri := github_to_vscode_link(self.path):
                subprocess.run(["open", uri])
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            bytes(
                "Handled by proxy. This tab should have been closed automatically.",
                "utf8",
            )
        )
        return


REPO_PATHS = {
    "proxy": "/Users/dan/src/devenv/tools/python",
    "sdk-core": "/Users/dan/src/temporalio/sdk-python/temporalio/bridge/sdk-core",
    "tonic": "/Users/dan/tmp/3p/tonic",
}


def file_to_vscode_link(path: str) -> Optional[str]:
    if path.startswith("/file/"):
        if repo := get_repo(path.removeprefix("/file/")):
            focus_vscode_workspace(repo)
        return f"vscode-insiders://{path}"


def get_repo(path: str) -> Optional[str]:
    for repo, dir in REPO_PATHS.items():
        if path.startswith(dir):
            return repo


def github_to_vscode_link(url: str) -> Optional[str]:
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
