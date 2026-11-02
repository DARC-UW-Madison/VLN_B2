# 非同期推論：workerの前に参照情報を整える

[English](asynchronous-runtime.md) · [文書一覧](README.ja.md) · [実行時の計測](model-runtime.ja.md)

## 実装した範囲

`src/b2_tic_vla/semantic_cache.py`は，thread間で一体として公開する境界と，メタデータ・入力の
検査を実装する．Mac・Jetsonのどちらでも，**worker，サービス，バックグラウンドプロセスを開始しない**．
別の実験ツールが，時間制限付きのカメラ・モデルloopを加える．送信部・独立した停止機構は未実装である．

段階別の実測は意味情報の推論と現在画像・行動処理の分離を調べる根拠だが，ライブの並行実行，走行品質，
10秒の運転遅延を検証しない．ここでのcacheの受付はメタデータの確認だけで，機体を動かす許可ではない．

ここでいう**shadow**は，予測を計算・記録し，機体へ送らない実行を指す．意味情報cacheは，
画像・指示・推論を含む会話全体をVLMで処理したattentionのkey・value tensorである．
行動decoderはそれらと新しい画像特徴を読む．プロセス・GPU上の一時メモリであり，
新しい重み，文章だけの答え，ディスク上のHugging Face cacheではない．

## cacheと参照観測を一体で扱う

`Observation`は画像，機体状態，指示を組にする．`begin()`はその不変の観測を持つ要求を返し，
`publish()`は結果本体，要求・参照情報，完了時刻をlockの中で一度に公開する．新しい要求を開始しても，
公開済みcacheの参照は変えない．置き換えられた要求，二重公開，`reset()`をまたいだ未完了要求は公開できない．
指示が変われば，それまでのcacheを直ちに拒否する．

画像は一意の名前で上書きしない．上書きされる画像のパスだけでは観測を維持できない．cacheの部品は
payloadの所有権を受け取るが，任意のtensorを不変にすることはできない．公開後のtensorを書き換えず，
独立したstorageが必要ならcloneする．`detach()`だけでは共有される．
[TorchのAPI](https://docs.pytorch.org/docs/2.2/generated/torch.Tensor.detach.html)を参照する．

利用側は選んだsnapshotを保持し，モデル計算の後にも`is_current()`で確認する．GPU処理中にもreset・
置換は起こり得る．実際の送信部には世代，期限，制御権，停止の独立した検査が必要で，
以前に返されたcontextが無期限に有効になるわけではない．

## 異なる三つの時刻

差分には対応が確認されたホストの単調時計を使い，未変換のカメラ・機体時刻を直接引かない．意味情報の
参照は，文脈に使う最新画像の撮影時刻とその姿勢であり，推論の完了時刻ではない．

| 量 | 定義 |
|---|---|
| 期限検査用の意味情報の古さ | 判断時刻−意味情報の参照画像の撮影時刻 |
| モデル入力の遅延 | 現在の行動用画像の撮影時刻−意味情報の参照画像の撮影時刻 |
| 観測・状態の新しさ | 判断時刻−各々の現在sample時刻．受信時刻も別に確認する |

`state_aligned_at`は，pose・velocityが表すホスト時計の時刻で，必要なら検証した補間を含む．
受信が新しくてもsampleが新しいとは限らない．確認済みの画像・状態sample時刻の差はpair-skewの
上限を満たす必要があり，受信時刻の差も別に検査する．確認flagを立てても時計は同期されず，先に証拠が必要である．

撮影・状態時計と姿勢を確認するまでは，通常の`select()`は受け付けない．`shadow_only=True`を明示すると，
撮影時刻が不明な場合は受信時刻から診断用の遅延・古さを返せる．これは**下限**と明示し，物理指令を許可しない．
cacheの制限値は引数で必須にし，B2で承認した運転上限として既定値を示さない．

## 状態ベクトルの座標系

確認した実装は`[vx, vy, yaw_rate, dx, dy, delay]`を使う．速度は現在の機体座標，
変位は**意味情報の参照時点の**機体座標で表す累積移動である．既存の二次元状態では，平面のyaw回転だけを扱う．

$$
\Delta x=x_{now}-x_{ref},\quad \Delta y=y_{now}-y_{ref},
$$

$$
d_x=\cos(\psi_{ref})\Delta x+\sin(\psi_{ref})\Delta y,\quad
d_y=-\sin(\psi_{ref})\Delta x+\cos(\psi_{ref})\Delta y.
$$

位置・変位はm，yawはrad，速度はm/s，yaw速度はrad/sである．現在・参照のposeは，同じ確認済みの
世界座標を必要とする．roll，pitch，上下移動は表現しないため，`pose_frame_verified`には平面近似が
適切であるという証拠も必要である．B2のデータではまだ確認していない．参照yawを現在yawに置き換えたり，
世界速度を機体速度と決めつけたりしない．

参照の規約は，固定した
[Spotの呼出し側](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/DynaNav/behavior/spot_test_ticvla.py#L994-L1006)と
[学習loader](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/policy_data.py#L354-L365)で確認した．
呼出し側の開始frame履歴と`predict_async`内で新たに公開するcacheが，切替時に一致しない可能性も
コードの確認で見つかった．本プロジェクトは履歴からの推定を写さず，実際のpayloadへ参照情報を付ける．
学習側のdelayのfloor・roundとfuture sampleのoffsetは，研究として再現を主張する前に対応を確認する必要がある．

## 検証と残る作業

単体テストでは，未完了要求の置換，reset，元の参照からの古さ，機体座標への投影，受信・撮影のpair，
古いsample，指示変更，不明な時刻，overflowを確認する．機体ではなく合成メタデータを使う．

`tools/profile_model_runtime.py --cached-actions N`は，数値的なcache再利用の試験を明示した場合に行う．
会話全体をVLMでforwardした出力を取得し，確認したcache APIを正規化して形状・容量を検査し，tensorをcloneする．
遅延ゼロで同期出力と照合してから，遅延付きのdecodeとbyte単位のcache維持を検査する．既定`N=0`では
追加試験を行わない．ライブのworkerとは別で，実際の結果は[実行時の手引き](model-runtime.ja.md)へ記す．

次は実状態・時計・座標系を確かめ，更新待ちの空白，長時間運用，失敗時の復帰を送信部の前に検証する．
初回B2作業はモーター出力なしのnetwork・状態調査であり，接続直後の自律歩行試験ではない．

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
書込可能な専用校正フォルダは[カメラのガイド](camera-runtime.ja.md)に従う．モデル側には，確認した
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
