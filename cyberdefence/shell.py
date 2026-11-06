"""The command interpreter driving the simulated terminal."""
import ipaddress
import posixpath
import shlex

from . import manpages
from .system import COMMANDS
from .vfs import FSError, mode_string
from .world import IptRule, UfwRule, SERVICE_NAMES
from .save import fmt_time


class CmdResult:
    def __init__(self, out="", code=0, editor=None):
        self.out = out
        self.code = code
        self.editor = editor   # ("nano", path) to open the full-screen editor


class Shell:
    def __init__(self, world, i18n, save, level_num):
        self.world = world
        self.tr = i18n
        self.save = save
        self.level_num = level_num
        self.cwd = "/home/player"
        self.user = "player"
        self.groups_map = {"player": ["player", "sudo", "adm"], "root": ["root"]}
        self.history = []
        self.hint_idx = 0
        self.env = {"HOME": "/home/player", "USER": "player", "PATH": "/usr/bin:/bin:/sbin"}
        self.aliases = {"ll": "ls -l", "la": "ls -la", "l": "ls -CF"}

    # ------------------------------------------------------------------ helpers
    @property
    def groups(self):
        return self.groups_map.get(self.user, [self.user])

    def home(self):
        return "/root" if self.user == "root" else "/home/player"

    def prompt(self):
        cwd = self.cwd
        home = self.home()
        if cwd == home:
            cwd = "~"
        elif cwd.startswith(home + "/"):
            cwd = "~" + cwd[len(home):]
        sym = "#" if self.user == "root" else "$"
        return f"{self.user}@websrv01:{cwd}{sym} "

    def abspath(self, path):
        return self.world.fs.norm(path, self.cwd, self.home())

    def _(self, key, **kw):
        return self.tr(key, **kw)

    def err(self, text):
        return CmdResult(text + "\n", 1)

    # ------------------------------------------------------------------ run line
    def run(self, line):
        line = line.rstrip("\n")
        if line.strip():
            self.history.append(line)
        # split on pipes (outside quotes handled by shlex per-segment)
        try:
            segments = self._split_pipes(line)
        except ValueError:
            return CmdResult("syntax error: unmatched quote\n", 2)
        data = ""
        result = CmdResult("")
        for i, seg in enumerate(segments):
            result = self._run_segment(seg, stdin=data)
            data = result.out
            if result.editor:
                return result
        return result

    def _split_pipes(self, line):
        parts, buf, quote = [], "", None
        for ch in line:
            if quote:
                buf += ch
                if ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
                buf += ch
            elif ch == "|":
                parts.append(buf)
                buf = ""
            else:
                buf += ch
        if quote:
            raise ValueError("unmatched quote")
        parts.append(buf)
        return parts

    def _run_segment(self, seg, stdin=""):
        seg = seg.strip()
        if not seg:
            return CmdResult(stdin)
        # redirection
        append = ">>" in seg
        redirect = None
        for op in (">>", ">"):
            if op in seg:
                left, right = seg.split(op, 1)
                redirect = right.strip().strip('"\'')
                seg = left.strip()
                break
        try:
            tokens = shlex.split(seg, posix=True)
        except ValueError:
            return CmdResult("syntax error: unmatched quote\n", 2)
        if not tokens:
            return CmdResult("")
        # environment assignment prefix like FOO=bar cmd — ignore for our purposes
        res = self._dispatch(tokens, stdin)
        if redirect is not None and res.editor is None:
            path = self.abspath(redirect)
            try:
                self.world.fs.write(path, res.out, append=append,
                                    owner=self.user if not self.world.fs.exists(path) else None)
                return CmdResult("", res.code)
            except FSError as e:
                return self.err(str(e))
        return res

    # ------------------------------------------------------------------ dispatch
    def _dispatch(self, tokens, stdin):
        # expand a shell alias in the command position, e.g. ll -> ls -l
        if tokens and tokens[0] in self.aliases:
            tokens = shlex.split(self.aliases[tokens[0]]) + tokens[1:]
        cmd = tokens[0]
        args = tokens[1:]

        # sudo / su elevate for a single command or a shell
        if cmd in ("sudo", "su"):
            return self._sudo(cmd, args, stdin)

        handler = getattr(self, "cmd_" + cmd.replace("-", "_"), None)
        if handler is None:
            if cmd in COMMANDS:
                return CmdResult("")   # harmless no-op stubs (true, false, etc. have handlers)
            return self.err(self._("sh.not_found", cmd=cmd))
        try:
            return handler(args, stdin)
        except FSError as e:
            return self.err(str(e))
        except PermissionError:
            return self.err(self._("sh.need_root", cmd=" ".join(tokens)))

    def _become_root(self):
        self.user = "root"
        self.env["USER"] = "root"
        self.env["HOME"] = "/root"
        return CmdResult(self._("sh.now_root") + "\n")

    def _spawns_root_shell(self, args):
        """True if `args` (the tokens after sudo/su) just open a root shell,
        e.g. `su`, `su -`, `su root`, `sudo su -`, `sudo bash`, `sudo -i`."""
        toks = list(args)
        # drop leading sudo-style options that don't change this
        while toks and toks[0] in ("-i", "-s", "-H", "-E"):
            toks.pop(0)
        if not toks:
            return True  # bare `sudo` / `sudo -i` / `sudo -s`
        if toks[0] in ("su", "bash", "sh", "-bash", "-sh", "ash", "dash"):
            rest = [t for t in toks[1:] if t not in ("-", "-l", "--login", "root", "-c")]
            # `su -c <cmd>` runs a command, not a login shell
            if "-c" in toks[1:]:
                return False
            return not rest
        return False

    def _sudo(self, cmd, args, stdin):
        if args and args[0] == "-l" and cmd == "sudo":
            return CmdResult("User player may run the following commands on websrv01:\n"
                             "    (ALL : ALL) NOPASSWD: ALL\n")
        # become root shell: `su`, `su -`, `su root`, `sudo`, `sudo -i`,
        # `sudo su -`, `sudo bash`, ...
        if cmd == "su":
            if "-c" in args:
                i = args.index("-c")
                args = args[i + 1:]  # run the quoted command as root
            elif not args or all(t in ("-", "-l", "--login", "root") for t in args):
                return self._become_root()
            else:
                return self._become_root()  # `su someuser` → root shell in this sim
        elif self._spawns_root_shell(args):
            return self._become_root()
        # run one command as root
        saved_user, saved_env = self.user, dict(self.env)
        self.user = "root"
        self.env["USER"] = "root"
        self.env["HOME"] = "/root"
        try:
            res = self._run_segment(" ".join(shlex.quote(a) for a in args), stdin)
        finally:
            self.user, self.env = saved_user, saved_env
        return res

    def need_root(self, cmd):
        if self.user != "root":
            raise PermissionError(cmd)

    # ------------------------------------------------------------------ files
    def cmd_pwd(self, a, s):
        return CmdResult(self.cwd + "\n")

    def cmd_cd(self, a, s):
        target = a[0] if a else "~"
        if target == "-":
            target = self.env.get("OLDPWD", self.cwd)
        path = self.abspath(target)
        node = self.world.fs.get(path)
        if node is None:
            return self.err("cd: " + self._("sh.no_file", path=target))
        if not node.is_dir:
            return self.err("cd: " + self._("sh.not_dir", path=target))
        if not self.world.fs.can(node, self.user, self.groups, 1):
            return self.err("cd: " + self._("sh.denied", path=target))
        self.env["OLDPWD"] = self.cwd
        self.cwd = path
        return CmdResult("")

    def _expand(self, args):
        """Glob-expand arguments against the VFS."""
        out = []
        for a in args:
            if any(c in a for c in "*?[") and not a.startswith("-"):
                pat = self.abspath(a)
                matches = self.world.fs.glob(pat)
                if matches:
                    out.extend(matches if a.startswith("/") or a.startswith("~")
                               else [posixpath.relpath(m, self.cwd) if not a.startswith("/") else m for m in matches])
                    continue
            out.append(a)
        return out

    def cmd_ls(self, a, s):
        flags = set("".join(x[1:] for x in a if x.startswith("-") and x != "-"))
        paths = [x for x in a if not x.startswith("-")]
        paths = self._expand(paths) or [self.cwd]
        long = "l" in flags
        show_all = "a" in flags
        fs = self.world.fs
        chunks = []
        multi = len(paths) > 1
        for p in paths:
            ap = self.abspath(p)
            node = fs.get(ap)
            if node is None:
                chunks.append("ls: " + self._("sh.no_file", path=p))
                continue
            if node.is_dir:
                entries = sorted(node.children.values(), key=lambda n: n.name)
                if show_all:
                    entries = [fs.get(ap)] + entries  # '.' loosely
                names = [n.name for n in entries if show_all or not n.name.startswith(".")]
                nodes = [n for n in entries if show_all or not n.name.startswith(".")]
                header = (f"{p}:\n" if multi else "")
                if long:
                    lines = [f"total {len(nodes)}"]
                    for n in nodes:
                        lines.append(self._long_line(n))
                    chunks.append(header + "\n".join(lines))
                else:
                    chunks.append(header + self._columns(names))
            else:
                chunks.append(self._long_line(node, name=p) if long else p)
        return CmdResult("\n".join(c for c in chunks if c) + ("\n" if chunks else ""))

    def _long_line(self, node, name=None):
        nm = name if name is not None else node.name
        if node.is_dir:
            nm += "/"
        return f"{mode_string(node)} {1:>2} {node.owner:<8} {node.group:<8} {node.size:>6} {node.mtime} {nm}"

    def _columns(self, names):
        if not names:
            return ""
        return "  ".join(names)

    def cmd_cat(self, a, s):
        files = self._expand([x for x in a if not x.startswith("-")])
        if not files:
            return CmdResult(s)
        out = []
        for f in files:
            ap = self.abspath(f)
            node = self.world.fs.get(ap)
            if node is None:
                out.append("cat: " + self._("sh.no_file", path=f))
                continue
            if node.is_dir:
                out.append("cat: " + self._("sh.is_dir", path=f))
                continue
            if not self.world.fs.can(node, self.user, self.groups, 4):
                out.append("cat: " + self._("sh.denied", path=f))
                continue
            out.append(node.content)
        text = "".join(c if c.endswith("\n") or not c else c + "\n" for c in out)
        return CmdResult(text, 0 if all("cat:" not in o for o in out) else 1)

    def cmd_tac(self, a, s):
        res = self.cmd_cat(a, s)
        return CmdResult("\n".join(reversed(res.out.splitlines())) + ("\n" if res.out else ""), res.code)

    def cmd_head(self, a, s):
        n, files = self._nlines(a, 10)
        return self._headtail(files, s, n, head=True)

    def cmd_tail(self, a, s):
        n, files = self._nlines(a, 10)
        return self._headtail(files, s, n, head=False)

    def _nlines(self, a, default):
        n = default
        files = []
        it = iter(a)
        for x in it:
            if x == "-n":
                n = int(next(it, default))
            elif x.startswith("-n"):
                n = int(x[2:])
            elif x.startswith("-") and x[1:].isdigit():
                n = int(x[1:])
            elif x.startswith("-f"):
                continue
            else:
                files.append(x)
        return n, files

    def _headtail(self, files, s, n, head):
        if not files:
            lines = s.splitlines()
            sel = lines[:n] if head else lines[-n:]
            return CmdResult("\n".join(sel) + ("\n" if sel else ""))
        out = []
        for f in files:
            content = self.world.fs.read(self.abspath(f))
            lines = content.splitlines()
            sel = lines[:n] if head else lines[-n:]
            out.append("\n".join(sel))
        return CmdResult("\n".join(out) + "\n")

    def cmd_wc(self, a, s):
        flags = [x for x in a if x.startswith("-")]
        files = [x for x in a if not x.startswith("-")]
        text = self.world.fs.read(self.abspath(files[0])) if files else s
        lines, words, chars = len(text.splitlines()), len(text.split()), len(text)
        if "-l" in flags:
            r = str(lines)
        elif "-w" in flags:
            r = str(words)
        elif "-c" in flags:
            r = str(chars)
        else:
            r = f"{lines:>7} {words:>7} {chars:>7}"
        return CmdResult(r + (f" {files[0]}" if files else "") + "\n")

    def cmd_grep(self, a, s):
        import re
        ignore = False
        count = False
        invert = False
        pat = None
        files = []
        it = iter(a)
        for x in it:
            if x.startswith("-") and len(x) > 1 and not pat:
                if "i" in x:
                    ignore = True
                if "c" in x:
                    count = True
                if "v" in x:
                    invert = True
                if "e" in x:
                    pat = next(it, "")
            elif pat is None:
                pat = x
            else:
                files.append(x)
        if pat is None:
            return self.err("usage: grep PATTERN [FILE...]")
        flags = re.IGNORECASE if ignore else 0
        try:
            rx = re.compile(pat, flags)
        except re.error:
            rx = re.compile(re.escape(pat), flags)
        sources = []
        if files:
            for f in files:
                try:
                    sources.append((f, self.world.fs.read(self.abspath(f))))
                except FSError:
                    sources.append((f, None))
        else:
            sources.append((None, s))
        out = []
        matched = False
        multi = len(sources) > 1
        for name, content in sources:
            if content is None:
                out.append(f"grep: {name}: No such file or directory")
                continue
            hits = [ln for ln in content.splitlines() if bool(rx.search(ln)) != invert]
            if hits:
                matched = True
            if count:
                out.append((f"{name}:" if multi else "") + str(len(hits)))
            else:
                for ln in hits:
                    out.append((f"{name}:" if multi else "") + ln)
        return CmdResult("\n".join(out) + ("\n" if out else ""), 0 if matched else 1)

    cmd_egrep = cmd_grep

    def cmd_echo(self, a, s):
        newline = True
        if a and a[0] == "-n":
            newline = False
            a = a[1:]
        return CmdResult(" ".join(a) + ("\n" if newline else ""))

    def cmd_printf(self, a, s):
        if not a:
            return CmdResult("")
        fmt = a[0].replace("\\n", "\n").replace("\\t", "\t")
        try:
            return CmdResult(fmt % tuple(a[1:]) if "%" in fmt else fmt)
        except (TypeError, ValueError):
            return CmdResult(fmt)

    def cmd_touch(self, a, s):
        for f in a:
            if f.startswith("-"):
                continue
            path = self.abspath(f)
            if not self.world.fs.exists(path):
                self.world.fs.write(path, "", owner=self.user, group=self.user)
        return CmdResult("")

    def cmd_mkdir(self, a, s):
        parents = "-p" in a
        for f in a:
            if f.startswith("-"):
                continue
            try:
                self.world.fs.mkdir(self.abspath(f), owner=self.user, group=self.user, parents=parents)
            except FSError as e:
                return self.err("mkdir: " + str(e))
        return CmdResult("")

    def cmd_rm(self, a, s):
        recursive = any(x in ("-r", "-rf", "-fr", "-R") for x in a)
        force = any("f" in x for x in a if x.startswith("-"))
        targets = self._expand([x for x in a if not x.startswith("-")])
        if not targets:
            return self.err("rm: missing operand")
        errs = []
        for f in targets:
            path = self.abspath(f)
            node = self.world.fs.get(path)
            if node is None:
                if not force:
                    errs.append("rm: " + self._("sh.no_file", path=f))
                continue
            parent = self.world.fs.parent(path)
            if not self.world.fs.can(parent, self.user, self.groups, 2):
                errs.append("rm: " + self._("sh.denied", path=f))
                continue
            if node.is_dir and not recursive:
                errs.append(f"rm: cannot remove '{f}': Is a directory")
                continue
            self.world.fs.remove(path)
        return CmdResult("\n".join(errs) + ("\n" if errs else ""), 1 if errs else 0)

    def cmd_rmdir(self, a, s):
        for f in a:
            if f.startswith("-"):
                continue
            path = self.abspath(f)
            node = self.world.fs.get(path)
            if node and node.is_dir and not node.children:
                self.world.fs.remove(path)
            elif node and node.children:
                return self.err(f"rmdir: failed to remove '{f}': Directory not empty")
        return CmdResult("")

    def cmd_cp(self, a, s):
        args = [x for x in a if not x.startswith("-")]
        if len(args) < 2:
            return self.err("usage: cp SRC DEST")
        *srcs, dest = args
        destp = self.abspath(dest)
        dest_is_dir = self.world.fs.isdir(destp)
        for src in srcs:
            sp = self.abspath(src)
            node = self.world.fs.get(sp)
            if node is None:
                return self.err("cp: " + self._("sh.no_file", path=src))
            target = posixpath.join(destp, posixpath.basename(sp)) if dest_is_dir else destp
            self.world.fs.write(target, node.content, mode=node.mode, owner=self.user, group=self.user)
        return CmdResult("")

    def cmd_mv(self, a, s):
        args = [x for x in a if not x.startswith("-")]
        if len(args) < 2:
            return self.err("usage: mv SRC DEST")
        *srcs, dest = args
        destp = self.abspath(dest)
        dest_is_dir = self.world.fs.isdir(destp)
        for src in srcs:
            sp = self.abspath(src)
            node = self.world.fs.get(sp)
            if node is None:
                return self.err("mv: " + self._("sh.no_file", path=src))
            target = posixpath.join(destp, posixpath.basename(sp)) if dest_is_dir else destp
            self.world.fs.write(target, node.content, mode=node.mode, owner=node.owner, group=node.group)
            self.world.fs.remove(sp)
        return CmdResult("")

    def cmd_chmod(self, a, s):
        self.need_root("chmod") if False else None
        args = [x for x in a if not (x.startswith("-") and x[1:].isalpha() and x != "-R")]
        recursive = "-R" in a
        args = [x for x in a if x != "-R"]
        if len(args) < 2:
            return self.err("usage: chmod MODE FILE")
        mode_s, files = args[0], args[1:]
        for f in self._expand(files):
            node = self.world.fs.get(self.abspath(f))
            if node is None:
                return self.err("chmod: " + self._("sh.no_file", path=f))
            if self.user != "root" and node.owner != self.user:
                return self.err("chmod: " + self._("sh.denied", path=f))
            node.mode = self._parse_mode(mode_s, node.mode)
        return CmdResult("")

    def _parse_mode(self, spec, current):
        if spec.isdigit():
            return int(spec, 8)
        mode = current
        who = ""
        i = 0
        while i < len(spec) and spec[i] in "ugoa":
            who += spec[i]
            i += 1
        if not who:
            who = "a"
        op = spec[i] if i < len(spec) else "="
        perms = spec[i + 1:]
        bits = 0
        if "r" in perms:
            bits |= 4
        if "w" in perms:
            bits |= 2
        if "x" in perms:
            bits |= 1
        shifts = {"u": 6, "g": 3, "o": 0}
        targets = [6, 3, 0] if "a" in who else [shifts[c] for c in who]
        for sh in targets:
            if op == "+":
                mode |= bits << sh
            elif op == "-":
                mode &= ~(bits << sh)
            else:
                mode = (mode & ~(7 << sh)) | (bits << sh)
        return mode

    def cmd_chown(self, a, s):
        self.need_root("chown")
        args = [x for x in a if x != "-R"]
        if len(args) < 2:
            return self.err("usage: chown OWNER FILE")
        owner = args[0]
        grp = None
        if ":" in owner:
            owner, grp = owner.split(":", 1)
        for f in self._expand(args[1:]):
            node = self.world.fs.get(self.abspath(f))
            if node is None:
                return self.err("chown: " + self._("sh.no_file", path=f))
            node.owner = owner
            node.group = grp or owner
        return CmdResult("")

    def cmd_stat(self, a, s):
        files = [x for x in a if not x.startswith("-")]
        out = []
        for f in files:
            node = self.world.fs.get(self.abspath(f))
            if node is None:
                return self.err("stat: " + self._("sh.no_file", path=f))
            octal = oct(node.mode)[-3:]
            out.append(f"  File: {f}\n  Size: {node.size:<10} {'directory' if node.is_dir else 'regular file'}\n"
                       f"Access: ({octal}/{mode_string(node)})  Uid: ({node.owner})   Gid: ({node.group})\nModify: {node.mtime}")
        return CmdResult("\n".join(out) + "\n")

    def cmd_file(self, a, s):
        out = []
        for f in a:
            node = self.world.fs.get(self.abspath(f))
            if node is None:
                out.append(f"{f}: cannot open (No such file or directory)")
            elif node.is_dir:
                out.append(f"{f}: directory")
            elif node.content.startswith("\x7fELF") or node.content.startswith("ELF"):
                out.append(f"{f}: ELF 64-bit LSB executable, x86-64")
            elif node.content.startswith("#!"):
                out.append(f"{f}: POSIX shell script, ASCII text executable")
            else:
                out.append(f"{f}: ASCII text")
        return CmdResult("\n".join(out) + "\n")

    def cmd_find(self, a, s):
        start = "."
        name = None
        owner = None
        ftype = None
        it = iter(a)
        for x in it:
            if x == "-name":
                name = next(it, "")
            elif x == "-user":
                owner = next(it, "")
            elif x == "-type":
                ftype = next(it, "")
            elif not x.startswith("-"):
                start = x
        import fnmatch
        base = self.abspath(start)
        out = []
        for path, node in self.world.fs.walk(base):
            if name and not fnmatch.fnmatch(node.name, name):
                continue
            if owner and node.owner != owner:
                continue
            if ftype == "f" and node.is_dir:
                continue
            if ftype == "d" and not node.is_dir:
                continue
            out.append(path)
        return CmdResult("\n".join(out) + ("\n" if out else ""))

    def cmd_tree(self, a, s):
        base = self.abspath(a[0]) if a and not a[0].startswith("-") else self.cwd
        lines = [base]
        root = self.world.fs.get(base)
        if not root or not root.is_dir:
            return self.err("tree: " + self._("sh.no_file", path=base))

        def walk(node, prefix):
            kids = sorted([n for n in node.children.values() if not n.name.startswith(".")], key=lambda n: n.name)
            for i, k in enumerate(kids):
                last = i == len(kids) - 1
                lines.append(prefix + ("└── " if last else "├── ") + k.name + ("/" if k.is_dir else ""))
                if k.is_dir:
                    walk(k, prefix + ("    " if last else "│   "))
        walk(root, "")
        return CmdResult("\n".join(lines) + "\n")

    # ------------------------------------------------------------------ editors
    def cmd_nano(self, a, s):
        files = [x for x in a if not x.startswith("-")]
        if not files:
            return self.err("usage: nano FILE")
        path = self.abspath(files[0])
        node = self.world.fs.get(path)
        if node and node.is_dir:
            return self.err("nano: " + self._("sh.is_dir", path=files[0]))
        if node and not self.world.fs.can(node, self.user, self.groups, 4):
            return self.err("nano: " + self._("sh.denied", path=files[0]))
        return CmdResult("", editor=("nano", path, self.user))

    cmd_vi = cmd_nano

    def cmd_sed(self, a, s):
        inplace = False
        script = None
        files = []
        it = iter(a)
        for x in it:
            if x == "-i" or x.startswith("-i"):
                inplace = True
                if len(x) > 2:
                    script = x[2:]
            elif x in ("-e", "-n"):
                if x == "-e":
                    script = next(it, "")
            elif script is None:
                script = x
            else:
                files.append(x)
        if not script:
            return self.err("usage: sed -i 's/OLD/NEW/[g]' FILE")

        def apply(text):
            return self._sed_script(script, text)
        if files:
            out = []
            for f in files:
                path = self.abspath(f)
                try:
                    content = self.world.fs.read(path)
                except FSError as e:
                    return self.err("sed: " + str(e))
                new = apply(content)
                if inplace:
                    node = self.world.fs.get(path)
                    if self.user != "root" and not self.world.fs.can(node, self.user, self.groups, 2):
                        return self.err("sed: " + self._("sh.denied", path=f))
                    self.world.fs.write(path, new)
                else:
                    out.append(new)
            return CmdResult("".join(out))
        return CmdResult(apply(s))

    def _sed_script(self, script, text):
        import re
        script = script.strip()
        if script.startswith("s"):
            delim = script[1]
            parts = script[2:].split(delim)
            if len(parts) >= 2:
                pat, repl = parts[0], parts[1]
                flags = parts[2] if len(parts) > 2 else ""
                count = 0 if "g" in flags else 1
                rx = re.compile(pat, re.IGNORECASE if "i" in flags else 0)
                return "\n".join(rx.sub(repl, ln, count=count) for ln in text.splitlines()) + ("\n" if text.endswith("\n") else "")
        if script.endswith("d") and script.startswith("/"):
            pat = script[1:script.rfind("/")]
            rx = re.compile(pat)
            return "\n".join(ln for ln in text.splitlines() if not rx.search(ln)) + "\n"
        return text

    # ------------------------------------------------------------------ text utils
    def cmd_sort(self, a, s):
        reverse = "-r" in a
        numeric = "-n" in a
        uniq = "-u" in a
        lines = s.splitlines()
        if numeric:
            def key(x):
                try:
                    return (0, float(x.split()[0]))
                except (ValueError, IndexError):
                    return (1, 0)
            lines.sort(key=key, reverse=reverse)
        else:
            lines.sort(reverse=reverse)
        if uniq:
            seen = []
            for ln in lines:
                if ln not in seen:
                    seen.append(ln)
            lines = seen
        return CmdResult("\n".join(lines) + ("\n" if lines else ""))

    def cmd_uniq(self, a, s):
        count = "-c" in a
        out = []
        prev = object()
        n = 0
        for ln in s.splitlines():
            if ln == prev:
                n += 1
            else:
                if prev is not object.__new__ and n:
                    out.append((f"{n:>7} " if count else "") + prev)
                prev, n = ln, 1
        if n:
            out.append((f"{n:>7} " if count else "") + prev)
        return CmdResult("\n".join(out) + ("\n" if out else ""))

    def cmd_cut(self, a, s):
        delim = "\t"
        fields = None
        it = iter(a)
        for x in it:
            if x.startswith("-d"):
                delim = x[2:] or next(it, "\t")
            elif x.startswith("-f"):
                fields = x[2:] or next(it, "1")
        out = []
        idx = []
        if fields:
            for part in fields.split(","):
                if "-" in part:
                    lo, hi = part.split("-")
                    idx.extend(range(int(lo), int(hi) + 1))
                else:
                    idx.append(int(part))
        for ln in s.splitlines():
            cols = ln.split(delim)
            out.append(delim.join(cols[i - 1] for i in idx if 0 < i <= len(cols)))
        return CmdResult("\n".join(out) + ("\n" if out else ""))

    def cmd_tr(self, a, s):
        args = [x for x in a if not x.startswith("-")]
        delete = "-d" in a
        if delete and args:
            return CmdResult("".join(c for c in s if c not in args[0]))
        if len(args) >= 2:
            table = str.maketrans(args[0], args[1][:len(args[0])].ljust(len(args[0]), args[1][-1]))
            return CmdResult(s.translate(table))
        return CmdResult(s)

    def cmd_rev(self, a, s):
        return CmdResult("\n".join(ln[::-1] for ln in s.splitlines()) + "\n")

    def cmd_nl(self, a, s):
        out = [f"{i:>6}\t{ln}" for i, ln in enumerate(s.splitlines(), 1)]
        return CmdResult("\n".join(out) + ("\n" if out else ""))

    def cmd_less(self, a, s):
        return self.cmd_cat(a, s)
    cmd_more = cmd_less

    def cmd_diff(self, a, s):
        files = [x for x in a if not x.startswith("-")]
        if len(files) < 2:
            return self.err("usage: diff FILE1 FILE2")
        import difflib
        x = self.world.fs.read(self.abspath(files[0])).splitlines()
        y = self.world.fs.read(self.abspath(files[1])).splitlines()
        d = list(difflib.unified_diff(x, y, files[0], files[1], lineterm=""))
        return CmdResult("\n".join(d) + ("\n" if d else ""))

    def cmd_md5sum(self, a, s):
        import hashlib
        return self._sum(a, s, hashlib.md5)

    def cmd_sha256sum(self, a, s):
        import hashlib
        return self._sum(a, s, hashlib.sha256)

    def _sum(self, a, s, fn):
        files = [x for x in a if not x.startswith("-")]
        out = []
        if not files:
            out.append(fn(s.encode()).hexdigest() + "  -")
        for f in files:
            try:
                content = self.world.fs.read(self.abspath(f))
                out.append(fn(content.encode()).hexdigest() + "  " + f)
            except FSError:
                out.append(f"{f}: No such file or directory")
        return CmdResult("\n".join(out) + "\n")

    def cmd_basename(self, a, s):
        return CmdResult((posixpath.basename(a[0]) if a else "") + "\n")

    def cmd_dirname(self, a, s):
        return CmdResult((posixpath.dirname(a[0]) or "." if a else ".") + "\n")

    def cmd_true(self, a, s):
        return CmdResult("")

    def cmd_false(self, a, s):
        return CmdResult("", 1)

    def cmd_yes(self, a, s):
        word = " ".join(a) if a else "y"
        return CmdResult((word + "\n") * 5)

    def cmd_sleep(self, a, s):
        return CmdResult("")

    def cmd_ln(self, a, s):
        args = [x for x in a if not x.startswith("-")]
        if len(args) >= 2:
            node = self.world.fs.get(self.abspath(args[0]))
            if node:
                self.world.fs.write(self.abspath(args[1]), node.content, mode=node.mode, owner=self.user)
        return CmdResult("")

    # ------------------------------------------------------------------ system info
    def cmd_whoami(self, a, s):
        return CmdResult(self.user + "\n")

    def cmd_id(self, a, s):
        if self.user == "root":
            return CmdResult("uid=0(root) gid=0(root) groups=0(root)\n")
        return CmdResult("uid=1000(player) gid=1000(player) groups=1000(player),4(adm),27(sudo)\n")

    def cmd_groups(self, a, s):
        return CmdResult(" ".join(self.groups) + "\n")

    def cmd_hostname(self, a, s):
        return CmdResult("websrv01\n")

    def cmd_uname(self, a, s):
        if "-a" in a:
            return CmdResult("Linux websrv01 6.1.0-cyberos #1 SMP x86_64 CyberOS/Linux\n")
        if "-r" in a:
            return CmdResult("6.1.0-cyberos\n")
        return CmdResult("Linux\n")

    def cmd_date(self, a, s):
        return CmdResult(self.world.now().strftime("%a %b %e %H:%M:%S UTC %Y") + "\n")

    def cmd_uptime(self, a, s):
        load = self.world.load
        return CmdResult(f" {self.world.now():%H:%M:%S} up 2:14,  1 user,  "
                         f"load average: {load:.2f}, {max(0.1,load*0.8):.2f}, {max(0.1,load*0.6):.2f}\n")

    def cmd_w(self, a, s):
        return CmdResult("USER     TTY      FROM             LOGIN@   WHAT\n"
                         "player   pts/0    10.0.0.5         09:00    -sh\n")
    cmd_who = cmd_w

    def cmd_last(self, a, s):
        return CmdResult("player   pts/0    10.0.0.5     Fri 09:00   still logged in\n"
                         "root     pts/0    10.0.0.5     Fri 08:30 - 08:55  (00:25)\n")

    def cmd_env(self, a, s):
        return CmdResult("".join(f"{k}={v}\n" for k, v in self.env.items()))

    def cmd_export(self, a, s):
        for x in a:
            if "=" in x:
                k, v = x.split("=", 1)
                self.env[k] = v
        return CmdResult("")

    def cmd_history(self, a, s):
        return CmdResult("".join(f"{i:>5}  {h}\n" for i, h in enumerate(self.history, 1)))

    def cmd_clear(self, a, s):
        return CmdResult("\x0c")

    def cmd_free(self, a, s):
        used = int(400 + self.world.load * 180)
        return CmdResult("               total        used        free      shared  buff/cache   available\n"
                         f"Mem:            3934        {used:>5}        {3934-used:>5}         45         {892:>5}       {3934-used-100:>5}\n"
                         "Swap:            974           0         974\n")

    def cmd_df(self, a, s):
        return CmdResult("Filesystem     1K-blocks     Used Available Use% Mounted on\n"
                         "/dev/vda1       41153856  9821044  29210628  26% /\n"
                         "tmpfs            2014208        0   2014208   0% /dev/shm\n")

    def cmd_du(self, a, s):
        base = self.abspath(a[-1]) if a and not a[-1].startswith("-") else self.cwd
        total = sum(n.size for _, n in self.world.fs.walk(base))
        return CmdResult(f"{total // 1024 + 1}\t{base}\n")

    # ------------------------------------------------------------------ processes
    def cmd_ps(self, a, s):
        flags = "".join(a)
        procs = sorted(self.world.procs, key=lambda p: p.pid)
        if "aux" in flags or "au" in flags:
            lines = ["USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND"]
            for p in procs:
                vsz = int(p.mem * 10000) + 20000
                rss = int(p.mem * 4000) + 2000
                stat = "Ss" if p.tty == "?" else "S+"
                if p.cpu > 50:
                    stat = "R" + stat[1:]
                lines.append(f"{p.user:<9} {p.pid:>5} {p.cpu:>4.1f} {p.mem:>4.1f} {vsz:>6} {rss:>5} "
                             f"{p.tty:<8} {stat:<4} {p.start}   0:00 {p.cmd}")
            return CmdResult("\n".join(lines) + "\n")
        lines = ["  PID TTY          TIME CMD"]
        for p in procs:
            if "e" in flags or p.user == self.user or self.user == "root":
                lines.append(f"{p.pid:>5} {p.tty:<12} 00:00:00 {p.name}")
        return CmdResult("\n".join(lines) + "\n")

    def cmd_top(self, a, s):
        procs = sorted(self.world.procs, key=lambda p: p.cpu, reverse=True)[:12]
        head = (f"top - {self.world.now():%H:%M:%S} up 2:14,  1 user,  load average: {self.world.load:.2f}\n"
                f"Tasks: {len(self.world.procs)} total\n"
                f"%Cpu(s): {min(99.9, self.world.load*12):.1f} us\n\n"
                "  PID USER      %CPU %MEM COMMAND")
        lines = [head]
        for p in procs:
            lines.append(f"{p.pid:>5} {p.user:<9} {p.cpu:>4.1f} {p.mem:>4.1f} {p.name}")
        return CmdResult("\n".join(lines) + "\n")

    def cmd_kill(self, a, s):
        sig = 15
        pids = []
        for x in a:
            if x.startswith("-"):
                token = x[1:]
                sig = int(token) if token.isdigit() else (9 if token.upper() in ("KILL", "9") else 15)
            else:
                pids.append(x)
        errs = []
        for ps in pids:
            try:
                pid = int(ps)
            except ValueError:
                errs.append(f"kill: {ps}: arguments must be process IDs")
                continue
            p = self.world.proc(pid)
            if p is None:
                errs.append(f"kill: ({pid}) - No such process")
                continue
            if self.user != "root" and p.user != self.user:
                errs.append(f"kill: ({pid}) - Operation not permitted")
                continue
            self.world.kill(p)
        return CmdResult("\n".join(errs) + ("\n" if errs else ""), 1 if errs else 0)

    def cmd_killall(self, a, s):
        names = [x for x in a if not x.startswith("-")]
        killed = 0
        for p in list(self.world.procs):
            if p.name in names or any(n in p.cmd for n in names):
                if self.user == "root" or p.user == self.user:
                    self.world.kill(p)
                    killed += 1
        if not killed:
            return self.err(f"{names[0] if names else ''}: no process found")
        return CmdResult("")
    cmd_pkill = cmd_killall

    # ------------------------------------------------------------------ networking (read)
    def cmd_ifconfig(self, a, s):
        return CmdResult(
            "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
            "        inet 192.0.2.10  netmask 255.255.255.0  broadcast 192.0.2.255\n"
            "        RX packets 918273  TX packets 772311\n\n"
            "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n"
            "        inet 127.0.0.1  netmask 255.0.0.0\n")

    def cmd_ip(self, a, s):
        if a and a[0] in ("a", "addr", "address"):
            return CmdResult("1: lo: <LOOPBACK,UP> mtu 65536\n    inet 127.0.0.1/8 scope host lo\n"
                             "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500\n    inet 192.0.2.10/24 scope global eth0\n")
        if a and a[0] in ("r", "route"):
            return CmdResult("default via 192.0.2.1 dev eth0\n192.0.2.0/24 dev eth0 proto kernel scope link\n")
        return CmdResult("Usage: ip [ addr | route ]\n")

    def cmd_ping(self, a, s):
        host = next((x for x in a if not x.startswith("-")), "")
        if not host:
            return self.err("usage: ping HOST")
        return CmdResult(f"PING {host}: 56 data bytes\n"
                         f"64 bytes from {host}: icmp_seq=0 ttl=56 time=12.3 ms\n"
                         f"64 bytes from {host}: icmp_seq=1 ttl=56 time=11.8 ms\n"
                         f"--- {host} ping statistics ---\n2 packets transmitted, 2 received, 0% packet loss\n")

    def cmd_netstat(self, a, s):
        flags = "".join(x[1:] for x in a if x.startswith("-"))
        show_listen = "l" in flags or "a" in flags
        numeric = "n" in flags or True
        show_prog = "p" in flags
        want_tcp = "t" in flags or not ("u" in flags and "t" not in flags)
        want_udp = "u" in flags
        if not ("t" in flags or "u" in flags):
            want_tcp = want_udp = True
        lines = ["Active Internet connections (servers and established)",
                 "Proto Recv-Q Send-Q Local Address           Foreign Address         State       " + ("PID/Program name" if show_prog else "")]
        w = self.world
        if show_listen:
            for port, proto, bind, svc in w.listening():
                if proto == "tcp" and not want_tcp:
                    continue
                if proto == "udp" and not want_udp:
                    continue
                local = f"{bind}:{port}"
                state = "LISTEN" if proto == "tcp" else ""
                prog = f"{svc.pid}/{svc.proc.split()[0].split('/')[-1][:12]}" if show_prog else ""
                lines.append(f"{proto:<5} {0:>6} {0:>6} {local:<23} {'0.0.0.0:*':<23} {state:<11} {prog}")
        for f in w.flows():
            if f.proto == "tcp" and not want_tcp:
                continue
            if f.proto == "udp" and not want_udp:
                continue
            if f.state == "LISTEN":
                continue
            local = f"{('192.0.2.10')}:{f.lport}"
            foreign = f"{f.remote}:{f.rport}"
            prog = ""
            if show_prog and f.proc:
                svc = w.service(f.proc)
                prog = f"{svc.pid}/{f.proc[:12]}" if svc else f"-/{f.proc[:12]}"
            lines.append(f"{f.proto:<5} {0:>6} {0:>6} {local:<23} {foreign:<23} {f.state:<11} {prog}")
        return CmdResult("\n".join(lines) + "\n")

    def cmd_ss(self, a, s):
        return self.cmd_netstat(a, s)

    def cmd_lsof(self, a, s):
        want_port = None
        for i, x in enumerate(a):
            if x.startswith("-i"):
                spec = x[2:] or (a[i + 1] if i + 1 < len(a) else "")
                if ":" in spec:
                    try:
                        want_port = int(spec.split(":")[-1])
                    except ValueError:
                        pass
        lines = ["COMMAND   PID     USER   FD   TYPE  NODE NAME"]
        w = self.world
        for port, proto, bind, svc in w.listening():
            if want_port and port != want_port:
                continue
            lines.append(f"{svc.proc.split()[0].split('/')[-1][:8]:<9} {svc.pid:<7} {svc.user:<7} "
                         f"{4:>3}u  IPv4  {proto.upper()} {bind}:{port} (LISTEN)")
        for f in w.flows():
            if want_port and f.port != want_port:
                continue
            svc = w.service(f.proc) if f.proc else None
            pid = svc.pid if svc else "-"
            lines.append(f"{(f.proc or '?')[:8]:<9} {str(pid):<7} {'root':<7} {5:>3}u  IPv4  "
                         f"{f.proto.upper()} 192.0.2.10:{f.lport}->{f.remote}:{f.rport} ({f.state})")
        return CmdResult("\n".join(lines) + "\n")

    def cmd_tcpdump(self, a, s):
        count = None
        port = None
        host = None
        it = iter(a)
        for x in it:
            if x == "-c":
                count = int(next(it, "0"))
            elif x.startswith("-c"):
                count = int(x[2:])
            elif x == "port":
                port = int(next(it, "0"))
            elif x == "host":
                host = next(it, "")
            elif x in ("src", "dst"):
                nxt = next(it, "")
                if nxt == "port":
                    port = int(next(it, "0"))
                else:
                    host = nxt
        w = self.world
        flows = w.flows()
        if port is not None:
            flows = [f for f in flows if f.port == port or f.lport == port or f.rport == port]
        if host is not None:
            flows = [f for f in flows if f.remote == host]
        lines = [f"tcpdump: listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes"]
        n = 0
        tbase = w.now()
        import datetime as _dt
        for i, f in enumerate(flows):
            if count and n >= count:
                break
            t = (tbase + _dt.timedelta(milliseconds=i * 37)).strftime("%H:%M:%S.%f")[:-3]
            if f.direction == "in":
                src, dst = f"{f.remote}.{f.rport}", f"192.0.2.10.{f.lport}"
            else:
                src, dst = f"192.0.2.10.{f.lport}", f"{f.remote}.{f.rport}"
            lines.append(f"{t} IP {src} > {dst}: {f.proto.upper()} {f.packet}")
            n += 1
        lines.append(f"{n} packets captured")
        return CmdResult("\n".join(lines) + "\n")

    # ------------------------------------------------------------------ firewall: ufw
    def cmd_ufw(self, a, s):
        self.need_root("ufw")
        fw = self.world.fw
        if not a:
            return self.err("usage: see 'man ufw'")
        sub = a[0]
        if sub == "enable":
            fw.ufw_enabled = True
            return CmdResult("Firewall is active and enabled on system startup\n")
        if sub == "disable":
            fw.ufw_enabled = False
            return CmdResult("Firewall stopped and disabled on system startup\n")
        if sub == "reset":
            fw.rules.clear()
            fw.ufw_enabled = False
            return CmdResult("Firewall reset to installed defaults\n")
        if sub == "status":
            return self._ufw_status("verbose" in a)
        if sub == "default":
            if len(a) >= 3:
                policy, direction = a[1], a[2]
                if "in" in direction:
                    fw.default_in = policy
                elif "out" in direction:
                    fw.default_out = policy
                return CmdResult(f"Default {direction} policy changed to '{policy}'\n(be sure to update your rules accordingly)\n")
            return self.err("usage: ufw default allow|deny incoming|outgoing")
        if sub == "delete":
            return self._ufw_delete(a[1:])
        if sub in ("allow", "deny", "reject", "limit"):
            return self._ufw_rule(sub, a[1:])
        return self.err(f"ufw: unknown command '{sub}'")

    def _ufw_rule(self, action, args):
        fw = self.world.fw
        direction = "in"
        remote = None
        port = None
        proto = None
        it = iter(args)
        for x in it:
            if x == "in":
                direction = "in"
            elif x == "out":
                direction = "out"
            elif x == "from":
                remote = next(it, None)
            elif x == "to":
                nxt = next(it, None)
                if nxt == "any":
                    pass
            elif x in ("port",):
                spec = next(it, "")
                port, proto = self._portspec(spec)
            elif x == "proto":
                proto = next(it, None)
            elif "/" in x and x.split("/")[0].isdigit():
                port, proto = self._portspec(x)
            elif x.isdigit():
                port = int(x)
            elif x in SERVICE_NAMES.values() or x in ("ssh", "http", "https", "mysql", "ftp", "telnet", "smtp", "dns",
                                                       "redis", "pop3", "imap", "ipp", "postgresql", "mongodb"):
                mapping = {"ssh": 22, "http": 80, "https": 443, "mysql": 3306, "ftp": 21, "telnet": 23, "smtp": 25,
                           "dns": 53, "redis": 6379, "pop3": 110, "imap": 143, "ipp": 631, "postgresql": 5432, "mongodb": 27017}
                port = mapping.get(x)
        net = None
        if remote:
            try:
                net = ipaddress.ip_network(remote, strict=False)
            except ValueError:
                return self.err(f"ERROR: Bad source address {remote}")
        rule = UfwRule(action, direction, net, port, proto)
        # replace duplicate
        fw.rules = [r for r in fw.rules if r.key() != rule.key()]
        fw.rules.append(rule)
        if not fw.ufw_enabled:
            return CmdResult("Rules updated\n(note: ufw is not enabled yet - run 'ufw enable')\n")
        return CmdResult("Rule added\n")

    def _portspec(self, spec):
        if "/" in spec:
            p, proto = spec.split("/", 1)
            return (int(p) if p.isdigit() else None, proto)
        return (int(spec) if spec.isdigit() else None, None)

    def _ufw_delete(self, args):
        fw = self.world.fw
        if args and args[0].isdigit():
            idx = int(args[0]) - 1
            if 0 <= idx < len(fw.rules):
                del fw.rules[idx]
                return CmdResult("Rule deleted\n")
            return self.err("Could not delete non-existent rule")
        if args and args[0] in ("allow", "deny", "reject", "limit"):
            action = args[0]
            before = len(fw.rules)
            port, proto = (None, None)
            remote = None
            it = iter(args[1:])
            for x in it:
                if x == "from":
                    remote = next(it, None)
                elif "/" in x or x.isdigit():
                    port, proto = self._portspec(x)
            net = ipaddress.ip_network(remote, strict=False) if remote else None
            fw.rules = [r for r in fw.rules if not (r.action == action and r.port == port and str(r.remote) == str(net))]
            return CmdResult("Rule deleted\n" if len(fw.rules) < before else "Could not delete non-existent rule\n")
        return self.err("usage: ufw delete NUM | ufw delete allow PORT")

    def _ufw_status(self, verbose):
        fw = self.world.fw
        if not fw.ufw_enabled:
            return CmdResult("Status: inactive\n")
        out = ["Status: active"]
        if verbose:
            out.append(f"Default: {fw.default_in} (incoming), {fw.default_out} (outgoing)")
        out.append("")
        out.append("To                         Action      From")
        out.append("--                         ------      ----")
        for r in fw.rules:
            out.append(r.describe())
        return CmdResult("\n".join(out) + "\n")

    # ------------------------------------------------------------------ firewall: iptables
    def cmd_iptables(self, a, s):
        self.need_root("iptables")
        fw = self.world.fw
        if "-L" in a or "-S" in a:
            return self._ipt_list(a)
        if "-F" in a:
            for chain in fw.ipt:
                fw.ipt[chain].clear()
            return CmdResult("")
        if "-A" in a or "-I" in a:
            return self._ipt_add(a)
        if "-D" in a:
            return self._ipt_del(a)
        return self.err("usage: see 'man iptables'")

    def _ipt_parse(self, a):
        chain = "INPUT"
        target = "DROP"
        src = dst = proto = None
        dport = None
        it = iter(a)
        for x in it:
            if x in ("-A", "-I", "-D"):
                chain = next(it, "INPUT").upper()
            elif x == "-j":
                target = next(it, "DROP").upper()
            elif x == "-s":
                src = next(it, None)
            elif x == "-d":
                dst = next(it, None)
            elif x == "-p":
                proto = next(it, None)
            elif x == "--dport":
                dport = int(next(it, "0"))
            elif x == "--sport":
                next(it, "0")
        srcn = ipaddress.ip_network(src, strict=False) if src else None
        dstn = ipaddress.ip_network(dst, strict=False) if dst else None
        return IptRule(chain, target, srcn, dstn, proto, dport)

    def _ipt_add(self, a):
        try:
            rule = self._ipt_parse(a)
        except ValueError as e:
            return self.err(f"iptables: bad argument ({e})")
        chain = self.world.fw.ipt.setdefault(rule.chain, [])
        if "-I" in a:
            chain.insert(0, rule)
        else:
            chain.append(rule)
        return CmdResult("")

    def _ipt_del(self, a):
        rule = self._ipt_parse(a)
        chain = self.world.fw.ipt.get(rule.chain, [])
        for i, r in enumerate(chain):
            if (r.target, str(r.src), str(r.dst), r.proto, r.dport) == (rule.target, str(rule.src), str(rule.dst), rule.proto, rule.dport):
                del chain[i]
                return CmdResult("")
        return self.err("iptables: Bad rule (does a matching rule exist in that chain?)")

    def _ipt_list(self, a):
        fw = self.world.fw
        chains = [x for x in a if x in fw.ipt]
        order = chains or ["INPUT", "FORWARD", "OUTPUT"]
        out = []
        for chain in order:
            out.append(f"Chain {chain} (policy ACCEPT)")
            out.append("target     prot opt source               destination")
            for r in fw.ipt.get(chain, []):
                out.append(r.describe())
            out.append("")
        return CmdResult("\n".join(out))

    # ------------------------------------------------------------------ services
    def cmd_systemctl(self, a, s):
        if not a:
            return self.cmd_systemctl(["list-units"], s)
        sub = a[0]
        name = a[1] if len(a) > 1 else None
        w = self.world
        if sub in ("list-units", "list-unit-files", "--type=service"):
            lines = ["UNIT                     LOAD   ACTIVE SUB     DESCRIPTION"]
            for svc in w.services.values():
                active = "active" if svc.running else "inactive"
                sub_s = "running" if svc.running else "dead"
                lines.append(f"{svc.unit + '.service':<24} loaded {active:<6} {sub_s:<7} {svc.desc}")
            return CmdResult("\n".join(lines) + "\n")
        if name is None:
            return self.err(f"systemctl: expected a unit name")
        svc = w.service(name)
        if svc is None:
            if sub == "status":
                return CmdResult(f"Unit {name}.service could not be found.\n", 4)
            return self.err(f"Failed to {sub} {name}.service: Unit {name}.service not found.")
        if sub == "status":
            return self._svc_status(svc)
        self.need_root("systemctl " + sub)
        if sub == "stop":
            w.stop_service(svc)
            return CmdResult("")
        if sub == "start":
            w.start_service(svc)
            return CmdResult("")
        if sub == "restart" or sub == "reload":
            w.restart_service(svc)
            return CmdResult("")
        if sub == "enable":
            svc.enabled = True
            return CmdResult(f"Created symlink /etc/systemd/system/multi-user.target.wants/{svc.unit}.service.\n")
        if sub == "disable":
            svc.enabled = False
            return CmdResult(f"Removed /etc/systemd/system/multi-user.target.wants/{svc.unit}.service.\n")
        if sub in ("daemon-reload",):
            return CmdResult("")
        return self.err(f"Unknown operation {sub}.")

    def _svc_status(self, svc):
        dot = "●" if svc.running else "○"
        active = (f"active (running)" if svc.running else "inactive (dead)")
        restart_note = ""
        if svc.needs_restart:
            restart_note = "\n   Note: configuration on disk has changed - restart to apply."
        return CmdResult(
            f"{dot} {svc.unit}.service - {svc.desc}\n"
            f"     Loaded: loaded (/lib/systemd/system/{svc.unit}.service; {'enabled' if svc.enabled else 'disabled'})\n"
            f"     Active: {active}\n"
            + (f"   Main PID: {svc.pid} ({svc.proc.split()[0].split('/')[-1]})\n" if svc.running else "")
            + restart_note + "\n", 0 if svc.running else 3)

    def cmd_service(self, a, s):
        if len(a) >= 2:
            name, action = a[0], a[1]
            return self.cmd_systemctl([action, name], s)
        return self.err("usage: service NAME start|stop|restart|status")

    # ------------------------------------------------------------------ sysctl
    def cmd_sysctl(self, a, s):
        w = self.world
        if "-a" in a:
            return CmdResult("".join(f"{k} = {v}\n" for k, v in sorted(w.sysctl.items())))
        if "-p" in a:
            self.need_root("sysctl -p")
            node = w.fs.get("/etc/sysctl.conf")
            applied = 0
            if node:
                for line in node.content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        w.sysctl[k.strip()] = v.strip()
                        applied += 1
            return CmdResult("".join(f"{k} = {w.sysctl[k]}\n" for k in w.sysctl if applied))
        if "-w" in a or any("=" in x for x in a):
            self.need_root("sysctl -w")
            for x in a:
                if "=" in x:
                    k, v = x.split("=", 1)
                    w.sysctl[k.strip()] = v.strip()
                    return CmdResult(f"{k.strip()} = {v.strip()}\n")
        # read
        for x in a:
            if not x.startswith("-"):
                if x in w.sysctl:
                    return CmdResult(f"{x} = {w.sysctl[x]}\n")
                return self.err(f"sysctl: cannot stat /proc/sys/{x.replace('.','/')}: No such file or directory")
        return self.err("usage: sysctl [-w] name[=value]")

    # ------------------------------------------------------------------ packages
    def cmd_apt(self, a, s):
        w = self.world
        if not a:
            return self.err("usage: apt COMMAND")
        sub = a[0]
        if sub == "update":
            self.need_root("apt update")
            return CmdResult("Hit:1 http://deb.cyberos.org stable InRelease\nReading package lists... Done\n")
        if sub in ("list",):
            if "--installed" in a:
                lines = ["Listing... Done"]
                for name, info in sorted(w.packages.items()):
                    lines.append(f"{name}/stable,now {info['installed']} amd64 [installed]")
                return CmdResult("\n".join(lines) + "\n")
            return CmdResult("Listing... Done\n")
        if sub == "policy":
            if len(a) < 2:
                return self.err("usage: apt policy PACKAGE")
            name = a[1]
            info = w.packages.get(name)
            if not info:
                return CmdResult(f"N: Unable to locate package {name}\n", 1)
            return CmdResult(f"{name}:\n  Installed: {info['installed']}\n  Candidate: {info['candidate']}\n"
                             f"  Version table:\n *** {info['installed']} 100\n     {info['candidate']} 500\n")
        if sub in ("install", "reinstall"):
            self.need_root("apt install")
            return self._apt_install(a[1:])
        if sub in ("remove", "purge", "autoremove"):
            self.need_root("apt remove")
            return self._apt_remove(a[1:])
        if sub in ("show",):
            name = a[1] if len(a) > 1 else ""
            info = w.packages.get(name)
            if not info:
                return CmdResult(f"N: Unable to locate package {name}\n", 1)
            return CmdResult(f"Package: {name}\nVersion: {info['installed']}\nDescription: {info['desc']}\n")
        if sub == "upgrade":
            self.need_root("apt upgrade")
            return CmdResult("Reading package lists... Done\n0 upgraded, 0 newly installed.\n")
        return self.err(f"E: Invalid operation {sub}")

    cmd_apt_get = cmd_apt

    def _apt_install(self, pkgs):
        w = self.world
        out = []
        for spec in pkgs:
            if spec.startswith("-"):
                continue
            if "=" in spec:
                name, ver = spec.split("=", 1)
            else:
                name, ver = spec, None
            info = w.packages.get(name)
            if not info:
                out.append(f"E: Unable to locate package {name}")
                continue
            target = ver or info["candidate"]
            info["installed"] = target
            out.append(f"Selecting previously unselected package {name}.\n"
                       f"Setting up {name} ({target}) ...")
            # downgrading liblzma affects the ssh service's need-to-restart state
            svc = w.service("ssh")
            if name in ("liblzma5", "xz-utils") and svc:
                svc.needs_restart = True
        return CmdResult("Reading package lists... Done\nBuilding dependency tree... Done\n" + "\n".join(out) + "\n")

    def _apt_remove(self, pkgs):
        w = self.world
        out = []
        for name in pkgs:
            if name.startswith("-"):
                continue
            if name in w.packages:
                svc = w.service(name.replace("-server", "").replace("cups-browsed", "cups-browsed"))
                b = w.service("cups-browsed") if name == "cups-browsed" else None
                if b:
                    w.stop_service(b)
                out.append(f"Removing {name} ...")
            else:
                out.append(f"E: Unable to locate package {name}")
        return CmdResult("\n".join(out) + "\n")

    def cmd_dpkg(self, a, s):
        w = self.world
        if "-l" in a:
            lines = ["Desired=Unknown/Install/Remove/Purge/Hold",
                     "| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend",
                     "||/ Name           Version         Architecture Description",
                     "+++-==============-===============-============-================================"]
            for name, info in sorted(w.packages.items()):
                lines.append(f"ii  {name:<14} {info['installed']:<15} amd64        {info['desc'][:40]}")
            return CmdResult("\n".join(lines) + "\n")
        if "-s" in a or "--status" in a:
            name = a[-1]
            info = w.packages.get(name)
            if info:
                return CmdResult(f"Package: {name}\nStatus: install ok installed\nVersion: {info['installed']}\n")
            return CmdResult(f"dpkg-query: package '{name}' is not installed\n", 1)
        if "-L" in a:
            return CmdResult(f"/.\n/usr\n/usr/bin\n")
        return self.err("usage: dpkg -l | dpkg -s PACKAGE")

    # ------------------------------------------------------------------ redis-cli
    def cmd_redis_cli(self, a, s):
        w = self.world
        args = a
        if args and args[0] == "-a":
            args = args[2:]
        if len(args) >= 2 and args[0].upper() == "CONFIG":
            action = args[1].upper()
            if action == "GET" and len(args) >= 3:
                key = args[2]
                val = w.redis.get(key, "")
                return CmdResult(f"1) \"{key}\"\n2) \"{val}\"\n")
            if action == "SET" and len(args) >= 4:
                key, val = args[2], args[3]
                w.redis[key] = val
                svc = w.service("redis")
                if svc:
                    svc.needs_restart = False  # redis-cli applies live
                if key == "bind":
                    svc.bind = val.split()[0]
                return CmdResult("OK\n")
        if args and args[0].upper() == "PING":
            return CmdResult("PONG\n")
        if args and args[0].upper() == "SHUTDOWN":
            self.world.stop_service(w.service("redis"))
            return CmdResult("")
        return CmdResult("OK\n")

    # ------------------------------------------------------------------ cron
    def cmd_crontab(self, a, s):
        w = self.world
        user = self.user
        it = iter(a)
        action = None
        for x in it:
            if x == "-u":
                user = next(it, user)
            elif x in ("-l", "-r", "-e"):
                action = x
        path = f"/var/spool/cron/crontabs/{user}"
        if action == "-l":
            node = w.fs.get(path)
            if node is None:
                return CmdResult(f"no crontab for {user}\n", 1)
            return CmdResult(node.content)
        if action == "-r":
            if user != self.user:
                self.need_root("crontab -u")
            if w.fs.remove(path):
                return CmdResult("")
            return CmdResult(f"no crontab for {user}\n", 1)
        if action == "-e":
            return CmdResult("", editor=("nano", path, self.user))
        return self.err("usage: crontab -l | -r | -u USER -l")

    # ------------------------------------------------------------------ printers
    def cmd_lpstat(self, a, s):
        w = self.world
        lines = []
        for name, uri in w.printers.items():
            lines.append(f"printer {name} is idle.  enabled since today\n    {uri}")
        return CmdResult("\n".join(lines) + ("\n" if lines else "no destinations added.\n"))

    def cmd_lpadmin(self, a, s):
        self.need_root("lpadmin")
        it = iter(a)
        for x in it:
            if x == "-x":
                name = next(it, "")
                if name in self.world.printers:
                    del self.world.printers[name]
                    return CmdResult("")
                return self.err(f"lpadmin: Printer {name} not found")
        return CmdResult("")

    def cmd_xz(self, a, s):
        if "--version" in a:
            ver = self.world.packages.get("xz-utils", {}).get("installed", "5.4.1")
            return CmdResult(f"xz (XZ Utils) {ver}\nliblzma {self.world.packages.get('liblzma5',{}).get('installed','5.4.1')}\n")
        return CmdResult("")

    def cmd_tar(self, a, s):
        return CmdResult("")

    # ------------------------------------------------------------------ help / game
    def cmd_exit(self, a, s):
        if self.user == "root":
            self.user = "player"
            self.env["USER"] = "player"
            self.env["HOME"] = "/home/player"
            return CmdResult("")
        return CmdResult("__EXIT__")

    def cmd_man(self, a, s):
        if not a:
            return self.err("What manual page do you want?")
        page = manpages.get(a[0], self.tr.lang)
        if page is None:
            return CmdResult(self._("sh.man_none", cmd=a[0]) + "\n", 1)
        return CmdResult(page + "\n\n" + self._("sh.man_limited") + "\n")

    def cmd_alias(self, a, s):
        if a and "=" in a[0]:
            name, _, val = " ".join(a).partition("=")
            self.aliases[name.strip()] = val.strip().strip("'\"")
            return CmdResult("")
        if a:  # `alias ll` -> show one
            name = a[0]
            if name in self.aliases:
                return CmdResult(f"alias {name}='{self.aliases[name]}'\n")
            return self.err(f"alias: {name}: not found")
        lines = [f"alias {k}='{v}'" for k, v in sorted(self.aliases.items())]
        return CmdResult("\n".join(lines) + ("\n" if lines else ""))

    def cmd_help(self, a, s):
        lines = [self._("sh.type_help"), ""]
        cols = 6
        cmds = COMMANDS
        for i in range(0, len(cmds), cols):
            lines.append("  " + "  ".join(f"{c:<10}" for c in cmds[i:i + cols]))
        lines.append("")
        lines.append("Game commands: mission  objectives  hint  man <cmd>  menu")
        return CmdResult("\n".join(lines) + "\n")

    def cmd_mission(self, a, s):
        key = f"lvl.{self.level_num}.name"
        brief = f"lvl.{self.level_num}.brief"
        head = f"=== {self._('sel.level')} {self.level_num}: {self._(key)} ==="
        return CmdResult(head + "\n\n" + self._(brief) + "\n")

    def cmd_objectives(self, a, s):
        lvl = self.world.level
        if not lvl:
            return CmdResult("")
        lines = [self._("hud.objectives") + ":"]
        for done, key in lvl.objectives():
            mark = "[x]" if done else "[ ]"
            lines.append(f"  {mark} {self._(key)}")
        if lvl.solved():
            lines.append("")
            lines.append(self._("sh.objectives_done"))
        return CmdResult("\n".join(lines) + "\n")

    def cmd_hint(self, a, s):
        hints = HINTS.get(self.level_num, [])
        if self.hint_idx >= len(hints):
            return CmdResult(self._("sh.no_hint") + "\n")
        pair = hints[self.hint_idx]
        self.hint_idx += 1
        self.save.add_hint(self.level_num)
        self.save.write()
        text = pair[1] if self.tr.lang == "ja" else pair[0]
        return CmdResult(f"[{self.hint_idx}/{len(hints)}] {text}\n" + self._("sh.hint_recorded") + "\n")

    def cmd_menu(self, a, s):
        return CmdResult("__MENU__")


# ---------------------------------------------------------------- hints
HINTS = {
    1: [("Use 'tcpdump -n port 80' to see the flood, and note the attacking IPs.",
         "'tcpdump -n port 80' で洪水を確認し、攻撃元IPをメモしよう。"),
        ("Block a whole subnet with: sudo ufw deny from 198.51.100.0/24 - then 'sudo ufw enable'.",
         "サブネット遮断: sudo ufw deny from 198.51.100.0/24 - その後 'sudo ufw enable'。"),
        ("Turn on SYN cookies: sudo sysctl -w net.ipv4.tcp_syncookies=1  (don't stop apache2!).",
         "SYN cookie有効化: sudo sysctl -w net.ipv4.tcp_syncookies=1  （apache2は止めない！）。")],
    2: [("Read /var/www/html/products.php - the id is put straight into the SQL query.",
         "/var/www/html/products.php を確認 - idがSQLにそのまま入っている。"),
        ("MySQL must not face the Internet: sudo ufw enable then sudo ufw deny 3306/tcp.",
         "MySQLはネット非公開に: sudo ufw enable 後 sudo ufw deny 3306/tcp。"),
        ("Patch the code with sed, casting id to int: sudo sed -i \"s/\\$_GET\\['id'\\]/intval(\\$_GET['id'])/\" /var/www/html/products.php",
         "sedでidを整数化: sudo sed -i \"s/\\$_GET\\['id'\\]/intval(\\$_GET['id'])/\" /var/www/html/products.php")],
    3: [("Find it: find /var/www -name '*.php'  and read the suspicious upload.",
         "探す: find /var/www -name '*.php' で不審なアップロードを確認。"),
        ("Kill the web shell process (ps aux | grep avatar) then delete the file with sudo rm.",
         "ウェブシェルのプロセスを停止(ps aux | grep avatar)しsudo rmで削除。"),
        ("Lock out the attacker IP: sudo ufw enable; sudo ufw deny from <attacker ip>.",
         "攻撃者IPを遮断: sudo ufw enable; sudo ufw deny from <攻撃IP>。")],
    4: [("See the attack: tail /var/log/auth.log  and tcpdump -n port 22.",
         "攻撃確認: tail /var/log/auth.log と tcpdump -n port 22。"),
        ("Edit /etc/ssh/sshd_config: set 'PermitRootLogin no' (sudo nano or sudo sed).",
         "/etc/ssh/sshd_config で 'PermitRootLogin no' に（sudo nano か sudo sed）。"),
        ("Apply it: sudo systemctl restart ssh. Or rate-limit: sudo ufw limit 22/tcp; sudo ufw enable.",
         "適用: sudo systemctl restart ssh。または制限: sudo ufw limit 22/tcp; sudo ufw enable。")],
    5: [("Find the hog: top  or  ps aux --sort  - note the xmrig PID.",
         "負荷元を確認: top か ps aux - xmrigのPIDをメモ。"),
        ("Remove persistence FIRST: sudo crontab -u www-data -r  (else cron relaunches it).",
         "先に永続化を除去: sudo crontab -u www-data -r （でないとcronが再起動）。"),
        ("Then: sudo kill -9 <pid> and sudo rm /tmp/.kworker/xmrig.",
         "次に: sudo kill -9 <pid> と sudo rm /tmp/.kworker/xmrig。")],
    6: [("Confirm exposure: netstat -tulpn | grep 6379  and tcpdump -n port 6379.",
         "露出確認: netstat -tulpn | grep 6379 と tcpdump -n port 6379。"),
        ("Quick fix: sudo ufw enable; sudo ufw deny 6379/tcp.",
         "即応: sudo ufw enable; sudo ufw deny 6379/tcp。"),
        ("Proper fix: set bind 127.0.0.1 and a requirepass in /etc/redis/redis.conf, then sudo systemctl restart redis.",
         "本修正: /etc/redis/redis.conf で bind 127.0.0.1 と requirepass を設定し sudo systemctl restart redis。")],
    7: [("This is CVE-2024-47176 in cups-browsed on UDP 631.",
         "これはUDP631のcups-browsedのCVE-2024-47176。"),
        ("Stop it: sudo systemctl stop cups-browsed  (and sudo systemctl disable cups-browsed).",
         "停止: sudo systemctl stop cups-browsed （および disable）。"),
        ("Block UDP 631 and remove the rogue printer: sudo ufw deny 631/udp; sudo lpadmin -x EVIL_PRINTER.",
         "UDP631遮断と不正プリンタ削除: sudo ufw deny 631/udp; sudo lpadmin -x EVIL_PRINTER。")],
    8: [("Check versions: apt policy liblzma5 - 5.6.1 is the backdoored xz (CVE-2024-3094).",
         "版確認: apt policy liblzma5 - 5.6.1 がバックドア版(CVE-2024-3094)。"),
        ("Downgrade: sudo apt install liblzma5=5.4.1-1 xz-utils=5.4.1-1.",
         "降格: sudo apt install liblzma5=5.4.1-1 xz-utils=5.4.1-1。"),
        ("Unload it from sshd: sudo systemctl restart ssh.",
         "sshdから解放: sudo systemctl restart ssh。")],
    9: [("Spot it: systemctl status update-check  and ps aux | grep update-check.",
         "発見: systemctl status update-check と ps aux | grep update-check。"),
        ("Disable+stop: sudo systemctl disable update-check; sudo systemctl stop update-check.",
         "無効化+停止: sudo systemctl disable update-check; sudo systemctl stop update-check。"),
        ("Clean up: sudo rm /usr/local/bin/update-check /etc/systemd/system/update-check.service and remove the attacker line from /root/.ssh/authorized_keys.",
         "後処理: sudo rm で該当ファイル削除、/root/.ssh/authorized_keys から攻撃者の行を除去。")],
    10: [("See what leaked: tail /var/log/apache2/access.log  (look for /.env and /backup.sql).",
          "漏洩確認: tail /var/log/apache2/access.log （/.env と /backup.sql に注目）。"),
         ("Protect the files: sudo chmod 640 /var/www/html/.env; sudo rm /var/www/html/backup.sql.",
          "ファイル保護: sudo chmod 640 /var/www/html/.env; sudo rm /var/www/html/backup.sql。"),
         ("Close the database: sudo ufw enable; sudo ufw deny 27017/tcp.",
          "DB遮断: sudo ufw enable; sudo ufw deny 27017/tcp。")],
}
