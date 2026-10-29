# 分離したRDPサーバーのビルドと導入確認

[English](rdp-build.md) · [文書目次](README.ja.md) · [遠隔画面の概念](remote-desktop.ja.md)

## このビルドが必要な理由

調べたUbuntu Focalの配布候補はxrdp `0.9.12-1ubuntu0.1`である．
[USN-8476-1](https://ubuntu.com/security/notices/USN-8476-1)の修正は，その候補にはないESM版に含まれる．
通常の古いパッケージの導入では，確認した修正条件を満たさない．Ubuntu Pro登録，
OS更新，描画ドライバの置換は今回の作業に含めない．

[remote-desktop.Dockerfile](../deploy/remote-desktop.Dockerfile)は，対応するL4Tコンテナで
新しい本家ソフトをビルドする候補レシピである．ホストへ明示的に確認して導入するファイルを作り，
モデル用コンテナの中でデスクトップを動かすものではない．ビルド，書き出し，ホスト導入，
サーバー起動，画面へのログイン成功という五つの証拠を分けて扱う．

## 固定入力と出力の境界

| 入力 | 固定した版 | 用途 |
|---|---|---|
| L4T 35.4.1の基底 | Dockerfileのdigest．確認済み推論レシピと共通 | 対応するARM64・Focalのビルド環境 |
| xrdp 0.10.6.1 | `80c52879fead585d6347df5b3c587718adf8f5a5` | RDPの待受とセッション管理 |
| xorgxrdp 0.10.5 | `c2d3cbafebe00be3221f985c06ef6b97f1c63790` | 既存Xorgへ追加するモジュール |
| Check 0.15.2 | `11970a7e112dfe243a2e68773f014687df2900e8` | ビルド時のテスト基盤だけ．書き出す実行環境へ含めない |

本家の公開情報は[xrdp](https://github.com/neutrinolabs/xrdp/releases/tag/v0.10.6.1)と
[xorgxrdp](https://github.com/neutrinolabs/xorgxrdp/releases/tag/v0.10.5)にある．
完全なGit版とsubmoduleのgitlinkを照合する．取得後にソースアーカイブのSHA256も記録するが，
別途事前承認した配布チェックサムではなく来歴の記録である．APTの版は記録するが完全固定していないため，
ビット単位で再現できるビルドとは主張しない．

両方のconfigureでstrict locationsを使う．Prefixだけでは本家がシステムの`/etc`や
Xorgモジュール先を選ぶ場合があるためである．出力は`/opt/output/opt/b2-remote`と，
明示的に準備するPAMの`/opt/output/etc/pam.d/xrdp-sesman`になる．バイナリ，ライブラリ，
Xorgモジュール，設定・unit雛形，ライセンス表示，ビルド・テスト・リンク情報を含める．
Xorg・GDM・NVIDIAドライバの置換物や，生成した秘密鍵は含めない．ホストのネットワーク，
Wi-Fiの秘密情報，サービス有効化はビルド入力ではない．

本家テストが必要とするCPUのpainter・RemoteFXライブラリを有効にする．任意のGPU画面描画，
xorgxrdpのSIMD，音声，ドライブ転送，smartcard，H264・JPEG codec連携は無効にする．
初期目的は基本的な設定画面の利用である．機能を減らしただけで，互換性・性能や，
実行ライブラリがホストに全てあることは証明しない．

## ビルドと書き出しの手順

準備済みJetsonで，レビューしたソースのルートから使う標準コマンドである．

```sh
sudo env DOCKER_BUILDKIT=0 docker build --pull=false --target bundle \
  --build-arg MAX_JOBS=4 --tag vln-b2-rdp-bundle:jp5 \
  --file deploy/remote-desktop.Dockerfile .
```

`MAX_JOBS=4`はコンパイルの並列数で，モデルの学習とは関係しない．開発パッケージは
ビルド用コンテナだけへ入る．重いGPU用Torchイメージは作り直さず，置換もしない．
xrdpの`make check`を必須とし，不明なconfigureオプションの警告や実行ライブラリ不足も失敗にする．
最後のscratch段階には，シェル，既定コマンド，待受サービスがない．

新しい未使用のローカルディレクトリへ出すには，コンテナを起動せずに作り，成果物だけをコピーする．
以下のコンテナ名と出力先が未使用であることを先に確認する．

```sh
mkdir -p local/rdp-export-01
sudo docker create --name b2-rdp-export-01 vln-b2-rdp-bundle:jp5 /not-started
sudo docker cp b2-rdp-export-01:/opt/output local/rdp-export-01/
```

`/not-started`は意図的に実行しないコマンド名であり，この成果物コンテナを起動しない．
イメージID，レシピのSHA256，ログ，ソース版，単体テスト，ファイル一覧を保管する．
書き出せたことは依存先の再配布許可ではない．各部品の表示を残し，配布相手は別に確認する．

## 記録したビルドの修復

初回はxrdp本体をコンパイルしたが，テストのコンパイルで止まった．FocalのCheck 0.10に，
固定した本家テストが使うassert APIがないことが原因である．修正ではビルド環境にCheck 0.15.2を
作り，そのpkg-configを選ぶ．Assertの削除やテストの省略をせず，本家のテストを維持する．
ビルド依存にはCheckのLGPL条件が引き続き適用されるが，ライブラリ・テスト実行物は
書き出す実行環境に含めない．初回ログと失敗したコンテナは診断用に保持する．
後の成功は明示的に記録する必要があり，修正の説明だけではビルド合格ではない．

## ホスト導入前の確認

既存の導入先へ無条件で展開しない．ホストを変える前に次を確認する．

1. `/opt/b2-remote`，PAMファイル，サービス・unit名，サービス用のユーザー・グループが未使用か確認する．
   既存なら所有者と保全方法を特定する．
2. 成果物のhash，秘密鍵や想定外パスがないことを検証する．表示・来歴を保管し，root管理の配置先を確認する．
   通常ユーザーがバイナリ・認証設定を書き換えられないようにする．
3. 配置後にホストのリンクを確認し，モジュールのXorg ABIを既存サーバーと比べる．
   ビルド時の`ldd`をホストでの成功と扱わない．
4. 別の管理接続を維持する．2026-10-28には通常のLAN OpenSSHを確立してからTailscaleを更新し，
   クライアント・デーモン1.104.4と，一時的なTailscale TCP転送を確認した．
5. 既存のNoMachine，GDM，ローカルセッション，GPU環境を維持する．
   試験を通すためだけに，作業内容を確認せずユーザーをログアウトしない．

導入では専用prefix，未作成なら非ログインのサービス用ユーザー・グループ，
許可した研究者のグループ，確認したPAM項目，専用unitだけを追加する設計にする．
TLS鍵はホストで作り，レポ・イメージへ転送しない．適用した正確な設定，バックアップ，
検証結果は導入記録へ残す．

## 最初の起動前に必要な設定

| 対象 | 必要な動作 |
|---|---|
| 待受 | xrdpのGlobalsで`tcp://127.0.0.1:3389`だけに限定．起動後に実際のsocketも確認 |
| 通信 | ホストで新規に作る証明書・鍵によるTLS．root所有と，サービスに必要な読取権だけ |
| 権限 | 待受は非ログインの専用`xrdp`ユーザー．セッション管理は必要なrootの役割を保持 |
| ログイン方針 | Rootログイン禁止，研究者の許可グループ，通常のPAM認証を維持 |
| 実行socket | `runtime_group`と`SessionSockdirGroup`を対応．後者はこの版のparserに従いsesmanのSecurityへ設定 |
| Xorg | 既存ホストの実行物，prefixの絶対設定パス，prefixと既存システムのmodule pathを明示 |
| 起動・終了 | 専用unit名と対応する依存関係．最初は手動起動し，起動時の自動有効化はしない |
| 転送 | 必要なchannelだけ有効にし，ホーム全体を自動共有しない |

固定版の[xrdp設定](https://raw.githubusercontent.com/neutrinolabs/xrdp/v0.10.6.1/xrdp/xrdp.ini.in)，
[sesman parser](https://raw.githubusercontent.com/neutrinolabs/xrdp/v0.10.6.1/sesman/libsesman/sesman_config.c)，
[権限の説明](https://github.com/neutrinolabs/xrdp/wiki/Running-the-xrdp-process-as-non-root)を使う．
一部のヘルパーは`xrdp`というグループ名を期待するため，任意の名称変更が使えると仮定しない．
`xrdp-chkpriv`，パス，ログ，実際の権限を調べる．失敗回避のためにpolkit全体を緩めたり，
描画ドライバを置き換えたりしない．

## 合格条件と復旧

最初にリンク，unit構文，制限したsocket，TLS識別，セッション管理の健全性を示す．
その後，確認したSSHトンネルからMacのWindows Appを試す．同じ研究ユーザーのコンソールGUIは
RDPと競合する場合があり，待受が動いても画面へのログイン完了ではない．
遠隔画面ガイドに従い，ログイン，設定権限，キーボード，再接続，HDMIなしの起動を確認する．
既存SSH，ローカルGUI，CUDAも別に確認する．ロボットの移動はこれらの試験に含めない．

新しいサービスが失敗したら，専用unitだけを止め，ログを保全する．後から有効化した場合は無効化する．
既存サービス・データを残し，今回導入した設定変更だけを戻す．Prefixと追加unit・PAMを
manifestとともに退避できる構成とし，ユーザー・グループを除去する前に所属を確認する．
Dockerの広範なprune，デスクトップ再導入，認証情報の削除を復旧方法にしない．

## 2026-10-28の導入・確認記録

修正した成果物のビルドが通った．イメージは
`sha256:15f5a046721dd9d3e2cca7fb71c411203a6ac1b9eab71a0e94ddc52d7d62e993`，
論理サイズは**19,594,974 bytes**，レシピのSHA256は
`e19bf5e283c46c5661e662b313ef52fb6b1bc177bbdb3b92d1fd2a0fbda8a787`である．
本家が報告する**213ケースが全て通り**，skip・fail・errorは0だった．
Checkの古いassert API，続いて本家のテストMakefileが要求するpainter・RemoteFXを無効にした構成，
という二つの失敗を保持した．最終レシピは両方のソフトウェア用ライブラリを有効にし，GPU描画・H264は
無効に保つ．CUDA依存は追加しない．Assertやテストは削除していない．

書き出した162件のmanifestを導入前に検証した．ホストには`/opt/b2-remote`，非ログインの
`xrdp:xrdp`，研究用ログインを含む許可グループ`b2-remote-users`，本家のDebian PAM，
専用unitの`/etc/systemd/system/b2-rdp.service`と`b2-rdp-sesman.service`を追加した．
既定設定はprefix内の`xrdp.ini.before-b2-setup`・`sesman.ini.before-b2-setup`へ保管した．
システムのXorg，GDM，NoMachine，Wi-Fiプロファイル，GPUイメージは維持した．

前述の設定表に加えて，次の値を適用した．

| ファイル・節 | 適用した値 |
|---|---|
| xrdp.ini Globals | `allow_channels=false`，TLS 1.2・1.3，prefixの証明書・鍵を明示 |
| sesman.ini Globals | `EnableUserWindowManager=false`，prefixの`startwm.sh`を絶対指定 |
| sesman.ini Security | `MaxLoginRetry=3`，`TerminalServerUsers=b2-remote-users`，`TerminalServerAdmins=xrdp`，`AlwaysGroupCheck=true`，両方向のclipboard制限`all` |
| sesman.ini Sessions | `MaxSessions=2` |
| Xorgの引数 | `/usr/lib/xorg/Xorg`，module path `/opt/b2-remote/lib/xorg/modules,/usr/lib/xorg/modules`，prefixの絶対config，`-noreset -nolisten tcp`，displayごとのローカルログ |
| ログ | `/opt/b2-remote/var/log/xrdp.log`はサービスが書込み可能．`xrdp-sesman.log`はroot所有 |
| Unit | 対応する専用依存名にした本家のType=exec雛形．sesmanが実行ディレクトリ`b2-remote`を0755で管理 |
| 鍵 | ホストで生成したTLS証明書・鍵とRSA鍵ファイル．root:xrdpの0640．秘密鍵はMac・Gitへコピーしない |

ホストで13実行物のリンク，unit検証，`xrdp-chkpriv`が通った．Unit検証は既存の無関係なunitの
警告も出したが，その設定は変更していない．両RDP unitを最初は手動起動し，操作者の基本操作の確認後に`b2-rdp.service`を起動時に有効化した．
sesmanは単独で有効化せず，必要な依存先として起動する．再起動せず，有効化・動作状態・loopback待受を確認した．
実際の待受は**127.0.0.1:3389だけ**で，受信プロセスはxrdp:xrdp，sesmanはrootで動いた．
一時的なSSHトンネルでRDPがTLSを選び，別に取得した公開証明書を信頼するクライアントで
TLS 1.3の`TLS_AES_256_GCM_SHA384`を検証した．その試験トンネルは終了した．

隔離した認証付きXorg画面は1024×768の`xdpyinfo`照会に応答し，試験後に終了した．
操作者の回答を受け，GNOMEの終了保留がない状態で通常のログアウトを行い，Windows Appの認証と
GNOMEデスクトップの表示が通った．資格情報は保存していない．導入後にモデル不要のFP32・BF16の
8演算も再確認した．機体への接続・指令は行っていない．

基本的な画面操作は操作者が確認した．設定権限，詳しい入力検査，切断・再接続，
電源投入からの起動には合格の証拠が必要である．
既存のChromeのクラッシュ通知が見えたが，報告は送信せず，原因は確定していない．
背景が表示できただけでGUI・起動全体の合格とは主張しない．生のビルド・導入・試験記録は
JetsonのGit対象外`local/remote-desktop-build`，`local/rdp-export-01`，`local/access-setup`にある．
個体の情報を含むため，公開ソースにはしない．

その後，HDMIなしで制御したソフトウェア再起動を行い，接続中の非EnterpriseのWi-Fi，
Tailscale，SSH，両RDPサービス，Dockerが復帰した．SSDのマウントとDockerのSSD保存先を確認した．
復旧したMacの専用バックグラウンドトンネル経由で，操作者がRDPの表示と入力を確認した．
物理的な電源の入れ直しや，eduroamの起動試験ではない．
