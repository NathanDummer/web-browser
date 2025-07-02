import socket
import ssl
import pathlib
import os
import tkinter as tk
import tkinter.font

# Default file to load if no URL is provided
default_path = r"C:\Users\natha\OneDrive\Desktop\default.txt"
WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18

# Fonts cache
FONTS = {}

# Plain HTML Text Node
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return repr(self.text)

# HTML Element Node
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return "<" + self.tag + ">"

INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}

# Applies style information to each node in DOM tree
def style(node, rules):
        node.style = {}

        # Inherit font properties from parent or default
        for property, default_value in INHERITED_PROPERTIES.items():
            if node.parent:
                node.style[property] = node.parent.style[property]
            else:
                node.style[property] = default_value

        # Apply matching style sheet rules
        for selector, body in rules:
            if not selector.matches(node): continue
            for property, value in body.items():
                node.style[property] = value

        # Style attribute trumps style sheet rules
        if isinstance(node, Element) and "style" in node.attributes:
            pairs = CSSParser(node.attributes["style"]).body()
            for property, value in pairs.items():
                node.style[property] = value

        # Resolving font-size percentages
        if node.style["font-size"].endswith("%"):
            if node.parent:
                parent_font_size = node.parent.style["font-size"]
            else:
                parent_font_size = INHERITED_PROPERTIES["font-size"]
            node_pct = float(node.style["font-size"][:-1]) / 100
            parent_px = float(parent_font_size[:-2])
            node.style["font-size"] = str(node_pct * parent_px) + "px"

        for child in node.children:
            style(child, rules)

# Drawing Primitives
class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.color = color
        self.bottom = y1 + font.metrics("linespace")

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            fill=self.color,
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


# Used to resolve which CSS rule takes precedence
def cascade_priority(rule):
    selector, body = rule
    return selector.priority



# CSS Selectors 

# Matches elements by tag name
class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1

    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag


# Matches elements with a given ancestor tag (e.g. div p)
class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority

    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False


# Recursive Parser for CSS
class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def parse(self):
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break

        return rules

    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
                pairs[prop.casefold()] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except Exception:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs

    def selector(self):
        out = TagSelector(self.word().casefold())
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.casefold())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.word()
        return prop.casefold(), val

    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing error")
        return self.s[start:self.i]

    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing error")
        self.i += 1

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    # currently unsupported pairs
    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None


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

                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.casefold()] = value

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

# Layout Classes for rendering HTML
# DocumentLayout is the root of the layout tree, BlockLayout handles block elements
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
            bgcolor = self.node.style.get("background-color", "transparent")
            if bgcolor != "transparent":
                x2, y2 = self.x + self.width, self.y + self.height
                rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
                cmds.append(rect)

            for x, y, word, font, color in self.display_list:
                cmds.append(DrawText(x, y, word, font, color))

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
            # self.weight   = "normal"
            # self.style    = "roman"
            # self.size     = 12
            self.line     = []

            # Lay out text into display_list
            self.recurse(self.node)
            self.flush()

            # Bottom–up: use the final cursor_y as our height
            self.height = self.cursor_y

    # determines the layout method for the block, e.g - inline or block
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

    # aligns along baseline, adds all words to display list, and updates cursor fields
    def flush(self):
        if not self.line: return

        metrics = [font.metrics() for x, word, font, color in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent

        for rel_x, word, font, color in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font, color))

        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = 0
        self.line = []

    def word(self, node, word):
        color = node.style["color"]
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style)

        w = font.measure(word)
        if self.cursor_x + w > self.width:
            self.flush()

        self.line.append((self.cursor_x, word, font, color))
        self.cursor_x += w + font.measure(" ")

    # traverses the tree recursively, handling text and tags
    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.flush()
            for child in node.children:
                self.recurse(child)


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
            height=HEIGHT,
            bg="white",
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
        
        links = [node.attributes["href"]
             for node in tree_to_list(self.nodes, [])
             if isinstance(node, Element)
             and node.tag == "link"
             and node.attributes.get("rel") == "stylesheet"
             and "href" in node.attributes]
        
        rules = DEFAULT_STYLE_SHEET.copy()
        style(self.nodes, sorted(rules, key=cascade_priority))

        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except:
                continue
            rules.extend(CSSParser(body).parse())

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

    # converts relative to full URL's
    def resolve(self, url):
        if "://" in url:
            return URL(url)
        
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url

        return URL(f"{self.scheme}://{self.host}:{self.port}{url}")

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

# general
def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list

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

    DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()
    Browser().load(url)
    tk.mainloop()