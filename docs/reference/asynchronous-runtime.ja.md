# 非同期推論：workerの前に参照情報を整える

[English](asynchronous-runtime.md) · [文書一覧](../README.ja.md) · [実行時の計測](../records/model-runtime.ja.md)

> 文書種別：**参照資料**．

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
追加試験を行わない．ライブのworkerとは別で，実際の結果は[実行時の手引き](../records/model-runtime.ja.md)へ記す．

次は実状態・時計・座標系を確かめ，更新待ちの空白，長時間運用，失敗時の復帰を送信部の前に検証する．
初回B2作業はモーター出力なしのnetwork・状態調査であり，接続直後の自律歩行試験ではない．

## 実験記録

実行コマンドと結果は[非同期カメラ推論の記録](../records/async-shadow.ja.md)にまとめる．制御周期の説明は[位置予測から速度制御へ](../explanations/control-loop.ja.md)を参照する．
