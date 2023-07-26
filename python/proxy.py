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
    "3p": "/Users/dan/tmp/3p",
    "bin": "/Users/dan/src/devenv/bin",
    "cli": "/Users/dan/src/temporalio/cli",
    "delta": "/Users/dan/src/delta",
    "devenv": "/Users/dan/src/devenv",
    "docker-builds": "/Users/dan/src/temporalio/docker-builds",
    "docker-compose": "/Users/dan/src/temporalio/docker-compose",
    "features-lite": "/Users/dan/src/temporalio/features-lite",
    "features": "/Users/dan/src/temporalio/features",
    "global-namespace-sdk-experiments": "/Users/dan/src/temporalio/global-namespace-sdk-experiments",
    "log-view": "/Users/dan/src/temporalio/log-view",
    "mathematics": "/Users/dan/src/mathematics",
    "misc-python": "/Users/dan/src/misc-python",
    "notes": "/Users/dan/src/temporalio/notes",
    "nushell-config": "/Users/dan/src/devenv/nushell-config",
    "pm": "/Users/dan/src/pm",
    "proxy": "/Users/dan/src/devenv/tools/python",
    "python-demo": "/Users/dan/src/temporalio/python-demo",
    "samples-java": "/Users/dan/src/temporalio/samples-java",
    "sdk-core": "/Users/dan/src/temporalio/sdk-python/temporalio/bridge/sdk-core",
    "sdk-dotnet-bridge": "/Users/dan/src/temporalio/sdk-dotnet/src/Temporalio/Bridge",
    "sdk-dotnet": "/Users/dan/src/temporalio/sdk-dotnet",
    "sdk-go": "/Users/dan/src/temporalio/sdk-go",
    "sdk-java": "/Users/dan/src/temporalio/sdk-java",
    "sdk-python-bridge": "/Users/dan/src/temporalio/sdk-python/temporalio/bridge",
    "sdk-python": "/Users/dan/src/temporalio/sdk-python",
    "sdk-typescript-bridge": "/Users/dan/src/temporalio/sdk-typescript/packages/core-bridge",
    "sdk-typescript": "/Users/dan/src/temporalio/sdk-typescript",
    "server": "/Users/dan/src/temporalio/docker-builds/temporal",
    "shell-config": "/Users/dan/src/devenv/shell-config",
    "src": "/Users/dan/src",
    "swimlanesio-links": "/Users/dan/src/swimlanesio-links",
    "temporal-cli": "/Users/dan/src/temporalio/cli",
    "temporal-docker-builds": "/Users/dan/src/temporalio/docker-builds",
    "temporal-docker-compose": "/Users/dan/src/temporalio/docker-compose",
    "temporal-features-lite": "/Users/dan/src/temporalio/features-lite",
    "temporal-features": "/Users/dan/src/temporalio/features",
    "temporal-log-view": "/Users/dan/src/temporalio/temporal-log-view",
    "temporal-notes": "/Users/dan/src/temporalio/notes",
    "temporal-python-demo": "/Users/dan/src/temporalio/python-demo",
    "temporal-samples-java": "/Users/dan/src/temporalio/samples-java",
    "temporal-sdk-core": "/Users/dan/src/temporalio/sdk-python/temporalio/bridge/sdk-core",
    "temporal-sdk-dotnet-bridge": "/Users/dan/src/temporalio/sdk-dotnet/src/Temporalio/Bridge",
    "temporal-sdk-dotnet": "/Users/dan/src/temporalio/sdk-dotnet",
    "temporal-sdk-go": "/Users/dan/src/temporalio/sdk-go",
    "temporal-sdk-java": "/Users/dan/src/temporalio/sdk-java",
    "temporal-sdk-python-bridge": "/Users/dan/src/temporalio/sdk-python/temporalio/bridge",
    "temporal-sdk-python": "/Users/dan/src/temporalio/sdk-python",
    "temporal-sdk-typescript-bridge": "/Users/dan/src/temporalio/sdk-typescript/packages/core-bridge",
    "temporal-sdk-typescript": "/Users/dan/src/temporalio/sdk-typescript",
    "temporal-server": "/Users/dan/src/temporalio/docker-builds/temporal",
    "temporalite": "/Users/dan/src/temporalio/temporalite",
    "tonic": "/Users/dan/tmp/3p/tonic",
    "tower": "/Users/dan/tmp/3p/tower",
    "twitch": "/Users/dan/src/twitch",
    "vscode-emacs-mcx": "/Users/dan/src/vscode-emacs-mcx",
    "vscode-etc": "/Users/dan/src/vscode-etc",
}


def file_to_vscode_link(path: str) -> Optional[str]:
    if path.startswith("/file/"):
        path = path.removeprefix("/file/")
        if repo := get_repo(path):
            focus_vscode_workspace(repo)
        return f"vscode-insiders://file/{path}"


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
