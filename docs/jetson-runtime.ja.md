# Jetsonの実行環境構築

[English](jetson-runtime.md) · [進捗](status.ja.md) · [互換性](runtime-compatibility.ja.md)

ホスト側のツールとモデル用コンテナを分けて構築する．既存のUbuntu 20.04／L4T 35.4.1，
CUDA，ROS，ZEDを維持する．この段階では機体への接続やモデルファイルを必要としない．

## ホストの作業領域とPython

監査済みのソースアーカイブを，外付けJetsonの`~/Developer/Projects/Robotics/b2/VLN_B2`へ転送した．
Gitの認証情報や別の機器の仮想環境は含まない．以降はこのディレクトリで作業する．専用ログインでは次を使う．

| 場所 | 用途 |
|---|---|
| `~/Developer/External/pyenv` | 公式pyenvのソース．`3fb25668b463ad38ac2db6092dbf476ef744c0ca`（`v2.8.14`）に固定 |
| `~/Developer/Environments/pyenv` | ユーザー用インタープリタの導入先 |
| `.venv/` | 本プロジェクト専用のPython依存先．Git管理外 |
| `local/` | ビルド成果物，ログ，非公開の調査記録．Git管理外 |

ホストのアプリ用インタープリタとして[CPython 3.11.18](https://www.python.org/downloads/release/python-31118/)を導入した．
公式の[pyenvのビルド定義](https://github.com/pyenv/pyenv/blob/3fb25668b463ad38ac2db6092dbf476ef744c0ca/plugins/python-build/share/python-build/3.11.18)により，
ソースアーカイブのチェックサムを確認する．Python 3.10はサポートが終了しており，パッケージの最低版を
新規環境の採用版と同一視しない．ホストでのビルドに必要な`libbz2-dev`，`libncurses-dev`，
`libreadline-dev`だけを追加し，既存パッケージの更新・削除は行っていない．システムPythonとシェルの
起動設定は置き換えない．ソースのビルドは並列数4に制限する．

調査したホストの新しいアカウントでは，次の手順で構築できる．pyenvの二つの保存先が既にある場合は
停止し，既存のツールを置き換えない．

```sh
sudo apt-get install -y --no-upgrade --no-install-recommends libbz2-dev libreadline-dev
mkdir -p "$HOME/Developer/External" "$HOME/Developer/Environments" local/python-build/tmp
git clone --depth 1 --branch v2.8.14 https://github.com/pyenv/pyenv.git \
  "$HOME/Developer/External/pyenv"
test "$(git -C "$HOME/Developer/External/pyenv" rev-parse HEAD)" = \
  3fb25668b463ad38ac2db6092dbf476ef744c0ca && \
  env PYENV_ROOT="$HOME/Developer/Environments/pyenv" \
    PYTHON_BUILD_MIRROR_URL_SKIP=1 MAKE_OPTS=-j4 \
    TMPDIR="$PWD/local/python-build/tmp" \
    "$HOME/Developer/External/pyenv/bin/pyenv" install 3.11.18
```

ユーザー用インタープリタのビルド完了後，既存の`.venv`がない場合だけ専用環境を作る．

```sh
"$HOME/Developer/Environments/pyenv/versions/3.11.18/bin/python3" -m venv .venv
PYTHONPATH=src .venv/bin/python -m b2_tic_vla replay
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/b2-tic-vla --help
```

この環境は独自に作成したツールを動かすもので，PyTorch，ZEDのバインディング，Unitree SDKを
導入したり，それらの互換性を確認したりするものではない．
2026-10-27に，圧縮，SSL，SQLite，ctypes，readlineのimportと，Jetsonのvenvでの全85件のテスト・
合成データの再生が成功した．これらのテストは，メーカーの接続部には引き続きモックを使う．
編集可能なパッケージ導入，CLIのヘルプ，`pip check`も通った．

管理者権限で既存ZED SDKのヘッダを読むと**4.1.2**で，共有ライブラリとバインディング用の
導入スクリプトも存在する．導入先はモード`0770`で，研究用ログインには閲覧権限がない．
権限は変更していない．カメラを接続する際に，アクセス方法か互換性のあるセンサー用の隔離環境を
整える．ヘッダの存在は，撮影やPythonバインディングの動作確認ではない．

## ホスト上のCUDA確認

独立した確認用プログラムがGPUに小さなバッファを三つ確保し，256個のFP32要素について
`output = 2 * x + y`を計算する．同期後，全要素をCPUの計算結果と比較する．性能評価やモデルの試験ではない．

```sh
mkdir -p local/native-smoke
timeout -k 5s 60s /usr/local/cuda/bin/nvcc -O2 -arch=sm_87 \
  deploy/cuda-smoke.cu -o local/native-smoke/cuda-smoke
timeout -k 5s 30s ./local/native-smoke/cuda-smoke
```

2026-10-27に外付けJetsonで成功した．compute capabilityは8.7，driver／runtime APIは11040，
最大絶対誤差は0だった．同じバイナリは，固定したNVIDIA基底コンテナ内でも，`--runtime=nvidia`と
`--network=none`で成功した．BF16・PyTorchの実行とナビゲーションは引き続き未検証である．

## 保存先の前提

既存の2 TB SSDには，割り当て済みのデータが約1 TBある．書き込みを伴わない調査のため，
`ro,noload,nodev,nosuid,noexec`で接続し，一般ユーザーが使える空きは約946 GBだった．
superblockには`needs_recovery`がある．[カーネル文書](https://docs.kernel.org/admin-guide/ext4.html)では，
通常の読み取り専用マウントでもext4のジャーナルを再生する場合があり，`noload`で再生を抑止すると説明される．
操作者の明示的な許可後，通常の書き込み可能なマウントでジャーナルを再生し，ext4のエラーは
観測されなかった．新しい`/mnt/b2-research/VLN_B2`を作り，既存の内容を残した．

保存先の準備手順は次のとおりである．

1. 既存データの管理者とバックアップ・復旧方法を確認し，ジャーナルの復旧と書き込み可能なマウントの
   明示的な許可を得る．
2. フォーマットやデータの削除をせず通常の方法でマウントし，`/mnt/b2-research/VLN_B2`などの
   新しい専用ディレクトリを作る．ファイルシステムのエラー時は停止し，強制マウントや自動修復は行わない．
3. Dockerのコンテナ・イメージ・volumeがないことを再確認する．旧保存先を残して設定をバックアップする．
   現地で確認したファイルシステムの識別情報でSSDのマウント設定を追加する．識別情報はGitへ入れない．
4. 新しいDocker保存先をSSDの専用ディレクトリへ向け，NVIDIAランタイムの設定を維持する．
   サービスのマウント依存とマウントポイントの検査を加え，SSDがないときにルートへ書き込まないようにする．
   設定を検査し，Docker再起動後に保存先とランタイム登録を確認する．失敗時は保存した設定へ戻し，両方の保存先を残す．

切り替え前のDockerには，コンテナ・イメージ・volumeがなかった．現在の保存先は
`/mnt/b2-research/VLN_B2/docker`で，再起動後のNVIDIAランタイム登録とOS側の空き約20 GBを確認した．
旧保存先は残している．設定のバックアップは`/etc/docker/daemon.json.before-vln-b2`と
`/etc/fstab.before-vln-b2`，起動時の検査は`/etc/systemd/system/docker.service.d/vln-b2-storage.conf`にある．
アカウントのグループは変更せず，OSの再起動はしていない．標準の`~/.cache/huggingface`は
SSDの新しい空のディレクトリへ接続した．モデルは取得していない．

## コンテナのビルドとモデル不要の確認

準備したDockerfileは，L4Tに対応する基底イメージのdigestとPython／Torch／torchvisionのソースを
固定している．Python段階はビルドでき，オフラインの検査でPython 3.11.18，ARM64，CUDAデバイス1台を確認した．
Torchを含む段階は別のソースビルド候補である．直接依存の固定は，推移的依存まで含む完全なlockではない．
ビルド成功時はDebianとPythonのパッケージ一覧をイメージ内に保存する．解決後のイメージIDとログは
ローカルの実験記録に残す．保存先を準備した後，軽いPython段階から始める．

```sh
sudo docker build --target python -f deploy/jetson-runtime.Dockerfile \
  -t vln-b2-python:jp5 .
sudo docker run --rm --pull=never --runtime=nvidia --network=none \
  vln-b2-python:jp5
sudo docker build --target runtime -f deploy/jetson-runtime.Dockerfile \
  -t vln-b2-runtime:jp5 .
sudo docker run --rm --pull=never --runtime=nvidia --network=none \
  vln-b2-runtime:jp5
```

最初の確認はPython 3.11とCUDAドライバ・デバイスの可視性，次はTorch／visionの版と実際の
FP32／BF16のGPU演算を調べる．いずれもモデルを読み込まない．任意の`--stage full`は，版と条件を
確認した上流チェックアウトを読み取り専用で接続してimportするが，モデルは作らない．
カメラ，ロボットのデバイス，モデルキャッシュ，Dockerソケットは，これらの試験へ接続しない．

上流のソースはプロジェクト外の`~/Developer/External/TIC-VLA`に置き，
`9fa6f8b66b9e121d5df5df071297bba8e5353ebb`へ固定した．sparse checkoutではPythonパッケージ，
ライセンス，パッケージ情報だけを選び，モデルのblobは選んでいない．Torchの検査が通った後，
この確認済みソースを使って任意のimport検査を行う．

```sh
sudo docker run --rm --pull=never --runtime=nvidia --network=none \
  --mount type=bind,source="$HOME/Developer/External/TIC-VLA",target=/opt/upstream,readonly \
  vln-b2-runtime:jp5 python3.11 /opt/runtime-smoke.py \
  --stage full --upstream-root /opt/upstream
```

**旧Torchの候補では，チェックポイントの読み込みは保留する．** 公表済みの脆弱性を修正するか，
別の変換・読込経路を検証してから外部の重みを使う．モデル取得では，対象ファイル，版，条件，
容量，公式キャッシュの保存先を別途確認する．重みは未取得である．[互換性の制約](runtime-compatibility.ja.md)を参照する．
