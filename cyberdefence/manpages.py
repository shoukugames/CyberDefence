"""Limited man pages, bilingual. Deliberately terse - part of the challenge."""

MAN = {
    "sudo": (
        "sudo - run a command as another user (usually root)\n\n"
        "  sudo COMMAND        run COMMAND as root\n"
        "  sudo -l             list what you may run\n"
        "  sudo -i / su -      become an interactive root shell\n\n"
        "This box gives the 'sudo' group NOPASSWD, so no password is asked.",
        "sudo - 他のユーザー（通常root）としてコマンドを実行\n\n"
        "  sudo COMMAND        COMMANDをrootで実行\n"
        "  sudo -l             実行可能な権限を一覧\n"
        "  sudo -i / su -      対話的なrootシェルになる\n\n"
        "このマシンはsudoグループにNOPASSWDを付与済。パスワード不要。"),
    "ufw": (
        "ufw - uncomplicated firewall\n\n"
        "  ufw enable|disable          turn the firewall on/off\n"
        "  ufw status [verbose]        show rules\n"
        "  ufw default deny incoming   set the default policy\n"
        "  ufw allow 22/tcp            allow a port\n"
        "  ufw deny from 1.2.3.4       block an IP\n"
        "  ufw deny from 1.2.3.0/24    block a subnet\n"
        "  ufw limit 22/tcp            rate-limit a port (good vs floods)\n"
        "  ufw delete allow 80/tcp     remove a rule",
        "ufw - 簡易ファイアウォール\n\n"
        "  ufw enable|disable          firewallの有効/無効\n"
        "  ufw status [verbose]        ルール表示\n"
        "  ufw default deny incoming   既定ポリシー設定\n"
        "  ufw allow 22/tcp            ポート許可\n"
        "  ufw deny from 1.2.3.4       IP遮断\n"
        "  ufw deny from 1.2.3.0/24    サブネット遮断\n"
        "  ufw limit 22/tcp            ポートを帯域制限（洪水対策）\n"
        "  ufw delete allow 80/tcp     ルール削除"),
    "iptables": (
        "iptables - low-level packet filter\n\n"
        "  iptables -L [-n]                 list rules\n"
        "  iptables -A INPUT -s IP -j DROP  drop packets from IP\n"
        "  iptables -A INPUT -p tcp --dport 22 -j DROP\n"
        "  iptables -F                      flush all rules",
        "iptables - 低レベルパケットフィルタ\n\n"
        "  iptables -L [-n]                 ルール一覧\n"
        "  iptables -A INPUT -s IP -j DROP  指定IPを遮断\n"
        "  iptables -A INPUT -p tcp --dport 22 -j DROP\n"
        "  iptables -F                      全ルール削除"),
    "netstat": (
        "netstat - network connections and listening ports\n\n"
        "  netstat -tulpn   TCP/UDP listening ports with PID/program\n"
        "  netstat -an      all sockets, numeric\n"
        "  netstat -tn      established TCP connections",
        "netstat - ネットワーク接続と待受ポート\n\n"
        "  netstat -tulpn   TCP/UDPの待受ポートとPID/プログラム\n"
        "  netstat -an      全ソケットを数値表示\n"
        "  netstat -tn      確立済TCP接続"),
    "ss": (
        "ss - another socket statistics tool (like netstat)\n\n"
        "  ss -tulpn    listening TCP/UDP sockets with process\n"
        "  ss -tn       established TCP connections",
        "ss - ソケット統計ツール（netstat類似）\n\n"
        "  ss -tulpn    待受TCP/UDPソケットとプロセス\n"
        "  ss -tn       確立済TCP接続"),
    "tcpdump": (
        "tcpdump - capture and show network packets\n\n"
        "  tcpdump -n               show live packets, numeric\n"
        "  tcpdump -n port 80       only port 80\n"
        "  tcpdump -n host 1.2.3.4  only that host\n"
        "  tcpdump -c 20            stop after 20 packets\n\n"
        "Use it to SEE who is attacking and on which port.",
        "tcpdump - ネットワークパケットを取得・表示\n\n"
        "  tcpdump -n               パケットを数値表示\n"
        "  tcpdump -n port 80       ポート80のみ\n"
        "  tcpdump -n host 1.2.3.4  指定ホストのみ\n"
        "  tcpdump -c 20            20パケットで停止\n\n"
        "誰がどのポートを攻撃しているか確認できます。"),
    "systemctl": (
        "systemctl - control system services\n\n"
        "  systemctl status NAME     is it running?\n"
        "  systemctl stop NAME       stop a service now\n"
        "  systemctl start NAME      start it\n"
        "  systemctl restart NAME    restart (re-reads its config)\n"
        "  systemctl disable NAME    stop it starting at boot\n"
        "  systemctl list-units      list services",
        "systemctl - システムサービスを制御\n\n"
        "  systemctl status NAME     稼働状態\n"
        "  systemctl stop NAME       今すぐ停止\n"
        "  systemctl start NAME      起動\n"
        "  systemctl restart NAME    再起動（設定を再読込）\n"
        "  systemctl disable NAME    自動起動を無効化\n"
        "  systemctl list-units      サービス一覧"),
    "ps": (
        "ps - report running processes\n\n"
        "  ps aux       every process, with user, CPU%, MEM%, command\n"
        "  ps -ef       every process, full listing\n\n"
        "Pipe into grep to find one:  ps aux | grep xmrig",
        "ps - 実行中プロセスを表示\n\n"
        "  ps aux       全プロセス（ユーザー/CPU/MEM/コマンド）\n"
        "  ps -ef       全プロセスを完全表示\n\n"
        "grepで絞込:  ps aux | grep xmrig"),
    "kill": (
        "kill - send a signal to a process (by PID)\n\n"
        "  kill PID        ask it to stop (TERM)\n"
        "  kill -9 PID     force it to stop (KILL)\n"
        "  killall NAME    kill every process named NAME\n"
        "  pkill NAME      kill by name match",
        "kill - プロセスにシグナル送信（PID指定）\n\n"
        "  kill PID        停止要求(TERM)\n"
        "  kill -9 PID     強制停止(KILL)\n"
        "  killall NAME    名前が一致する全プロセスを停止\n"
        "  pkill NAME      名前一致で停止"),
    "sysctl": (
        "sysctl - read and write kernel parameters\n\n"
        "  sysctl NAME            show a value\n"
        "  sysctl -w NAME=VALUE   set a value\n"
        "  sysctl -a              list all\n\n"
        "Example (defend vs SYN flood):  sysctl -w net.ipv4.tcp_syncookies=1",
        "sysctl - カーネルパラメータの読み書き\n\n"
        "  sysctl NAME            値を表示\n"
        "  sysctl -w NAME=VALUE   値を設定\n"
        "  sysctl -a              全一覧\n\n"
        "例（SYN洪水対策）:  sysctl -w net.ipv4.tcp_syncookies=1"),
    "apt": (
        "apt / apt-get - package manager\n\n"
        "  apt list --installed        show installed packages\n"
        "  apt policy NAME             installed vs candidate version\n"
        "  apt install NAME=VERSION    install a specific version (downgrade)\n"
        "  apt remove NAME             remove a package\n"
        "  apt update                  refresh package lists",
        "apt / apt-get - パッケージ管理\n\n"
        "  apt list --installed        導入済一覧\n"
        "  apt policy NAME             導入版と候補版\n"
        "  apt install NAME=VERSION    特定版を導入（降格）\n"
        "  apt remove NAME             パッケージ削除\n"
        "  apt update                  リスト更新"),
    "redis-cli": (
        "redis-cli - talk to the Redis server\n\n"
        "  redis-cli CONFIG GET requirepass\n"
        "  redis-cli CONFIG SET requirepass 'secret'\n"
        "  redis-cli CONFIG SET protected-mode yes\n\n"
        "Better: edit /etc/redis/redis.conf and restart redis.",
        "redis-cli - Redisサーバーと通信\n\n"
        "  redis-cli CONFIG GET requirepass\n"
        "  redis-cli CONFIG SET requirepass 'secret'\n"
        "  redis-cli CONFIG SET protected-mode yes\n\n"
        "推奨: /etc/redis/redis.conf を編集しredisを再起動。"),
    "chmod": (
        "chmod - change file permission bits\n\n"
        "  chmod 640 FILE    owner rw, group r, others none\n"
        "  chmod o-r FILE    remove 'others can read'\n"
        "  chmod +x FILE     make executable",
        "chmod - ファイルの権限ビットを変更\n\n"
        "  chmod 640 FILE    所有者rw/グループr/他なし\n"
        "  chmod o-r FILE    「その他の読取」を除去\n"
        "  chmod +x FILE     実行可能にする"),
    "grep": (
        "grep - search text for a pattern\n\n"
        "  grep WORD FILE       lines containing WORD\n"
        "  grep -i WORD FILE    ignore case\n"
        "  grep -c WORD FILE    count matches\n"
        "  ... | grep WORD      filter another command's output",
        "grep - テキストからパターン検索\n\n"
        "  grep WORD FILE       WORDを含む行\n"
        "  grep -i WORD FILE    大小無視\n"
        "  grep -c WORD FILE    一致数\n"
        "  ... | grep WORD      他コマンドの出力を絞込"),
    "crontab": (
        "crontab - scheduled jobs\n\n"
        "  crontab -l         list the current user's jobs\n"
        "  crontab -r         remove all of the user's jobs\n"
        "  crontab -u USER -l list another user's jobs\n\n"
        "Cron files live in /var/spool/cron/crontabs/<user>.",
        "crontab - 定期ジョブ\n\n"
        "  crontab -l         現ユーザーのジョブ一覧\n"
        "  crontab -r         ジョブを全削除\n"
        "  crontab -u USER -l 他ユーザーのジョブ一覧\n\n"
        "cronファイルは /var/spool/cron/crontabs/<user>。"),
    "sed": (
        "sed - stream editor (edit text non-interactively)\n\n"
        "  sed -i 's/OLD/NEW/' FILE       replace first OLD per line, in place\n"
        "  sed -i 's/OLD/NEW/g' FILE      replace all\n"
        "  sed -i '/PATTERN/d' FILE       delete matching lines",
        "sed - ストリームエディタ（非対話編集）\n\n"
        "  sed -i 's/OLD/NEW/' FILE       各行最初のOLDを置換（上書き）\n"
        "  sed -i 's/OLD/NEW/g' FILE      全置換\n"
        "  sed -i '/PATTERN/d' FILE       一致行を削除"),
    "nano": (
        "nano - a simple text editor\n\n"
        "In this simulator nano opens a full-screen editor.\n"
        "  Ctrl-O  save    Ctrl-X  exit\n"
        "Use it to edit config files like /etc/ssh/sshd_config.",
        "nano - シンプルなテキストエディタ\n\n"
        "このシミュレータではnanoが全画面エディタを開きます。\n"
        "  Ctrl-O  保存    Ctrl-X  終了\n"
        "/etc/ssh/sshd_config 等の編集に使用。"),
    "find": (
        "find - search for files\n\n"
        "  find /path -name '*.php'    by name\n"
        "  find / -user www-data       by owner\n"
        "  find /tmp -type f           only files",
        "find - ファイル検索\n\n"
        "  find /path -name '*.php'    名前で検索\n"
        "  find / -user www-data       所有者で検索\n"
        "  find /tmp -type f           ファイルのみ"),
    "lpadmin": (
        "lpadmin / lpstat - manage printers (CUPS)\n\n"
        "  lpstat -p           list printers\n"
        "  lpadmin -x NAME     remove a printer",
        "lpadmin / lpstat - プリンタ管理(CUPS)\n\n"
        "  lpstat -p           プリンタ一覧\n"
        "  lpadmin -x NAME     プリンタ削除"),
}

# A few aliases
MAN["apt-get"] = MAN["apt"]
MAN["egrep"] = MAN["grep"]
MAN["killall"] = MAN["kill"]
MAN["pkill"] = MAN["kill"]
MAN["service"] = MAN["systemctl"]
MAN["su"] = MAN["sudo"]
MAN["lpstat"] = MAN["lpadmin"]
MAN["vi"] = MAN["nano"]


def get(cmd, lang):
    entry = MAN.get(cmd)
    if not entry:
        return None
    return entry[1] if lang == "ja" else entry[0]
