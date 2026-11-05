# 接続障害とホスト保守の記録

[English](host-maintenance.md) · [記録目次](README.ja.md)

> 文書種別：**記録**．実行した設定・検査の証拠を保存する．現在の操作手順とは区別する．

## 接続断とデスクトップ不調の切り分け

2026-11-03の調査では，通知，接続断，画面フリーズを一つの確定原因として扱わず，次を分けた．

- 操作者の再起動前，保存syslogにeduroamの接続・認証タイムアウトが繰り返し記録されていた．
  NetworkManagerは保存済みsecretが存在すると明示し，再要求後に最後は`no-secrets`で失敗した．
  この最終理由だけで保存パスワードの欠落・誤りを断定しない．再起動後は同じ保存profileでPEAPが成功し，
  GUIログイン前に接続した．AP・認証service・supplicantのどこに責任があるかは未確定である．
  Wi-Fiの認証情報，CA確認，再試行設定は変更していない．
- 旧GUIアカウントは，それまで維持した自動ログイン先だった．操作者が再起動後に研究用アカウントへ変更し，
  エージェントは変更していない．再起動前もLinux認証自体は成功し，その後のローカルGUI起動でGNOME FIFO警告と
  XRDP音声用の環境変数が記録された．セッション残留・競合は仮説で，フリーズ原因の証明ではない．
  現在もローカル・RDPのGUIが同じアカウントを共有する．RDP client切断をsessionログアウトと同一視しない．
  session終了，GNOME reset，描画driver置換は行っていない．
- 未処理の報告一つは，2026-11-01の本プロジェクトの**意図的な起動待ち失敗試験**で生成されたものだった．
  想定内の例外を未処理にしたため，ホストのクラッシュ報告機構が働いた．helperは修正し，想定したアドレス・
  ファイル・subprocess失敗を捕捉して短い診断を残し，systemd再試行用の終了コード1を返す．
  特定した自分の古い試験報告だけを非公開へ退避し，別の古いブラウザ報告は維持した．操作者が見た通知が
  どちらの報告かは独立に確認していない．helperの失敗はWi-Fi接続断の説明にはならない．

journalは揮発保存で，今回の起動分だけだった．保存syslog・認証ログから直前起動の一部を得た．
生の抜粋はGit対象外の`local/access-incident-20261103-01`に置く．起動時計は時刻同期で修正された．
その際のTailscaleの大きな見かけ上のsleep時間だけでは，物理的なサスペンドの証明にならない．
同一起動内はmonotonic時刻を使い，起動をまたぐ経過時間は時計補正を確認して解釈する．
調査時，両GUIアカウントのAC時サスペンド動作は`nothing`だったが，過去の設定を復元する証拠ではない．

再発時は，可能なら再起動前に，今回・前回の起動ログの有無，NetworkManager・supplicantのmessage，
login・session状態を保全する．クラッシュはまず**メタデータ**を確認し，報告のupload，ブラウザ内容の収集，
networkパスワードの表示は行わない．実際のactive connectionとsecret保存flagを値を出さずに調べ，
認証情報の不足，認証失敗，IP取得失敗を区別する．相手の識別情報・生ログは非公開にする．
[本家XRDPの議論](https://github.com/neutrinolabs/xrdp/issues/2027)は関連するGNOME・FIFO事例で，
この個体も同じ原因という証明ではない．想定失敗の処理・導入済みhelperの検査は通り，
Mac・Jetsonで通常テスト164件が成功した．一回の再起動復帰で，次のeduroam認証停止からの自動復旧は証明しない．


同日，実際の画面を取得し，汎用の`update-notifier`のシステム障害通知であることを確認した．
残っていたクラッシュファイルは，2026-10-28の古いChrome SIGTRAP報告一つだった．通知自体は，
現在新たに故障している部品や，Chromeの詳しい停止原因を示さない．報告のupload・ブラウザ報告の削除は行っていない．
画面の証拠を保存後，操作者の依頼で実機側の研究用GUIだけをログアウトした．遠隔GUI・SSHは維持され，
その後RDP displayでGNOMEとEWMHのwindow managerが動作し，操作者もclient側の画面表示を確認した．
GUI自動ログイン設定は維持したため，一回のログアウトだけで次回起動時の物理GUI・RDP重複を防ぐわけではない．



## 手動更新とデスクトップ通知

以下の通知だけの変更後，別途操作者が承認した**2026-11-03**の保守処理でAPT索引を更新し，
OpenSSH client／server／SFTPを`1:8.2p1-4ubuntu0.12`から`1:8.2p1-4ubuntu0.13`へ，
Chromeを`156.0.8078.47-1`から`156.0.8078.79-1`へ更新した．追加・削除・他packageの版変更はなく，
SSH設定とservice検査も通った．GPUイメージ，JetPack／CUDA，kernelは維持した．
Ubuntu 20.04の追加修正には研究室のESM権利が必要な場合があり，契約は追加していない．
最新保護を全て満たすという意味ではない．[保守記録](milestone-2026-11-03.ja.md#62026-11-03に適用した保守更新)を参照する．

外付けJetsonは，実測した環境に合わせてUbuntu 20.04，JetPack 5.1.2・L4T 35.4.1，CUDA 11.4を
意図的に維持する．ホストのrelease・kernel・GPU更新には互換性・復旧の計画が必要で，コンテナでも
ホストdriver変更の影響は隔離できない．BSP packageの組と対応する更新経路は
[NVIDIAの35.4.1更新手順](https://docs.nvidia.com/jetson/archives/r35.4.1/DeveloperGuide/text/SD/SoftwarePackagesAndTheUpdateMechanism.html)に記載されている．
セキュリティ更新まで全て不要という意味ではない．

2026-11-03の調査では，release通知は既に`never`で，unattended-upgrades serviceは未導入，
package索引の毎日更新は有効，package holdはなかった．既存のローカル索引による模擬実行では
143個の更新，追加・削除ゼロが提案された．今回の通知変更ではpackage取引や索引の再取得は行っていない．
このcache上の提案は，現在の脆弱性監査・互換性承認ではない．索引更新・通知と，packageの自動導入は別である．

導入済み`update-notifier` 3.192.30.19は，`no-show-notifications`の分岐より前にUpdate Managerを
起動する．対応する[Ubuntu公式source archive](https://ports.ubuntu.com/ubuntu-ports/pool/main/u/update-notifier/update-notifier_3.192.30.19.tar.xz)を
確認し，そのGSettingsだけでは更新画面の自動表示を止められないと分かった．source archive・hash・
選んだ設定は非公開で維持し，packageの実行ファイルは改変していない．

操作者は**更新・クラッシュ報告の両GUI通知**を止める方針を明示的に選んだ．研究用アカウントだけの
`~/.config/autostart/update-notifier.desktop`へsystemのdesktop entryを写し，`Hidden=true`にした．
動作中の研究用notifierも終了した．ユーザー単位の上書きは[XDG autostart仕様](https://specifications.freedesktop.org/autostart/latest/)に従う．
desktop fileは，元からのEncoding非推奨警告だけで検証を通り，updater GUI processは残っていない．
他のアカウントとsystem側autostartファイルは維持した．背景監視，Mac設定，package削除，代わりの更新serviceは加えていない．

クラッシュ収集，`/var/crash`，journal・syslog，手動分析は残る．今後，研究用GUIではこのnotifierによる
新しいクラッシュの自動通知も出なくなる．RDP，Tailscale，Wi-Fiの通知・認証serviceは別である．
意図した手動updater起動やAPTを禁止する設定ではなく，索引更新timerも維持する．

[Ubuntuのpackageガイド](https://ubuntu.com/server/docs/how-to/software/package-management/)のとおり，APTは使える．
`apt update`は索引更新で，導入済みソフトの更新ではない．まず候補を確認し，**選んだ**packageを模擬実行する．

```sh
sudo apt update
apt list --upgradable
sudo apt-get -s install --only-upgrade PACKAGE_NAME
```

版，依存，service再起動，復旧を確認してから，選んだ取引を実行する．

```sh
sudo apt install --only-upgrade PACKAGE_NAME
```

`PACKAGE_NAME`は代入するための雛形で，そのまま実行する名前ではない．未確認の一括`upgrade`・`full-upgrade`，
一般PC用NVIDIA driver，Ubuntu release更新をJetson保守の代わりに使わない．BSP・CUDA・ROS・ZED変更や
セキュリティpatchは，対象と確認方法を別途決める．GPU imageとモデル用Python依存は別の版管理対象で，
ホストAPT更新ではそれらのimageや固定モデル入力は更新されない．

変更前・適用・検証の非公開記録は`local/update-policy-01`にある．戻す場合は，元のユーザーoverrideが
存在したら復元し，なければ新しく作ったユーザーoverrideだけを取り除いて再ログインする．この対象機に
以前のoverrideはなかった．systemのファイルを維持し，通知を戻すためにクラッシュログを書き換えない．

2026-11-03に依頼されたARM64 VS Codeを，新規host package `code`（1.144.1）1個だけ導入した．
この取引で他の導入済みpackage版は変わらず，Microsoft APT sourceも追加しなかった．
RDPはclipboard無効から文字だけ双方向転送へ変更し，既存sessionは閉じていない．
[操作手順](../how-to/remote-desktop.ja.md)を参照する．証拠と設定backupは非公開`local/editor-setup-01`に置いた．
