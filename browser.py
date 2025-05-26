import socket
import ssl
import pathlib
import os

import tkinter as tk

default_path = r"C:\Users\natha\OneDrive\Desktop\default.txt"
WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100

class Browser:
    def __init__(self):
        self.window = tk.Tk()
        self.canvas = tk.Canvas(
            self.window, 
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
        self.window.title("Nathan's Beautiful Browser")
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<MouseWheel>", self.on_mousewheel)
        

    def draw(self):
        self.canvas.delete("all")
        HSTEP, VSTEP = 13, 18

        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def load(self, url):
        body = url.request()
        text = lex(body)
        self.display_list = layout(text)
        self.draw()

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

    def on_mousewheel(self, event):
        self.scroll += int(-1 * (event.delta / 120) * SCROLL_STEP)
        self.draw()

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
        
        
        if '/' not in url:
            url += '/'
        
        self.host, url = url.split('/', 1)
        self.path = '/' + url

        # custom port handling
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)


    def request(self): 

        if self.scheme == "file":
            # local file handling
            path = os.path.join(pathlib.Path.home(), self.path[1:])
            
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
        request += "\r\n"  # two newlines to end the headers

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

def lex(body):
    text = ""
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
                    text += c

            elif not in_tag:
                text += c

        elif not in_tag:
            text += c
        i += 1
        
    return text

def layout(text):
    display_list = []
    HSTEP, VSTEP = 13, 18
    cursor_x, cursor_y = HSTEP, VSTEP
    
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP

        # newline handling
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list

if __name__ == "__main__":
    import sys

    # if no URL browser opens default file
    if len(sys.argv) > 1:
        url = URL(sys.argv[1])
    else:
        url = URL("file:///" + default_path.replace("\\", "/"))

    Browser().load(url)
    tk.mainloop()