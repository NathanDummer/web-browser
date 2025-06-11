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
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return "<" + self.tag + ">"


class DrawText:
    def __init__(self, x1, y1, text, font):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            
            anchor='nw')
    

class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color)


class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []
        self.SELF_CLOSING_TAGS = [
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
            "command", "keygen", "menuitem", "source", "track"
        ]

        self.HEAD_TAGS = [
            "base", "basefont", "bgsound", "noscript",
            "link", "meta", "title", "style", "script",
        ]

    # malformed html handling
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]

            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] \
                 and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and \
                 tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else: break

    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}

        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                attributes[key.casefold()] = value

                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
            else:
                attributes[attrpair.casefold()] = ""

        return tag, attributes
    
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)

        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)

        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)

        return self.unfinished.pop()

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)

        # ignoring docstring and comments
        if tag.startswith("!"): return

        self.implicit_tags(tag)

        if tag.startswith("/"):
            # last node
            if len(self.unfinished) == 1: return

            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)

        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)

        else:
            # first tag
            parent = self.unfinished[-1] if self.unfinished else None

            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def parse(self):
        text = ""
        in_tag = False

        i = 0
        while i < len(self.body):
            c = self.body[i]
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = ""

            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""

            # elif c == "&":
            #     if self.body[i+3]:
            #         if self.body[i+1:i+4] == "lt;":
            #             in_tag = True
            #             if text: self.add_text(text)
            #             text = ""
            #             i += 3

            #         elif self.body[i+1:i+4] == "gt;":
            #             in_tag = False
            #             print(f'tag: {text}')
            #             self.add_tag(text)
            #             text = ""
            #             i += 3

            #         else:
            #             text += c
            #     else:
            #         text += c

            else:
                text += c
            i += 1

        if not in_tag and text: self.add_text(text)
        return self.finish()


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP

        child.layout()
        self.height = child.height

    def paint(self):
        return []


class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.display_list = []

        self.x = None
        self.y = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.width = None
        self.height = None

        self.BLOCK_ELEMENTS = [
            "html", "body", "article", "section", "nav", "aside",
            "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
            "footer", "address", "p", "hr", "pre", "blockquote",
            "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
            "figcaption", "main", "div", "table", "form", "fieldset",
            "legend", "details", "summary"
        ]

    def paint(self):
        cmds = []
        if self.layout_mode() == "inline":

            if isinstance(self.node, Element) and self.node.tag == "pre":
                x2, y2 = self.x + self.width, self.y + self.height
                rect = DrawRect(self.x, self.y, x2, y2, "gray")
                cmds.append(rect)

            for x, y, word, font in self.display_list:
                cmds.append(DrawText(x, y, word, font))
        return cmds
    

    # lays out the block, recursively building children and calculating height
    def layout(self):
        # 1) Top–down: establish this block’s x, y, width
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        self.x = self.parent.x
        self.width = self.parent.width

        mode = self.layout_mode()

        if mode == "block":
            # Build children
            prev = None
            for html_child in self.node.children:
                blk = BlockLayout(html_child, self, prev)
                self.children.append(blk)
                prev = blk

            # Recurse into children
            for blk in self.children:
                blk.layout()

            # Bottom–up: sum up their heights
            self.height = sum(blk.height for blk in self.children)

        else:  # inline leaf
            # Reset cursors & styles
            self.cursor_x = 0
            self.cursor_y = 0
            self.weight   = "normal"
            self.style    = "roman"
            self.size     = 12
            self.line     = []

            # Lay out text into display_list
            self.recurse(self.node)
            self.flush()

            # Bottom–up: use the final cursor_y as our height
            self.height = self.cursor_y

    # determines the layout method for the block
    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and \
                  child.tag in self.BLOCK_ELEMENTS
                  for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"
        else:
            return "block"

    def layout_intermediate(self):
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next

    # aligns along baseline, adds all words to display list, and updates cursor fields
    def flush(self):
        if not self.line: return

        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent

        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = 0
        self.line = []

    def word(self, word):

        # returns font object
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)

        if self.cursor_x + w > self.width:
            self.flush()

        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "sup":
            self.size /= 2
        elif tag == "br":
            self.flush()    
        
    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "sup":
            self.size *= 2
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP

    # traverses the tree recursively, handling text and tags
    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)


# paints the layout tree to the display list
def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)


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
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT: continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll, self.canvas)

    def load(self, url):
        body = url.request()
        self.nodes = HTMLParser(body).parse()

        self.document = DocumentLayout(self.nodes)
        self.document.layout()

        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.draw()

    def scrolldown(self, e):
        max_y = max(self.document.height + 2*VSTEP - HEIGHT, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()

    def on_mousewheel(self, event):
        min_y = 0
        max_y = max(self.document.height + 2*VSTEP - HEIGHT, 0)
        new_scroll = self.scroll + int(-1 * (event.delta / 120) * SCROLL_STEP)  
        if new_scroll >= min_y and new_scroll <= max_y: self.scroll = new_scroll
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


# font caching functionality
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight,
            slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

if __name__ == "__main__":
    import sys

    # prints the tree structure of the parsed HTML in terminal
    # body = URL(sys.argv[1]).request()
    # nodes = HTMLParser(body).parse()
    # print_tree(nodes)

    # if no URL browser opens default file
    if len(sys.argv) > 1:
        url = URL(sys.argv[1])
    else:
        url = URL("file:///" + default_path.replace("\\", "/"))

    Browser().load(url)
    tk.mainloop()