# Jetsonでのオフラインモデル確認

[English](model-runtime.md) · [文書一覧](README.ja.md) · [入力](model-artifacts.ja.md) · [変換](checkpoint-conversion.ja.md) · [進捗](status.ja.md)

モデル読込と数値的な推論の確認記録であり，B2のナビゲーション評価ではない．承認したローカル資材と
既存のJetson GPUイメージをネットワークなしで使い，カメラ，SDK制御client，機体への指令送信部は使わない．

## 2026-10-29に通ったこと

| 確認 | 結果 | 限界 |
|---|---|---|
| 承認した取得 | 公式Hub client 0.24.7で17ファイル，3,827,163,803バイト，固定した容量・digestを照合 | 非公開研究用の承認は再配布の許可ではない |
| 実際のCPU変換 | 1,324名，3,773,492,276バイトのsafetensors，元・読戻しを検証 | 本家の条件を維持し，古いGPU Torchに元のpickleを復元させない |
| 厳密なGPU読込 | 重複を除く948,462,978パラメータ，horizon 30，action 3層，約10.42秒 | 事前checksumを除いた1回の読込であり，推論時間ではない |
| 生成画像の推論 | 448×448の生成RGB画像と速度0で，有限なXY座標30個，約13.64秒 | 実画像，精度，停止，制御周期の検証ではない |
| PyTorchの確保量 | 読込peak 2,110,120,960バイト，推論peak 2,624,592,384バイト | GPU allocatorだけで，CPU RAM，driverの確保，unified memory全体は含まない |
| 通常のテスト | Mac・Jetsonで134件成功 | 単体・合成試験はセンサー，firmware，移動を検証しない |

生成画像の試験は本家の設定（最大200 new token，sampling有効，temperature 0.7）を維持した．
seedは固定・記録していない．上限を設けた1回の動作確認であり，数値の再現benchmarkや遅延の平均値ではない．
人工の場面に対する座標で走行品質は判断できない．この同期処理は3秒の経路の予測に13.64秒かかったため，
そのまま歩行ループには接続できない．非同期推論，cacheメタデータの一貫性，新しい観測，watchdog，停止は今後の作業である．

13.64秒は同期の画像入力から経路出力までを囲んだ測定であり，行動方策単体の周期ではない．
TIC-VLAは，遅れて届く意味情報の推論と，現在観測・遅延情報を使った行動生成を分ける．
このJetsonでは，まだ各段階を個別に計測していない．定常的な性能を判断する前に，初回の初期化，
繰返し実行の時間，生成token数も分けて記録する必要がある．非同期にするだけで，いくら古い意味情報でも
使えると証明されるわけではない．

GPUイメージは既存の`vln-b2-runtime:jp5`を使った．

```text
sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a
```

CPU変換した実際の入力のSHA256は次である．

```text
2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4
```

## 入力・コード・ファイルシステムの境界

基盤snapshotは承認したHubキャッシュの固定InternVL版である．実行前に独自Python 5本とconfigを
静的に読み，相対import先が揃い，5本の中に明示的なnetwork・subprocess・exec・eval・pickle・
独立した重み読込の呼出しが見つからないことを確認した．依存コード全体の安全性の証明ではない．
FlashAttention・apexの任意importは不在ならfallbackし，`use_flash_attn=False`でeager attentionを使う．
configからhidden 896・24層のQwen2ForCausalLMを作るため，残っている32Bという名前の文字列から
大きいモデルを作るわけではない．

独自wrapperはAutoModelをローカル・safetensors限定にする．実際の実行でもネットワークなし，通常UID，
capabilityなし，no-new-privileges，アプリ・基盤・変換物・本家は読み取り専用，一時module cacheは
書き込み可能とした．読込後のconfig・独自コード5本のhashは，承認した取得結果と一致した．
ホームや認証情報は渡していない．機体・USB・profilingのdeviceマウントやグループは明示せず，
NVIDIA runtimeが所定のGPUインターフェースを供給する．

基盤の**リポジトリのキャッシュディレクトリ全体**を読み取り専用にし，`snapshots`と`blobs`を含める．
snapshotだけを別の場所へマウントすると相対symlinkが切れる．基盤リポジトリだけを渡すため，別の
データセットキャッシュにある元のTIC pickleは見えない．変換したtensorファイルは別に渡す．
モデルの入力を読み取り専用にしても，Transformersは確認した独自Pythonをコピーするため，
`HF_MODULES_CACHE`には書込可能な一時領域が必要である．追加のモデル取得や，元のsnapshotの変更ではない．

## GPUアクセスと最初の失敗

非rootコンテナでは初めCUDAを認識しなかった．同じ2 GiB条件でもdeviceのvideoグループなしでは
認識せず，その数値GIDだけをコンテナ内へ追加するとGPU 1台を認識した．ホストの所属・device権限は
変更していない．この確認した権限の代わりに，`--privileged`，`/dev`全体のマウント，rootを使わない．

続く最初の読込検査は，Torch 2.2.2でCUDA初期化前にメモリ統計をresetしたため，**モデル構築前**に停止した．
初期化とdevice選択を明示してツールを修正し，厳密な読込の試行02が成功した．チェックポイントの互換性が
原因の失敗ではない．各試行，コマンド，ソース・イメージのhash，報告，stderrはJetsonのGit対象外
`local/model-loading`と`local/model-inference`へ非公開で維持する．

## 明示的な読込確認を再現する

取得・変換・コード確認の後，記録したイメージを使い，Jetsonのプロジェクトルートで実行する．Mac用ではない．
試行ごとに新しい出力先を選び，非公開の入力hashを先に確認する．次の前景の例は読込だけで，推論や移動は行わない．

```sh
mkdir -m 700 local/model-check-01
sudo docker run --rm --pull never --runtime nvidia --network none --read-only \
  --user "$(id -u):$(id -g)" --group-add "$(stat -c '%g' /dev/nvmap)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 24g --cpus 2 --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/tools/verify_model_load.py,dst=/workspace/verify.py,readonly" \
  --mount "type=bind,src=$(readlink -f "$HOME/.cache/huggingface")/hub/models--OpenGVLab--InternVL3-1B,dst=/input/base-repo,readonly" \
  --mount "type=bind,src=$(readlink -f models/tic-vla-671de608-01/model.safetensors),dst=/input/weights/model.safetensors,readonly" \
  --mount "type=bind,src=$HOME/Developer/External/TIC-VLA,dst=/opt/upstream,readonly" \
  --mount "type=bind,src=$(pwd)/local/model-check-01,dst=/reports" \
  -e PYTHONPATH=/workspace/src -e HOME=/tmp/home \
  -e HF_HOME=/tmp/hf-home -e HF_MODULES_CACHE=/tmp/hf-modules \
  -e XDG_CACHE_HOME=/tmp/cache -e TORCH_HOME=/tmp/torch -e CUDA_CACHE_PATH=/tmp/cuda \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 \
  -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e TOKENIZERS_PARALLELISM=false \
  -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3.11 vln-b2-runtime:jp5 \
  /workspace/verify.py --base-model /input/base-repo/snapshots/4415a3b810e636d11dfa86b0e9ba40bb00535aa8 \
  --checkpoint /input/weights/model.safetensors \
  --expected-sha256 2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4 \
  --upstream-root /opt/upstream --report /reports/load-report.json
```

生成画像の推論を明示的に行うには，別の新しい報告領域を使い，ツールの引数へ`--synthetic-inference`を追加する．
生成PNGと，有限な座標・時間を含む非公開JSONを書き出す．既定の読込だけでは画像を作らず推論も呼ばない．
既存の報告はruntimeのimport前に拒否し，形式・checksum・offlineの検査で不正な開始を防ぐ．

記録したホスト側runnerは名前付きコンテナを監視し，読込900秒・生成画像推論1,200秒で打ち切り，
自分のコンテナを停止するようにした．前景の例には同等の操作者の監視が必要であり，自律サービスや機体の
watchdogではない．実行ではメモリ24 GiB，CPU二つ，プロセス128，一時領域256 MiBを上限にした．
この上限は，device全体のメモリ使用量の計測や，実時間性の証明ではない．

## 保存したカメラ画像と段階別の時間

ZEDの初回取得後，`tools/profile_model_runtime.py`で1280×720の実画像を二回処理した．
機体状態は**明示的に仮定した静止状態**であり，B2は接続せず，機体の状態も受信していない．
二回とも有限なXY座標30個を出力した．実カメラのファイル入力と数値的互換性の確認であり，
机上の場面での走行品質，機体取付後の視野，ライブ制御の検証ではない．

| 計測した段階 | 初回 | 二回目 |
|---|---:|---:|
| 意味情報の生成：画像・言語の理解 | 11.573 s | 9.566 s |
| 意味情報cacheのforward | 0.225 s | 0.217 s |
| 現在画像の特徴抽出 | 0.089 s | 0.089 s |
| 行動decoder | 0.0058 s | 0.0057 s |
| 同期呼出し全体 | 12.001 s | 9.931 s |

モデル読込は別に9.254秒かかった．GPU allocatorのpeakは両方2,628,811,264バイトで，
unified memory全体の使用量ではない．段階の境界でGPUを同期し，内側の視覚処理は別途加算しない．
この診断による追加時間があり，表に含まれない前処理・管理処理も残る．二回の試行は遅延分布，
継続的な処理量，保証された制御周期を示さない．

画像と指示は同じで，本家のsampling設定（最大200 new token，temperature 0.7）を維持した．
呼出し前にPython・NumPy・Torchのseedを0へ戻したが，決定的なalgorithmは強制せず，
実際の出力token数は記録していない．差を初期化だけの影響と断定しない．意味情報の処理時間は
推論・行動の分離を進める根拠になるが，約10秒古いcacheで走行できる証明ではない．

最初はコンテナ内へ`profile.py`として渡したため，依存のimport時にPython標準モジュールと
衝突し，推論前に停止した．試行02は`profile_model_runtime.py`にして成功した．この区別できる
名前を維持する．正確なコマンド，画像・報告のhash，ソース・イメージの版，仮定した状態，上限は
非公開の`local/model-profiling/attempt-02`に残す．オフライン，非root，読み取り専用のGPUコンテナで，
RAM 24 GiB，CPU二つ，プロセス128，一時領域256 MiB，監視180秒を上限にした．
入力は保存画像だけを渡し，カメラ・USB，ホーム，認証情報は渡さず，元のpickleもマウントしていない．

再現時は厳密な読込試験と同じ制限付きマウント・環境を使い，区別できる名前で計測ツールを渡し，
保存画像を読み取り専用にし，新しい報告先を選ぶ．そのコンテナ内の明示的な呼出しは次である．

```sh
python3.11 /workspace/profile_model_runtime.py \
  --base-model /input/base-repo/snapshots/4415a3b810e636d11dfa86b0e9ba40bb00535aa8 \
  --checkpoint /input/model.safetensors \
  --expected-sha256 2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4 \
  --upstream-root /opt/upstream --image /input/frame.jpg \
  --report /reports/profile.json --assumed-stationary --repeats 2
```

仮定した状態のflagを必須にし，報告の上書き，非オフライン，チェックポイントのchecksum不一致は
モデル読込前に拒否する．hookの復元・二重計上の抑制と入力の検査は単体テストで確認した．
Mac・Jetsonで全134件が通ったが，実際のB2観測の検証ではない．

## 次の受入確認

初回RGB取得と，保存した実画像二回の段階別計測は通った．次は意味情報の推論と行動実行を分け，
cacheの参照情報を一体で扱い，古さ，推論停止，新しい画像の扱いを指令なしで試す．追加のモデル取得は不要である．
継続的なカメラ取得，撮影時計の対応，予定する取付後の視野も確認する．机上の画像だけではそれらを証明できない．

B2では，まず既存の手動操作・停止手順を確認し，Ethernetのnetworkと計算機の役割を調べ，
モーター指令なしで状態を受信する．カメラと機体への接続は独立した検査であり，一方の成功で他方は証明されない．
両方が通ってから実画像と状態を組にして保存し，オフライン推論，指令を送らない非同期結合へ進む．

指令なしで実RGBと機体状態を使い，時計，座標系，単位，校正を確認し，モデルの処理を段階別に計測する．
送信部の前に，非同期経路とcacheの古さの制限を実装・試験する．現地でSDKの制御権，リモコンの優先順位，
実際の停止を確認する．生成画像のforward成功は互換性の有用な段階であり，これらを省く許可ではない．
