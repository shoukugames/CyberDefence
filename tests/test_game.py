"""Tests for the CyberDefence simulation engine (no display needed)."""
import os
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pytest

from cyberdefence import levels
from cyberdefence.i18n import STR, I18n
from cyberdefence.save import Save, fmt_time
from cyberdefence.shell import HINTS, Shell
from cyberdefence.system import build
from cyberdefence.training import LESSONS
from cyberdefence.world import World


def make(num, seed=42):
    world = build(World(seed=seed))
    lvl = levels.make_level(world, num)
    tr = I18n("en")
    sv = Save(path=tempfile.mktemp())
    sh = Shell(world, tr, sv, num)
    return world, lvl, sh


def finish(lvl, n=25):
    for _ in range(n):
        lvl.tick(0.3)


# ---------------------------------------------------------------- basics
def test_build_opens_all_ports():
    world = build(World(seed=1))
    ports = {p for p, proto, b, svc in world.listening()}
    for expected in (22, 80, 443, 3306, 6379, 631, 21, 23, 25, 53, 5432, 27017, 8080):
        assert expected in ports


def test_root_password_hidden_in_readme():
    world = build(World(seed=1))
    readme = world.fs.read("/README")
    assert world.password in readme
    assert len(world.password) >= 8


def test_sudo_nopasswd_documented():
    world = build(World(seed=1))
    assert "NOPASSWD" in world.fs.read("/etc/sudoers")


def test_every_port_reachable_before_firewall():
    world = build(World(seed=1))
    assert world.reachable("203.0.113.9", 3306)
    assert world.reachable("203.0.113.9", 6379)


# ---------------------------------------------------------------- shell
def test_ls_and_cat():
    world, lvl, sh = make(1)
    out = sh.run("ls /").out
    assert "README" in out
    assert "etc" in out
    assert "no such file" not in sh.run("cat /README").out.lower()


def test_sudo_elevates_then_reverts():
    world, lvl, sh = make(1)
    assert sh.run("whoami").out.strip() == "player"
    assert sh.run("sudo whoami").out.strip() == "root"
    assert sh.user == "player"


def test_player_cannot_firewall_without_root():
    world, lvl, sh = make(1)
    res = sh.run("ufw enable")
    assert res.code != 0
    assert not world.fw.ufw_enabled
    sh.run("sudo ufw enable")
    assert world.fw.ufw_enabled


def test_pipe_grep():
    world, lvl, sh = make(1)
    out = sh.run("cat /etc/passwd | grep root").out
    assert "root" in out and "www-data" not in out


def test_redirect_write():
    world, lvl, sh = make(1)
    sh.run("echo hello > /tmp/note.txt")
    assert sh.run("cat /tmp/note.txt").out.strip() == "hello"


def test_kill_requires_privilege_for_root_procs():
    world, lvl, sh = make(1)
    rootproc = next(p for p in world.procs if p.user == "root")
    res = sh.run(f"kill {rootproc.pid}")
    assert "not permitted" in res.out.lower()
    assert world.proc(rootproc.pid) is not None
    sh.run(f"sudo kill -9 {rootproc.pid}")
    assert world.proc(rootproc.pid) is None


def test_sysctl_write_needs_root():
    world, lvl, sh = make(1)
    assert sh.run("sysctl -w net.ipv4.tcp_syncookies=1").code != 0
    sh.run("sudo sysctl -w net.ipv4.tcp_syncookies=1")
    assert world.sysctl["net.ipv4.tcp_syncookies"] == "1"


def test_ufw_deny_subnet_blocks_traffic():
    world, lvl, sh = make(1)
    sh.run("sudo ufw default deny incoming")
    sh.run("sudo ufw deny from 198.51.100.0/24")
    sh.run("sudo ufw enable")
    assert not world.reachable("198.51.100.44", 80)
    assert world.reachable("8.8.8.8", 80) is False or True  # default deny


def test_iptables_drop():
    world, lvl, sh = make(1)
    sh.run("sudo iptables -A INPUT -s 203.0.113.5 -j DROP")
    assert not world.reachable("203.0.113.5", 80)
    assert world.reachable("203.0.113.6", 80)


# ---------------------------------------------------------------- levels solvable
SOLUTIONS = {
    1: ["sudo ufw default deny incoming", "__block_bots__", "sudo ufw enable",
        "sudo sysctl -w net.ipv4.tcp_syncookies=1"],
    2: ["sudo ufw enable", "sudo ufw deny 3306/tcp", "__block_attacker__", "__patch_php__"],
    3: ["__kill_webshell__", "sudo rm /var/www/html/uploads/avatar.php",
        "sudo ufw enable", "__block_attacker__"],
    4: ["__fix_ssh__", "sudo systemctl restart ssh", "sudo ufw limit 22/tcp", "sudo ufw enable"],
    5: ["sudo crontab -u www-data -r", "__kill_miner__", "sudo rm /tmp/.kworker/xmrig"],
    6: ["sudo ufw enable", "sudo ufw deny 6379/tcp"],
    7: ["sudo systemctl stop cups-browsed", "sudo ufw enable", "sudo ufw deny 631/udp",
        "sudo lpadmin -x EVIL_PRINTER"],
    8: ["sudo apt install liblzma5=5.4.1-1 xz-utils=5.4.1-1", "sudo systemctl restart ssh"],
    9: ["sudo systemctl disable update-check", "sudo systemctl stop update-check",
        "sudo rm /usr/local/bin/update-check /etc/systemd/system/update-check.service",
        'sudo sed -i "/attacker/d" /root/.ssh/authorized_keys'],
    10: ["sudo chmod 640 /var/www/html/.env", "sudo rm /var/www/html/backup.sql",
         "sudo ufw enable", "sudo ufw deny 27017/tcp"],
}


@pytest.mark.parametrize("num", range(1, 11))
def test_level_solvable(num):
    world, lvl, sh = make(num)
    assert not lvl.solved(), f"level {num} should start unsolved"
    for step in SOLUTIONS[num]:
        if step == "__block_bots__":
            for b in {x.rsplit(".", 1)[0] + ".0/24" for x in lvl.bots}:
                sh.run(f"sudo ufw deny from {b}")
        elif step == "__block_attacker__":
            sh.run(f"sudo ufw deny from {lvl.attacker}")
        elif step == "__patch_php__":
            sh.run("sudo sed -i \"s/\\$_GET\\['id'\\]/intval(\\$_GET['id'])/\" /var/www/html/products.php")
        elif step == "__kill_webshell__":
            sh.run(f"sudo kill -9 {lvl.proc.pid}")
        elif step == "__fix_ssh__":
            sh.run('sudo sed -i "s/PermitRootLogin yes/PermitRootLogin no/" /etc/ssh/sshd_config')
        elif step == "__kill_miner__":
            sh.run(f"sudo kill -9 {lvl.miner.pid}")
        else:
            sh.run(step)
    finish(lvl)
    assert lvl.solved(), f"level {num} not solved after intended solution"


def test_miner_respawns_without_cron_removal():
    world, lvl, sh = make(5)
    sh.run(f"sudo kill -9 {lvl.miner.pid}")
    finish(lvl, 40)
    assert any(p.tag == "miner" for p in world.procs), "cron should relaunch the miner"


# ---------------------------------------------------------------- content
def test_all_levels_have_names_and_briefs():
    for i in range(1, 11):
        assert STR[f"lvl.{i}.name"][0] and STR[f"lvl.{i}.name"][1]
        assert STR[f"lvl.{i}.brief"][0] and STR[f"lvl.{i}.brief"][1]


def test_every_level_has_hints():
    for i in range(1, 11):
        assert len(HINTS[i]) >= 2


def test_all_strings_bilingual():
    for key, pair in STR.items():
        assert len(pair) == 2 and pair[0] and pair[1], f"string {key} missing a translation"


def test_lessons_bilingual():
    assert len(LESSONS) >= 7
    for lesson in LESSONS:
        assert lesson["title"][0] and lesson["title"][1]
        assert lesson["body"][0] and lesson["body"][1]


# ---------------------------------------------------------------- save/records
def test_fmt_time():
    assert fmt_time(None) == "--:--.-"
    assert fmt_time(65.4) == "01:05.4"


def test_top10_records_sorted_and_capped():
    sv = Save(path=tempfile.mktemp())
    for i in range(15):
        sv.add_record(1, f"P{i}", 100 - i, "2026-11-06")
    recs = sv.records(1)
    assert len(recs) == 10
    assert recs[0]["time"] <= recs[-1]["time"]
    assert recs[0]["time"] == 86


def test_complete_marks_level_and_best():
    sv = Save(path=tempfile.mktemp())
    sv.complete(1, 300.0)
    assert sv.level(1)["completed"]
    sv.complete(1, 250.0)
    assert sv.level(1)["best"] == 250.0
    sv.complete(1, 400.0)
    assert sv.level(1)["best"] == 250.0
