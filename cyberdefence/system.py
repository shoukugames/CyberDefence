"""Builds the starting state of the server that every level shares."""
from .world import World, Service, HOSTNAME, SERVER_IP, LAN_IP

COMMANDS = sorted("""
ls cd pwd cat less more head tail grep egrep wc sort uniq cut tr echo printf touch mkdir rm rmdir cp mv find
chmod chown ln stat file which whoami id groups hostname uname date uptime clear history help man hint
mission objectives ps top kill killall pkill free df du ifconfig ip ping netstat ss lsof tcpdump ufw iptables
sudo su exit systemctl service sysctl sed nano vi crontab apt apt-get dpkg tar md5sum sha256sum env export
redis-cli lpstat lpadmin xz w who last tree true false sleep basename dirname rev yes nl tac diff
alias ll la l
""".split())

PASSWD = """root:x:0:0:root:/root:/bin/sh
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
mysql:x:105:110:MySQL Server:/nonexistent:/bin/false
redis:x:106:111::/var/lib/redis:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
sshd:x:107:65534::/run/sshd:/usr/sbin/nologin
player:x:1000:1000:Junior Admin:/home/player:/bin/sh
"""

SSHD_CONFIG = """# OpenSSH server configuration  (see: man sshd_config)
Port 22
ListenAddress 0.0.0.0
PermitRootLogin yes
PasswordAuthentication yes
PubkeyAuthentication yes
MaxAuthTries 6
X11Forwarding yes
UsePAM yes
Subsystem sftp /usr/lib/openssh/sftp-server
"""

MY_CNF = """[mysqld]
user            = mysql
port            = 3306
datadir         = /var/lib/mysql
# Allow connections from anywhere (TODO: lock down before go-live!)
bind-address    = 0.0.0.0
max_connections = 151
"""

REDIS_CONF = """# Redis configuration file
bind 0.0.0.0
port 6379
protected-mode no
# requirepass foobared
dir /var/lib/redis
appendonly no
"""

INDEX_HTML = """<!doctype html>
<html><head><title>Shouku Widgets - Online Shop</title></head>
<body><h1>Welcome to Shouku Widgets</h1>
<p>Browse our <a href="/products.php?id=1">products</a>.</p></body></html>
"""

README = """================================================================
  HANDOVER NOTES  -  websrv01
================================================================
Hi new admin!  I'm off on holiday, so the server is yours now.

 * Your account 'player' is in the sudo group. Try:  sudo -l
 * If sudo ever breaks, the root password is below. Keep it secret!
     root password:  {password}
 * Logs live in /var/log . Web site lives in /var/www/html .
 * The firewall (ufw) is installed but NOT enabled yet, so every
   port is wide open. Sorry...
 * Patches from the dev team are dropped into /root/patches .

Good luck,
  - Ken (old sysadmin)
"""

WELCOME = """Welcome to websrv01, junior admin!

You are logged in as the normal user 'player'.
Most defence tools (ufw, iptables, kill, systemctl, apt ...) need root.

Useful first commands:
  help            list every command in this simulator
  mission         show the mission briefing again
  objectives      show what still needs doing
  hint            get a hint (it is recorded in your progress report)
  man <command>   read a short manual page

Tip: the previous admin left a note somewhere at the top of the
file system...
"""


def build(world: World):
    fs = world.fs
    for d in ("/bin", "/sbin", "/usr/bin", "/usr/sbin", "/usr/local/bin", "/usr/local/sbin", "/usr/lib", "/lib/x86_64-linux-gnu", "/etc/ssh", "/etc/mysql",
              "/etc/redis", "/etc/apache2", "/etc/cups", "/etc/systemd/system", "/etc/php/8.3/cgi", "/etc/ufw",
              "/var/log/apache2", "/var/log/mysql", "/var/log/redis", "/var/log/cups", "/var/www/html/uploads",
              "/var/backups", "/var/lib/mysql", "/var/lib/redis", "/run", "/dev", "/proc", "/opt", "/srv", "/mnt",
              "/media"):
        fs.mkdir(d)
    fs.mkdir("/tmp", mode=0o1777)
    fs.mkdir("/var/tmp", mode=0o1777)
    fs.mkdir("/var/spool/cron/crontabs", mode=0o730, group="crontab")
    fs.mkdir("/root", mode=0o700)
    fs.mkdir("/root/.ssh", mode=0o700)
    fs.mkdir("/root/patches", mode=0o700)
    fs.mkdir("/home/player", mode=0o755, owner="player", group="player")
    fs.mkdir("/var/www/html/uploads").owner = "www-data"
    for c in COMMANDS:
        fs.write(f"/bin/{c}", "\x7fELF busybox applet\n", mode=0o755)
    fs.write("/dev/null", "", mode=0o666)

    fs.write("/README", README.format(password=world.password))
    fs.write("/etc/hostname", HOSTNAME + "\n")
    fs.write("/etc/hosts", f"127.0.0.1\tlocalhost\n{LAN_IP}\t{HOSTNAME}\n")
    fs.write("/etc/os-release", 'PRETTY_NAME="CyberOS 12 (BusyBox edition)"\nNAME="CyberOS"\nVERSION_ID="12"\nID=cyberos\n')
    fs.write("/etc/passwd", PASSWD)
    fs.write("/etc/group", "root:x:0:\nadm:x:4:player\nsudo:x:27:player\nwww-data:x:33:\nplayer:x:1000:\n")
    fs.write("/etc/shadow", "root:$y$j9T$Qm1x9Wc0$Yf3QbLhRZ2...:20398:0:99999:7:::\nplayer:$y$j9T$7aBpL1$k2n...:20398:0:99999:7:::\n",
             mode=0o640, group="shadow")
    fs.write("/etc/sudoers", "root    ALL=(ALL:ALL) ALL\n%sudo   ALL=(ALL:ALL) NOPASSWD: ALL\n", mode=0o440)
    fs.write("/etc/ssh/sshd_config", SSHD_CONFIG)
    fs.write("/etc/mysql/my.cnf", MY_CNF)
    fs.write("/etc/redis/redis.conf", REDIS_CONF, owner="redis", group="redis", mode=0o640)
    fs.write("/etc/apache2/apache2.conf", "ServerName websrv01\nDocumentRoot /var/www/html\nScriptAlias /cgi-bin/ /usr/lib/cgi-bin/\n")
    fs.write("/etc/cups/cups-browsed.conf", "# cups-browsed configuration\nBrowseRemoteProtocols dnssd cups\nBrowseAllow All\n")
    fs.write("/etc/crontab", "SHELL=/bin/sh\n# m h dom mon dow user  command\n17 *  * * *  root  run-parts /etc/cron.hourly\n25 6  * * *  root  run-parts /etc/cron.daily\n")
    fs.write("/etc/ufw/ufw.conf", "ENABLED=no\nLOGLEVEL=low\n")
    fs.write("/etc/sysctl.conf", "# Kernel tuning. Apply with: sysctl -p\n#net.ipv4.tcp_syncookies=1\n")
    fs.write("/etc/motd", "CyberOS 12 - authorised use only.\n")

    fs.write("/home/player/welcome.txt", WELCOME, owner="player")
    fs.write("/home/player/.profile", "PS1='\\u@\\h:\\w\\$ '\n", owner="player")
    fs.write("/root/.profile", "PS1='\\u@\\h:\\w# '\n")
    fs.write("/root/.ssh/authorized_keys", "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKen0ld4dm1nK3y ken@admin-laptop\n", mode=0o600)
    fs.write("/root/patches/README", "Patches from the dev team land here.\n", mode=0o600)

    fs.write("/var/www/html/index.html", INDEX_HTML, owner="www-data")
    fs.write("/var/backups/README", "Nightly backups are written here.\n")

    log_header = f"{world.stamp(-3600)} {HOSTNAME} systemd[1]: Started System Logging Service.\n"
    fs.write("/var/log/syslog", log_header, mode=0o640, group="adm")
    fs.write("/var/log/kern.log", f"{world.stamp(-3600)} {HOSTNAME} kernel: [    0.000000] Linux version 6.1.0-cyberos\n", mode=0o640, group="adm")
    fs.write("/var/log/auth.log", f"{world.stamp(-1800)} {HOSTNAME} sshd[811]: Accepted publickey for root from 10.0.0.5 port 51122 ssh2\n",
             mode=0o640, group="adm")
    access = []
    for i in range(6):
        access.append(f'100.{70 + i}.{12 * i}.{9 + i} - - [{world.web_stamp(-900 + i * 60)}] "GET / HTTP/1.1" 200 512 "-" "Mozilla/5.0"')
    fs.write("/var/log/apache2/access.log", "\n".join(access) + "\n", mode=0o640, group="adm")
    fs.write("/var/log/apache2/error.log", "", mode=0o640, group="adm")
    fs.write("/var/log/mysql/error.log", f"{world.now():%Y-%m-%d} 08:00:01 0 [Note] mysqld: ready for connections.\n", mode=0o640, group="adm")
    fs.write("/var/log/redis/redis-server.log", "1:M 06 Nov 2026 08:00:02.000 * Ready to accept connections tcp\n", mode=0o640, group="adm")
    fs.write("/var/log/cups/error_log", "", mode=0o640, group="adm")

    world.pkg("openssh-server", "1:9.2p1-2+deb12u3", desc="secure shell (SSH) server")
    world.pkg("apache2", "2.4.62-1", desc="Apache HTTP Server")
    world.pkg("php8.3-cgi", "8.3.14-1", desc="server-side, HTML-embedded scripting language (CGI binary)")
    world.pkg("mysql-server", "8.0.40-1", desc="MySQL database server")
    world.pkg("redis-server", "7.2.6-1", desc="Persistent key-value database")
    world.pkg("cups-browsed", "2.0.1-1", desc="OpenPrinting cups-browsed")
    world.pkg("xz-utils", "5.4.1-1", desc="XZ-format compression utilities")
    world.pkg("liblzma5", "5.4.1-1", desc="XZ-format compression library")
    world.pkg("busybox", "1:1.36.1-6", desc="Tiny utilities for small and embedded systems")
    world.pkg("ufw", "0.36.2-1", desc="program for managing a Netfilter firewall")
    world.pkg("tcpdump", "4.99.3-1", desc="command-line network traffic analyzer")

    for p in ("/sbin/init", "[kthreadd]", "/lib/systemd/systemd-journald", "/usr/sbin/cron -f", "/usr/sbin/rsyslogd -n"):
        world.spawn("root", p, cpu=0.0, mem=0.2)
    services = [
        Service("ssh", "ssh", [(22, "tcp")], "sshd: /usr/sbin/sshd -D [listener]", desc="OpenBSD Secure Shell server", aliases=("sshd", "openssh")),
        Service("apache2", "apache2", [(80, "tcp"), (443, "tcp")], "/usr/sbin/apache2 -k start", user="www-data", desc="The Apache HTTP Server", aliases=("apache", "httpd")),
        Service("mysql", "mysql", [(3306, "tcp")], "/usr/sbin/mysqld", user="mysql", desc="MySQL Community Server", aliases=("mysqld",)),
        Service("redis", "redis-server", [(6379, "tcp")], "/usr/bin/redis-server 0.0.0.0:6379", user="redis", desc="Advanced key-value store", aliases=("redis-server",)),
        Service("cups", "cups", [(631, "tcp")], "/usr/sbin/cupsd -l", desc="CUPS Scheduler", aliases=("cupsd",)),
        Service("cups-browsed", "cups-browsed", [(631, "udp")], "/usr/sbin/cups-browsed", desc="Make remote CUPS printers available locally"),
        Service("vsftpd", "vsftpd", [(21, "tcp")], "/usr/sbin/vsftpd /etc/vsftpd.conf", desc="vsftpd FTP server", aliases=("ftp",)),
        Service("telnet", "inetd", [(23, "tcp")], "/usr/sbin/inetd -i", desc="Internet superserver (telnet)", aliases=("inetd",)),
        Service("postfix", "postfix", [(25, "tcp")], "/usr/lib/postfix/sbin/master -w", desc="Postfix Mail Transport Agent"),
        Service("named", "named", [(53, "tcp"), (53, "udp")], "/usr/sbin/named -u bind", user="bind", desc="BIND Domain Name Server", aliases=("bind9", "dns")),
        Service("dovecot", "dovecot", [(110, "tcp"), (143, "tcp")], "/usr/sbin/dovecot -F", desc="Dovecot IMAP/POP3 server"),
        Service("postgresql", "postgresql", [(5432, "tcp")], "/usr/lib/postgresql/15/bin/postgres", user="postgres", desc="PostgreSQL RDBMS", aliases=("postgres",)),
        Service("mongod", "mongod", [(27017, "tcp")], "/usr/bin/mongod --bind_ip_all", user="mongodb", desc="MongoDB Database Server", aliases=("mongodb",)),
        Service("tomcat", "tomcat10", [(8080, "tcp")], "/usr/bin/java -Dcatalina.home=/usr/share/tomcat10", user="tomcat", desc="Apache Tomcat 10", aliases=("tomcat10",)),
    ]
    for svc in services:
        world.add_service(svc)
    world.spawn("player", "-sh", cpu=0.0, mem=0.1, tty="pts/0")
    return world
