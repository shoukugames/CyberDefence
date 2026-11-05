"""A small in-memory Unix-like file system with owners and permission bits."""
import fnmatch
import posixpath


class Node:
    __slots__ = ("name", "is_dir", "content", "children", "mode", "owner", "group", "mtime")

    def __init__(self, name, is_dir=False, content="", mode=None, owner="root", group="root", mtime="Nov  6 07:00"):
        self.name = name
        self.is_dir = is_dir
        self.content = content
        self.children = {} if is_dir else None
        self.mode = mode if mode is not None else (0o755 if is_dir else 0o644)
        self.owner = owner
        self.group = group
        self.mtime = mtime

    @property
    def size(self):
        return 4096 if self.is_dir else len(self.content.encode("utf-8"))


class FSError(Exception):
    pass


class VFS:
    def __init__(self):
        self.root = Node("/", True)

    # path helpers ---------------------------------------------------------
    @staticmethod
    def norm(path, cwd="/", home="/root"):
        if path == "~" or path.startswith("~/"):
            path = home + path[1:]
        if not path.startswith("/"):
            path = posixpath.join(cwd, path)
        path = posixpath.normpath(path)
        if path.startswith("//"):
            path = path[1:]
        return path

    def get(self, path):
        if path == "/":
            return self.root
        node = self.root
        for part in path.strip("/").split("/"):
            if not node.is_dir or part not in node.children:
                return None
            node = node.children[part]
        return node

    def parent(self, path):
        return self.get(posixpath.dirname(path) or "/")

    def exists(self, path):
        return self.get(path) is not None

    def isdir(self, path):
        n = self.get(path)
        return bool(n and n.is_dir)

    # permissions ------------------------------------------------------------
    @staticmethod
    def can(node, user, groups, bit):
        """bit: 4 read, 2 write, 1 execute."""
        if user == "root":
            return True
        if node.owner == user:
            return bool((node.mode >> 6) & bit)
        if node.group in groups:
            return bool((node.mode >> 3) & bit)
        return bool(node.mode & bit)

    # building -----------------------------------------------------------------
    def mkdir(self, path, mode=0o755, owner="root", group="root", parents=True):
        node = self.root
        parts = [p for p in path.strip("/").split("/") if p]
        for i, part in enumerate(parts):
            if part not in node.children:
                if not parents and i < len(parts) - 1:
                    raise FSError(f"cannot create directory '{path}': No such file or directory")
                node.children[part] = Node(part, True, mode=mode, owner=owner, group=group)
            node = node.children[part]
            if not node.is_dir:
                raise FSError(f"cannot create directory '{path}': Not a directory")
        return node

    def write(self, path, content, mode=None, owner=None, group=None, append=False):
        parent = self.parent(path)
        if parent is None or not parent.is_dir:
            raise FSError(f"{path}: No such file or directory")
        name = posixpath.basename(path)
        node = parent.children.get(name)
        if node is None:
            node = Node(name, False, "", mode if mode is not None else 0o644,
                        owner or "root", group or owner or "root")
            parent.children[name] = node
        elif node.is_dir:
            raise FSError(f"{path}: Is a directory")
        else:
            if mode is not None:
                node.mode = mode
            if owner:
                node.owner = owner
                node.group = group or owner
        node.content = node.content + content if append else content
        node.mtime = "Nov  6 09:41"
        return node

    def remove(self, path):
        parent = self.parent(path)
        name = posixpath.basename(path)
        if parent and name in parent.children:
            del parent.children[name]
            return True
        return False

    def read(self, path):
        node = self.get(path)
        if node is None:
            raise FSError(f"{path}: No such file or directory")
        if node.is_dir:
            raise FSError(f"{path}: Is a directory")
        return node.content

    def walk(self, path):
        """Yield (path, node) for path and everything beneath it."""
        start = self.get(path)
        if start is None:
            return
        stack = [(path, start)]
        while stack:
            p, n = stack.pop()
            yield p, n
            if n.is_dir:
                for name in sorted(n.children, reverse=True):
                    stack.append((posixpath.join(p, name) if p != "/" else "/" + name, n.children[name]))

    def glob(self, pattern):
        """Expand a single absolute glob pattern."""
        parts = [p for p in pattern.strip("/").split("/") if p]
        results = ["/"]
        for part in parts:
            nxt = []
            for base in results:
                node = self.get(base)
                if not node or not node.is_dir:
                    continue
                if any(c in part for c in "*?["):
                    for name in sorted(node.children):
                        if name.startswith(".") and not part.startswith("."):
                            continue
                        if fnmatch.fnmatchcase(name, part):
                            nxt.append(posixpath.join(base, name))
                elif part in node.children:
                    nxt.append(posixpath.join(base, part))
            results = nxt
        return results


def mode_string(node):
    chars = "d" if node.is_dir else "-"
    for shift in (6, 3, 0):
        bits = (node.mode >> shift) & 7
        chars += ("r" if bits & 4 else "-") + ("w" if bits & 2 else "-") + ("x" if bits & 1 else "-")
    return chars
