import socket
import ssl
import pathlib
import os

import tkinter as tk
import tkinter.font

default_path = r"C:\Users\natha\OneDrive\Desktop\default.txt"
WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18

FONTS = {}

class Text: 
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag

class Layout:
    def __init__(self, tokens):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12

        
        self.line = []

        for tok in tokens:
            self.token(tok)
        self.flush()

    # aligns along baseline, adds all words to display list, and updates cursor fields
    def flush(self):
        if not self.line: return

        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent

        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = HSTEP
        self.line = []

    def word(self, word):

        # returns font object
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)

        if self.cursor_x + w >= WIDTH - HSTEP:
            self.flush()


        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)

        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()    
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP


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
        
        for x, y, c, f in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c, font=f, anchor="nw")
            
    def load(self, url):
        body = url.request()
        text = lex(body)
        self.display_list = Layout(text).display_list
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
    out = []
    buffer = ""
    in_tag = False

    i = 0
    while i < len(body):
        c = body[i]

        if c == "<":
            in_tag = True
            if buffer: out.append(Text(buffer))
            buffer = ""

        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""

        elif c == "&":
            if body[i+3]:
                if body[i+1:i+4] == "lt;":
                    in_tag = True
                    if buffer: out.append(Text(buffer))
                    buffer = ""
                    i += 3

                elif body[i+1:i+4] == "gt;":
                    in_tag = False
                    out.append(Tag(buffer))
                    buffer = ""
                    i += 3

                else:
                    buffer += c
            else:
                buffer += c
        else:
            buffer += c
        i += 1

    if not in_tag and buffer: out.append(Text(buffer))
    return out

# font cahing functionality
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight,
            slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

if __name__ == "__main__":
    import sys

    # if no URL browser opens default file
    if len(sys.argv) > 1:
        url = URL(sys.argv[1])
    else:
        url = URL("file:///" + default_path.replace("\\", "/"))

    Browser().load(url)
    tk.mainloop()