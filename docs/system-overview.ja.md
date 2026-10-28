# システム全体像と無人起動

[English](system-overview.md) · [進捗](status.ja.md) · [実行環境構築](jetson-runtime.ja.md)

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
FP32・BF16の8種類のGPU演算と本家ソースのimportが通ったが，モデルは構築していない．

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
| `/mnt/b2-research/VLN_B2/huggingface` | 空のモデルキャッシュ．標準の`~/.cache/huggingface`から参照する |

ホストへ追加した開発用パッケージは`libbz2-dev`，`libncurses-dev`，`libreadline-dev`の三つで，
既存パッケージは更新・削除していない．プロジェクトは専用venvへ編集可能な形で導入した．
DockerではNVIDIAの基底イメージを取得してPython用イメージをビルドし，Torch／visionもその中で構築する．
CUDA，TensorRT，Docker，ROS，ZEDは元からあった．モデルの重みは未取得である．

システム全体の変更は，`/etc/fstab`のSSD設定，Docker保存先，`docker.service.d`のマウント検査である．
設定のバックアップと旧Docker保存先は残している．Wi-Fiは自動接続を無制限に再試行する設定へ変更し，
旧プロファイルも保存した．研究用ログインのAC時の自動サスペンドは無効化した．GUI起動は維持し，
再起動やネットワークの切断は要求していない．

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
GPUイメージはモデル実行環境の候補用である．カメラや状態を取得する前には，SDKの権限とバインディングの
互換性を別途確認する．

## GUIと無人起動

現地での復旧用に`graphical.target`とデスクトップを維持する．今回確認した主要GUIプロセスのRSS合計は
約0.7 GiBだったが，デスクトップを追加した場合の厳密な負荷測定ではなく，共有ページの重複もある．
この64 GBの機器で，現時点からCLI専用起動にする必要はない．

目標は，給電→Ubuntu起動→システムのWi-Fi接続→Tailscale→SSHである．GUIの自動ログインは
現地の操作に便利だが，ネットワークサービスの起動には本来不要である．NetworkManager，tailscaled，SSHは
起動時に有効で，現在も動作している．
Macからの画面操作は[リモートデスクトップ](remote-desktop.ja.md)を参照する．既存Vinoは未起動で，
Windows App・RDPとホストのxrdp案を優先する．サーバーは未導入・未有効化で，画面なし・ログイン時の動作は
現地で検証する．Tailscaleはログイン状態を保持するため，通常は起動ごとに
`tailscale up`をやり直さない．認証キーの期限は，別途[Tailscaleの管理画面](https://tailscale.com/docs/features/access-control/key-expiry)で確認する．

現在の企業向けWi-Fiプロファイルは，ユーザーのsecret agentでパスワードを扱う設定
（`password-flags=1`）で，利用できるログインも限定される．NetworkManagerの設定キャッシュから
パスワードは取得できなかった．ログイン前から接続するには，物理端末または自分の対話型SSH端末で
一度だけ入力して保存する．チャットやコマンド引数へパスワードを書かない．

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

保存後は，現地に人と画面・キーボードを用意し，計画した再接続・電源投入からの起動試験を行う．
実行中のソースビルドは中断しない．試験が通るまでは，無人アクセスの設定をした段階で，動作の実証ではない．
Wi-Fiの電波，大学の認証，認証情報の期限は外部の条件として残る．
[大学の公式Wi-Fi設定](https://kb.wisc.edu/ns/page.php?id=25020)と
[NetworkManagerの認証・信頼設定](https://networkmanager.dev/docs/api/latest/settings-802-1x.html)を維持する．

純正開発キットは[給電すると自動起動するのが既定](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/howto.html)である．
実機のJ42ジャンパー，電源，極性，電圧，容量は物理的に確認する必要がある．B2の電池・出力仕様は未確認で，
コネクタの形だけから適合すると考えたり，未確認の機体電源へ接続したりしない．
自動ログインによって，本プロジェクトやモーターを自動起動させることはない．

## 個人の認証情報と共有・返却

UWの[公式eduroam手順](https://kb.wisc.edu/ns/page.php?id=25020)では，個人のNetIDメールと
NetIDパスワードを使う．システム保存では，そのパスワードをroot保護されたNetworkManagerの設定へ置く．
管理者から守る暗号化ではない．[keyfileの公式資料](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html)にも，
平文の秘密情報が入り得るため，他ユーザーからファイルを保護する必要があると明記されている．
sudoユーザーや，そのファイルへアクセスできる強い権限のコンテナは読み出せる．
別のLinuxログイン，venv，通常のコンテナで，個人の大学パスワードをホスト管理者から守れるわけではない．
設定をリポジトリ，イメージ，一般のバックアップ，サポートログへ入れない．

現在のWi-Fiはユーザーのsecret agentを使い，パスワードをシステム設定へ保存する変更はしていない．
既存のユーザーキーリングの内容は調べていない．現在の接続は，ログイン前から起動時に接続できる証拠ではない．
デスクトップへのログインや，成立済みの認証セッションでつながっている可能性がある．
CA設定はあるが，サーバー名の照合設定は未指定だった．ツールは既存設定を維持するもので，適切さを保証しない．
個人の認証情報を保存する前に，大学の公式Linuxインストーラーと照合する．
サーバー名を推定したり，証明書検証を無効にしたりしない．

現地では，今回のソースビルドが終了し，画面・キーボードで復旧できる状態で次を行う．

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
