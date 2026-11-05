# リモートデスクトップの設定・検査記録

[English](desktop-history.md) · [記録目次](README.ja.md)

> 文書種別：**記録**．実行した設定・検査の証拠を保存する．現在の操作手順とは区別する．

## MacとJetsonの間で文字をコピー・貼り付けする

2026-11-03，以前のserver設定に`allow_channels=false`と両方向のclipboard制限`all`があり，
文字転送を禁止していたと確認した．解除だけでは一連の転送成功を確認できなかった．
現在は文字を双方向に許可した．`xrdp.ini`は`allow_channels=true`とし，channelは
`cliprdr`だけを有効化し，他は無効のままにした．`sesman.ini`では
`RestrictInboundClipboard=file,image`と`RestrictOutboundClipboard=file,image`で
file・画像を禁止し，文字を許可する．対象版の[clipboard設定](https://raw.githubusercontent.com/neutrinolabs/xrdp/v0.10.6.1/sesman/sesman.ini.in)を
確認してから適用した．

反映と確認は次の順序で行う．

1. Jetson画面の作業を保存し，**GUI sessionからログアウト**する．切断だけではchannel serverと旧制限が残る場合がある．SSHは維持できる．
2. Windows AppでこのPCを編集し，**Devices & Audio**のClipboardを有効，または**Bidirectional**にして保存する．操作者用の手順であり，エージェントはMacの設定・profileを変更していない．[Microsoftの転送手順](https://learn.microsoft.com/en-us/windows-app/device-audio-folder-redirection-teams)も参照する．
3. 再接続して新しいJetson RDP sessionへログインする．秘密でない試験用文字列をMacからJetsonのeditorへ貼り付け，逆方向も試す．
4. JetsonではLinuxのキーを使う．通常editorはCtrl+C／Ctrl+V，端末は通常**Ctrl+Shift+C／Ctrl+Shift+V**である．MacはCommand+C／Command+Vを使う．

session managerだけをreloadし，listener再起動やGUI終了はしていない．設定とservice稼働は確認済みだが，
操作者はBidirectional選択・client再起動後も転送できないと報告した．GUI全体のログアウト・新session試験は
未確認である．B2 network調査中は切り分けを保留し，JetsonのVS CodeでMarkdownのガイドを開く方法を使える．
現在のclipboard内容は読んでいない．
元iniは非公開`local/editor-setup-01/rdp-config-before`へ保存した．復元には管理者権限と新sessionが必要である．
TLS，Tailscale専用待受，firewall，login規則は変えていない．


## Jetsonに導入したVS Code

2026-11-03にMicrosoft公式の**ARM64 Debian版VS Code 1.144.1**を導入した．
公式update metadataのSHA256と取得物が一致した．APT模擬実行と前後一覧で，新規`code` 1個だけ，
他packageの更新・削除なしを確認した．`code --version`は想定版・commit・ARM64で，`dpkg --audit`も正常である．
既存RDP GUIでアプリを起動し，日本語cameraデモ操作書を開いたwindowも確認した．この起動にGUIログアウトは不要だった．
CUDA，JetPack，Python，モデルcontainerは変更していない．GUI用のhost editorであって，
モデル環境の置換ではない．その端末からも従来どおりデモのコマンドを使う．

**Jetsonデスクトップ内**の端末でプロジェクトを開く．

```bash
cd ~/Developer/Projects/Robotics/b2/VLN_B2
code .
```

仮想RDP画面でElectron／GPU描画に問題が出る場合は，その起動だけGPU描画を無効にする．

```bash
code --disable-gpu .
```

通常の回避策として`--no-sandbox`を加えない．packageのsandboxは有効のままである．
installerにはMicrosoft APT sourceを追加しないと明示し，Microsoft repository／key sourceは増えていない．
今後のeditor更新は確認した公式packageをAPTで導入できる．拡張，account login，Settings Syncは設定していない．
MacへのVS Code導入も不要である．[MicrosoftのLinux導入手順](https://code.visualstudio.com/docs/setup/linux)と
[バイナリの利用条件](https://code.visualstudio.com/license)が適用され，このレポのMITでアプリ自体を再許諾しない．
package，導入，window検査の証拠はGit対象外の`local/editor-setup-01`に残す．


## 適用した直接接続の設定

既存ホストxrdpは，loopback・wildcardではなく**設定したTailscale IPv4だけ**で待ち受ける．
TLS設定，証明書・鍵，PAM，許可group，Linux認証は維持した．IPv4 INPUTへ一つのlabel付きruleを加え，
その正確な宛先・TCP 3389へ`tailscale0`以外から来た通信をdropする．既存ruleのflush，既定firewall方針，
SSH，NoMachine，Wi-Fiは変更しない．Tailscale側のアクセス規則も引き続き適用される．

確認した[起動準備helper](../../deploy/rdp-tailnet-ready.py)と[systemd drop-in](../../deploy/rdp-tailnet.conf)は，
**Jetsonだけ**で動く．実際の登録IPv4は非公開の`/opt/b2-remote/etc/xrdp/tailnet-address`へ置く．
helperは`tailscale ip -4`との一致と`tailscale0`上のUP状態を確認してから，対象を絞ったruleの存在を
確認・必要時だけ追加し，xrdpを開始する．不一致・interface未準備は起動を失敗させ，全interfaceへ代替しない．
serviceはtailscaledの後で開始し，失敗は5秒ごとに，開始回数の上限なしで再試行する．起動時の有効化は維持した．
登録・アドレスを変更する場合は，非公開ファイル，xrdpのbind，古い専用ruleを一緒に確認する．

元の設定は非公開の`local/direct-rdp/attempt-01`へ保存した．serviceを二回再起動してlistener・session managerの
動作と，専用firewall ruleが一つだけであることを確認した．アドレス準備を意図的に失敗させると起動は拒否され，
設定を戻すと自動再試行で復帰した．Wi-Fi・SSHの再起動やTailscale登録の変更はしていない．
Macから直接TCP・RDP交渉を行い，TLS 1.3と，
SSHで確認したJetson証明書とのSHA256一致を確認した．この通信検査ではパスワードを送っていない．
**操作者は2026-11-03に新経路でのデスクトップ表示を確認した．変更後の機器全体の再起動検証は別である**．同じbackendでは以前の経路で
画面・入力を確認済みである．Mac・Jetsonの通常テスト164件も成功したが，模擬guard検査だけで実通信を証明しない．

2026-11-03に，想定内の起動失敗を未処理例外・GUIのクラッシュ報告にしないようhelperを修正した．
前回の意図的な試験報告は退避し，systemdの再試行は維持する．
[調査の証拠と限界](../reference/system-overview.ja.md#接続断とデスクトップ不調の切り分け)を参照する．

Jetsonで問題を調べる場合は，`systemctl status b2-rdp.service`，journal，`tailscale ip -4`，
bind設定，`ss -ltnp`を確認する．アドレス・許可の不具合を避けるために大学・機体interfaceへ3389を開かない．
戻す場合はRDPを止め，保存した元iniへ戻し，このdrop-inと正確なlabel付きruleだけを除き，
systemdを再読込して元のloopback serverを始める．Macのtunnelを作る操作ではない．無関係なruleやTailscale登録を除去しない．

以下は以前の調査と，置き換えたSSH経路の仕組みを説明する過去の記録である．現在の接続手順ではない．
この対象機には上の直接接続を使う．


## 現在わかっていること

**2026-10-27**の読み取り調査では，Ubuntu 20.04・L4T 35.4.1でVino 3.22が導入済みだった．
`vino-server`のプロセスとTCP 5900・3389の待受はなかった．xrdp・xorgxrdp・
gnome-remote-desktopは未導入である．GUI起動と，別アカウントへの既存のGUI自動ログインは
維持した．新たな遠隔画面のサービス，認証設定，GUIログイン先は有効にしていない．
これは過去の確認結果であり，現在のサービスを再確認した結果ではない．

**2026-10-28**の管理用SSHへの接続試行はタイムアウトした．原因は確定しておらず，
タイムアウトだけではWi-Fi・認証・電源・ホストのどれが原因かを特定できない．
以下の構成は対象機へ接続できない状態で準備した．MacへRDPクライアントを入れるだけで
ホストへの接続が復旧するとは考えない．

その後の**2026-10-28**の調査は，操作者がTailscaleを復旧し，SSHの本人確認を完了して成功した．
信頼済み接続から得たホスト鍵で，通常のLAN OpenSSHも確認した．この別経路を維持してTailscaleだけを
**1.104.4**へ更新し，クライアントと動作中のデーモンの版を確認した．新しいTailscale SSHと，
ホストOpenSSHへ向けた一時的なloopback TCP転送も成功し，試験用トンネルは終了した．
これは端末・転送の検証で，RDPの画面が使えることの検証ではない．

既存の**NoMachine 8.20.1-5**も見つかった．有効で，IPv4・IPv6の各インターフェースのTCP 4000で
待ち受けている．今回導入・再設定・無効化していない．xrdpとは別の遠隔画面プロトコルで，
Windows Appへの対応を示すものではない．Macクライアント・セッションは未検証である．
操作者の回答を受け，研究用のコンソールGUIを通常の手順でログアウトした．GNOMEの終了保留はなく，
その後のRDP認証とデスクトップ表示が通った．GDMの自動ログイン先は変更していない．

ローカルのパッケージ情報にはxrdp `0.9.12-1ubuntu0.1`，xorgxrdp `1:0.2.12-1`，
追加依存ssl-cert `1.0.39`があり，模擬導入は更新・削除なしの三つの追加だった．
ただし，xrdp候補には[Ubuntu USN-8476-1](https://ubuntu.com/security/notices/USN-8476-1)が示すESM修正版がない．
この古い候補を準備済みの解決策として導入しない．Ubuntu ProやESM配布元は有効化していない．
ホストの描画環境を置換せず，別に版を固定したソースビルド候補を評価できる．
ビルド・導入の証拠は別に記録する．

[ソースビルドのガイド](rdp-build.ja.md)に，分離した成果物と必要なホスト設定を説明する．
既定設定のまま無条件に導入・起動しない．


## 以前トンネルを使った理由

操作者はMacのシステム・network設定の変更を避けたいと希望している．本プロジェクトのために
macOSの経路変更，SSHサーバーの有効化，常駐する転送サービスの導入を行わない．既存のトンネルは
ローカルの一つのポートを転送するSSH clientのプロセスであり，Macのnetworkを再設定する要件ではない．

NoMachineのNX直接接続で想定する経路は次のとおりである．

```text
Mac NoMachine client -> Tailscale private network -> Jetson NoMachine server :4000
```

Mac側はclientアプリを用意し，Jetsonの到達可能なTailscale IP，NX方式，4000番，JetsonのLinuxアカウントを
接続情報として登録する．この経路に別のSSHトンネルは含まれない．4000番は既定値であり，このホストでの
到達性・アクセスの検証済みという意味ではない．Jetson側の待受，tailnetの許可，画面なしでの表示を
確認してから利用する．Macのシステム変更を意味しない．既存のTailscaleをプライベートな通信路として使う．
製品の[直接接続の手順](https://www.nomachine.com/support/documents/getting-started-with-nomachine)を参照する．
IPでの直接接続と，製品独自の別サービスNoMachine Networkは区別する．

RDP自体にSSHは不要である．WindowsのRDPホストでは，ネットワークのインターフェースで接続を受け，
firewallとポリシーでアクセスを制御する構成が一般的である．到達できるIPとアカウントをクライアントへ
指定すれば接続でき，xrdpでも同じ構成は可能である．
[Tailscaleの直接RDPの案内](https://tailscale.com/docs/solutions/access-remote-desktops-using-windows-rdp)も
RDPホストのtailnetアドレスへ接続する方式を示す．Windows向けの案内であり，Linux側の設定の検証ではない．

以前は導入したxrdpの待受を意図的にloopbackへ限定したため，その設定でSSH転送が必要だった．
LinuxやRDPの必須条件ではなく，維持する接続が一つ増える．tailnet限定のRDP待受と，対応する
起動順序，TLS，認証，アクセス規則を整えれば，転送を省ける．ホストの待受・ポリシーの変更が必要で，
Windows Appの接続先を書き換えるだけでは成立しない．その直接待受への変更は，上の2026-11-01の手順で適用した．
Tailscale自体が暗号化したプライベートネットワークを提供し，RDPで使うためにSSH転送を必ず重ねるわけではない．

既存のNoMachineを先に試せば構築作業を減らせた可能性がある．このホストでNoMachineとxrdpを
比較していないため，ソースから構築したことはRDPが必須だった，速かったという証拠ではない．
現在のxrdp成果物はCPUでの描画とRemoteFXを有効にし，H.264符号化は無効である．画面操作は通ったが，
動画の転送量，遅延，CPU負荷は測定していない．NoMachineにも
[圧縮・動画の符号化方式](https://kb.nomachine.com/DT07X00332)があり，実際の利用可否は版，セッション，
ハードウェアによる．画面の更新を送ることだけで，各方式の負荷が同じとは判断できない．
操作者の希望により，現在の候補からVNCを除外する．導入済みのNoMachineと動作確認済みのRDP設定は維持する．


## 過去のSSHトンネル構成

以下は以前の構成の記録で，現在の接続には実行しない．当時はJetsonのxrdpをloopbackだけで待ち受け，認証付きSSHで接続した．
大学LANや機体のネットワークへTCP 3389を公開せずに済む．選んだ版の待受設定の書式，
サーバーの認証，TLS証明書へのアクセス，実際のソケットのアドレスを確認する．
最初の接続を成功させるために認証・TLSの確認・ファイアウォールを無効にしない．
クリップボード・フォルダー・デバイスの転送は，用途に必要なものだけを有効にする．

Tailscale SSHで転送を試す前に，
[Tailscaleの公式セキュリティ告知](https://tailscale.com/security-bulletins)を確認する．
調査したクライアント・デーモンは1.104.2で，2026-10-26のSSHの告知TS-2026-014・015の
修正版は1.104.4以上である．現在動作する版とポリシーを確認し，実機や別経路での復旧を確保してから，
適切なサポート中の版へ更新し，転送を使う．唯一の遠隔経路を再起動したり，接続を戻すために
再認証の方針を弱めたりしない．前述の管理された更新・転送の確認は2026-10-28に完了した．

xrdpを設定し，Jetsonのループバック3389番だけで待ち受けることを検証してから，
**Macで**以下の例を使う．実際の値は手元で指定する．

```sh
ssh -N -L 127.0.0.1:13389:127.0.0.1:3389 RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
```

`-N`は遠隔のシェルを開かない指定である．`-L`はMacのループバック13389番で待ち受け，
SSHを通してJetsonのループバック3389番へ通信を転送する．同じように見える二つの
ループバックアドレスは，別々のコンピューターを指す．13389番は，ローカルにRDPサーバーが
あっても競合しにくいように選んだ，例のローカルポートである．RDP利用中はトンネルを維持する．
閉じると，この通信経路はなくなる．

Windows Appの**Add PC**で，**PC name**を`127.0.0.1:13389`にする．
遠隔ログインを求められたら，研究用のLinuxアカウントを使う．このSSHトンネルの例では，
RDP gatewayは不要である．別に信頼を確認したホストを通して，期待するサーバー証明書を確認し，
識別情報の変更を無条件に受け入れない．パスワードをコマンド引数，リポジトリ，共有する画面へ
書き込まない．このJetsonでトンネル，Linux認証，GNOMEデスクトップの表示を確認した．Macに
`B2 Jetson (SSH tunnel)`という接続先を作り，資格情報は必要時に入力する設定で，パスワードは保存していない．
フォルダ，クリップボード，プリンター，smartcard，マイク，カメラ，音声の転送は無効である．
既存のChromeのクラッシュ通知が見えたが，報告は送信していない．基本的な画面操作は操作者が確認した．設定権限，詳しい入力検査には別の証拠が必要である．その後，HDMIなしのソフトウェア再起動後の再接続を操作者が確認した．


### トンネルを端末から独立させる

通常のSSHシェルと，画面用の転送接続は別の接続である．Macのローカル13389番に
待受がなければ，SSHが動いていてもWindows Appはつながらない．初回の画面試験後に
起きた接続不良はこの状態であり，JetsonのRDPサービスは動作していた．サーバーを
導入しただけでは，MacとJetsonの間に恒久的な接続はできない．

以下の専用helperは過去の経路の説明のために残す．現在の直接RDPでは開始せず，Macの背景処理を再作成しない．

```sh
python3 tools/desktop_tunnel.py start RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
python3 tools/desktop_tunnel.py status RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
python3 tools/desktop_tunnel.py stop RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
```

保存したWindows Appの接続先を開く前に`start`を実行する．`status`と`stop`は，
別の確認・終了操作であり，開始直後に順番に実行する手順ではない．各操作で接続先の
表記とポート指定をそろえる．所有者専用の制御ソケットと専用のOpenSSH masterを使い，
`-fNT`でバックグラウンド起動する．Macのloopbackだけで待ち受け，通常のSSHのホスト鍵・
本人確認を維持し，パスワードは保存しない．使用中のポートや無関係な接続は終了しない．
masterが存在しないとき，`status`は認証を開始しない．確認対象はSSH masterであり，
RDPログイン，画面の動作，その接続が現在検知できる範囲を超えた到達性は検証しない．

起動に使った端末やチャットを閉じても，このmasterは動き続ける．自動再接続サービスや
Mac起動時のエージェントではないため，どちらかの再起動や長い通信断の後は`start`を再実行する．
一致するmasterが生きていれば維持し，終了していれば作り直す．応答の止まったmasterが
残っている場合は`stop`の後に`start`を使う．通常のSSHシェルを開くだけでは，RDP転送は復元されない．


## 過去のVinoの調査

Vinoは以前から導入済みで，停止していた．初期の計画では既存のコンソール画面を共有する方法として
検討したが，操作者の希望により現在の計画からVNCを除外する．Vinoの設定・転送コマンドは示さない．
成功したHDMIなしの試験はxrdpの結果であり，Vinoの結果ではない．構成調査は過去の証拠として残し，
VNCを現在の代替案としては扱わない．
