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
| 通常のテスト | Mac・Jetsonで130件成功 | 単体・合成試験はセンサー，firmware，移動を検証しない |

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

## 次の受入確認

実物なしで，意味情報の推論と行動生成を別々に測り，初回と繰返しの時間を分ける．この作業に
追加のモデル取得は不要である．次に実物から入力を取る試験は，外付けZED 2iをこのJetsonへ
USB接続し，B2へ接続せずにRGBを取得して確認することである．カメラが現地にしかなければ，そこで行う．

B2では，まず既存の手動操作・停止手順を確認し，Ethernetのnetworkと計算機の役割を調べ，
モーター指令なしで状態を受信する．カメラと機体への接続は独立した検査であり，一方の成功で他方は証明されない．
両方が通ってから実画像と状態を組にして保存し，オフライン推論，指令を送らない非同期結合へ進む．

指令なしで実RGBと機体状態を使い，時計，座標系，単位，校正を確認し，モデルの処理を段階別に計測する．
送信部の前に，非同期経路とcacheの古さの制限を実装・試験する．現地でSDKの制御権，リモコンの優先順位，
実際の停止を確認する．生成画像のforward成功は互換性の有用な段階であり，これらを省く許可ではない．
