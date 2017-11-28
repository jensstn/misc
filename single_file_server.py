#!/usr/bin/env python3

import argparse
import http.server
import os
import shutil
import sys

class HTTPServerWithBundle(http.server.HTTPServer):
    def __init__(self, server_address, requestHandlerClass, bundle):
        http.server.HTTPServer.__init__(self, server_address,
            requestHandlerClass)
        self.bundle = bundle

class SingleFileHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def __get_file(self, handle_file_func):
        file_path = self.server.bundle["file-path"]
        if file_path is not None:
            if self.path.strip(os.sep) == file_path.split(os.sep)[-1]:
                try:
                    with open(file_path, "rb") as f:
                        self.send_response(http.server.HTTPStatus.OK)
                        self.send_header("Content-type",
                            "application/octet-stream; charset=utf8")
                        self.end_headers()
                        handle_file_func(f)
                except FileNotFoundError as e:
                    self.send_error(http.server.HTTPStatus.NOT_FOUND,
                        "not found: {}".format(file_path))
            else:
                self.send_error(http.server.HTTPStatus.NOT_FOUND,
                    "not found: {}".format(self.path.strip(os.sep)))
        else:
            self.send_error(http.server.HTTPStatus.NOT_FOUND,
                "no file specified")

    def do_GET(self):
        self.__get_file(lambda f: shutil.copyfileobj(f, self.wfile))

    def do_HEAD(self):
        # no-op
        self.__get_file(lambda x: x)

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("file-path")
    parser.add_argument("-p", "--port", type=int, default=8080)
    return parser.parse_args()

def main():
    args = setup_args()
    file_path = vars(args)["file-path"]

    server_address = ("", args.port)
    server = HTTPServerWithBundle(server_address,
        SingleFileHTTPRequestHandler, {"file-path": file_path})
    print("serving file on {}:{}/{}".format(server.server_name,
        server.server_port, file_path))
    server.serve_forever()

if __name__ == "__main__":
    main()
