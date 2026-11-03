# ZED画像をTIC-VLAに入力し，予測経路を表示する

[English](run-camera-demo.md) · [ドキュメント](README.ja.md) · [初期構築](setup-from-scratch.ja.md)

## 1．この実習で行うこと

ZED 2iを**外付けJetsonのUSB 3ポート**に接続します．画像を1枚保存し，
導入済みモデルで1回推論して，入力画像，別枠の俯瞰経路図，全座標の表を開きます．
B2は接続しません．以下はJetsonの同じBash端末で，プロジェクトルートから実行します．
MacはSSHや表示に使えますが，推論をせず，Dockerも不要です．
インストールと資材取得が終わっていれば，実行時のインターネットは不要です．

これはロボットの状態を明示的に**静止と仮定した保存画像の試験**です．
歩行アプリケーション，地面への校正済み重ね描き，通行可能性の証明ではありません．
プログラムはロボット用クライアントも指令も作りません．実状態を使う後続手順は
[現地での観測](onsite.ja.md)を参照します．

準備済みGPUイメージ，確認済み上流ソース，承認済みローカルモデル，ZED SDK 4.1.2，
専用Pythonバインディング，接続カメラに一致する校正が必要です．ホストのvenvだけには
揃っていません．不足があれば[初期構築](setup-from-scratch.ja.md)から進めます．
一般的なpipインストールやシステムCUDAの置換では解決しません．

## 2．既存の入力と新しい出力先を選ぶ

Bashを使います．別のシェルなら`bash`を開きます．確認済みの別配置ではソースの場所を
調整します．`camera-demo-02`は未作成である必要があり，実験ごとに新しい名前を選びます．
今回の実測は`camera-demo-01`に残っています．`sudo -v`の認証は端末で行い，
チャットや保存コマンドにパスワードを書きません．

```bash
set -euo pipefail
umask 077
cd ~/Developer/Projects/Robotics/b2/VLN_B2
PROJECT="$PWD"
IMAGE="$(sudo docker image inspect vln-b2-runtime:jp5 --format '{{.Id}}')"
CAMERA_API="$PROJECT/local/camera-runtime/attempt-01/python"
CAMERA_SETTINGS="$PROJECT/local/camera-runtime/attempt-01/settings"
HUB="$(readlink -f "$HOME/.cache/huggingface")/hub"
BASE_REPO="$HUB/models--OpenGVLab--InternVL3-1B"
BASE_REV=4415a3b810e636d11dfa86b0e9ba40bb00535aa8
UPSTREAM="$HOME/Developer/External/TIC-VLA"
CHECKPOINT="$(readlink -f "$PROJECT/models/tic-vla-671de608-01/model.safetensors")"
CHECKPOINT_SHA=2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4
RUN_DIR="$PROJECT/local/camera-demo-02"
sudo -v
mkdir -m 700 "$RUN_DIR"
test -d "$CAMERA_API/pyzed"
test -d "$CAMERA_SETTINGS"
test -f "$BASE_REPO/snapshots/$BASE_REV/config.json"
test -f "$CHECKPOINT"
test -d "$UPSTREAM/ticvla"
printf '%s  %s\n' "$CHECKPOINT_SHA" "$CHECKPOINT" | sha256sum -c -
printf '%s\n' "$IMAGE" > "$RUN_DIR/runtime-image-id.txt"
```

`IMAGE`には変更可能なタグではなく，実際のローカルイメージIDを固定します．
確認済み参照イメージは`sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a`です．
再ビルドしたイメージでは初期構築の検査を通します．IDの違いだけでは成功も互換性も判断できません．
safetensorsのハッシュ確認は必須です．基盤モデルは`blobs`と`snapshots`を含む
**リポジトリ全体**をマウントします．snapshotだけでは相対シンボリックリンクが切れます．

## 3．カメラを接続して識別する

USB 3のデータ用ケーブルと十分な電源を使います．ZED Explorerなど，カメラを使用中の
別プロセスを閉じます．この実習ではロボットのEthernetは接続しません．
USBシリアル番号や室内画像をGitに入れず，手元で確認します．

```bash
lsusb
lsusb -t
ls -l /dev/video*
for node in /sys/class/video4linux/video*; do
  printf '%s: ' "$node"
  cat "$node/name"
  readlink -f "$node/device"
done
```

`2b03:f880`がZED映像側，`2b03:f881`が補助側です．sysfsの接続先と照合して
videoノードを対応づけます．V4L2ノードが2個あることは，このプログラムに左右の独立カメラを
2台入力する意味ではありません．`lsusb -t`で映像側が5000Mになっているか確認します．
ノード番号は再接続や再起動で変わる場合があります．

次の値は**2026-11-03の試験時だけの例**です．実行前に上の調査結果で置き換えます．
存在しない，または別の機器のノードなら実行を止め，原因を確認します．
`/dev`全体の公開やprivileged指定で回避しません．

```bash
VIDEO_0=/dev/video0
VIDEO_1=/dev/video1
USB_VIDEO=/dev/bus/usb/002/003
USB_COMPANION=/dev/bus/usb/001/008
for node in "$VIDEO_0" "$VIDEO_1" "$USB_VIDEO" "$USB_COMPANION"; do
  test -c "$node"
done
```

設定フォルダには接続カメラに一致する工場校正が必要です．別シリアル番号のファイルを
名前だけ変えて使いません．深度と物体検出モデルは無効です．不足があれば
[カメラ構築](camera-runtime.ja.md)を確認します．本体内蔵カメラをこのUSB経由で読むわけではありません．

## 4．画像を1枚取得する

```bash
sudo docker run --rm --pull never --name b2-camera-demo-capture \
  --runtime nvidia --network none --read-only \
  --user "$(id -u):$(id -g)" \
  --group-add "$(stat -c %g /dev/nvmap)" \
  --group-add "$(stat -c %g /usr/local/zed)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 4g --cpus 2 --pids-limit 128 \
  --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --device "$VIDEO_0" --device "$VIDEO_1" \
  --device "$USB_VIDEO" --device "$USB_COMPANION" \
  --mount "type=bind,src=$PROJECT/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$CAMERA_API,dst=/camera-api,readonly" \
  --mount "type=bind,src=/usr/local/zed,dst=/usr/local/zed,readonly" \
  --mount "type=bind,src=$(readlink -f /usr/lib/aarch64-linux-gnu/libturbojpeg.so.0),dst=/camera-libs/libturbojpeg.so.0,readonly" \
  --mount "type=bind,src=$CAMERA_SETTINGS,dst=/camera-settings" \
  --mount "type=bind,src=$RUN_DIR,dst=/run-output" \
  -e HOME=/tmp/home -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/camera-api:/workspace/src \
  -e LD_LIBRARY_PATH=/camera-libs:/usr/local/zed/lib:/usr/local/cuda/lib64:/usr/lib/aarch64-linux-gnu/tegra \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  --entrypoint timeout "$IMAGE" -k 5s 45s \
  python3.11 -m b2_tic_vla camera \
  --settings-dir /camera-settings --output /run-output/frame.jpg
```

成功すると`RUN_DIR`に`frame.jpg`と`frame.jpg.json`ができます．付属JSONは
画像寸法と撮影側・ホスト受信側の時刻を保存しますが，両時計の同期は証明しません．
推論前に画像の向き，空画像でないこと，意図した視野を確認します．
SDKが左側の補正済み画像を取得し，アダプタがBGRAをRGBに変換して1280×720のJPEGにします．
深度は`NONE`です．RGB-Dカメラでも深度を計算せずRGB入力として使えます．

NVIDIA runtimeは対応するホストのGPUライブラリとデバイスをコンテナに渡します．
カメラのネイティブSDKとバインディングは読み取り専用です．選んだデバイス，書き込み可能な
専用校正フォルダ，一時領域，出力先だけを渡します．video／SDKの数値グループは
このプロセス内のアクセス権で，ホストのグループ所属やSDK権限は変更しません．
コンテナ内部も通常UIDで動かしますが，Docker自体は強い権限を持つホストサービスであり，
仮想マシン同等の隔離ではありません．`timeout`をコンテナの入口にすることで，45秒を超えた
撮影を停止し，さらに5秒後に強制終了します．GPUもホストの統合メモリを使います．
4 GiBはコンテナの制限であり，専用VRAMの容量ではありません．

## 5．保存画像から将来のXY位置を予測する

```bash
sudo docker run --rm --pull never --name b2-camera-demo-predict \
  --runtime nvidia --network none --read-only \
  --user "$(id -u):$(id -g)" --group-add "$(stat -c %g /dev/nvmap)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 24g --cpus 2 --pids-limit 128 \
  --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --mount "type=bind,src=$PROJECT/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$PROJECT/tools,dst=/workspace/tools,readonly" \
  --mount "type=bind,src=$BASE_REPO,dst=/input/base-repo,readonly" \
  --mount "type=bind,src=$CHECKPOINT,dst=/input/model.safetensors,readonly" \
  --mount "type=bind,src=$UPSTREAM,dst=/opt/upstream,readonly" \
  --mount "type=bind,src=$RUN_DIR/frame.jpg,dst=/input/frame.jpg,readonly" \
  --mount "type=bind,src=$RUN_DIR,dst=/reports" \
  -e HOME=/tmp/home -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src:/workspace/tools \
  -e HF_HOME=/tmp/hf -e HF_MODULES_CACHE=/tmp/hf-modules \
  -e XDG_CACHE_HOME=/tmp/cache -e TORCH_HOME=/tmp/torch \
  -e CUDA_CACHE_PATH=/tmp/cuda -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 \
  -e HF_HUB_DISABLE_TELEMETRY=1 -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 \
  -e TOKENIZERS_PARALLELISM=false \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  --entrypoint timeout "$IMAGE" -k 5s 180s \
  python3.11 /workspace/tools/predict_image.py \
  --image /input/frame.jpg \
  --base-model "/input/base-repo/snapshots/$BASE_REV" \
  --checkpoint /input/model.safetensors --expected-sha256 "$CHECKPOINT_SHA" \
  --upstream-root /opt/upstream --instruction "Move straight ahead." \
  --assumed-stationary --output /reports/prediction.json
```

こちらのコンテナには**カメラのノードもネットワークもありません**．JPEG，確認済みPythonソース，
基盤モデル，変換済み重みを読み取り専用で渡します．結果用フォルダだけが書き込み可能です．
ホーム全体，HFトークン，SSH鍵，Dockerソケット，B2接続は渡しません．
一時的なモジュール／GPUキャッシュはコンテナ終了とともに消えます．180秒は終了期限であって
目標周期ではありません．24 GiBはコンテナの資源上限です．

`predict_image.py`が重みのSHA256を確認し，ローカルファイルだけを使って厳密に読み込みます．
推論前後で画像ハッシュも確認します．明示フラグで姿勢・速度をゼロと仮定し，
B2から受信したと偽らず，結果に仮定と記録します．同じ画像を現在画像と意味情報の参照画像に使い，
遅延と相対変位をゼロにした同期呼び出しです．非同期実験より単純な構成です．

成功時の`prediction.json`には`passed: true`，XY点30個，ロード／推論所要時間，
モデル情報，`motion_sent: false`，`robot_connected: false`が入ります．
失敗レポートは有効な経路ではありません．実験を残して原因を確認し，ハッシュや厳密な読込を緩めません．

## 6．入力画像と予測経路を表示する

```bash
python3 tools/render_prediction.py   --report "$RUN_DIR/prediction.json" --image "$RUN_DIR/frame.jpg"   --output "$RUN_DIR/prediction.html"
python3 -m json.tool "$RUN_DIR/prediction.json"
```

Jetsonのブラウザで**`RUN_DIR/prediction.html`**を開きます．例えば既存RDP画面の
ファイルマネージャーから開けます．このHTMLだけMacへコピーしてローカルで開くこともできます．
元JPEGとSVGを内包するので，Webサーバー，SSHトンネル，JavaScriptサービス，インターネットは不要です．
任意のJSON整形表示は長くなりますが，ロボットへの送信機能はありません．

| ファイル | 意味 |
|---|---|
| `frame.jpg` | 実際に撮影した左側補正済み画像 |
| `frame.jpg.json` | 取得時の情報．時計の同期は未確認 |
| `prediction.json` | 指示，画像・重みのハッシュ，所要時間，将来XY位置 |
| `prediction.html` | 入力画像，経路図，座標表を内包した表示用ファイル |
| `runtime-image-id.txt` | 実行に選んだ実際のソフトウェアイメージID |

右側の図はモデル相対座標のメートル表示です．x前方を上，y左方を左に描きます．
赤が仮定した原点，青が予測列です．各点は相対**位置**なので，累積和は取りません．
マウスを重ねるか表で座標を確認できます．`time_from_now`の0.1秒刻みは確認した実装からの
アダプタ上の仮定であり，実測したB2の制御周期ではありません．30点／3秒という表示でも，
推論自体が長ければ結果が新鮮とは限りません．

左の画像には**床面へ投影した経路を描いていません**．カメラ内部校正，B2との位置・姿勢，
座標符号，撮影時計の対応を機体上で検証していないからです．それらを確認せず画像の床に
線を描くと，根拠のない位置関係を示してしまいます．衝突・地形評価，停止距離の妥当性，
目標到達の保証もありません．

## 7．内部で何が起きるか

1. USBでホストのカメラ機構へ画素を送り，`pyzed`がネイティブZED SDKを呼びます．
2. アダプタがRGB画素と時刻を保存します．Dockerは実行環境を提供するだけで，画像理解も
   ロボット制御も行いません．
3. PyTorchが基盤VLMとTIC-VLAのパラメータをJetsonのメモリへ読み込みます．
   確認済み上流Pythonが構造を定義し，このレポが入力を検査して呼び出します．
4. 上流の画像処理が視覚エンコーダ用にリサイズ・正規化します．確認した設定は448画素です．
   言語条件付きの意味計算が画像と指示を解釈し，行動側が視覚特徴，意味情報，
   与えた運動・遅延入力からXY位置30個を出します．
5. 独自アダプタが形状と有限値を確認してJSONへ保存します．標準ライブラリだけの描画ツールが
   JSONと一致するJPEGを読み，SVG／HTMLを作ります．この実習にROS，RViz，DDSは使いません．
6. 将来の制御器は経路を追従し，制限した上位速度指令をB2の既存歩行制御器に送ります．
   この送信器は未実装です．姿勢安定化や関節制御は既存のブラックボックス側に残す設計です．

意味計算と行動計算の分離，この単純化した呼び出しの省略点は
[TIC-VLAの説明](ticvla-explained.ja.md)と[限定的な非同期実験](asynchronous-runtime.ja.md)を参照します．

## 8．実測結果と問題の切り分け

2026-11-03にソース`6900bfc`と参照イメージで，撮影・推論・描画が全て終了コード0でした．
JPEGは218,278バイト，JSONは5,081バイト，HTMLは299,580バイトです．
モデルロード**13.109秒**，推論**13.290秒**で有限値30点を得ました．
HTMLを描画して目視も確認しました．机上の視野なので，指示「Move straight ahead.」に対する
正しい追従，空き空間，経路品質を確認した実験ではありません．

| 症状 | 次に確認すること |
|---|---|
| フォルダ／レポートが既存 | 新しい実験名を選び，過去の記録を残す |
| `pyzed`や共有ライブラリがない | ホストvenvではなく専用prefix・SDK・ライブラリのマウントを使う |
| カメラを開けない | 機器の対応，USB 3，ケーブル・電源，競合プロセス，一致する校正 |
| GPUの権限エラー | `/dev/nvmap`の実際の数値グループとNVIDIA runtime |
| snapshot不足／オフライン読込エラー | 承認済み固定版とblobsを含むリポジトリ全体のマウント |
| ハッシュ／厳密読込の不一致 | 停止し，資材・変換履歴を照合．検査を回避しない |
| HTMLが画像を拒否 | 推論レポートに記録したハッシュと一致する元JPEGを使う |
| 最初の結果が遅い | ロードと推論を分ける．どちらも定常制御周期の証明にはならない |

画像，JSON，HTMLは全てGit対象外の非公開`local/`へ保存します．HTML内の画像にも
人物・画面・研究室情報が含まれ得るため，そのまま公開できる成果物ではありません．
この試験を繰り返しても移動の許可にはなりません．次は[現地カード](field-card.ja.md)で
Ethernetと状態受信を調べ，[マイルストーン](milestone-2026-11-03.ja.md)で到達範囲を確認します．
