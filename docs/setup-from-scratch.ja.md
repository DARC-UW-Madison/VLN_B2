# JetsonでTIC-VLAを動かすための初期構築

[English](setup-from-scratch.md) · [ドキュメント](README.ja.md) · [実行と表示](run-camera-demo.ja.md)

## 1．一般的なPython導入ではなく，対応する機体から始める

未準備のJetsonからカメラ実習までの順序を示します．確認済みは
**Jetson AGX Orin 64 GB，ARM64，JetPack 5.1.2／L4T 35.4.1，Ubuntu 20.04，CUDA 11.4**です．
別のJetPack，PC用GPU，Macでそのまま使えるという意味ではありません．B2は接続しません．

本当に空の機器なら，モジュール・キャリアボード・ストレージを特定し，研究室が承認した
OSを選びます．[NVIDIAのJetPack 5.1.2資料](https://developer.nvidia.com/embedded/jetpack-sdk-512)に
対応リリースと書き込み方法があります．書き込みは破壊的操作で，対応するUbuntu x86ホストが
必要な場合があります．MacからのSSHはOS書き込み手段ではありません．現在の共有Jetsonは
初期化せず，PC向けGPUドライバも使いません．今回の作業は既存OSとZED SDKを再利用しており，
**新規フラッシュや保存版のネイティブSDK再導入は実施していません**．

研究用アカウント，現地復旧手段，安定した電源を準備します．SSH，任意のTailscale／RDPは
[導入手順](jetson-bootstrap.ja.md)と[構成一覧](system-overview.ja.md)を参照します．
管理用接続であって，推論の依存条件ではありません．起動時接続にGUI自動ログインは不要です．
Wi-Fi認証，アドレス，ホスト鍵，アカウント設定は公開しません．

## 2．確認済みソースを配置し，ストレージを調べる

ソースは研究室のリポジトリ[DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2)で公開しています．
確認済みの固定コミットを`~/Developer/Projects/Robotics/b2/VLN_B2`へcloneし，動き続けるブランチではなくそのコミットをcheckoutします．
機器がGitHubへ接続できない場合は，管理者から確認済み`git archive`とコミット・ハッシュを受け取り，同じ場所へ展開します．
Macのvenv，生の研究記録，SSH認証，上流コード，モデルキャッシュをアーカイブに混ぜません．
配置したソースのコミットを機器側の非公開記録に残します．

```bash
umask 077
cd ~/Developer/Projects/Robotics/b2/VLN_B2
mkdir -p local
python3 tools/inspect_target.py --output local/initial-inventory.json
cat /etc/nv_tegra_release
findmnt /mnt/b2-research
df -h / /mnt/b2-research
sudo docker info --format '{{.DockerRootDir}} {{json .Runtimes}}'
stat -c '%g' /dev/nvmap
```

調査スクリプトはPython 3.8以上の標準ライブラリだけなので，venv作成前でも使えます．
本体は3.10以上，コンテナ内は3.11.18です．ホストのpyenv／venvは開発・テストには便利ですが，
推論プロセスへCUDA，ZED，モデル依存を供給する仕組みではありません．

参照機にはOS用64 GB eMMCと，大きな研究資材用の**2 TB NVMe SSDが1台**あります．
3.83 GBの取得と3.77 GBの変換物だけでなく，Torchコンパイル，wheel，イメージ層，ログの
容量も見積もります．eMMCだけで十分とは考えず，実測空き容量とビルド中の使用量を確認します．

専用領域がなければ[実行環境の記録](jetson-runtime.ja.md)のストレージ手順に従い，
既存データの所有者，マウント識別子，Docker移設，マウント確認を扱います．
一般的なフォーマットコマンドではなく，機器ごとの判断が必要です．現在の専用配置は次のとおりです．

| パス | 内容と作成担当 |
|---|---|
| `/mnt/b2-research/VLN_B2/docker` | Docker保存先．管理者がdaemonとマウント確認を設定 |
| `/mnt/b2-research/VLN_B2/huggingface` | 研究用所有のキャッシュ親．`~/.cache/huggingface`の接続先 |
| `~/.cache/huggingface/hub` | 公式クライアントが作るHubリポジトリ・blob保管先 |
| `/mnt/b2-research/VLN_B2/models` | 研究用所有の派生物．プロジェクトの`models`が参照 |
| `local/` | 実験画像，結果，wheel，ログ．Git対象外 |

既存キャッシュや`models`をリンクで上書きしません．新規機では管理者が書き込み可能な専用領域を作り，
既存配置と接続先を調べてからリンクを作ります．以前の保存先は残します．
今回のext4ジャーナル回復への承認は，別ディスクの修復・消去を許可するものではありません．

## 3．DockerとホストGPUの境界を準備する

調査時点でDockerとNVIDIA runtimeは既に存在し，一般的なDocker／NVIDIA環境を
最初から導入したわけではありません．新規ホストでは
[NVIDIAのJetsonコンテナ資料](https://developer.nvidia.com/embedded/jetson-cloud-native/)に従い，
Docker engineとJetPackに対応するNVIDIA container runtimeを先に準備します．
SSD保存先を追加する際も既存daemon設定を保ちます．`docker info`に`nvidia`があり，
`/dev/nvmap`とホストCUDAが必要です．不足ならここで止めます．pipのTorch導入では
ホストGPUドライバの欠落は解決しません．

長いビルドの前に[ネイティブCUDA検査](jetson-runtime.ja.md#ホスト上のcuda確認)を実施し，
次の2段階をビルドします．ビルド時の通信はソフトウェア取得用で，モデル取得とは別です．
Python，Torch，torchvisionをイメージ層へ構築する作業であり，推論もB2の移動も始めません．

```bash
sudo env DOCKER_BUILDKIT=0 docker build --target python   -f deploy/jetson-runtime.Dockerfile -t vln-b2-python:jp5 .
sudo docker run --rm --pull never --runtime nvidia --network none \
  --user "$(id -u):$(id -g)" --group-add "$(stat -c %g /dev/nvmap)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --cpus 2 --pids-limit 128 --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m vln-b2-python:jp5
sudo env DOCKER_BUILDKIT=0 docker build --target runtime   -f deploy/jetson-runtime.Dockerfile -t vln-b2-runtime:jp5 .
sudo docker run --rm --pull never --runtime nvidia --network none \
  --user "$(id -u):$(id -g)" --group-add "$(stat -c %g /dev/nvmap)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 4g --cpus 2 --pids-limit 128 --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  -e HOME=/tmp -e CUDA_CACHE_PATH=/tmp/cuda vln-b2-runtime:jp5
```

両検査が終了コード0と成功JSONになることを確認し，出力とイメージIDを非公開で保存します．
Python段階は処理系とGPUの認識，runtime段階はFP32／BF16の実計算を確認します．
CUDA 11.4，sm_87，Torch 2.2.2，torchvision 0.17.2，Python 3.11.18です．
Glooを残し，未使用RPCの互換性問題をハッシュ検査付きパッチで処理します．
これは古いTorchのチェックポイント読込脆弱性を直すパッチではありません．

ソース・ベースのdigestと直接依存は固定していますが，Pythonの間接依存とAPTは完全な
不変ロックではありません．再構築時の解決結果とイメージIDは変わり得ます．
一覧，`pip check`，smoke，実モデルの厳密読込を検証し，バイト単位の再現性を保証しません．
wheel，コンパイル，層の意味は[ビルドの基礎](build-fundamentals.ja.md)を参照します．

## 4．別管理のモデル実装を配置する

[利用条件](licensing.ja.md)と[第三者資材](../THIRD_PARTY.ja.md)を先に確認します．
必要な研究室承認後，上流の固定版をこのレポの外へ取得します．以下は新しい外部checkout用で，
既存パスでは止まります．既存checkoutは置換せず調べます．

```bash
UPSTREAM="$HOME/Developer/External/TIC-VLA"
mkdir -p "$HOME/Developer/External"
mkdir "$UPSTREAM"
git -C "$UPSTREAM" init
git -C "$UPSTREAM" remote add origin https://github.com/ucla-mobility/TIC-VLA.git
git -C "$UPSTREAM" sparse-checkout init --no-cone
git -C "$UPSTREAM" sparse-checkout set /ticvla/ /LICENSE.md /pyproject.toml
git -C "$UPSTREAM" fetch --depth 1 origin 9fa6f8b66b9e121d5df5df071297bba8e5353ebb
git -C "$UPSTREAM" checkout --detach FETCH_HEAD
test "$(git -C "$UPSTREAM" rev-parse HEAD)" = 9fa6f8b66b9e121d5df5df071297bba8e5353ebb
```

ライセンス，パッケージ定義，実行するモデルPythonを確認します．上流の学習用依存を
一括導入せず，確認済みの推論環境を使います．上流ソースをこのレポのMIT対象へコピーしません．
ソースがモデルの構造を，重みが学習済みの数値を与えます．名前やimport成功だけでは両方は揃いません．

## 5．承認したモデルファイルだけを取得する

参照実験は公式Hugging Faceクライアントで17ファイル，3,827,163,803バイトを取得しました．
TICのdataset版`671de608f39ccae41b66cbb24ab923c0275f8fb4`から1ファイル，
InternVL3-1B版`4415a3b810e636d11dfa86b0e9ba40bb00535aa8`から16ファイルです．
名前，ハッシュ，容量，条件は[モデル資材](model-artifacts.ja.md)にあります．
今回の非公開学術試用は承認済みですが，別の導入先では条件と保存先を確認します．
その確認前に取得ブロックを実行しません．

最初の行は計画表示だけです．残りは明示的に取得して全ファイルを検証します．
新しいレポート先を使います．`--cache`は親の`HF_HOME`ではなく**Hubサブフォルダ**です．
モデル処理のうちここだけ通信が必要で，ホーム内の認証情報やGPUは渡しません．

```bash
python3 tools/acquire_model_assets.py
HUB="$(readlink -f "$HOME/.cache/huggingface")/hub"
mkdir -p "$HUB"
mkdir -m 700 local/model-acquisition-02
sudo docker run --rm --pull never --runtime runc --network bridge --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --cpus 2 --pids-limit 128 --tmpfs /tmp:rw,nosuid,nodev,size=128m \
  --mount "type=bind,src=$PWD/tools/acquire_model_assets.py,dst=/tools/acquire.py,readonly" \
  --mount "type=bind,src=$HUB,dst=/hub" \
  --mount "type=bind,src=$PWD/local/model-acquisition-02,dst=/reports" \
  -e HOME=/tmp -e HF_HOME=/tmp/hf -e HF_HUB_OFFLINE=0 \
  -e HF_HUB_DISABLE_TELEMETRY=1 -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
  -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3.11 \
  vln-b2-runtime:jp5 /tools/acquire.py --download \
  --cache /hub --report /reports/assets.json
```

`assets.json`で17ファイルと合計容量の検証成功を確認します．latestの利用，未承認ファイルの
追加，推論中の隠れた取得はしません．基盤snapshotには重み・tokenizer・設定のほかPythonコードも
あるため，オフラインでも確認済みのローカルコードは実行されます．

## 6．古いチェックポイントを別のCPU環境で変換する

元の`.ckpt`をGPU用Torch 2.2.2で復号しません．`weights_only=True`でも不十分です．
新しいCPU専用converterを構築し，[変換ガイド](checkpoint-conversion.ja.md)の生成fixtureと
旧環境でのtensor読戻しを確認してから実資材を変換します．出力先は未作成である必要があります．
**準備済みの現機では変換を省略し，既存結果のハッシュを確認します**．

```bash
sudo env DOCKER_BUILDKIT=0 docker build --pull=false \
  --build-arg BASE_IMAGE="$(sudo docker image inspect vln-b2-python:jp5 --format '{{.Id}}')" \
  -f deploy/checkpoint-converter.Dockerfile -t vln-b2-converter:cpu-v1 .
TIC_REV=671de608f39ccae41b66cbb24ab923c0275f8fb4
SOURCE="$(readlink -f "$HUB/datasets--handsomeYun--TIC-VLA/snapshots/$TIC_REV/TIC-VLA-model.ckpt")"
SOURCE_SHA=376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036
MODELS="$(readlink -f models)"
test -d "$MODELS"
test ! -e "$MODELS/tic-vla-671de608-01"
sudo docker run --rm --pull never --runtime runc --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 32g --cpus 2 --pids-limit 128 --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --mount "type=bind,src=$PWD/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$SOURCE,dst=/input/source.ckpt,readonly" \
  --mount "type=bind,src=$MODELS,dst=/models" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/workspace/src \
  --entrypoint timeout vln-b2-converter:cpu-v1 -k 5s 1200s \
  python -m b2_tic_vla.checkpoint_conversion \
  /input/source.ckpt /models/tic-vla-671de608-01 \
  --expected-sha256 "$SOURCE_SHA" --repository handsomeYun/TIC-VLA \
  --repository-type dataset --revision "$TIC_REV"
printf '%s  %s\n'   2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4   "$MODELS/tic-vla-671de608-01/model.safetensors" | sha256sum -c -
```

元SHA256を検証し，CPUの制限付き読込で全1,324 tensor名を保ち，バイト単位の読戻しを確認します．
safetensorsは3,773,492,276バイトです．aliasを実体化したため元より大きくなります．
形式変換であって追加学習や再配布許可ではありません．古いGPU Torchにはsafetensorsだけを渡します．
変換履歴JSON，原本，変換物はGit対象外です．

## 7．ネイティブZEDソフトウェア，binding，校正を準備する

新規ホストではベンダーの公式保存版／サポートから，**L4T 35.4.1に対応するZED SDK 4.1.2**を
入手します．[StereolabsのJetson導入資料](https://docs.stereolabs.com/docs/development/zed-sdk/linux/work-with-nvidia-jetson)に従い，
対応L4Tと利用条件を確認します．別JetPack向けの最新版で代用せず，保存版URLを捏造しません．
同じinstallerが入手できなければベンダーと確認する段階で止めます．記録だけで無人の新規導入まで
保証できません．AI／深度モデルを自動取得しません．現機は`/usr/local/zed`の4.1.2と既存校正を
再利用し，所有者やホストのグループ所属を変更していません．

[カメラ構築の具体的コマンド](camera-runtime.ja.md#非公開のpython配置先を再構築する)で
ハッシュ固定した2つのPython wheelを**新しい専用prefix**に導入します．
`local/camera-runtime/rebuild-01/python`ができるので，実行ガイドの`CAMERA_API`を合わせます．
NumPyは推論イメージが供給します．system Pythonへ入れず，venv内にもあると考えません．

必要なら公式ツールでカメラを確認し，機器に一致する工場校正を探します．
検証したファイルだけを，名前を保って新しい専用領域へコピーします．これはAIモデルではありません．
不足時は公式手段で取得し，シリアル一致を確認してから続けます．別個体の校正は使いません．

```bash
mkdir -m 700 local/camera-settings-01
CALIBRATION_FILE=/path/to/verified/matching-camera-calibration.conf
test -f "$CALIBRATION_FILE"
sudo install -m 600 -o "$(id -u)" -g "$(id -g)"   "$CALIBRATION_FILE" "local/camera-settings-01/$(basename "$CALIBRATION_FILE")"
```

実行ガイドの`CAMERA_SETTINGS`を新しい領域に合わせます．既存の`libturbojpeg.so.0`を使い，
新規ホストに不足する場合は管理者が対応するUbuntu ARM64版`libturbojpeg0`のAPT変更計画を
確認して導入します．無関係なライブラリフォルダを丸ごと公開しません．

## 8．実行と表示を確認してから次へ進む

[カメラ実習](run-camera-demo.ja.md)で，USB識別，JPEG撮影，厳密なモデル読込，XY予測，HTML作成，
表示まで進めます．実行可能なDockerコマンドと全入力・出力の意味があります．
この推論成功が，先のモデルなしsmokeを超えた，実モデルのGPU読込確認にもなります．

開発する場合はPython 3.10以上でホストの単体テストを実行します．現機では専用3.11 venvを使います．
システム処理系の置換は不要です．テストは合成入力や模擬ライブラリなので，走行性能は証明しません．

カメラ・モデルの検査後に，[現地カード](field-card.ja.md)と別構築の
[Unitree環境](unitree-runtime.ja.md)でB2のEthernet・状態確認へ進みます．
SDK用コンテナは推論と独立です．ROS 2は任意で，この経路には不要です．
指令送信を実装・有効化する前に，内蔵サービス，操作権，座標・時刻，停止，実状態でのshadow試験が残ります．

新規機での再現に残る点も含め，実際に実行した事実は
[2026-11-03マイルストーン](milestone-2026-11-03.ja.md)を参照します．

一枚の合格後は[短い操作デモ](live-camera-demo.ja.md)の確認・起動・表示・終了コマンドで
カメラ予測の更新を確認する．
