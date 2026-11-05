"""The simulated server: files, firewall, services, processes, packages and traffic."""
import datetime
import ipaddress
import random
import string

from .vfs import VFS

HOSTNAME = "websrv01"
SERVER_IP = "192.0.2.10"
LAN_IP = "10.0.0.15"

PORT_NAMES = {"ssh": 22, "http": 80, "https": 443, "mysql": 3306, "ftp": 21, "telnet": 23,
              "smtp": 25, "dns": 53, "domain": 53, "pop3": 110, "imap": 143, "ipp": 631,
              "redis": 6379, "postgresql": 5432, "mongodb": 27017, "http-alt": 8080,
              "OpenSSH": 22, "Apache": 80, "WWW": 80, "CUPS": 631}

SERVICE_NAMES = {22: "ssh", 80: "http", 443: "https", 3306: "mysql", 21: "ftp", 23: "telnet", 25: "smtp",
                 53: "domain", 110: "pop3", 143: "imap", 631: "ipp", 6379: "redis", 5432: "postgresql",
                 27017: "mongodb", 8080: "http-alt", 4444: "krb524", 3333: "dec-notes", 12345: "italk"}


def make_password():
    rnd = random.SystemRandom()
    words = ["Falcon", "Nebula", "Copper", "Maple", "Quartz", "Ripple", "Tundra", "Comet", "Willow", "Ember"]
    return f"{rnd.choice(words)}-{rnd.randint(10, 99)}{rnd.choice('!#%&*+?')}{rnd.choice(string.ascii_lowercase)}{rnd.choice(words).lower()}"


def net(text):
    if text in (None, "any", "Anywhere", "0.0.0.0/0"):
        return None
    return ipaddress.ip_network(text, strict=False)


def in_net(ip, network):
    return network is None or ipaddress.ip_address(ip) in network


# ---------------------------------------------------------------- firewall
class UfwRule:
    def __init__(self, action, direction="in", remote=None, port=None, proto=None, text=""):
        self.action = action        # allow / deny / reject / limit
        self.direction = direction  # in / out
        self.remote = remote        # ip_network or None
        self.port = port
        self.proto = proto
        self.text = text

    def key(self):
        return (self.action, self.direction, str(self.remote), self.port, self.proto)

    def matches(self, direction, remote_ip, port, proto):
        if direction != self.direction:
            return False
        if self.port is not None and port != self.port:
            return False
        if self.proto is not None and proto != self.proto:
            return False
        return in_net(remote_ip, self.remote)

    def describe(self):
        to = f"{self.port}" if self.port is not None else "Anywhere"
        if self.port is not None and self.proto:
            to += f"/{self.proto}"
        frm = str(self.remote) if self.remote else "Anywhere"
        if self.remote and self.remote.prefixlen == 32:
            frm = str(self.remote.network_address)
        action = self.action.upper() + (" OUT" if self.direction == "out" else " IN")
        if self.direction == "out":
            return f"{frm:<26}{action:<12}{to}"
        return f"{to:<26}{action:<12}{frm}"


class IptRule:
    def __init__(self, chain, target, src=None, dst=None, proto=None, dport=None):
        self.chain, self.target, self.src, self.dst, self.proto, self.dport = chain, target, src, dst, proto, dport

    def matches(self, direction, remote_ip, port, proto):
        if (self.chain == "INPUT") != (direction == "in"):
            return False
        if self.proto and self.proto != proto:
            return False
        if self.dport is not None and self.dport != port:
            return False
        network = self.src if direction == "in" else self.dst
        if direction == "in" and self.dst is not None:
            return False
        if direction == "out" and self.src is not None:
            return False
        return in_net(remote_ip, network)

    def describe(self):
        src = str(self.src) if self.src else "0.0.0.0/0"
        dst = str(self.dst) if self.dst else "0.0.0.0/0"
        extra = f"{self.proto} dpt:{self.dport}" if self.dport is not None else ""
        return f"{self.target:<10} {(self.proto or 'all'):<5} --  {src:<20} {dst:<20} {extra}"


class Firewall:
    def __init__(self):
        self.ufw_enabled = False
        self.default_in = "allow"   # every port is open when the game starts
        self.default_out = "allow"
        self.rules = []
        self.ipt = {"INPUT": [], "OUTPUT": [], "FORWARD": []}

    def permits(self, direction, remote_ip, port, proto="tcp", flood=False):
        for rule in self.ipt["INPUT" if direction == "in" else "OUTPUT"]:
            if rule.matches(direction, remote_ip, port, proto):
                if rule.target in ("DROP", "REJECT"):
                    return False
                break
        if not self.ufw_enabled:
            return True
        for rule in self.rules:
            if rule.matches(direction, remote_ip, port, proto):
                if rule.action == "limit":
                    return not flood
                return rule.action == "allow"
        return (self.default_in if direction == "in" else self.default_out) == "allow"


# ---------------------------------------------------------------- services / procs
class Service:
    def __init__(self, name, unit, ports, proc, user="root", desc="", aliases=(), bind="0.0.0.0"):
        self.name = name
        self.unit = unit
        self.ports = ports          # list of (port, proto)
        self.proc = proc
        self.user = user
        self.desc = desc
        self.aliases = set(aliases) | {name, unit}
        self.running = True
        self.enabled = True
        self.bind = bind
        self.loaded = {}
        self.needs_restart = False
        self.pid = None


class Proc:
    def __init__(self, pid, user, cmd, cpu=0.0, mem=0.1, tag=None, start="09:00", tty="?"):
        self.pid, self.user, self.cmd, self.cpu, self.mem, self.tag, self.start, self.tty = pid, user, cmd, cpu, mem, tag, start, tty

    @property
    def name(self):
        first = self.cmd.split()[0]
        return first.rsplit("/", 1)[-1].strip("[]:")


class Flow:
    """One network conversation, used by netstat, ss, lsof and tcpdump."""

    def __init__(self, remote, rport, lport, proto="tcp", state="ESTABLISHED", direction="in",
                 kind="benign", proc=None, packet=None, flood=False):
        self.remote, self.rport, self.lport, self.proto = remote, rport, lport, proto
        self.state, self.direction, self.kind, self.proc = state, direction, kind, proc
        self.packet = packet or ""
        self.flood = flood

    @property
    def port(self):
        """The service port the conversation is about (local for inbound, remote for outbound)."""
        return self.lport if self.direction == "in" else self.rport


# ---------------------------------------------------------------- the world
class World:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.fs = VFS()
        self.fw = Firewall()
        self.services = {}
        self.procs = []
        self.next_pid = 2400
        self.packages = {}
        self.updated = False
        self.sysctl = {"net.ipv4.tcp_syncookies": "0", "net.ipv4.ip_forward": "0",
                       "net.ipv4.tcp_max_syn_backlog": "128", "net.ipv4.icmp_echo_ignore_broadcasts": "1",
                       "kernel.randomize_va_space": "2", "net.ipv4.conf.all.rp_filter": "0"}
        self.redis = {"requirepass": "", "bind": "0.0.0.0", "protected-mode": "no"}
        self.printers = {"Office_Laser": "ipp://10.0.0.40/ipp/print"}
        self.password = make_password()
        self.time = 0.0
        self.alerts = []
        self.level = None
        self.start_dt = datetime.datetime.now()
        self.load = 0.3
        self.netload = 0.1
        self.packets_blocked = 0
        self.extra = {}

    # ---- time
    def now(self):
        return self.start_dt + datetime.timedelta(seconds=self.time)

    def stamp(self, offset=0.0):
        """Syslog style time, e.g. 'Nov  6 09:12:01'."""
        t = self.now() + datetime.timedelta(seconds=offset)
        return f"{t:%b} {t.day:>2} {t:%H:%M:%S}"

    def web_stamp(self, offset=0.0):
        t = self.now() + datetime.timedelta(seconds=offset)
        return t.strftime("%d/%b/%Y:%H:%M:%S +0000")

    def alert(self, text, severity="warn"):
        self.alerts.append((self.time, severity, text))
        del self.alerts[:-60]

    def log(self, path, line):
        node = self.fs.get(path)
        if node is not None:
            node.content += line + "\n"
            lines = node.content.splitlines(True)
            if len(lines) > 400:
                node.content = "".join(lines[-400:])

    # ---- procs
    def spawn(self, user, cmd, cpu=0.0, mem=0.1, tag=None, tty="?"):
        self.next_pid += self.rng.randint(1, 37)
        p = Proc(self.next_pid, user, cmd, cpu, mem, tag, self.now().strftime("%H:%M"), tty)
        self.procs.append(p)
        return p

    def proc(self, pid):
        for p in self.procs:
            if p.pid == pid:
                return p
        return None

    def procs_tagged(self, tag):
        return [p for p in self.procs if p.tag == tag]

    def kill(self, p):
        if p in self.procs:
            self.procs.remove(p)
            for svc in self.services.values():
                if svc.pid == p.pid:
                    svc.running = False
            if self.level:
                self.level.on_kill(self, p)

    # ---- services
    def service(self, name):
        name = name[:-8] if name.endswith(".service") else name
        for svc in self.services.values():
            if name in svc.aliases:
                return svc
        return None

    def add_service(self, svc):
        self.services[svc.name] = svc
        p = self.spawn(svc.user, svc.proc, cpu=round(self.rng.uniform(0, 0.8), 1),
                       mem=round(self.rng.uniform(0.2, 3.0), 1), tag="svc:" + svc.name)
        svc.pid = p.pid
        self.snapshot(svc)

    def start_service(self, svc):
        if not svc.running:
            p = self.spawn(svc.user, svc.proc, cpu=0.3, mem=1.0, tag="svc:" + svc.name)
            svc.pid = p.pid
            svc.running = True
        self.snapshot(svc)
        svc.needs_restart = False

    def stop_service(self, svc):
        svc.running = False
        self.procs = [p for p in self.procs if p.tag != "svc:" + svc.name]
        svc.pid = None

    def restart_service(self, svc):
        self.stop_service(svc)
        self.start_service(svc)

    def snapshot(self, svc):
        """Remember the config a service read when it started (so edits need a restart)."""
        if svc.name == "ssh":
            conf = self.read_conf("/etc/ssh/sshd_config", " ")
            svc.loaded = {"PermitRootLogin": conf.get("PermitRootLogin", "yes"),
                          "PasswordAuthentication": conf.get("PasswordAuthentication", "yes"),
                          "liblzma": self.packages.get("liblzma5", {}).get("installed", "")}
        elif svc.name == "mysql":
            conf = self.read_conf("/etc/mysql/my.cnf", "=")
            svc.bind = conf.get("bind-address", "0.0.0.0")
        elif svc.name == "redis":
            conf = self.read_conf("/etc/redis/redis.conf", " ")
            self.redis["requirepass"] = conf.get("requirepass", "")
            self.redis["bind"] = conf.get("bind", "0.0.0.0").split()[0]
            self.redis["protected-mode"] = conf.get("protected-mode", "no")
            svc.bind = self.redis["bind"]
        elif svc.name == "apache2":
            svc.loaded = {"php": self.packages.get("php8.3-cgi", {}).get("installed", "")}

    def read_conf(self, path, sep):
        out = {}
        node = self.fs.get(path)
        if not node:
            return out
        for line in node.content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("["):
                continue
            if sep == "=":
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
            else:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    out[parts[0]] = parts[1].strip()
        return out

    def listening(self):
        """(port, proto, bind, service) for every running service."""
        out = []
        for svc in self.services.values():
            if svc.running:
                for port, proto in svc.ports:
                    out.append((port, proto, svc.bind, svc))
        return sorted(out, key=lambda t: (t[1], t[0]))

    def reachable(self, remote_ip, port, proto="tcp", flood=False):
        """Can a host on the Internet reach this port right now?"""
        for lport, lproto, bind, svc in self.listening():
            if lport == port and lproto == proto:
                if bind.startswith("127.") or bind == "::1":
                    return False
                return self.fw.permits("in", remote_ip, port, proto, flood)
        return False

    def can_reach_out(self, remote_ip, port, proto="tcp"):
        return self.fw.permits("out", remote_ip, port, proto)

    def flow_allowed(self, f):
        if f.direction == "in":
            return self.reachable(f.remote, f.lport, f.proto, f.flood)
        return self.can_reach_out(f.remote, f.rport, f.proto)

    # ---- traffic
    def flows(self):
        flows = list(self.benign_flows())
        if self.level:
            flows.extend(self.level.traffic(self))
        return [f for f in flows if self.flow_allowed(f)]

    def benign_flows(self):
        rng = random.Random(int(self.time // 6))
        flows = []
        if self.reachable("100.72.14.9", 443):
            for _ in range(rng.randint(2, 4)):
                flows.append(Flow(f"100.{rng.randint(64, 127)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
                                  rng.randint(40000, 65000), rng.choice([80, 443]), proc="apache2",
                                  packet="Flags [P.], length {}".format(rng.randint(200, 1400))))
        flows.append(Flow("10.0.0.5", 51122, 22, proc="sshd", packet="Flags [P.], length 36"))
        return flows

    # ---- packages
    def pkg(self, name, version, candidate=None, repo=None, desc=""):
        self.packages[name] = {"installed": version, "candidate": candidate or version,
                               "repo": repo or candidate or version, "desc": desc}
