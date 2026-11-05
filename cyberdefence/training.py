"""Training academy: bilingual lessons on Linux basics and defending against attacks."""

# Each lesson: key -> dict(title=(en,ja), body=(en,ja))
LESSONS = [
    {
        "key": "linux-basics",
        "title": ("1. Linux Survival Kit", "1. Linux 基本コマンド"),
        "body": (
            """The terminal is your only tool. A command is: NAME [options] [arguments].

Moving around and looking:
  pwd                 print the directory you are in
  ls                  list files here        ls -l   long list (shows owner & permissions)
  ls -la /etc         list ALL files (incl. hidden) in /etc
  cd /var/log         change directory       cd ..   go up one      cd ~   go home
  cat FILE            print a whole file
  less FILE           page through a long file
  head / tail FILE    first / last 10 lines  (tail -n 50 for 50 lines)

Finding things:
  grep WORD FILE      show lines containing WORD
  find / -name '*.php'   find files by name
  command | grep X    filter one command's output through grep   (a "pipe")

Changing things:
  touch FILE          create an empty file
  rm FILE             delete a file          rm -r DIR   delete a folder
  cp A B / mv A B     copy / move
  nano FILE           open the text editor (Ctrl-O save, Ctrl-X exit)

Tip: 'help' lists every command here. 'man ls' shows a short manual.""",
            """ターミナルが唯一の道具です。コマンドは: 名前 [オプション] [引数]。

移動と確認:
  pwd                 現在のディレクトリを表示
  ls                  ファイル一覧        ls -l   詳細表示（所有者と権限）
  ls -la /etc         /etc の隠しファイルも全表示
  cd /var/log         ディレクトリ移動    cd ..   上へ    cd ~   ホームへ
  cat FILE            ファイル全体を表示
  less FILE           長いファイルをページ送り
  head / tail FILE    先頭/末尾10行  (tail -n 50 で50行)

検索:
  grep WORD FILE      WORD を含む行を表示
  find / -name '*.php'   名前でファイル検索
  command | grep X    出力を grep で絞込（パイプ）

変更:
  touch FILE          空ファイル作成
  rm FILE             削除             rm -r DIR   フォルダ削除
  cp A B / mv A B     コピー / 移動
  nano FILE           テキストエディタ（Ctrl-O保存, Ctrl-X終了）

ヒント: 'help' で全コマンド、'man ls' で簡易マニュアル。"""),
    },
    {
        "key": "root-sudo",
        "title": ("2. Becoming root (sudo)", "2. root になる (sudo)"),
        "body": (
            """Defence needs power. The superuser 'root' can do anything; your account
'player' cannot - until you borrow root's power with sudo.

  whoami              who am I right now?
  id                  my user id and groups
  sudo COMMAND        run ONE command as root
  sudo -l             list what I'm allowed to run
  sudo -i   (or  su -)   become a full root shell; type 'exit' to go back

On THIS server the previous admin put your group in /etc/sudoers with NOPASSWD,
so sudo never asks for a password. How would you confirm that? Read the file:

  cat /etc/sudoers

See the line:  %sudo  ALL=(ALL:ALL) NOPASSWD: ALL
That means any member of the 'sudo' group (you!) runs anything as root, free.

Still, there IS a root password hidden on this box as a README, in case sudo
ever breaks. Explorers who run 'ls /' and 'cat /README' will find it.""",
            """防御には権限が必要です。スーパーユーザー 'root' は何でもでき、あなたの
アカウント 'player' はできません - sudo で root の力を借りるまでは。

  whoami              今の自分は誰か
  id                  ユーザーIDとグループ
  sudo COMMAND        1つのコマンドを root で実行
  sudo -l             実行可能な権限を一覧
  sudo -i   (または su -)   完全な root シェルに。'exit' で戻る

このサーバーでは前任者が /etc/sudoers にあなたのグループを NOPASSWD で登録
済みなので、sudo はパスワードを聞きません。確認するには:

  cat /etc/sudoers

次の行に注目:  %sudo  ALL=(ALL:ALL) NOPASSWD: ALL
'sudo' グループの一員（＝あなた）は何でも root で無料実行できる、の意味。

なお sudo が壊れた時のため root パスワードが README として隠されています。
'ls /' と 'cat /README' を試す探究者は見つけられます。"""),
    },
    {
        "key": "see-attack",
        "title": ("3. Seeing the attack", "3. 攻撃を観察する"),
        "body": (
            """You cannot block what you cannot see. Three tools reveal an attack:

1) Open ports - what is listening to the world?
     netstat -tulpn        TCP/UDP listeners with program names
     ss -tulpn             the same, newer tool
   Every open port is a door. Which ones should really be open?

2) Live packets - who is talking to us, on which port?
     tcpdump -n                  show packets (numbers, not names)
     tcpdump -n port 80          only web traffic
     tcpdump -n host 1.2.3.4     only one address
     tcpdump -c 20 -n port 22    stop after 20 packets on SSH
   Watch for one IP (or many) hammering a port - that's your attacker.

3) The logs - what has already happened?
     tail -n 40 /var/log/auth.log      SSH logins (good and failed)
     tail /var/log/apache2/access.log  every web request
     grep Failed /var/log/auth.log     just the failures

Combine them: tcpdump tells you the attacker's IP; netstat tells you the port;
the logs tell you what they tried.""",
            """見えない攻撃は防げません。攻撃を可視化する3つの道具:

1) 開いているポート - 世界に対し何が待ち受けているか？
     netstat -tulpn        TCP/UDPの待受をプログラム名付きで
     ss -tulpn             同じ、新しい道具
   開いた各ポートは扉。本当に開けておくべきなのはどれ？

2) 生パケット - 誰がどのポートに話しかけているか？
     tcpdump -n                  パケット表示（数値）
     tcpdump -n port 80          Web通信のみ
     tcpdump -n host 1.2.3.4     特定アドレスのみ
     tcpdump -c 20 -n port 22    SSHで20パケット後に停止
   1つ（または多数）のIPがポートを叩いていたら、それが攻撃者。

3) ログ - すでに何が起きたか？
     tail -n 40 /var/log/auth.log      SSHログイン（成功と失敗）
     tail /var/log/apache2/access.log  全Webリクエスト
     grep Failed /var/log/auth.log     失敗のみ

組み合わせる: tcpdumpで攻撃者IP、netstatでポート、ログで試行内容。"""),
    },
    {
        "key": "firewall",
        "title": ("4. The firewall (ufw & iptables)", "4. ファイアウォール (ufw・iptables)"),
        "body": (
            """A firewall decides which packets may enter or leave. ufw is the easy one.

Turn it on and check it:
  sudo ufw status verbose
  sudo ufw enable                 (every port is OPEN until you do this!)

Set a safe default, then open only what you need:
  sudo ufw default deny incoming
  sudo ufw allow 80/tcp           let the website through
  sudo ufw allow 443/tcp

Block an attacker or a whole subnet:
  sudo ufw deny from 203.0.113.5
  sudo ufw deny from 203.0.113.0/24
  sudo ufw deny 3306/tcp          close a dangerous port (MySQL)

Slow a flood without closing the door completely:
  sudo ufw limit 22/tcp           rate-limit SSH

Remove a rule:
  sudo ufw status numbered
  sudo ufw delete 2

iptables is the lower-level tool underneath ufw:
  sudo iptables -L -n                       list rules
  sudo iptables -A INPUT -s 1.2.3.4 -j DROP block an IP
  sudo iptables -A INPUT -p tcp --dport 23 -j DROP   close telnet""",
            """ファイアウォールはパケットの出入りを判断します。ufw が簡単です。

有効化と確認:
  sudo ufw status verbose
  sudo ufw enable                 (これをするまで全ポート開放！)

安全な既定を設定し、必要なものだけ開ける:
  sudo ufw default deny incoming
  sudo ufw allow 80/tcp           Webサイトを通す
  sudo ufw allow 443/tcp

攻撃者やサブネットを遮断:
  sudo ufw deny from 203.0.113.5
  sudo ufw deny from 203.0.113.0/24
  sudo ufw deny 3306/tcp          危険なポートを閉じる(MySQL)

扉を完全に閉じず洪水を抑える:
  sudo ufw limit 22/tcp           SSHを帯域制限

ルール削除:
  sudo ufw status numbered
  sudo ufw delete 2

iptables は ufw の下の低レベル道具:
  sudo iptables -L -n                       ルール一覧
  sudo iptables -A INPUT -s 1.2.3.4 -j DROP IP遮断
  sudo iptables -A INPUT -p tcp --dport 23 -j DROP   telnetを閉じる"""),
    },
    {
        "key": "processes",
        "title": ("5. Processes & malware", "5. プロセスとマルウェア"),
        "body": (
            """Malware runs as a process. Find it, then stop it.

List processes:
  ps aux               every process: USER, %CPU, %MEM, COMMAND
  ps aux | grep xmrig  find one by name
  top                  live view, busiest first (great for crypto-miners)

A miner or rogue script usually shows huge %CPU and an odd name or path
(e.g. /tmp/.kworker/xmrig). Note its PID (the number in column 2).

Stop it:
  sudo kill PID        politely ask it to stop
  sudo kill -9 PID     force it to stop
  sudo killall NAME    kill every process with that name

Beware PERSISTENCE - attackers make malware restart itself:
  * cron jobs:   crontab -l,  sudo crontab -u www-data -l
                 remove with: sudo crontab -u www-data -r
  * services:    systemctl status NAME
                 sudo systemctl disable --now NAME
If you kill the process but leave its cron job or service, it comes back.
Remove the persistence FIRST, then kill the process, then delete the file.""",
            """マルウェアはプロセスとして動きます。見つけて止めましょう。

プロセス一覧:
  ps aux               全プロセス: USER, %CPU, %MEM, COMMAND
  ps aux | grep xmrig  名前で検索
  top                  稼働中をCPU順に表示（マイナー発見に最適）

マイナーや不正スクリプトは %CPU が高く、変な名前やパス
(例: /tmp/.kworker/xmrig) を持ちます。PID（2列目の番号）をメモ。

停止:
  sudo kill PID        丁寧に停止要求
  sudo kill -9 PID     強制停止
  sudo killall NAME    その名前の全プロセスを停止

永続化に注意 - 攻撃者はマルウェアを再起動させます:
  * cronジョブ:  crontab -l,  sudo crontab -u www-data -l
                 削除: sudo crontab -u www-data -r
  * サービス:    systemctl status NAME
                 sudo systemctl disable --now NAME
プロセスだけ消してcronやサービスを残すと復活します。
先に永続化を除去 → プロセス停止 → ファイル削除、の順で。"""),
    },
    {
        "key": "services-config",
        "title": ("6. Hardening services", "6. サービスの堅牢化"),
        "body": (
            """Most break-ins abuse a running service (SSH, MySQL, Redis...). Two ideas:
don't expose it, and configure it safely.

Control services:
  systemctl status ssh         is it running?
  sudo systemctl stop NAME     stop now
  sudo systemctl restart NAME  restart - IMPORTANT: re-reads its config file
  sudo systemctl disable NAME  stop it starting at boot

The golden rule: editing a config file is NOT enough - you must restart the
service so it reads the change. Example (SSH):
  sudo nano /etc/ssh/sshd_config      set:  PermitRootLogin no
  sudo systemctl restart ssh          now it takes effect

Edit configs quickly with sed instead of the editor:
  sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

Don't let databases face the Internet. Bind them to localhost:
  /etc/mysql/my.cnf     bind-address = 127.0.0.1
  /etc/redis/redis.conf bind 127.0.0.1   and set  requirepass <strong>
...then restart the service (or just firewall the port shut).""",
            """侵入の多くは稼働中のサービス(SSH, MySQL, Redis...)を悪用します。要点は2つ:
露出させない、安全に設定する。

サービス制御:
  systemctl status ssh         稼働中か？
  sudo systemctl stop NAME     今すぐ停止
  sudo systemctl restart NAME  再起動 - 重要: 設定ファイルを再読込
  sudo systemctl disable NAME  自動起動を無効化

鉄則: 設定ファイルの編集だけでは不十分 - サービスを再起動して変更を
読み込ませる必要があります。例(SSH):
  sudo nano /etc/ssh/sshd_config      設定:  PermitRootLogin no
  sudo systemctl restart ssh          これで有効化

エディタの代わりに sed で素早く編集:
  sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

データベースをインターネットに晒さない。localhostに限定:
  /etc/mysql/my.cnf     bind-address = 127.0.0.1
  /etc/redis/redis.conf bind 127.0.0.1   と  requirepass <強固>
...その後サービス再起動（またはポートを遮断）。"""),
    },
    {
        "key": "patching",
        "title": ("7. Patching & supply chain", "7. パッチとサプライチェーン"),
        "body": (
            """Software has holes (vulnerabilities). We fix them by patching - usually
upgrading. But sometimes a NEW version is the attack (a supply-chain backdoor,
like the real xz/liblzma CVE-2024-3094). Then you must DOWNGRADE.

Inspect packages:
  apt list --installed            everything installed
  apt policy liblzma5             installed vs candidate version
  dpkg -l | grep ssl              search installed packages

Fix:
  sudo apt update                 refresh lists
  sudo apt upgrade                patch everything
  sudo apt install NAME=VERSION   install a SPECIFIC version (this downgrades)
  sudo apt remove NAME            uninstall

Check what you actually run:
  xz --version                    shows the liblzma version linked in

After changing a library, restart any service that uses it (e.g. ssh) so the
old, vulnerable copy is unloaded from memory.""",
            """ソフトには欠陥(脆弱性)があります。パッチ=通常はアップグレードで直します。
しかし時に新バージョン自体が攻撃(サプライチェーンのバックドア、実在の
xz/liblzma CVE-2024-3094 等)のことも。その場合はダウングレードが必要。

パッケージ調査:
  apt list --installed            導入済み一覧
  apt policy liblzma5             導入版と候補版
  dpkg -l | grep ssl              導入パッケージ検索

修正:
  sudo apt update                 リスト更新
  sudo apt upgrade                全体をパッチ
  sudo apt install NAME=VERSION   特定版を導入（＝降格）
  sudo apt remove NAME            削除

実際に動いている版を確認:
  xz --version                    連結中のliblzma版を表示

ライブラリ変更後は、それを使うサービス(例: ssh)を再起動し、古く脆弱な
コピーをメモリから解放させましょう。"""),
    },
    {
        "key": "web-security",
        "title": ("8. Web & database attacks", "8. Webとデータベース攻撃"),
        "body": (
            """Web servers are the most attacked part of any box. The big ones (OWASP):

Injection (SQL injection): user input is dropped straight into a database
query. /products.php?id=1 UNION SELECT user,pass FROM users-- steals data.
  Fix: never trust input. Use prepared statements, or at least cast to the
  expected type:  $id = intval($_GET['id']);
  And never let the database port (3306/5432/27017) face the Internet.

Unrestricted upload / web shell: an attacker uploads avatar.php that runs
system($_GET['cmd']). Now they run commands as www-data.
  Fix: delete the file, kill its process, block uploads of executable code,
  and stop the uploads folder from running PHP.

Exposed secrets: .env files, database backups (backup.sql), and keys left in
the web root get downloaded. Check your access.log for GET /.env .
  Fix: remove them from the web root, or make them non-readable (chmod 640),
  and rotate any leaked password or key.

Always read the logs:  tail /var/log/apache2/access.log""",
            """Webサーバーはどのマシンでも最も攻撃されます。代表例(OWASP):

インジェクション(SQLi): 入力がそのままDBクエリに入る。
/products.php?id=1 UNION SELECT user,pass FROM users-- でデータ窃取。
  対策: 入力を信用しない。プリペアドステートメント、最低でも型変換:
  $id = intval($_GET['id']);
  そしてDBポート(3306/5432/27017)をインターネットに晒さない。

無制限アップロード/ウェブシェル: 攻撃者が system($_GET['cmd']) を実行する
avatar.php をアップロード。www-data権限でコマンド実行される。
  対策: ファイル削除、プロセス停止、実行コードのアップロード禁止、
  アップロードフォルダでPHPを実行させない。

秘密情報の露出: .env、DBバックアップ(backup.sql)、Webルートの鍵が
ダウンロードされる。access.log の GET /.env を確認。
  対策: Webルートから除去、または読取不可に(chmod 640)、
  漏洩したパスワードや鍵は再発行。

常にログを読む:  tail /var/log/apache2/access.log"""),
    },
    {
        "key": "playbook",
        "title": ("9. Defender's playbook", "9. 防御者の手順書"),
        "body": (
            """A calm, repeatable routine beats panic. When a level starts:

1. READ the briefing:   mission
2. SEE it:              netstat -tulpn   /   tcpdump -n   /   tail the logs
3. IDENTIFY the threat: which port? which process? which file? which IP?
4. CONTAIN it fast:     block the IP or port with ufw; kill the live process
5. REMOVE it properly:  delete malware, remove cron/service persistence,
                        patch or fix the vulnerable config/code
6. KEEP SERVICE UP:     don't break the thing you're defending
                        (e.g. stop the flood but keep the website running)
7. VERIFY:              objectives    (each [ ] should become [x])
8. If stuck:            hint          (recorded in your progress report)

Remember the order for persistent malware:
   persistence first  ->  process  ->  file.

The clock is running, but accuracy beats speed on your first clear. Speed comes
with practice - and that's what the Top 10 speed runs are for.""",
            """慌てるより、落ち着いた反復手順が勝ちます。レベル開始時:

1. briefingを読む:    mission
2. 観察する:          netstat -tulpn / tcpdump -n / ログをtail
3. 脅威を特定:        どのポート？どのプロセス？どのファイル？どのIP？
4. 素早く封じ込め:    ufwでIP/ポート遮断、稼働プロセスをkill
5. 適切に除去:        マルウェア削除、cron/サービスの永続化除去、
                      脆弱な設定/コードをパッチ・修正
6. サービス維持:      守っている対象を壊さない
                      (例: 洪水は止めてもWebサイトは稼働維持)
7. 検証:              objectives   (各 [ ] が [x] になるように)
8. 行き詰まったら:    hint         (進捗レポートに記録)

永続マルウェアの順序を忘れずに:
   永続化が先 → プロセス → ファイル。

時計は進みますが、初クリアは速さより正確さ。速さは練習で付きます -
そのためのトップ10スピードランです。"""),
    },
]


def lesson_keys():
    return [l["key"] for l in LESSONS]
