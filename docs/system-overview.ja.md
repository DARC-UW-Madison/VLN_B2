# システム全体像と無人起動

[English](system-overview.md) · [進捗](status.ja.md) · [実行環境構築](jetson-runtime.ja.md)

2026-11-01のMac方針：JetsonのTailscale IPv4へ直接RDP接続する．Windows Appの登録は操作者が行い，
Macのtunnel，自動起動，経路変更，新clientは追加しない．既存Tailscaleと前景の作業用SSHを使い，
作業SSHは使用後に終了する．Jetsonにはアドレス準備helper，`b2-rdp.service`の再試行drop-in，
TCP 3389だけのINPUT ruleを加えた．TLS，認証，大学Wi-Fi，機体Ethernetは維持する．
Macから通信・TLSは通ったが，新経路のGUIログインと変更後の機器全体の再起動は未検証である．
[直接画面接続](remote-desktop.ja.md)を参照する．

## 外付けJetsonの確認済み構成

2026-10-27の調査では，Jetson AGX Orin Developer Kitの64 GBクラスである．

| 項目 | 構成と確認範囲 |
|---|---|
| CPU | Armの12コアがオンライン．報告される最大クロックは2.2016 GHz．AGX Orinの仕様上はCortex-A78AE |
| GPU | NVIDIA Ampere．SMが16基で，CUDAコア2048基・Tensorコア64基に対応．compute capability 8.7，報告される最大GPUクロック1.3 GHz |
| メモリ | 64 GBクラス，Linuxの認識は約61.3 GiB．CPUとGPUで共有し，別に64 GBの専用VRAMがあるわけではない |
| 公称性能 | このクラスの上限は疎なINT8演算で275 TOPS，LPDDR5の帯域204.8 GB/s．メーカー値であり，TIC-VLAの実測ではない |
| 現在の電力モード | 以前からのMAXN設定を維持．消費電力の実測値ではない |
| OS用ストレージ | 約64 GBのeMMC，デバイスは`mmcblk0`．ルート領域は約60.8 GB，空き約20.3 GB |
| 研究用ストレージ | Samsung SSD 990 PRO 2 TBのNVMe．PCIe 4.0 x4のリンクを確認．初期構築後の空き約933 GBで，ビルド中は変化する |
| Wi-Fi | Realtek RTL8822CE，802.11acのPCIeアダプタ．管理用に使用中 |
| 機体向けEthernet | キャリアなし．B2はまだ未接続 |
| ソフトウェア | Ubuntu 20.04.6，L4T 35.4.1／JetPack 5.1.2系，CUDA 11.4，TensorRT 8.5.2．既存ROS FoxyディレクトリとZED SDK 4.1.2ヘッダあり |

[NVIDIAの仕様](https://developer.nvidia.com/embedded/jetson-developer-kits)と
[AGX Orinの技術資料](https://www.nvidia.com/content/dam/en-zz/Solutions/gtcf21/jetson-orin/nvidia-jetson-agx-orin-technical-brief.pdf)を参照する．
ディスク速度，継続時の消費電力，TIC-VLAの実行速度は未測定である．ネイティブCUDAの数値演算，
一致する基底コンテナ内の演算，PythonコンテナのCUDA可視性を確認した．完成した実行環境でも，
モデル不要の段階でFP32・BF16の8種類のGPU演算と本家sourceのimportが通った．
その後，モデル読込，保存画像の計測，時間制限付きカメラshadow推論も成功した．[現在の進捗](status.ja.md)を参照する．

## ストレージと変更箇所

SSDが2台ではなく，eMMCとNVMe SSDが各1台である．eMMCにはUbuntu，ドライバ，アカウントのファイル，
ソース，小さなホスト用Python環境を置き，大きなDockerイメージ・ビルド・標準モデルキャッシュはSSDへ置く．

SSDには既存の割り当て済みデータが約1 TBあり，当初`needs_recovery`が表示された．
これはジャーナルの復旧を示す状態であり，それだけでSSDの故障と判定したわけではない．
最初は再生による書き込みを避けるため`ro,noload`で調べた．操作者の明示的な許可後に通常の方法で
マウントし，ジャーナルを再生した．ext4のエラーは観測されず，現在は書き込み可能な状態で使用している．
既存データのフォーマット・削除はしていない．[保存先の手順](jetson-runtime.ja.md#保存先の前提)を参照する．

| 場所 | 本プロジェクトで作成・設定したもの |
|---|---|
| `~/Developer/Projects/Robotics/b2/VLN_B2` | 監査済みソース，専用`.venv`，ログ・ネイティブ検査用のGit管理外`local/` |
| `~/Developer/External/pyenv` | 版を固定したPython管理ツールのソース |
| `~/Developer/External/TIC-VLA` | 版を固定した利用制限のある上流ソースのみ．公開用プロジェクトの外に置く |
| `~/Developer/Environments/pyenv/versions/3.11.18` | システムPython 3.8とは別のユーザー用Python |
| `/mnt/b2-research/VLN_B2/docker` | SSD上の新しい共有Dockerデーモン保存先 |
| `/mnt/b2-research/VLN_B2/build-logs` | イメージのビルドログとモデル不要の検査結果 |
| `/opt/b2-remote/libexec/rdp-tailnet-ready.py`，`b2-rdp.service.d/tailnet.conf` | Jetsonだけの直接RDP準備・受信制限と起動再試行．非公開アドレスはRDP設定フォルダへ置く |
| `/mnt/b2-research/VLN_B2/models` | 非公開の変換済みsafetensors・manifest．Git対象外の`models` symlinkで参照 |
| `/mnt/b2-research/VLN_B2/observations` | 非公開の時間制限付きカメラ実験画像・各frame manifest |
| `local/camera-runtime/attempt-01` | 非公開pyzed・Cython prefix，専用校正，カメラ検査記録．SDKは読み取り専用 |
| `local/async-shadow`，`local/unitree-build`，`local/unitree-check-01` | 非公開の実験・build・オフライン検査の来歴と報告 |
| `/mnt/b2-research/VLN_B2/huggingface` | 承認した元モデル資材．標準の`~/.cache/huggingface`から参照する |

最初のPython構築でホストへ追加した開発用パッケージは`libbz2-dev`，`libncurses-dev`，`libreadline-dev`の三つで，
その時点で既存パッケージは更新・削除していない．2026-10-28には通常のLAN SSHを確認後，
Tailscaleだけを1.104.4へ更新した．別にビルドしたRDPのprefix，非ログインのサービス用`xrdp`，
許可グループ`b2-remote-users`，`/etc/pam.d/xrdp-sesman`，専用の`b2-rdp`・`b2-rdp-sesman` unitも追加した．
ホストのTLS鍵はroot管理で，レポには保存しない．xrdpのAPTパッケージ，Xorgの置換，CUDAドライバ，
新しいROSは追加していない．プロジェクトは専用venvへ編集可能な形で導入した．
DockerではNVIDIAの基底イメージを取得してPython用イメージをビルドし，Torch／visionもその中で構築する．
CUDA，TensorRT，Docker，ROS，ZEDは元からあった．承認した元の資材はSSDの標準Hubキャッシュへ置き，変換したsafetensors・manifestは
SSDのmodels領域へ置いてプロジェクトのGit対象外symlinkから参照する．ホストvenvのパッケージやレポのソースではない．

システム全体の変更は，`/etc/fstab`のSSD設定，Docker保存先，`docker.service.d`のマウント検査である．
設定のバックアップと旧Docker保存先は残している．Wi-Fiは自動接続を無制限に再試行する設定へ変更し，
旧プロファイルも保存した．研究用ログインのAC時の自動サスペンドは無効化した．GUI起動は維持し，
その後，制御したソフトウェア再起動を行い，その時点のWi-Fiでの自動復帰を確認した．下の起動確認を参照する．

## 隔離される範囲

- **Linuxユーザー**はホーム，認証情報，通常のアクセス権を分ける．研究用ログインにはsudoがあり，
  ホスト全体を変更できるため，強いサンドボックスではない．
- **Pythonのvenv**はプロジェクトのPythonパッケージを分ける．Pythonコードからのファイル，ネットワーク，
  GPUへのアクセスを制限するものではない．
- **Docker**はアプリ用のファイルシステムと依存先を分けるが，ホストのカーネルとNVIDIAドライバを使う．
  デーモンは共有し，sudoでDockerを扱う権限も強い．検査には必要な入力だけを接続し，
  モデル不要の実行時はネットワークを切り，機体へ指令を送らない．

[Dockerのセキュリティモデル](https://docs.docker.com/engine/security/)も参照する．

イメージはアプリ環境のひな形で，コンテナはそれを動かした実体である．Torchのイメージを作っても，
全ユーザーのホストPythonへTorchが入るわけではない．ホストのvenvはプロジェクトのツール用，
GPUイメージはモデル実行環境の候補用である．カメラには，別に検証した非公開binding prefix，
読み取り専用のネイティブSDK，コンテナ内だけのグループを使う．別のUnitree状態専用イメージは
オフラインのimport・符号化を通った．どちらもホストvenvへvendor packageを導入しない．
実際のB2状態取得は未検証である．[カメラ設定](camera-runtime.ja.md)と[状態環境](unitree-runtime.ja.md)を参照する．

## GUIと無人起動

現地での復旧用に`graphical.target`とデスクトップを維持する．今回確認した主要GUIプロセスのRSS合計は
約0.7 GiBだったが，デスクトップを追加した場合の厳密な負荷測定ではなく，共有ページの重複もある．
この64 GBの機器で，現時点からCLI専用起動にする必要はない．

目標は，給電→Ubuntu起動→システムのWi-Fi接続→Tailscale→SSHである．GUIの自動ログインは
現地の操作に便利だが，ネットワークサービスの起動には本来不要である．NetworkManager，tailscaled，SSHは
起動時に有効で，現在も動作している．
Macからの画面操作は[リモートデスクトップ](remote-desktop.ja.md)を参照する．既存Vinoは未起動で，
以前の確認ではWindows App・RDPとホストのxrdpを使った．サーバーは`/opt/b2-remote`へ導入して動作中で，Windows Appの認証・画面表示が通り，操作者も基本操作を確認した．
RDP本体を起動時に有効化し，sesmanは必要な依存先として起動する．HDMIなしでソフトウェアから再起動し，
Wi-Fi，Tailscale，SSH，RDPサービスが手動の再接続なしで復帰した．SSDのマウントとDockerの起動も通った．
初回のWi-Fiは非Enterprise設定だったため，その後eduroamへ切り替え，2回目のHDMIなしのソフトウェア再起動と，
操作者によるRDPの表示・入力確認も行い，成功した．物理的な電源の入れ直しは未確認である．Tailscaleはログイン状態を保持するため，通常は起動ごとに
`tailscale up`をやり直さない．認証キーの期限は，別途[Tailscaleの管理画面](https://tailscale.com/docs/features/access-control/key-expiry)で確認する．

2026-10-27に調べた企業向けWi-Fiプロファイルは，ユーザーのsecret agentでパスワードを扱う設定
（`password-flags=1`）で，利用できるログインも限定されていた．その後の保存・起動確認の結果は下に記す．NetworkManagerの設定キャッシュから
パスワードは取得できなかった．2026-10-28に調べた，その時点の有効なWi-Fiプロファイルには802.1X設定がなかった．
以前の企業向けプロファイルの結論を別の接続へ適用しない．ヘルパーはPEAP以外の設定変更を拒否する．
認証情報を操作する前に，対象のeduroamプロファイルを改めて特定する．
ログイン前から企業向け接続を使うには，物理端末または自分の対話型SSH端末で
一度だけ入力して保存する．チャットやコマンド引数へパスワードを書かない．
既定では有効なプロファイルを編集する．保存済みの非アクティブな設定には，
`--connection-id SAVED_PROFILE_NAME`を付ける．名前が一つの接続に厳密に一致する必要がある．
どちらも接続を有効にしない．対象を選ぶためだけにWi-Fiを切り替えない．
リモートデスクトップの手引きにGUIと端末の両手順を記した．

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
sudo /usr/bin/python3 tools/configure_unattended_wifi.py --apply
```

ツールは現在の認証アカウントを表示して，
入力を画面に出さずにパスワードを2回受け取って照合する．認証ID，CA，EAP方式，サーバー検査は維持し，
NetworkManagerのroot保護されたシステムプロファイルへ保存し，全ユーザー向けの自動接続を設定する．
バックアップを作り，Wi-Fi，GDM，Tailscale，
本体は再起動しない．管理者はシステム保存の認証情報を読めるため，機器の管理者から隔離した保存ではない．
`--apply`なしでは読み取り確認だけを行う．GUI自動ログインは別の任意の選択で，明示的に希望する場合だけ
`--autologin RESEARCH_USER`を追加し，プレースホルダーを目的の通常ログインへ置き換える．
切り替えは認証情報の保存成功後にだけ行う．共有機ではデスクトップのログイン認証を維持することを推奨する．
起動時のWi-Fi・Tailscale・SSHにGUI自動ログインは不要である．

今後の変更では，時間制限付きの復元または現地での復旧を用意して再接続する．
完了したeduroamの再接続・ソフトウェア再起動の証拠は下に記す．物理的な電源の入れ直しには，
現地の人とコンソールでの復旧手段が引き続き必要である．実行中の作業は中断しない．設定だけでは復帰の証明にならない．
Wi-Fiの電波，大学の認証，認証情報の期限は外部の条件として残る．
[大学の公式Wi-Fi設定](https://kb.wisc.edu/ns/page.php?id=25020)と
[NetworkManagerの認証・信頼設定](https://networkmanager.dev/docs/api/latest/settings-802-1x.html)を維持する．

純正開発キットは[給電すると自動起動するのが既定](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/howto.html)である．
実機のJ42ジャンパー，電源，極性，電圧，容量は物理的に確認する必要がある．B2の電池・出力仕様は未確認で，
コネクタの形だけから適合すると考えたり，未確認の機体電源へ接続したりしない．
自動ログインによって，本プロジェクトやモーターを自動起動させることはない．

## UWNetのポータル登録とeduroamの違い

初回の非EnterpriseのWi-Fiによる再起動試験はUWNetだった．その後，認証情報を保存して切り替え，
2回目の再起動でeduroamを確認した．順番に行った別の観測であり，同じ接続について矛盾した報告ではない．
保存済みのUWNet設定は残っているが，設定があることだけではインターネットの利用許可を証明しない．

| 保存・管理の場所 | 残る可能性がある状態 | 確認した範囲 |
|---|---|---|
| ホストのNetworkManager | UWNetのSSID，自動接続，通信設定．オープンなWi-Fi自体の秘密として大学パスワードは不要 | 以前のUWNet設定は非Enterpriseで，現在も保存されている |
| ブラウザ・キーリング | ブラウザの選択による保存パスワード，cookie，ログイン履歴 | 未調査．ポータルへの入力だけでは，端末への保存・非保存のどちらも証明しない |
| 大学側のシステム | 機器のMACアドレスとアカウントの登録，期限，認証・利用の記録 | 大学はアカウントに紐づく機器登録を説明している．この機器のポータル側の記録は未調査 |
| ホストのeduroam設定 | Enterpriseの認証ID，信頼設定，システム保存したパスワード | 今回，全ユーザー向けのPEAP自動接続とパスワード保存を確認した．root管理者は秘密を読める |

同じ大学IDを使っても，認証の経路は同じではない．UWNetのポータルはアカウントを認証して機器を
利用可能にし，eduroamはEnterpriseのWi-Fi接続時に認証する．
[UWNetのブラウザ登録の案内](https://kb.wisc.edu/helpdesk/22915)では，大学関係者の登録は学期末までで，
MACアドレスをNetIDへ紐づける．一方，[手動の機器登録](https://kb.wisc.edu/ns/79140)は更新時から6か月の
期限を設定する別の手続きである．全てのゲストへ同じ期間を当てはめたり，この機器の登録を見ずに
正確な期限を断定したりしない．

大学は[UWNetを非暗号化，eduroamを暗号化された接続と説明している](https://chemconnect.wisc.edu/comphelp/chemistry-network/)．
UWNetでもHTTPSやSSHは各アプリケーションの接続を暗号化できるため，Wi-Fiがオープンであるだけで
ポータルの認証情報が漏れたとは判断できない．一方，ブラウザのログアウト，Wi-Fi設定の削除，大学側の
登録の削除は別の操作であり，どれも大学側の全ログの消去を意味しない．サーバー側のパスワードの表現や
保存期間はこちらからは分からず，大学が平文で保存しているとも，入力しても記録が残らないとも断定しない．
認められた共有IDなら利用はそのIDに紐づくため，共有が許可されているかを大学の運用に照らして確認する．
引き継ぎ時はブラウザの保存情報と機器登録を確認し，認められた研究ファイルを維持し，他のアカウントの
登録を無断で削除しない．

自動再接続には，電源，有効な認証情報，電波，Tailscaleの認証が必要である．JetsonをB2に載せても
Wi-Fiの電波範囲は増えない．将来の推論・制御はMacの常時接続なしでJetson内で行い，
機体とのEthernetと現地の停止動作は別に試験する．

## 個人の認証情報と共有・返却

UWの[公式eduroam手順](https://kb.wisc.edu/ns/page.php?id=25020)では，個人のNetIDメールと
NetIDパスワードを使う．システム保存では，そのパスワードをroot保護されたNetworkManagerの設定へ置く．
管理者から守る暗号化ではない．[keyfileの公式資料](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html)にも，
平文の秘密情報が入り得るため，他ユーザーからファイルを保護する必要があると明記されている．
sudoユーザーや，そのファイルへアクセスできる強い権限のコンテナは読み出せる．
別のLinuxログイン，venv，通常のコンテナで，個人の大学パスワードをホスト管理者から守れるわけではない．
設定をリポジトリ，イメージ，一般のバックアップ，サポートログへ入れない．

保存済みのeduroam設定は，初めはユーザーのsecret agentとログイン制限を使っていた．
その後，所有者が自分のSSH端末へパスワードを入力し，ツールで全ユーザー向けの自動接続，
無制限の再試行，password flags 0にした．管理権限で空でない秘密の保存を確認し，値は表示していない．
既存のユーザーキーリングは調査・削除していない．CATのCAの束にはUSERTrust RSA Certification Authorityが
含まれ，DNSのalternative-subjectの明示的な照合を維持している．以前の報告ではdomain-match欄が
空であることだけを見て，この別形式のサーバー名検証を見落としていた．CAやサーバー照合は無効化・交換していない．
ツールは信頼設定を維持するもので，任意のプロファイルの適切さを独立に保証するものではない．

既知のWi-Fiからeduroamへの初回切り替えは，180秒のNetworkManagerの復元予約で保護した．
新規のTailscale SSH，正常な接続，管理サービスを確認して予約を解除した．2回目のHDMIなしの
ソフトウェア再起動では，自動でeduroamへ接続し，対象機の稼働時間が約24秒の時点で新規SSHが戻った．
boot IDの変更，各管理サービスの起動時有効化と動作，SSDのマウント，DockerのSSD保存先，
RDPのloopback限定待受を確認した．所有者が再びRDPの表示と入力を確認した．GUI自動ログインは変更していない．
ソフトウェア再起動での観測結果であり，物理的な電源の入れ直しの結果や，大学の電波範囲，
認証情報の有効性，Tailscaleのポリシーを保証するものではない．

今後の設定変更では，実行中の作業を終了し，現地操作または時間制限付きの通信復元を用意して次を行う．

1. 専用利用中は操作者本人の承認されたeduroam認証を使い，他の研究者のパスワードを流用しない．
   システム保存前に実際のプロファイル，公式のCA・サーバー検査，sudo権限を確認する．
   秘密情報は操作者の端末で入力し，チャットへ送らない．
2. 許容できる場合は，ツールで起動時Wi-Fiの認証情報を保存する．GUIログインは別に決める．
   現在の自動ログイン先は別のログインで，変更していない．
3. 再接続し，計画した電源投入からの起動を，デスクトップへ誰もログインせずに試験する．
   Wi-FiとMacからのTailscale SSHを確認する．起動時の表示や現在の接続だけでは，この一連の動作を証明できない．

共有へ移行する前に，大学・研究室のIT担当へ，共有機に承認された接続や機器認証を相談する．
共有eduroamアカウントがあるとは仮定せず，個人のNetIDパスワードを共有しない．
研究者ごとにログインを分け，sudo権限を見直し，一時的な弱いログインパスワードも変更する．
共有時はGUI自動ログインを無効にする．これらの方針・認証情報の変更はまだ実施していない．

合意した返却時の確認は研究用ログインだけでなく，既存の研究室用ログインも対象にする．
UWNetのポータル認証は研究用ログインを作る前に，その既存ログインで行われたため，
ブラウザのcookie・保存パスワード，webセッション，キーリングが以前のホームに属する可能性がある．
新しいログインを作っても移動・消去されない．所有者・管理者とそのアカウントを確認し，返却・共有を
求められた時点で特定した個人のアクセスだけを処理する．研究室のファイルや無関係な利用者の秘密は維持する．
ブラウザ・キーリングの整理はまだ行っていない．

引き継ぎ・返却では，最初に現地操作と代わりの通信手段を用意する．以下は確認計画であり，**自動削除を実行したわけではない**．
共有・返却の依頼時には，承認した研究ファイル，実行環境，有用な構築物を残す．個人のアクセスと
認証情報のコピーを一覧化し，削除・失効する対象を特定する．所有者や保持の判断が曖昧なら先に確認する．
ディスク全消去を既定にしない．ブラウザのログアウトとSSH鍵の削除だけでは，Wi-Fiの秘密情報，
root用バックアップ，サーバー側のアクセス登録は消えない．

- 個人のWi-Fi設定を切断・除去する．ユーザーキーリング，NetworkManager・wpa_supplicantの設定，
  `/etc/NetworkManager/vln-b2-backups`を含むroot保護の設定バックアップ，システムバックアップ内の
  認証情報のコピーも確認する．個人の認証IDが残る古い設定を復元しない．
- 個人のTailscaleからログアウトし，[管理画面](https://tailscale.com/docs/features/access-control/device-management/how-to/remove)で
  機器を除去または移管する．Tailscaleの停止やLinuxユーザーの削除だけでは完了しない．
- SSH鍵・許可されたアクセス，Git認証情報，トークン，ブラウザ・キーリングのセッション，自動ログインを確認する．
  研究ファイルは適用条件に従って引き継ぎ，所有者・管理者の合意のもとで個人のアクセスを外す．
- 再起動後に，以前の大学IDと個人のtailnetへ再接続しないことを確認する．認証情報をコピーされた可能性や，
  バックアップの除去を確認できない場合は，大学の公式手順でパスワードを変更し，該当するトークンも失効させる．
  SSD上のファイルを削除しただけで，完全な消去を証明したことにはならない．

遠隔操作の唯一の復旧経路である間は，通信を切ったり認証情報を除去したりしない．
ここでアカウントの削除，認証情報の変更，データの消去は行っていない．

ソースの同期，本家・モデルとの境界，レイヤごとの通信経路は[実行の流れ](runtime-flow.ja.md)を参照する．

## 4台の担当と次の段取り

```text
Mac -- Wi-Fi/internet + Tailscale/SSH --> External AGX Orin
                                                |
                                    planned robot Ethernet
                                                |
                                   B2 internal network (unknown)
                                      /                 \
                           reported onboard Jetson   motion-control system
                           sensor/localization?       existing walking/balance
```

確認済みの接続はMacと外付けJetsonの間だけで，内部の計算機，サービス，ケーブルの行き先は未確認である．
[UnitreeのB2仕様](https://www.unitree.com/b2/)にはIntelのプラットフォーム・開発用計算機と，
Orin NXの選択肢があるが，研究室の納入構成を確定する資料ではない．
[公開されたB2 SDK](https://github.com/unitreerobotics/unitree_sdk2/blob/main/include/unitree/robot/b2/sport/sport_client.hpp)は
想定する上位指令の経路を裏付けるもので，この機体で制御に成功したという意味ではない．

外付けJetsonで認識・計画を行い，B2の既存の歩行制御を利用する構成を目指す．状態・センサー・移動の
サービスに到達できれば，変更するソフトウェアを外付け側に集約できる可能性があるが，機体の全機能への
アクセスが保証されるものではない．機体へのEthernetはローカルな配線で，大学の有線LAN設備とは別である．
大学に有線設備がなくても，機体との有線接続は構成できる．SDK2はDDSを使い，外付けホストのROS 2は任意である．
[ネットワーク設計](network-topology.ja.md)を参照する．

GPU環境の検査と無人アクセス試験を終え，モデルの対象・読込方法を確認する．実際の内蔵計算機と
センサー配線を特定し，指令を送らずに画像・状態を取得する．制御権と独立した停止方法を検証してから，
管理された走行試験へ進む．内部ソフトウェアは，役割とインターフェースを理解するまで維持する．
