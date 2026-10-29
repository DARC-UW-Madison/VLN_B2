# 外付けZEDカメラの準備

[English](camera-runtime.md) · [文書一覧](README.ja.md) · [現地カード](field-card.ja.md)

## 現在の確認結果

2026-10-29に，Jetson既存のheader・libraryからZED SDK 4.1.2を確認した．SDKは既存の研究室用
ログインとSDKグループの所有で，研究用ログインにはアクセスがなく，研究用venvにも`pyzed`はなかった．
ホストの権限，所属グループ，Python環境は維持した．

別の非公開Python配置先に，ARM64・CPython 3.11用の公式`pyzed` 4.1とCython 3.0.12を置いた．
NumPy 1.26.4は既存GPUイメージを使う．オフラインの非rootコンテナで`pyzed.sl`をimportし，
SDK 4.1.2，`DEPTH_MODE.NONE`，`optional_settings_path`を確認し，`pip check`も通った．
カメラは開いていない．この調査時点ではZED・video deviceは存在しなかった．import成功はUSB取得，校正，画質の検証ではない．

### 最初の実画像取得が成功

その後接続された機器をZED 2i一台と確認した．映像側は5 Gbpsで接続し，V4L2のnodeが二つ存在した．
付属のHID・USB側も別に割り当て，特定したカメラのnodeだけをコンテナへ渡した．対応する既存の
1,568バイトの校正を非公開の設定先へコピーし，元のSDKは変更せず，校正・モデルの取得も不要だった．
深度を無効にしてプロジェクトのカメラアダプターから1280×720の左の補正済みJPEGを取得し，
196,592バイトを保存して45秒上限の監視内に正常終了した．画像を目視し，上下が正しく空白でないことを
確認した．机上の場面であり，機体へ取り付けた状態のナビゲーション画像ではない．元・受信時刻を別に記録し，
撮影時計の対応は引き続き未検証である．

生画像，serial番号，正確なdevice割当はGit対象外の非公開記録へ置く．CLIの`camera`と`record`に
`--settings-dir`を追加し，別の書き込み可能なマウントへ校正を分離できるようにした．


別の短い連続取得試験では，**SDKのgrabが90/90回成功**し，失敗は0回だった．最初と最後の受信は
2.968秒の間隔で，約29.99 grabs/s，元の時刻は単調増加だった．各フレームを画像へ符号化・保存する
ループではないため，JPEG保存性能や長時間の信頼性の試験ではない．時計の対応，取付後の校正，
ライブ推論は未検証である．後の確認では任意のHID nodeがなくなっていたが，映像・USB側は存在し，
そのnodeだけで連続取得が成功した．SDK使用・再接続後は，古い名前を維持せず実際のdeviceを再確認する．

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
[依存の固定ファイル](../deploy/zed-camera-requirements.lock)に二つのソフトウェアを記録した．深度・AIモデルは取得・有効化していない．

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
