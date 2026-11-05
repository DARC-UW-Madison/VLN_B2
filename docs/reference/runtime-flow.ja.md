# リポジトリのファイルから機体の動作まで

[English](runtime-flow.md) · [システム全体像](system-overview.ja.md) · [構成](architecture.ja.md)

> 文書種別：**参照資料**．

このガイドでは，現在あるものと，今後の実機構成を区別する．外付けJetsonでは実行環境を構築し，
モデル不要の検査，実モデルの厳密なGPU読込，生成画像の1回の推論が通った．承認した重みはSSDへ非公開で
保存・変換済みで，ZEDの実RGB取得も一回通った．継続取得・時計の整合は未検証，B2へのEthernetも未接続で，本プロジェクトに
モーター指令を送る実装はない．

Macを軽い役割にできる理由，Dockerが任意であること，ROSの配置，コンテナ・センサーの接続は
[配置方針](../explanations/deployment-design.ja.md)で説明する．全ガイドは[文書目次](../README.ja.md)を参照する．

## どのファイルを共有するか

研究用ログインの`~/Developer`は，今回の構築で使う作業領域である．このログインに属し，
全ユーザー共通のシステムディレクトリではない．配下のプロジェクト，外部ソース，Pythonの配置は
今回の作業用に整えた．他のユーザーのホームと既存SSDデータは別である．Macの`~/Developer`も
独立しており，同じ名前だけでは同期しない．

Jetsonの`~/Developer/Projects/Robotics/b2/VLN_B2`は，Macから転送した確認済みの
ソースアーカイブである．Git管理するソースは，転送対象のMacのコミットと一致させる．
現時点のJetson側には`.git`がなく，`local/source-revision.txt`に転送した版を記録する．
どちらかで編集しても他方には自動反映されず，研究室のGitHubにもまだこのソースを送っていない．
初回の公開を承認してpushした後は，双方でcloneと明示的なコミットを使う形へ移行できる．

| 共有するプロジェクトの内容 | 用途 |
|---|---|
| `src/b2_tic_vla/` | 独自に書いたカメラ・状態取得部，記録，同期モデル接続部，候補軌道の追従，CLI |
| `tools/` | ホストの読み取り調査と，操作者が実行する起動時Wi-Fi設定ツール |
| `deploy/` | コンテナの構築手順，依存先の候補，モデル不要のCUDA・Python・GPU検査 |
| `examples/`，`tests/` | 合成観測，未検証の制限値，現地記録の空欄，モックを使った試験 |
| `docs/`，README，CONTRIBUTING | 日英の説明，手順，確認結果，現在の進捗 |
| LICENSE，THIRD_PARTY | 独自成果物のライセンスと，外部資料に別途適用される条件 |

各機器の`.venv`，`local/`，コンパイル済みファイル，Dockerの層，キャッシュ，認証情報，
記録データ，モデルはGitの対象外である．したがって，管理対象のファイルがすべて一致しても，
フォルダ全体が同一ではない．`git pull`で更新されるのはソースであり，これらのローカル項目の同期や
イメージの再ビルドは自動で行わない．

## 本家TIC-VLAとのつながり

モデルの実行には，別々のものが必要になる．

1. **モデルのコード**は，ニューラルネットワークの構造と前処理・推論方法を定義する．
   版を固定した本家のソースを，本プロジェクト外の`~/Developer/External/TIC-VLA`に置く．
2. **重み**は，学習した数値の集合である．TIC-VLAのチェックポイントとInternVLの基盤モデルは
   承認した固定版をSSDの標準Hubキャッシュへ取得した．別のCPU環境でナビゲーション用のtensor形式へ
   変換し，元と変換物の条件を維持する．重みはソースファイルではなく，Gitには入れない．
3. **実行ライブラリ**は，Python，PyTorch，Transformers，CUDAなどで演算を行う．
   これらをビルドしても，重みを取得したことにはならない．
4. **本プロジェクトの接続部**は，画像・指示・機体状態を渡し，本家のPython APIを呼び，
   返ってきた計画を検査する．

```text
Our inference.py
    | Python import from separately supplied upstream_root
    v
ticvla.models.ticvla.TICVLA
    | constructs the model from separately supplied local base-model assets
    | receives compatible checkpoint tensors through our strict loader
    v
PyTorch operations -> CUDA -> host NVIDIA driver -> Orin GPU
    |
    v
Future relative XY positions -> our validated Plan object
```

同じ推論プロセス内でPython関数を呼び，ローカルファイルを読む．GitHub，クラウドのモデルAPI，
内蔵PCへ推論を依頼する構成ではない．確認済みのコードとファイルを揃えれば，推論にインターネットは
不要である．本家やモデルのPythonコードは実行されるため，オフライン設定だけで安全な隔離になるわけではない．

現在の`infer`は**オフラインの同期接続部**である．記録した観測を一つ読み，意味情報の遅延を0として
結果を書き出すが，B2へは送らない．今後の実時間処理には，非同期の意味情報キャッシュ，時刻・姿勢の
整合，監視，指令送信を別途実装する必要がある．候補の古いTorchにはチェックポイント読込の未解決の
セキュリティ問題があるため，元のチェックポイントはGPU環境へ復元させない．確認したCPU環境でsafetensorsへ
変換した入力では，厳密なGPU読込と生成画像推論が通った．`weights_only=True`が使えるだけで元を復元しない．[互換性調査](../records/runtime-compatibility.ja.md)を参照する．

### ライセンスの境界

このリポジトリのMITは，独自の接続部・ツール・文書だけに適用する．本家TIC-VLAには適用しない．
確認した[Academic Software License](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/LICENSE.md)は，
指定された教育・学術研究の利用に限定し，改変物を含む第三者への移転を禁じている．
Gitの外へ置いても，この条件はなくならない．独自ソースと一緒に誤って公開することを防ぐ配置である．

本家の実装をMITのファイルへコピーしたり，MITの表示だけを根拠に，本家入りのイメージ，
本家の改変コード，変換・追加学習した重みを公開したりしない．研究室内で引き継ぐ場合も含め，
対象の成果物と相手に対して許される範囲を先に確認する．本プロジェクトは独立した結合作業であり，
本家を再ライセンスしたforkではない．コード，基盤モデル，チェックポイント，データの条件は別に残る．
[外部資料の確認](../../THIRD_PARTY.ja.md)を参照する．

## Dockerで実際に何を動かすか

Dockerは推論ソフトウェアをまとめて実行するための層である．モデルの代わりにB2と通信したり，
新しいGPUドライバを提供したりするものではない．

```text
External Jetson hardware: CPU / shared RAM / GPU / USB / Ethernet / SSD
  Host Ubuntu + Linux kernel + NVIDIA driver + system services
    Docker daemon -> image layers stored on SSD
      Running container process
        private application filesystem: Python + Torch + dependencies
        NVIDIA runtime: exposes compatible host GPU support
        explicit mounts: selected source, approved assets, outputs
        network mode: selected for this run
```

**イメージ**は保存したアプリ環境のひな形で，**コンテナ**はそこから起動したプロセスと書き込み用の層である．
ファイルシステム・プロセス・ネットワークを分けながら，このJetsonのCPU・GPUと共通のカーネルを使う．
別の物理計算機でも，独立したOSを丸ごと起動するものでもない．コンテナを終了すると処理も終了する．
`--rm`で終了後のコンテナを片付ける場合，出力を残すには外部マウントへの書き出しか，今回の報告のように
ホスト側での保存が必要である．イメージは明示的に除去するまで残る．
[Dockerの実行リファレンス](https://docs.docker.com/engine/containers/run/)を参照する．

構築手順では，Python 3.11を含む`vln-b2-python:jp5`を作り，続いてTorch，torchvision，
推論用の依存先を含む候補`vln-b2-runtime:jp5`を作る．調査したL4T・CUDAの世代に合わせる．
ホストのvenvは軽量なプロジェクト用ツールの環境であり，コンテナのPythonとしては使わない．
現在の実行環境のレシピに入るのは検査コードと依存先で，**本プロジェクトのCLI全体，本家ソース，
重みは入っていない**．全import検査では，本家のソースを読み取り専用で接続する．
将来のアプリ用イメージ・起動設定では，本プロジェクトと承認済みのモデルファイルを明示的に用意する．

構築済みのPythonイメージは，B2やインターネットなしで検査できる．

```sh
sudo docker run --rm --pull=never --runtime=nvidia --network=none vln-b2-python:jp5
```

`--rm`は終了したコンテナを片付け，`--pull=never`は既存イメージだけを使い，
`--runtime=nvidia`はGPUを使えるようにし，`--network=none`は外部との通信を止める．
イメージの既定の処理でPythonとCUDAデバイスの可視性を検査してJSONを表示する．
ナビゲーションを起動するコマンドではない．全実行環境の既定の処理もモデル不要のTorch検査であり，
機体操作を自動で有効にしない．

ビルド時はソフトウェアを取得してコンパイルし，イメージの層を作る．上の検査の実行では行わない．
将来モデルキャッシュをマウントすれば，イメージにコピーせずコンテナから読める．
モデルのプロセスにホーム全体，NetworkManagerの設定，Tailscaleの状態，Dockerのソケットは接続しない．
コンテナ内のrootや広いデバイス・ネットワーク権限は隔離を弱める．ホストの管理者から守る仕組みではない．

## レイヤごとの通信

### 管理経路：Macから外付けJetson

```text
Mac terminal
  -> SSH over the Tailscale private network
  -> Wi-Fi/internet transport (direct peer path or relay)
  -> Jetson tailscaled / SSH service
  -> research user's shell
  -> start a host tool or ask the local Docker daemon to run a container
```

SSHのサービスとシェルは，モデルのコンテナ内ではなくホストにある．Tailscaleは遠隔からの到達性と認証を扱い，
SSHで端末を操作する．大学の有線LANは不要で，機体のサブネットへの転送やWi-Fi・Ethernetのブリッジは
設定していない．SSHを閉じると通常の前面処理は終了する可能性があるが，現在のビルドは明示的に切り離している．
将来の無人アプリには，Macの端末を開き続ける代わりに，専用サービスと検証済みの停止動作が必要になる．

### 観測・指令の経路：外付けJetsonからB2

想定するSDKの経路は次のとおりだが，この機体ではまだ実証していない．

```text
Robot state publisher
  -> DDS serialization / RTPS transport, normally UDP/IP
  -> B2-side network -> Ethernet -> Jetson eth0
  -> CycloneDDS -> Unitree SDK2 subscription -> our RobotState

Our future live planner/tracker + command authority/watchdog
  -> Unitree SDK2 high-level velocity request
  -> CycloneDDS / RTPS -> IP -> Ethernet -> B2 service
  -> existing walking/balance control -> robot's actuator system
```

SDKはアプリから呼ぶライブラリで，別の計算機ではない．DDSが相手の発見と型の決まったデータ交換を扱い，
Ethernet・IPが通信を運ぶ．`ping`が通っても，DDSで発見できることや，サービスの互換性は確認できない．
DDSのインターフェース・ドメイン，メッセージの定義，発見方法，QoS，ファイアウォールを実際の構成に合わせる．
サービスの物理的な実行先，内部の転送，アクチュエーターのバスは未確認である．公開された上位APIから
内部IP，周期，バスの方式を推定で決めない．

ROS 2もRMW実装を介してDDSを使える．したがって，SDK→ROS 2→機体という直列の経路が必須なのではない．
外付け側からSDK2を直接使える．内蔵ROS 2ノードが有用な情報を出していれば，互換性のある方法で購読するか，
目的を限定した接続部を用意する．既存の内蔵ROS 2サービスは維持する．
[Unitreeの相互運用ガイド](https://github.com/unitreerobotics/unitree_ros2)と
[ネットワーク設定](../explanations/network-topology.ja.md)を参照する．

LinuxのDockerの既定のブリッジは，DDSの発見を複雑にすることがある．将来の機体向けコンテナでは，
ホストのネットワークを使い，DDSを確認済みの機体側インターフェースへ限定する方法が候補になる．
[host networking](https://docs.docker.com/engine/network/drivers/host/)はホストとネットワークを共有し，
管理側のインターフェースも見えるため，発見方法とインターフェースを意図して設定する．
現在のオフライン検査では有効にしない．別案として，観測・制御をホストで行い，推論を隔離したコンテナへ
置くなら，画像・状態・時刻・計画を受け渡すIPCの仕様が必要になる．どちらの実時間構成も未実装であり，
ドライバと時刻の実測を踏まえて選ぶ．

### センサー経路は配線で決まる

- ZED 2iを外付けJetsonへUSB接続する場合は，ホストのUSBアクセス→互換性のあるZED SDK・Pythonバインディング
  →RGB画像となる．Docker内で使うなら，合うSDKとデバイス権限を明示的に用意する．
  ホストに導入済みでも，イメージ内に自動で現れない．
- ZEDを内蔵PCへつなぐ別構成なら，その計算機から映像を取り出す必要がある．通信方式，圧縮，時刻，
  カメラと機体の座標変換を定める．B2へEthernetを挿すだけで，USBのデータが転送されるわけではない．
- Mid-360は，Ethernetのセンサーパケット→実際の接続先のホスト・ドライバ→必要に応じて点群・自己位置となる．
  本プロジェクトに直接のLiDAR入力部はなく，センサーを付けるだけで深度・障害物処理が追加されるものではない．

到達できた内蔵Intel i7では，一時的なROS 2プログラムから状態・映像へアクセスできた．モデル推論は外付けJetson，
歩行・バランスは既存の動作制御系が担当する．内部全体の基板構成と，外付けからの直接DDS経路は未確定である．
直接接続・中継を選ぶ前に，[実際の通信の順序](../explanations/network-topology.ja.md)を参照する．
