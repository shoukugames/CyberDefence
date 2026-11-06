"""English / Japanese string tables and the translator."""

STR = {
    # --- generic UI ---
    "app.title": ("CyberDefence", "サイバーディフェンス"),
    "app.tagline": ("Defend the server. Beat the clock.", "サーバーを守れ。時間との勝負。"),
    "menu.play": ("Select Level", "レベル選択"),
    "menu.training": ("Training", "トレーニング"),
    "menu.progress": ("Progress Report", "進捗レポート"),
    "menu.records": ("Top 10 Speed Runs", "トップ10スピードラン"),
    "menu.credits": ("Credits", "クレジット"),
    "menu.settings": ("Settings", "設定"),
    "menu.quit": ("Quit", "終了"),
    "menu.back": ("Back", "戻る"),
    "menu.hint.nav": ("Up/Down: move   Enter: select   Esc: back", "上下: 移動   Enter: 決定   Esc: 戻る"),
    "menu.hint.toggle": ("L: language   M: music   F: fullscreen", "L: 言語   M: 音楽   F: 全画面"),
    "common.completed": ("COMPLETED", "クリア済"),
    "common.locked": ("LOCKED", "ロック中"),
    "common.open": ("OPEN", "挑戦可"),
    "common.best": ("Best", "最速"),
    "common.on": ("ON", "オン"),
    "common.off": ("OFF", "オフ"),
    "common.yes": ("yes", "はい"),
    "common.no": ("no", "いいえ"),
    "common.press_enter": ("Press Enter to continue...", "Enterで続ける..."),
    "common.none_yet": ("No records yet - be the first!", "記録なし - 一番乗りを目指そう！"),
    "lang.name": ("English", "日本語"),

    # --- settings ---
    "set.lang": ("Language", "言語"),
    "set.bgm": ("Background music", "BGM"),
    "set.sfx": ("Sound effects", "効果音"),
    "set.fullscreen": ("Fullscreen", "全画面表示"),
    "set.volume": ("Music volume", "音量"),
    "set.reset": ("Reset all progress", "進捗をリセット"),
    "set.reset.confirm": ("Press R again to erase ALL progress and records", "もう一度Rで全進捗と記録を消去"),
    "set.reset.done": ("All progress erased.", "全進捗を消去しました。"),

    # --- level select ---
    "sel.title": ("SELECT A LEVEL", "レベルを選択"),
    "sel.level": ("Level", "レベル"),
    "sel.threat": ("Threat", "脅威"),
    "sel.start": ("Enter: start level", "Enter: レベル開始"),
    "sel.complete_count": ("Levels complete: {done} / {total}", "クリア: {done} / {total}"),

    # --- level names + briefings ---
    "lvl.1.name": ("DDoS Flood", "DDoS 洪水攻撃"),
    "lvl.2.name": ("SQL Injection", "SQLインジェクション"),
    "lvl.3.name": ("PHP Web Shell", "PHPウェブシェル"),
    "lvl.4.name": ("SSH Brute Force", "SSHブルートフォース"),
    "lvl.5.name": ("Crypto-Miner Malware", "仮想通貨マイナー"),
    "lvl.6.name": ("Exposed Redis RCE", "Redis無認証RCE"),
    "lvl.7.name": ("CUPS Printer RCE", "CUPS プリンタRCE"),
    "lvl.8.name": ("XZ Supply-Chain Backdoor", "XZサプライチェーン"),
    "lvl.9.name": ("Rogue Exfil Script", "不正流出スクリプト"),
    "lvl.10.name": ("Data Breach / Secrets", "情報漏洩・秘密情報"),

    "lvl.1.brief": (
        "A botnet is hammering port 80 with a SYN flood. The web server is drowning.\n"
        "Stop the flood WITHOUT taking the website down for real users.",
        "ボットネットがポート80にSYN洪水攻撃を仕掛けています。ウェブサーバーが溺れそうです。\n"
        "本物の利用者のサイトを落とさずに、洪水を止めてください。"),
    "lvl.2.brief": (
        "sqlmap is injecting SQL through /products.php and reading your database.\n"
        "Fix the vulnerable code and make sure MySQL is not exposed to the Internet.",
        "sqlmap が /products.php 経由でSQLを注入し、データベースを読み取っています。\n"
        "脆弱なコードを修正し、MySQLがインターネットに露出しないようにしてください。"),
    "lvl.3.brief": (
        "An unrestricted upload let an attacker drop a PHP web shell in /uploads.\n"
        "Kill it, delete it, and lock the attacker out.",
        "無制限アップロードにより攻撃者が /uploads にPHPウェブシェルを設置しました。\n"
        "プロセスを停止し、ファイルを削除し、攻撃者を遮断してください。"),
    "lvl.4.brief": (
        "A botnet is brute-forcing the SSH root password. One guess could own the box.\n"
        "Shut down root password logins (and reload sshd) or firewall SSH off.",
        "ボットネットがSSHのrootパスワードを総当たり中です。1回の的中で乗っ取られます。\n"
        "rootのパスワードログインを無効化（sshd再読込）するか、SSHを遮断してください。"),
    "lvl.5.brief": (
        "A crypto-miner is pinning the CPU and has added itself to cron for persistence.\n"
        "Kill the miner, remove its cron job and delete the binary.",
        "仮想通貨マイナーがCPUを占有し、cronに登録して居座っています。\n"
        "マイナーを停止し、cronジョブを削除し、バイナリを消してください。"),
    "lvl.6.brief": (
        "Redis is listening on 0.0.0.0 with no password. Attackers can write files as root.\n"
        "Lock Redis down: firewall it, or bind to localhost + set a password, then restart.",
        "Redisがパスワードなしで0.0.0.0を待ち受け中。攻撃者がroot権限でファイルを書けます。\n"
        "Redisを封鎖: 遮断するか、localhostに限定＋パスワード設定後に再起動してください。"),
    "lvl.7.brief": (
        "cups-browsed on UDP 631 is accepting rogue printers (CVE-2024-47176) - RCE risk.\n"
        "Stop cups-browsed or block UDP 631, and remove the rogue printer.",
        "UDP631のcups-browsedが不正プリンタを受付中（CVE-2024-47176）。RCEの危険。\n"
        "cups-browsedを停止するかUDP631を遮断し、不正プリンタを削除してください。"),
    "lvl.8.brief": (
        "liblzma5 5.6.1 carries the xz backdoor (CVE-2024-3094) and is linked into sshd.\n"
        "Downgrade the compromised package and restart sshd to unload it.",
        "liblzma5 5.6.1 にxzバックドア（CVE-2024-3094）が仕込まれ、sshdに連結されています。\n"
        "汚染パッケージをダウングレードし、sshdを再起動して解放してください。"),
    "lvl.9.brief": (
        "A rogue systemd service 'update-check' is exfiltrating /etc every 30 seconds.\n"
        "Disable and remove the service, kill it, and clean the attacker's SSH key.",
        "不正なsystemdサービス'update-check'が30秒ごとに/etcを流出させています。\n"
        "サービスを無効化・削除・停止し、攻撃者のSSH鍵を除去してください。"),
    "lvl.10.brief": (
        "Your .env, a SQL backup, and an open MongoDB are leaking customer data.\n"
        "Remove/secure the exposed files and close MongoDB to the Internet.",
        ".env、SQLバックアップ、無認証MongoDBから顧客データが漏洩しています。\n"
        "露出ファイルを削除・保護し、MongoDBをインターネットから遮断してください。"),

    # --- objectives ---
    "obj.ddos.block": ("Block the flooding bot IPs (or rate-limit port 80)", "洪水を起こすボットIPを遮断（またはポート80を制限）"),
    "obj.ddos.syn": ("Enable SYN cookies (net.ipv4.tcp_syncookies=1)", "SYN cookieを有効化 (net.ipv4.tcp_syncookies=1)"),
    "obj.ddos.up": ("Keep the web server (port 80) running", "ウェブサーバー（ポート80）を稼働維持"),
    "obj.sqli.db": ("Close MySQL (3306) to the Internet", "MySQL (3306) をインターネットから遮断"),
    "obj.sqli.code": ("Patch products.php against injection", "products.php の注入脆弱性を修正"),
    "obj.sqli.block": ("Block the attacker's IP from the web server", "攻撃者IPをウェブサーバーから遮断"),
    "obj.webshell.rm": ("Delete the web shell file", "ウェブシェルのファイルを削除"),
    "obj.webshell.kill": ("Kill the web shell process", "ウェブシェルのプロセスを停止"),
    "obj.webshell.block": ("Block the attacker's IP", "攻撃者のIPを遮断"),
    "obj.brute.root": ("Disable root password login in sshd_config", "sshd_configでrootパスワードログインを無効化"),
    "obj.brute.apply": ("Reload sshd (or firewall SSH off the Internet)", "sshdを再読込（またはSSHを遮断）"),
    "obj.brute.block": ("Stop the brute-force reaching port 22", "総当たりがポート22に届かないようにする"),
    "obj.ransom.kill": ("Kill the crypto-miner process", "マイナーのプロセスを停止"),
    "obj.ransom.cron": ("Remove the miner's cron job", "マイナーのcronジョブを削除"),
    "obj.ransom.bin": ("Delete the miner binary", "マイナーのバイナリを削除"),
    "obj.redis.closed": ("Stop Redis facing the Internet", "Redisのインターネット露出を停止"),
    "obj.redis.auth": ("Require a password or bind to localhost", "パスワード必須化またはlocalhost限定"),
    "obj.redis.apply": ("Apply the change (restart / firewall)", "変更を適用（再起動／遮断）"),
    "obj.cups.stop": ("Stop cups-browsed (or block UDP 631)", "cups-browsedを停止（またはUDP631遮断）"),
    "obj.cups.block": ("Block rogue printer discovery on UDP 631", "UDP631の不正プリンタ探索を遮断"),
    "obj.cups.printer": ("Remove the rogue EVIL_PRINTER", "不正なEVIL_PRINTERを削除"),
    "obj.backdoor.downgrade": ("Downgrade liblzma5 off 5.6.x", "liblzma5を5.6系から降格"),
    "obj.backdoor.restart": ("Restart sshd to unload the backdoor", "sshdを再起動してバックドアを解放"),
    "obj.backdoor.proc": ("Remove the backdoor listener", "バックドアのリスナーを除去"),
    "obj.script.stop": ("Disable + stop the rogue service", "不正サービスを無効化・停止"),
    "obj.script.rm": ("Delete the script and unit file", "スクリプトとユニットファイルを削除"),
    "obj.script.key": ("Remove the attacker's SSH key from root", "rootから攻撃者のSSH鍵を削除"),
    "obj.exfil.env": ("Stop .env being downloadable", ".envのダウンロードを阻止"),
    "obj.exfil.backup": ("Remove the SQL backup from the web root", "ウェブルートからSQLバックアップを削除"),
    "obj.exfil.mongo": ("Close MongoDB (27017) to the Internet", "MongoDB (27017) をインターネットから遮断"),

    # --- in-game HUD ---
    "hud.time": ("TIME", "時間"),
    "hud.load": ("LOAD", "負荷"),
    "hud.net": ("NET", "通信"),
    "hud.level": ("LEVEL", "レベル"),
    "hud.objectives": ("OBJECTIVES", "目標"),
    "hud.secured": ("SERVER SECURED", "サーバー防衛成功"),
    "game.win.title": ("*** LEVEL CLEARED - THREAT NEUTRALISED ***", "*** レベルクリア - 脅威排除 ***"),
    "game.win.time": ("Completed in {time} on {date}", "{date} に {time} でクリア"),
    "game.win.record": ("NEW TOP 10 RECORD!  Rank #{rank}", "トップ10入り！ {rank}位"),
    "game.win.name": ("Enter your name for the leaderboard: ", "ランキングに名前を入力: "),
    "game.win.saved": ("Saved. Returning to menu...", "保存しました。メニューに戻ります..."),
    "game.win.cont": ("Type 'menu' to return, or keep exploring the server.", "'menu'でメニューへ。サーバー探索も続行可。"),
    "game.quit": ("Type 'menu' to abandon the level and return to the main menu.", "'menu'でレベルを放棄しメニューへ。"),

    # --- shell / errors ---
    "sh.welcome_hdr": ("CyberOS 12 (BusyBox edition)  -  websrv01  -  UNDER ATTACK", "CyberOS 12 (BusyBox版)  -  websrv01  -  攻撃を受けています"),
    "sh.type_help": ("Type 'help' for commands, 'mission' for the briefing, 'hint' if stuck.", "'help'でコマンド、'mission'で任務、'hint'でヒント。"),
    "sh.need_root": ("permission denied: this needs root. Try: sudo {cmd}", "権限がありません: rootが必要です。例: sudo {cmd}"),
    "sh.not_found": ("{cmd}: command not found", "{cmd}: コマンドが見つかりません"),
    "sh.no_file": ("{path}: No such file or directory", "{path}: そのようなファイルやディレクトリはありません"),
    "sh.is_dir": ("{path}: Is a directory", "{path}: ディレクトリです"),
    "sh.not_dir": ("{path}: Not a directory", "{path}: ディレクトリではありません"),
    "sh.denied": ("{path}: Permission denied", "{path}: 権限がありません"),
    "sh.usage": ("usage: {u}", "使い方: {u}"),
    "sh.hint_recorded": ("[hint recorded in your progress report]", "[ヒントは進捗レポートに記録されました]"),
    "sh.no_hint": ("No more hints for this level. You've got this!", "このレベルのヒントは以上です。頑張って！"),
    "sh.objectives_done": ("All objectives met! The threat is neutralised.", "全目標達成！脅威は排除されました。"),
    "sh.man_none": ("No manual entry for {cmd}", "{cmd} のマニュアルはありません"),
    "sh.man_limited": ("(man pages are limited in this simulator)", "（このシミュレータのmanは簡易版です）"),
    "sh.sudo_ask": ("[sudo] password for player: ", "[sudo] player のパスワード: "),
    "sh.sudo_hint": ("Hint: the sudoers file gives your group NOPASSWD. Just run 'sudo <command>'.", "ヒント: sudoersでグループにNOPASSWDが付与済。'sudo <コマンド>'でOK。"),
    "sh.now_root": ("You are now root. Type 'exit' to drop back to player.", "rootになりました。'exit'でplayerに戻ります。"),
    "sh.confirm_flood": ("Server still under attack - objectives not yet met.", "サーバーは攻撃継続中 - 目標未達成。"),

    # --- training ---
    "train.title": ("TRAINING ACADEMY", "トレーニング・アカデミー"),
    "train.intro": ("Pick a lesson. Read it, then try the commands in a real level.", "レッスンを選び、実際のレベルで試そう。"),
    "train.read": ("[read]", "[読了]"),
    "train.scroll": ("Up/Down or PgUp/PgDn: scroll   Esc: back", "上下/PgUp/PgDn: スクロール   Esc: 戻る"),

    # --- progress / records ---
    "prog.title": ("PROGRESS REPORT", "進捗レポート"),
    "prog.subtitle": ("For players, teachers and parents", "プレイヤー・先生・保護者向け"),
    "prog.overall": ("Levels completed: {done} of {total}   ({pct}%)", "クリア済レベル: {done}/{total}   ({pct}%)"),
    "prog.playtime": ("Total play time: {time}", "総プレイ時間: {time}"),
    "prog.hints": ("Hints used: {n}", "使用ヒント数: {n}"),
    "prog.lessons": ("Lessons read: {n} of {total}", "読了レッスン: {n}/{total}"),
    "prog.col.level": ("Level / Threat", "レベル／脅威"),
    "prog.col.status": ("Status", "状態"),
    "prog.col.best": ("Best time", "最速"),
    "prog.col.when": ("Completed on", "クリア日時"),
    "prog.col.tries": ("Tries", "挑戦"),
    "prog.skills": ("Skills practised: firewalls, process control, log analysis, service hardening, patching.",
                    "習得スキル: ファイアウォール、プロセス制御、ログ解析、サービス堅牢化、パッチ適用。"),
    "rec.title": ("TOP 10 SPEED RUNS", "トップ10スピードラン"),
    "rec.pick": ("Left/Right: choose level", "左右: レベル選択"),
    "rec.rank": ("Rank", "順位"),
    "rec.name": ("Name", "名前"),
    "rec.time": ("Time", "タイム"),
    "rec.date": ("Date", "日付"),

    # --- credits ---
    "cred.title": ("CREDITS", "クレジット"),
    "cred.created": ("Created by", "制作"),
    "cred.with": ("with", "協力"),
    "cred.version": ("Version", "バージョン"),
    "cred.date": ("Release date", "リリース日"),
    "cred.web": ("Website", "ウェブサイト"),
    "cred.email": ("Email", "メール"),
    "cred.license": ("License", "ライセンス"),
    "cred.ages": ("Recommended ages 16+", "対象年齢 16歳以上"),
    "cred.thanks": ("Thank you for playing. Stay curious, stay secure.", "プレイありがとう。好奇心を持って、安全に。"),
}


class I18n:
    def __init__(self, lang="en"):
        self.lang = lang if lang in ("en", "ja") else "en"

    def set(self, lang):
        self.lang = lang if lang in ("en", "ja") else "en"

    def toggle(self):
        self.lang = "ja" if self.lang == "en" else "en"
        return self.lang

    def __call__(self, key, **kw):
        pair = STR.get(key)
        if pair is None:
            return key
        text = pair[1] if self.lang == "ja" else pair[0]
        if kw:
            try:
                return text.format(**kw)
            except (KeyError, IndexError):
                return text
        return text

    def t(self, pair_or_key, **kw):
        if isinstance(pair_or_key, tuple) and len(pair_or_key) == 2 and isinstance(pair_or_key[1], dict):
            return self(pair_or_key[0], **pair_or_key[1])
        return self(pair_or_key, **kw)
