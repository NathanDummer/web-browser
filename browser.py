import socket
import ssl
import pathlib
import os

default_path = r"C:\Users\natha\OneDrive\Desktop\default.txt"

class URL:
    def __init__(self, url):

        # splits request type and hostname
        self.scheme, url = url.split("://", 1)
        self.path = url

        assert self.scheme in ("http", "https", "file",)

        if self.scheme == "https":
            self.port = 443
        elif self.scheme == "http":
            self.port = 80

        if (self.path == "") or (self.path == "/"): self.path = default_path
        
        if '/' not in url:
            url += '/'
        
        self.host, url = url.split('/', 1)
        if self.path and self.path[0] != '/': self.path = '/' + self.path

        # custom port handling
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)


    def request(self): 

        if self.scheme == "file":
            # local file handling
            path = os.path.join(pathlib.Path.home(), self.path[1:])
            print(f'\n{path}\n')
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
            with open(path, 'r') as f:
                return f.read()
            
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        s.connect((self.host, self.port))
        if self.scheme == "https": 
            # wrapping with ssl library
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        request = f"GET {self.path} HTTP/1.0\r\n"
        request += f"Host: {self.host}\r\n"
        request += "User-Agent: NathansBeautifulBrowser\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"                       # two newlines to end the headers

        s.send(request.encode("utf8"))

        # reading servers response
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        # grabbing headers
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # weird formatting
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()

        return content

def show(body):

    in_tag = False
    i = 0
    while i < len(body):
        c = body[i]
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif c == "&":
            if body[i+3]:
                if body[i+1:i+4] == "lt;":
                    in_tag = True
                    i += 3
                elif body[i+1:i+4] == "gt;":
                    in_tag = False
                    i += 3
                elif not in_tag:
                    print(c, end="")

            elif not in_tag:
                print(c, end="")

        elif not in_tag:
            print(c, end="")
        i += 1


def load(url):
    body = url.request()
    show(body)

if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))