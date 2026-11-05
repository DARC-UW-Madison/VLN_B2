# 非同期カメラ推論の実験記録

[English](async-shadow.md) · [記録目次](README.ja.md)

> 文書種別：**実験記録**．source `c261a5e`の実行結果で，継続制御の完成を示さない．

## 時間制限付きのカメラ・モデル実験

`tools/record_camera_stream.py`は新しい非公開フォルダを所有し，固有名のJPEGと各frameの情報を
書いてから，完成した画像・manifestに対してのみ`latest.json`を一体で置き換える．公開した画像は
読み取り専用にする．SDKの元時計を別に維持し，不明な撮影時刻はnull・未検証のままにする．
取得窓は最大60秒，目標は最大10枚/秒である．逃した時刻の取得を連続で埋め合わせない．
ネイティブSDK・deviceが停止すると外部のプロセス期限が必要である．

`tools/observe_async.py`は同じフォルダを**読み取り専用**で読み，schema，時計，容量を制限した通常ファイル，
パス，不変のbasename，SHA256を使用前に確認する．確認済みsafetensors・base modelをオフラインで読み，
thread workerには意味情報の要求を最大一つだけ置く．main threadでは公開済みcacheと新しい画像を使う．
意味情報・行動処理は別のCUDA streamを使い，各streamだけの完了を待つ．重ねて進める実験を可能にするが，
GPU kernelの実際の重なり，他のモデル版でのthread安全性，遅延上限を保証しない．
モデルparameterは読み取りだけで共有し，cache tensorは公開前にcloneする．
状態購読，追従計算，送信部，robot clientは作らない．

workerは同期package predictorを呼んで会話全体のcacheを得る．その呼出しには使わない同期の行動計算も含む．
報告内のpredictor説明は，この同期部品を記述したままである．外側の実験ツールが並行処理を付ける．
本家DynaNavの再現や，複数画像の履歴を扱う実装ではない．

observerには`--assumed-stationary --shadow-only`と正の`--max-semantic-age`を明示する必要がある．
実状態ではなく，移動ゼロの仮定を使う．受信基準の古さは下限のままである．各行動の**前後**で
新しさとcacheの同一性を検査し，無効な結果を破棄する．受信から0.5秒を超えた入力は見送るが，
この診断値は承認済みB2閾値ではない．実験時間はモデル読込後に数える．終了時はcacheをresetし，
新要求を始めず，最後のGPU呼出しを待ち，遅い完了結果を破棄する．外部監視は180秒で，
この二つの実験コンテナだけを停止する必要がある．`Future.cancel()`はネイティブGPU計算を中断できない．

### 準備したコンテナ内のコマンド

以下は明示的な**コンテナ内**コマンドであり，ホストvenvやMac設定のコマンドではない．
通常UID，読み取り専用root，`--network none`，capabilityなし，no-new-privilegesを指定した
二つのNVIDIAコンテナを準備する．カメラ用の非公開binding，読み取り専用SDK，現時点のUSB・video node，
書込可能な専用校正フォルダは[カメラのガイド](../reference/camera-runtime.ja.md)に従う．モデル側には，確認した
source・base repository・変換済みsafetensorsを読み取り専用で渡し，Hubオフライン設定，一時module cache，
専用の書込可能な報告先を指定する．USB・認証情報は不要である．プロジェクトの`src`・`tools`は読み取り専用で
渡し，observerは`PYTHONPATH=/workspace/src:/workspace/tools`を使う．

`/observations`へ書くのはカメラだけである．observerは同じSSDフォルダを読み取り専用でmountする．
親は事前に存在し，`frames`は新規でなければならない．producerを始め，完成した`latest.json`を待ってから
observerを始める．両者は同じホストのmonotonic時計を使う．古いmanifestをライブ観測として再生しない．
各試行で新しい出力先を使い，データを上書きしない．

```sh
python3.11 /workspace/record_camera_stream.py \
  --output-dir /observations/frames --settings-dir /camera-settings \
  --duration 55 --fps 5
```

```sh
python3.11 /workspace/tools/observe_async.py \
  --observations /observations/frames \
  --base-model /input/base-repo/snapshots/4415a3b810e636d11dfa86b0e9ba40bb00535aa8 \
  --checkpoint /input/model.safetensors \
  --expected-sha256 2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4 \
  --upstream-root /opt/upstream --report-dir /reports/run \
  --duration 25 --max-semantic-age 20 --assumed-stationary --shadow-only
```

### 実測結果と空白

最初の対象機試験はsource `c261a5e`，既存GPUイメージ
`sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a`で成功した．
カメラ・モデルのメモリ上限は4 GiB・24 GiB，CPUは各二つ，プロセス128，一時領域256 MiBだった．
ホストservice・Macの常駐jobは作らず，両コンテナは正常終了して除去された．

| 観測 | 結果 |
|---|---|
| カメラの公開 | 55秒の取得窓で不変JPEG 275枚，画像39,668,458バイト |
| モデル読込 | 観測窓の前に9.354秒 |
| observer | 約25秒で異なる最新観測126個．保存した全画像を消費する設計ではない |
| 意味情報要求 | 二回完了．初回は12.659秒で公開，二回目は終了後に完了して破棄 |
| 受け入れたshadow行動 | 35回，全て次の意味情報要求の処理中．各回で有限なXY 30点 |
| 行動の経過時間 | 最小0.131秒，中央値0.156秒，最大0.283秒．現在画像・特徴・decoder・stream待ちを含む |
| 見送った観測 | cacheがない間65個，実験用の意味情報期限20秒を過ぎて26個 |
| 受け入れた行動の意味情報の古さ | 受信基準の下限で約13.05〜19.98秒 |
| エラー・終了 | エラーゼロ，reset後の遅い意味情報結果一つを破棄 |

件数には，準備待ち・更新待ちの大きな空白が出ている．最速の行動時間の逆数を，全体の制御周期と扱わない．
20秒の上限は診断を観測可能にしただけで，走行品質や許される物理delayを証明しない．
撮影時計の対応，実機の移動，取付後の視野，空間の安全余裕，途切れない制御の可用性，物理的停止は未検証である．

非公開の呼出し・source・image記録とevent・summary JSONは`local/async-shadow/attempt-01`，
画像・各frame情報はSSD専用observations領域へ置き，Git対象外にする．cacheモジュールの検査に加え，
壊れた・変化したmanifest，不明な時刻，公開失敗，古い・遅い行動，worker失敗，終了を単体テストで確認する．
Mac・Jetsonで通常テスト162件が成功する．これらのテストと短い試験は，長時間信頼性や制御権の証明ではない．
