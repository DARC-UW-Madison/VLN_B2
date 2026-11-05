# 次回のB2訪問：構成を調べ，Jetsonで状態を受信する

[English](next-visit.md) · [ドキュメント](../README.ja.md) · [仕組み](../explanations/network-topology.ja.md)

> 文書種別：**操作手順**．目的は既存i7の構成調査と，外付けJetsonへの状態streamの記録である．姿勢・移動は要求しない．事前確認の結果は[準備の記録](../records/previsit-readiness-2026-11-04.ja.md)に記す．

## 1．既存の配線から始める

B2のUSB-C → Anker Ethernet adapter → LANケーブル → 外付けJetsonという既存配線を使う．B2を起動し，
外付けJetsonは現在の別電源で動かす．この手順を始めるために，別のadapterを探したり購入したりする必要はない．
pairing済みリモコンと研究室の操作者を用意し，機体は現在の休止状態を保つ．動作exampleは起動しない．

以下のコマンドは，全て**外付けJetsonの端末**で実行する．MacのSSHでもJetsonの画面でもよい．Macが機体状態を配信するわけではない．
profileは接続設定を保存したJSONで，固定host keyは信頼したSSH接続先を識別する鍵である．非公開profileは，以前に確認したi7の接続先とhost keyから準備してあり，パスワードは含まない．訪問前に存在を確認する．

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
python3 tools/field_visit.py --config local/field-connection.json
```

既定の`plan`段階は，profileの書式と固定host keyファイルの存在を調べる．接続せず，到達性は確認しない．profileの権限は600にする．
正規アカウント，scope付きIPv6接続先，固定host keyの別名，既存ROS設定二つのpath，内部interface，DDS domainを指定している．
これらの識別子は非公開とする．一般的な項目の定義は[tool](../../tools/field_visit.py)の`CONFIG_KEYS`にある．

## 2．i7のソフト・経路・filterを保存する

```sh
python3 tools/field_visit.py --config local/field-connection.json \
  --stage inventory --output local/next-visit-01-inventory
```

必要ならSSHが端末で内蔵Linuxアカウントのパスワードを求める．外付けJetsonや大学Wi-Fiのパスワードとは別である．
コマンド，JSON，チャット，Gitへ書かない．host keyが違う場合は中止し，機器と信頼する鍵を照合する．照合を無効化しない．

コマンドは子shellで既存ROS・message環境を読み込み，i7のsystem Pythonを実行して終了する．i7へファイル・ソフトは導入しない．
packageの版とmoduleの場所，アドレス・経路，bridgeへの所属，転送設定，message sourceの版，閲覧できるfirewall ruleを収集する．
firewallは`sudo -n`で読むため，sudoのパスワードを要求・保存しない．拒否された項目は`permission_required`と残る．
配布packageのmetadataがなくても，sourceから導入されている場合があり，SDK不存在の証明にはならない．

新しい出力先には次が入る．

| ファイル | 意味 |
|---|---|
| `method.json` | ソース版，実行したremote codeとprofileのhash，検査段階 |
| `events.jsonl` | i7から返った非公開inventoryとJetsonでの受信時刻 |
| `ssh-stderr.log` | 認証・workspaceの非公開診断 |
| `summary.json` | 収集結果と追加確認が必要な項目 |

`collection_complete: true`は，報告を欠けずに受け取った意味である．`probes_needing_followup`，`package_metadata_missing`，
inventory本体を読む．全ソフトの版・firewallを確認できたという意味ではない．現地で閲覧権限のある調査が必要な場合もある．
`plan`の出力には，固定鍵を使ってi7のshellを開くSSHコマンド全体が表示される．そのコマンドを外付けJetsonの端末で実行して認証する．
開いた**i7のshell**では，次でIPv4・IPv6 ruleを変更せず表示できる．

```sh
sudo iptables-save
sudo ip6tables-save
```

出力を読んで非公開で記録し，`exit`でJetsonのshellへ戻る．権限がない・commandがない場合は未解決と記す．この手順ではtool導入，ruleの消去，新たな権限付与は行わない．
状態取得の前に，profileの内部interface・domainをinventoryと照合する．

## 3．Jetsonへ10秒のstreamを記録する

```sh
python3 tools/field_visit.py --config local/field-connection.json \
  --stage state --seconds 10 --output local/next-visit-01-state
```

i7は`/lf/sportmodestate`だけを購読し，一件ずつSSHの標準出力へ流す．Jetsonは届く間に読み，Jetsonの受信時刻を付け，一行にJSON一件を保存する形式（JSONL）へ記録する．
取得後にまとめてファイルをコピーする方式でも，Jetsonが直接DDSへ参加する方式でもない．i7側のprocessは45秒，
呼出側は別に55秒の期限を持つ．Ctrl+Cでこの診断を終了できる．node・中継・自動起動serviceを常駐させる手順ではない．

表示された集計と`summary.json`を読む．診断基準は，有限値（NaN・無限大ではない数値）の状態20件以上，受信の時間幅2秒以上，受信間隔0.5秒以下，
最後の件数の一致，SSHの正常終了である．この訪問で継続性を調べる基準であり，**制御ループの承認済み制限値ではない**．
終了コードが非ゼロ，または`transport_passed: false`なら経路を合格としない．
可能な場合は実際に読み込まれたDDS libraryのファイルとhashも残すが，それだけでsource版を確定しない．

位置・速度・姿勢・mode・errorは機体が報告した生の値で，座標系と機体側の時計は未検証と明記する．Jetsonとi7の受信時刻は
別々の単調時計（時刻合わせで逆戻りしない経過時間用の時計）であり，引き算して片道遅延としない．この記録を，検証済みのモデル入力として扱わない．

再試行では新しい出力名を使う．既存の出力先は上書きせず拒否する．

## 4．確認に失敗した場合

| 観測 | 次にすること |
|---|---|
| profile・固定鍵がない | 非公開の準備済みファイルを復旧する．IPを推測しない |
| 最初のSSH宛先がtimeout | B2電源・配線・JetsonのEthernet carrier（ケーブル先と物理リンクが成立しているか）を確認し，下の別profileを選ぶ |
| 認証失敗・鍵の変更 | 研究室の認証・機器同一性を確認する．再試行や鍵確認の無効化を続けない |
| ROS workspace・module不足 | `ssh-stderr.log`とinventoryを読む．conda Pythonへの置換やROS再導入を自動で行わない |
| 状態0件・最後の集計なし | i7内部interface，domain，配信元，エラーを再確認する |
| 長い空白・一度にまとめて届く | 記録を残し，モデル結合前に処理割当て・ネットワーク配送を調べる |
| firewallの閲覧拒否 | 許可された読取調査を完了する．bridge・ルーティングの実現性は未解決とする |

別profileは，同じi7で以前に確認した別のlink-local宛先と，同じ固定鍵を使う．最初の宛先がtimeoutした後にだけ，新しい出力先で使う．

```sh
python3 tools/field_visit.py --config local/field-connection-alternate.json \
  --stage inventory --output local/next-visit-02-inventory
```

## 5．ネットワークの具体案を残して終了する

inventoryから，管理通信・既存機体serviceを維持して，現在のUSB側と内部側をbridgeまたはルーティングできるか調べる．
アプリケーション中継と，物理的に同定できた場合の内部LANへの別Ethernet接続も比較する．SSH streamが通っても，
方式の決定や設定変更の許可が自動的に済むわけではない．

選ぶ案について，必要なinterface・アドレス・filter変更，復旧経路，繰り返せる受信専用の受入試験を残す．
この診断手順ではbridge・経路・firewallを変更しない．次の別作業は，状態・画像の時刻と座標を検証し，指令を送らないモデル入力へ結合することになる．
姿勢・移動・物理的停止には，別に場所と試験手順を用意する．

任意の内蔵カメラ確認には[センサー手順](built-in-sensors.ja.md)，外付けカメラ・モデルのデモには[短いデモ](live-camera-demo.ja.md)を使う．
これらは確認する対象が違うため，状態試験の代わりにしない．
