# 外付けZEDカメラの準備

[English](camera-runtime.md) · [文書一覧](../README.ja.md) · [現地カード](../how-to/field-card.ja.md)

> 文書種別：**参照資料**．

本書は段階ごとのcamera構築証拠を残す．現在の操作は[推論と表示](../how-to/run-camera-demo.ja.md)，
後のlive shadow結果と残る制限は[マイルストーン](../records/milestone-2026-11-03.ja.md)を参照する．
初期の「未検証」はその検査の範囲であり，後続実験が存在しないという意味ではない．

## 現在の確認結果

この結果・経緯は[記録](../records/camera-checks.ja.md)を参照する．

## ファイル・依存・隔離

SDKはカメラを扱うネイティブのソフトウェアで，`pyzed`はそれをPythonから呼ぶ部品である．
wheelだけではネイティブSDKを代替できない．公式の
[Python API手順](https://docs.stereolabs.com/docs/development/api-languages/python)を参照する．

| 要素 | 確認した入力 |
|---|---|
| 既存イメージ | `vln-b2-runtime:jp5`，ID `sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a` |
| ネイティブSDK | 既存ホストの`/usr/local/zed`，4.1.2，読み取り専用で渡す |
| Python API | 公式`pyzed-4.1-cp311-cp311-linux_aarch64.whl`，762,664バイト，SHA256 `677d95054027aa1d332e92af5f8228de62f9ab32d1a4a17c9d2cc4a6e309848f` |
| 宣言された依存 | PyPIのCython 3.0.12，ARM64・CPython 3.11 wheel，3,444,055バイト，SHA256 `dfdbea486e702c328338314adb8e80f5f9741f06a0ae83aaec7463bc166d12e8` |
| 非公開の配置先 | `local/camera-runtime/attempt-01/python`．コンテナで明示した`PYTHONPATH`だけに使う |
| 追加のネイティブlibrary | ホスト既存の`libturbojpeg.so.0`だけを読み取り専用で渡す．このイメージにはなかった |

bindingのwheelにはMITライセンスがあり，CythonはApache-2.0を宣言する．ネイティブSDKの条件は別に維持する．
SDK，wheel，撮影画像，メーカーのモデルは本レポで配布しない．
[依存の固定ファイル](../../deploy/zed-camera-requirements.lock)に二つのソフトウェアを記録した．深度・AIモデルは取得・有効化していない．

実際の導入はネットワークなし・CPU専用コンテナで，照合したローカルwheelを`pip --no-deps --target`で
配置した．通常の研究用UIDで，非公開の配置先だけへ書き込む．GPUイメージ，ホストPython，プロジェクトvenvは
変更していない．Cythonはbindingが宣言する依存を満たす．NumPyはbindingの要求どおり2.0未満に維持する．
来歴，wheel，importのログはJetsonのGit対象外`local/camera-runtime/attempt-01`に残す．

## 非公開のPython配置先を再構築する

一致するJetsonに確認済みイメージがある場合，新しい配置先へ次の手順で固定した二つのソフトウェアwheelだけを
Stereolabs・PyPIから取得できる．import・撮影と違い，この明示的な導入だけはnetworkを使うが，
SDK，カメラ，ホーム，モデルは公開しない．新しい保存先を選び，導入報告を維持する．既存先なら`mkdir`が失敗する．

```sh
mkdir -p local/camera-runtime
mkdir -m 700 local/camera-runtime/rebuild-01
sudo docker run --rm --pull never --runtime runc --network bridge --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/local/camera-runtime/rebuild-01,dst=/camera" \
  --mount "type=bind,src=$(pwd)/deploy/zed-camera-requirements.lock,dst=/spec/requirements.lock,readonly" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3.11 \
  vln-b2-runtime:jp5 -m pip install --only-binary=:all: --require-hashes \
  --no-deps --no-compile --target /camera/python \
  --report /camera/install-report.json -r /spec/requirements.lock
```

以下のimportコマンドでは`attempt-01/python`の代わりに新しい配置先を使い，同じコンテナ環境で
`python3.11 -m pip check`も実行する．lockはイメージ内のNumPy・Torchを置き換えない．
SDK，Python ABI，L4Tが違う場合は，既存環境を上書きせず別に互換性を確認する．

## import確認の再現

準備済みJetsonのプロジェクトルートで実行する．

```sh
sudo docker run --rm --pull never --runtime nvidia --network none --read-only \
  --user "$(id -u):$(id -g)" \
  --group-add "$(stat -c '%g' /dev/nvmap)" \
  --group-add "$(stat -c '%g' /usr/local/zed)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/local/camera-runtime/attempt-01/python,dst=/camera-api,readonly" \
  --mount type=bind,src=/usr/local/zed,dst=/usr/local/zed,readonly \
  --mount "type=bind,src=$(readlink -f /usr/lib/aarch64-linux-gnu/libturbojpeg.so.0),dst=/camera-libs/libturbojpeg.so.0,readonly" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/camera-api \
  -e LD_LIBRARY_PATH=/camera-libs:/usr/local/zed/lib:/usr/local/cuda/lib64:/usr/lib/aarch64-linux-gnu/tegra \
  --entrypoint python3.11 vln-b2-runtime:jp5 \
  -c 'import pyzed.sl as sl; print(sl.Camera.get_sdk_version())'
```

追加した二つの数値グループはコンテナ内だけに存在する．SDKのマウントは，グループの権限にかかわらず
読み取り専用である．ホストのlibraryディレクトリ全体を重ねず，実際に起きた`libturbojpeg.so.0`の
import失敗を一つのlibraryで解決した．NVIDIA runtimeがメーカーのGPUインターフェースを供給する．
このimport試験ではUSB・video deviceを明示的に渡さず，撮影しない．

## カメラ実物の初回確認

1. 外付けZED 2iをJetsonのUSBへ直接接続する．`lsusb`，`lsusb -t`，新しいvideo nodeを調べ，
   実際の接続速度と機器の識別を確認する．
2. 取得用コンテナには，特定したカメラのnodeと必要なdeviceグループだけを渡す．
   `--privileged`や，無関係なUSB機器の公開は行わない．
3. 既存SDKを読み取り専用に保ち，カメラ設定・校正には非公開の書き込み先を用意する．接続したカメラの
   校正が既にあるか，公式の取得が必要かを確認する．RGB取得のためにAI深度を勝手に有効化したり，神経モデルを取得したりしない．
4. プロセスの時間上限を設けて左の補正済みRGBを一枚取得し，写る場面，向き，露出，元の時刻・受信時刻を
   確認する．B2接続は不要である．その後，実観測を保存してオフラインのモデル入力へ使う．

初回のdevice割当，校正，実際の取得は上記のとおり通った．再接続後はnodeを調べ直す．固定名とは扱わない．ホストvenvにはbindingを入れていないため，
既存の汎用`camera` CLIもこの準備済みコンテナで使い，ホストのコマンドがそのまま動くとは扱わない．
B2状態受信とモーター指令は後の別の検査であり，USBカメラの成功だけで機体を動かせる状態とは判断しない．
