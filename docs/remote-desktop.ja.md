# Macからのリモートデスクトップ

[English](remote-desktop.md) · [文書一覧](README.ja.md) · [システム全体像](system-overview.ja.md) · [現地手順](field-network.ja.md)

**2026-11-01の現在方針**：Windows Appから，JetsonのTailscale IPv4・TCP 3389へ直接接続する．
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

## 適用した直接接続の設定

既存ホストxrdpは，loopback・wildcardではなく**設定したTailscale IPv4だけ**で待ち受ける．
TLS設定，証明書・鍵，PAM，許可group，Linux認証は維持した．IPv4 INPUTへ一つのlabel付きruleを加え，
その正確な宛先・TCP 3389へ`tailscale0`以外から来た通信をdropする．既存ruleのflush，既定firewall方針，
SSH，NoMachine，Wi-Fiは変更しない．Tailscale側のアクセス規則も引き続き適用される．

確認した[起動準備helper](../deploy/rdp-tailnet-ready.py)と[systemd drop-in](../deploy/rdp-tailnet.conf)は，
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
[調査の証拠と限界](system-overview.ja.md#接続断とデスクトップ不調の切り分け)を参照する．

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

## クライアント，サーバー，プロトコル，セッション

| 用語 | この構成での意味 |
| --- | --- |
| クライアント | MacのWindows App．遠隔の画面を表示し，操作を送る |
| サーバー | Jetsonのxrdp．接続を認証し，画面の通信を扱う |
| RDP | Remote Desktop Protocol．両者が画面と操作をやり取りするための規則 |
| xorgxrdp | Xorgの画面サーバーとxrdpを接続するモジュール |
| GUIセッション | Jetsonで動くデスクトップ，ウィンドウ，ユーザーのサービスのまとまり |
| SSHトンネル | 認証した接続を通して，ローカルのTCPポートをJetsonへ運ぶ仕組み |
| ループバック | `127.0.0.1`など，そのコンピューター自身を表すローカルアドレス |

MacのMicrosoft Remote Desktopは，現在は**Windows App**に置き換わっている．
直接接続するPCの追加だけなら，MicrosoftアカウントでWindows Appへサインインする必要はない．
遠隔のLinuxログインは別のアカウントであり，eduroamの大学IDではない．
Microsoftの[置き換えの案内](https://learn.microsoft.com/en-us/previous-versions/remote-desktop-client/remote-desktop-macos)，
[接続手順](https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps)，
[アカウントの説明](https://learn.microsoft.com/en-us/windows-app/user-account-settings-add-remove-manage)を参照する．

[xrdp](https://github.com/neutrinolabs/xrdp)はLinuxのRDPサーバーで，ARMにも対応する．
Xorgバックエンドでは，xrdp-sesmanが[xorgxrdp](https://github.com/neutrinolabs/xorgxrdp)の
モジュールを使うXorgサーバーを起動し，続いてユーザーのデスクトップを起動する．
遠隔用の仮想セッションなら，物理画面へ先にログインしなくてもデスクトップを用意できる．
これは仕組みの目的であり，このJetsonで画面なしログインが確認済みという意味ではない．

通常は，HDMIの画面をそのまま映すのではなく，別のデスクトップを作る．
実機の画面で開いていたブラウザーや設定画面が，RDP側にも見えるとは限らない．
ただし両方とも同じホストを使い，同じアカウントならホーム内のファイルも共通である．
画面が別になってもサンドボックスが別になるわけではない．RDPは画面の更新とキーボード・
マウス操作を送る．アプリケーションと，そこから開始した計算はMacではなくJetsonで動く．

解像度やデスクトップセッションの設定によって，ドック，拡大率，テーマがHDMI画面と違う場合がある．
見た目の差だけで接続不良とは判断しない．ファイルや設定が失われたと考える前に，ログイン先とセッションを確認する．

## NoMachine，RDP，VNC

| 名称 | 何を指すか | 今回の構成との関係 |
|---|---|---|
| NoMachine | NXという独自方式を使う遠隔操作製品．利用できるセッションは版・設定による | ホストに以前から存在し，変更していない．Macクライアントは未検証 |
| RDP | 遠隔デスクトップの通信方式．今回はWindows Appとxrdp・xorgxrdpが実装する | 選択して検証した管理経路．今回のbackendは別の仮想Xorgデスクトップを開始する |
| VNC | RFBを使う遠隔デスクトップ技術．実装によって既存画面の共有も仮想画面の生成もある | 既存のVinoは未起動で，今回は採用していない |

製品の[NoMachine FAQ](https://www.nomachine.com/support/faq)と
[RealVNCの方式の説明](https://help.realvnc.com/hc/en-us/articles/360002320638-How-does-VNC-technology-work)を参照する．
方式の名前だけでは，画面の共有，暗号化，性能，安定性は決まらない．RDPで別に作る画面は，
同じユーザーのホームを使っていてもドック，テーマ，解像度，セッション設定が違う場合がある．
別のLinuxアカウントやサンドボックスではない．

以前のRDPサーバーは，**Jetson自身**のloopbackアドレスだけでTCP接続を受けた．
Windows Appは**Mac自身**のloopbackポートへ接続し，SSHが通信を転送する．

```text
Windows App -> Mac 127.0.0.1:13389 -> SSH over Tailscale
            -> Jetson 127.0.0.1:3389 -> xrdp -> virtual desktop
```

Tailscaleはプライベートなネットワークの到達性，SSHは認証とTCP転送，RDPは画面の認証・描画・入力を担当する．
RDPサーバーのTLSも有効なままである．別の待受・アクセス方針を承認して設定すればMacからRDPへ
直接接続することも可能であり，当時は別の構成だった．3389番を大学・機体のインターフェースに公開せず，
確認したSSH経路を使う．転送用masterは対話型のSSH端末とは別であり，端末を開くだけでは画面の
トンネルはできない．専用トンネルを閉じてもxrdpやロボットのアプリケーションは終了しない．
このトンネルは画面接続だけを運び，機体のDDS通信全般やモデルの制御ループは運ばない．

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

## セッションと描画の制約

2026-11-03に，研究用アカウントの物理GUI・RDP GUIが同時に存在した．操作者の依頼で物理側だけを
ログアウトし，RDP・SSHを維持すると，RDP displayでGNOME・window managerが起動した．
clientの接続を開き直して画面を確認する．これは一回のログアウトで，自動GUIログイン設定の変更でも，
以前のフリーズ原因の証明でもない．

[xrdpのFAQ](https://github.com/neutrinolabs/xrdp/wiki/Tips-and-FAQ)には，systemdを使う環境で，
同じユーザーが実機の画面とxrdpへ同時にログインすると競合する問題が説明されている．
研究用アカウントでRDPへ入る前に，そのアカウントの実機GUIからログアウトする方針にする．
SSHの端末は，二つ目のGUIデスクトップとは異なる．別アカウントの既存の自動ログインを
勝手に変えたり，原因のわからないセッション競合を隠すためだけにアカウントを増やしたりしない．

既存のJetsonのグラフィックス環境は維持する．Xorgが起動するか，デスクトップをCPUで描画するか，
GPUで計算できるか，デスクトップ描画をGPUで高速化できるかは，それぞれ別の問題である．
設定画面程度ならソフトウェア描画を使う場合があるが，それだけでCUDA計算の可否は判断できない．
両方を別々に確認する．未調査のxrdp問題に対して，PC向けNVIDIAドライバの導入，GDMの置き換え，
JetPackの更新，新しいUbuntuのGNOME Remote Desktop手順の流用を行わない．

[NVIDIAのVNC手順](https://developer.nvidia.com/embedded/learn/tutorials/vnc-setup)は，
このxrdp構成を検証する資料ではない．
[AGX Orin・Ubuntu 20.04に関するNVIDIAのサポート投稿](https://forums.developer.nvidia.com/t/the-orin-module-ubuntu20-04-system-is-controlled-remotely-from-a-pc/269195)
からも，RDPが常に安定するとは判断できない．復旧手段として頼る前に，選んだ版を実機で試す．

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
認証情報を保存する操作は意図的に別になっている．[起動時の通信と認証情報](system-overview.ja.md)を参照する．
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

Vinoは以前から導入済みで，停止していた．初期の計画では既存のコンソール画面を共有する方法として
検討したが，操作者の希望により現在の計画からVNCを除外する．Vinoの設定・転送コマンドは示さない．
成功したHDMIなしの試験はxrdpの結果であり，Vinoの結果ではない．構成調査は過去の証拠として残し，
VNCを現在の代替案としては扱わない．

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
