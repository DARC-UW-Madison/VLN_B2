# Macからのリモートデスクトップ

[English](remote-desktop.md) · [文書一覧](../README.ja.md) · [システム全体像](../reference/system-overview.ja.md) · [現地手順](field-network.ja.md)

> 文書種別：**操作手順**．

**2026-11-03の現在方針**：Windows Appから，JetsonのTailscale IPv4・TCP 3389へ直接接続する．
以前のMac用tunnel・profileは除去済みである．Macのtunnel，自動起動，経路変更，新しいclientは不要で，
Windows Appの接続先は操作者が登録する．既存Tailscaleを管理用の非公開networkとして使う．
モデル推論・将来の実機制御は，画面接続とは独立してJetson上で動く．

## Windows Appから直接つなぐ

1. Mac・Jetsonで既存のTailscale接続を有効にする．
2. Windows Appの**Add PC**で，下表を入力する．
3. 保存したPCを開き，求められたらJetsonのLinuxアカウントのパスワードを入力する．
   xrdpのsession選択が出たら**Xorg**を選ぶ．大学・Microsoftの認証をLinuxログインへ使わない．
4. 証明書の確認が出たら，信頼したJetsonの証明書と照合する．証明書確認を全体で無効にしない．
   証明書自体は維持していても，新しい接続先の初回は確認が出ることがある．

| 設定 | 値 |
|---|---|
| PC name | `JETSON_TAILSCALE_IP:3389`．操作者へ非公開で伝えた実IPを使う |
| User account | 研究用Linux login，または必要時に入力 |
| Password | そのLinuxアカウントのパスワード．チャット・Gitへ記録しない |
| Gateway | No gateway |
| Friendly name | `B2 Jetson`など任意の説明名 |

古い`127.0.0.1:13389`の接続やtunnel開始は使わない．SSHと同じ研究用アカウントである．
client画面は[MicrosoftのWindows App手順](https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps)も参照する．
指定するのは，変化する大学Wi-FiのleaseではなくnodeのTailscale IPである．
[Tailscaleのアドレス割当](https://tailscale.com/docs/concepts/ip-and-dns-addresses)を参照する．
RDP自体が大学portalへログインするわけではない．

## MacとJetsonの間で文字をコピー・貼り付けする

この結果・経緯は[記録](../records/desktop-history.ja.md)を参照する．

## Jetsonに導入したVS Code

この結果・経緯は[記録](../records/desktop-history.ja.md)を参照する．

## 適用した直接接続の設定

この結果・経緯は[記録](../records/desktop-history.ja.md)を参照する．

## 現在わかっていること

この結果・経緯は[記録](../records/desktop-history.ja.md)を参照する．

## クライアント，サーバー，プロトコル，セッション

[接続方式の解説](../explanations/remote-access.ja.md)を参照する．

## NoMachine，RDP，VNC

[接続方式の解説](../explanations/remote-access.ja.md)を参照する．

## 廃止したローカル待受RDP設定

この結果・経緯は[記録](../records/desktop-history.ja.md)を参照する．

## セッションと描画の制約

[接続方式の解説](../explanations/remote-access.ja.md)を参照する．

## インストール計画の前の読み取り調査

SSHまたは実機の端末が使えるようになったら，Jetsonで次を実行する．導入候補を調べ，
依存先の変更をシミュレーションし，現在のサービスを表示する．パッケージの導入，Wi-Fiの変更，
画面の管理サービスの再起動は行わない．

```sh
apt-cache policy xrdp xorgxrdp xserver-xorg-core
apt-get -s install xrdp xorgxrdp
systemctl is-active gdm3 xrdp xrdp-sesman
loginctl list-sessions
ss -ltn
```

`apt-cache policy`は，ホストに保存されたパッケージ情報から，導入版と候補版を表示する．
`apt-get -s`は導入をシミュレーションするので，導入・更新・削除の提案を全て確認する．
情報が古い場合があり，これはパッケージの安全性調査や，全て取得可能という確認ではない．
パッケージがなければ，`systemctl`は`inactive`・`failed`やサービス不明を返す場合がある．
表示の意味を解釈し，存在しないことをRDP検査の成功として扱わない．
セッションと待受の表示には個別の識別情報が含まれる場合があるため，Gitへ保存しない．

調査後の導入計画には，実際のARM64パッケージの版，依存先，サービス開始時の動作，
バックアップ先，戻し方を記す．導入する版の`man xrdp.ini`と`man sesman.ini`を確認する．
現在の上流文書には，Ubuntu 20.04のパッケージにはない設定が記載されている場合がある．
Ubuntuの[Focal向けxrdp.iniマニュアル](https://manpages.ubuntu.com/manpages/focal/man5/xrdp.ini.5.html)
も参考資料であり，実機で今選ばれる候補版の証拠ではない．

管理用サーバーは，推論コンテナの外にある**ホスト**へ導入する．Wi-Fiの設定はホストの
NetworkManagerが担当する．このためにモデル用コンテナへデスクトップ，セッションのバス，
ネットワーク管理権限を渡す必要はない．パッケージの導入時にサービスが自動起動する場合がある．
最初からアクセスを制限して開始できる段取りを用意し，実際の待受を検証する．
ループバックにしたつもりで，全インターフェースの既定の待受を公開しない．
この計画が確定するまでは，導入コマンドをここで指定しない．

## 過去のSSHトンネル構成

この結果・経緯は[記録](../records/desktop-history.ja.md)を参照する．

## 導入したサーバーの使い方

サービスは起動時に有効化済みである．Jetsonで現在の状態を調べ，必要なら手動で起動するには次を使う．

```sh
sudo systemctl start b2-rdp.service
systemctl is-active b2-rdp.service b2-rdp-sesman.service
```

基本操作の確認後，`systemctl enable`で`b2-rdp.service`を起動時に有効化した．
必要な`b2-rdp-sesman.service`は依存関係から起動し，単独の起動時有効化は行わない．
初めは再起動せずに有効化と動作状態を確認した．その後，HDMIなしでソフトウェアから再起動し，
人の操作なしでWi-Fi，Tailscale，SSHが復帰した．対象機の稼働時間が約25秒の時点でSSHが戻った．
NetworkManager，tailscaled，SSH，両RDPサービス，Dockerの動作，SSDのマウント，
DockerのSSD保存先，RDPのloopback限定待受も確認した．接続中のWi-Fiは全ユーザー向けの
非Enterprise設定であり，eduroamではなかった．この接続でのソフトウェア再起動後の復帰を
確認した結果であり，eduroamのログイン前接続や物理的な電源の入れ直しを実証したものではない．
再起動後のGUIの表示と入力は，その後に操作者が確認した．GUI自動ログインは不要で，ロボットの移動を開始させない．
MacでSSHトンネルを作り，保存した`B2 Jetson (SSH tunnel)`を開く．自己署名証明書は期待する
サーバーの識別を確認し，変更を無視したり恒久的な検証回避を保存したりしない．
独立したTLS試験では，実際の公開証明書を信頼の基準として検証した．

## RDPからのeduroam設定

遠隔で設定画面を開けることと，システムの接続設定を変更できることは異なる．
GUIの権限確認には**polkit**を使い，遠隔セッションを実機のコンソールと違う条件で扱う場合がある．
既存の接続の権限，認証情報の保存先，利用できるパスワードエージェントも関係する．
したがってRDPで画面が出ただけでは，既存のeduroam設定を編集できる証明にはならない．

必要なNetworkManagerの設定操作そのものを試す．GUIの経路が拒否される，または曖昧な場合は，
大学のCA・サーバー設定と現在のプロファイルを確認した上で，準備済みの端末用ヘルパーを
明示的なsudo権限で使う．既定の動作は読み取りのみである．

```sh
/usr/bin/python3 tools/configure_unattended_wifi.py
```

Jetsonのプロジェクトルートで，ホストのシステムPythonと既存のシステムD-Bus bindingを使う．
認証情報を保存する操作は意図的に別になっている．[起動時の通信と認証情報](../reference/system-overview.ja.md)を参照する．
設定画面を使うためだけに，遠隔の全てのpolkit操作を許可しない．

Wi-Fiの認証情報をシステムへ保存すると，NetworkManagerはGUIログイン前にも接続できる．
そのためにデスクトップへの自動ログインやRDPは必要ない．認証情報は所有者が対話式の端末，
または信頼できる設定画面へ入力し，秘密の値は記録しない．所有者はGUIの権限拒否後，
端末から保存を完了した．polkitの許可範囲は広げていない．
プロファイルを書き込むことと，再接続を試験することも別である．RDP・SSHに使っているWi-Fiを
再接続すると両方とも切れる場合があるため，先に復旧手段を用意する．

### 非アクティブなeduroam設定をGUIで保存する

現在のWi-Fiと，保存済みのeduroam設定が異なる場合がある．端末のヘルパーは既定では有効な設定を
選ぶが，`--connection-id`で保存済み設定を明示的に一つ選べる．編集のために接続を切り替える必要はない．Jetsonの画面内の端末で実行する．

```sh
nm-connection-editor
```

既存のeduroam接続を選んで編集する．**General**で自動接続と
**All users may connect to this network**を有効にする．**Wi-Fi Security**で所有者の
パスワードを入力し，保存方法のメニューから**Store the password for all users**を選ぶ．
大学の設定による認証ID，認証方式，CA，サーバー照合は維持する．保存時に権限確認が出たら，
許可されたLinux管理アカウントで認証する．その端末の管理パスワードと大学のWi-Fiパスワードは
用途が異なる．まだ新しい接続は有効にせず，パスワードを報告へ出力したり，保存のために証明書の
検証を外したりしない．遠隔セッションに権限がなければ止め，polkitの許可を広げる代わりに，
明示的に認められた端末操作を使う．

保存後は，全ユーザー向けか，自動接続が有効か，secret flagsが0か，空でないパスワードが
存在するかだけを調べ，値は表示しない．RDPとSSHはこの回線を使うため，Wi-Fi切り替え前に
NetworkManagerの時間制限付き復元を用意し，既知の接続へ戻せるようにする．
eduroamで新規SSH接続とインターネット・Tailscaleを確認してから，復元予約を解除する．
Macのトンネルを戻してRDPも再試験する．eduroamの再起動試験は，確認済みの非Enterpriseの
Wi-Fiとは別に行う．設定の保存だけでは，どちらの結果も実証しない．

### polkitがGUI編集を拒否した場合の端末手順

操作者はRDPの表示と操作を確認できたが，編集画面の保存時にpolkitの権限がないという
エラーが出た．権限の境界があることを示す結果であり，Wi-Fiパスワードの誤りの診断ではない．
polkitの包括的な例外は追加していない．所有者自身のJetsonへのSSH端末で，明示的なsudo権限と
保存済み設定の名前を使い，確認済みのヘルパーを実行する．

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
sudo /usr/bin/python3 tools/configure_unattended_wifi.py --connection-id SAVED_PROFILE_NAME --apply
```

プレースホルダーを手元で置き換える．名前の不一致・重複と未対応の認証方式は，大学パスワードを
求める前に拒否する．非表示の入力欄へ大学パスワードを2回入力し，コマンド引数やチャットへ書かない．
CA，alternative-subject・domainの照合，認証ID，EAP，IP設定などは維持し，全ユーザー向けの
接続を有効にしてsecret flagsを0にする．rootで保護した`/etc/NetworkManager/vln-b2-backups`へ
プロファイル別にバックアップし，最初のコピーを維持する．以前の有効な設定のバックアップがあれば，
それも残す．秘密の値を表示せず保存を照合する．Wi-Fiの有効化やサービスの再起動は行わず，
別のオプションを明示しない限りGUI自動ログインも変更しない．保存と，制御した接続切り替えの試験は別の段階である．

### 完了したeduroamの受入確認

2026-10-28に所有者自身の対話型SSH端末で保存が成功した．管理権限で，全ユーザー向けの自動接続，
password flags 0，空でない秘密の保存，CA・サーバー照合の維持を確認し，値は出力していない．
180秒のNetworkManagerのcheckpointで切り替えを保護し，新規のTailscale SSH，正常な接続，
管理サービスの動作を確認してから予約を解除した．続くソフトウェア再起動もHDMIなしで行い，
自動でeduroamへ戻った．対象機の稼働時間が約24秒の時点で新規SSHが動いた．boot IDの比較，
サービスの起動時有効化と動作，SSDのマウント，DockerのSSD保存先，RDPのloopback限定待受が通った．
Macのトンネルを再開し，操作者がWindows Appでの表示と操作を再確認した．GUI自動ログインは変更していない．
物理的な電源の入れ直しと，詳しい画面操作の確認は未実施である．個体の記録とバックアップはホストのGit対象外に残す．

## 過去のVinoの調査

この結果・経緯は[記録](../records/desktop-history.ja.md)を参照する．

## 合格条件と復旧試験

| 確認 | 必要な証拠 |
| --- | --- |
| 通信とログイン | 制限された待受，期待するサーバーの識別情報，認証付きトンネル，Windows AppからのLinuxログイン成功 |
| 設定作業 | 端末とNetworkManagerの設定画面が開き，必要なシステム操作がpolkitの一括変更なしで許可される |
| 入力と使いやすさ | キーボード配列，必要な場合の日本語入力，マウス，解像度，再接続が正しく動く |
| セッションの所有者 | 意図した遠隔セッションを特定し，同じアカウントの実機GUIと競合せず，他のアカウントのセッションを維持する |
| ロック・ログアウト・再接続 | ロックや接続の切断をログアウトと区別し，選んだ方針に従って再ログインできる |
| 画面なしの起動 | 復旧手段がある状態で，HDMIなしのコールドブート後にWi-Fi・SSHが動き，実機GUIへログインせず遠隔ログインできる |
| 既存ソフトウェア | 設定後も実機の画面，通常のSSH，既存のモデル不要CUDA検査が動く |
| インターネットなし | 別途検証したJetsonのホットスポット上で，Tailscaleの調整や大学Wi-Fiを使わず，通常のローカルOpenSSHと同じトンネルで接続できる |
| 復旧 | Wi-Fiの再接続や遠隔サーバーが失敗しても，実機・別経路での復旧手順を確認している |

ホットスポットと，そのLANでの通常のOpenSSH接続は未設定・未検証である．
TailscaleアドレスのTailscale SSHと，ローカルLANアドレスのOpenSSHは別のアクセス経路である．
オフラインへ移る前に，後者の認証とホスト鍵を確認する．外部APの存在は前提にしない．

これらを確認すれば，通常のHDMI利用をRDPで減らせる．ただし完全に届かなくなったWi-Fiを，
その切れた回線を通して復旧することはできない．最初の起動・通信試験では実機での復旧手段を残す．
実機の実験には，独立したローカルプロセスの継続方法，停止方針，操作者の物理的な介入手段が必要である．
Windows Appを閉じたことが，暗黙に機体の動作を決める構成にしない．
