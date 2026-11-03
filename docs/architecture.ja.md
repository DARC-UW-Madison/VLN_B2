# 構成と仕組み

[English](architecture.md) · [ホーム](../README.ja.md)

以下のライブシステム全体は接続構成の計画である．現在のリポジトリには観測アダプタ，
保存データの同期推論，オフライン評価用の追従計算，cacheの参照管理がある．別の実験ツールは
時間制限付きの実カメラ非同期shadow試験を行う．実状態を使うライブ制御・移動指令送信は未実装である．[現在の実装範囲](#現在の実装範囲)を参照する．

## 課題と方針

画像言語モデル（VLM）は画像と言語指示を解釈し，ナビゲーション方策がその情報を移動につなげる．
推論に時間がかかると，得られた情報は過去の状況を表している．TIC-VLAでは，
現在の観測に加えて，遅延した意味情報と時刻に関する情報を行動方策に渡す．
詳細は[論文の第2版](https://arxiv.org/html/2602.02459v2#S3)を参照する．

B2への接続では既存の歩行制御を使い，その上位のナビゲーションを評価する．関節制御は置き換えない．
ROS 2は候補の一つであり，この文書で採用を決めた前提条件ではない．

```text
RGB images + robot state + instruction
                 |
     Timestamped observation history
          |                  |
     VLM worker        Current observation
          |                  |
 Semantic cache              |
 + capture time              |
 + reference pose            |
          |                  |
          +------+-----------+
                 |
           Action policy
                 |
   Relative plan -> trajectory -> velocity command
                 |
     Command limits and expiry checks
                 |
       B2 high-level motion interface
                 |
        Existing walking controller
```

図は，画像・機体状態・指示から，時刻付きの履歴，意味情報のキャッシュ，行動方策，
軌道と速度への変換，指令の制限を経て，B2の歩行制御に至る流れを示す．

## 時刻と座標系

画像と機体状態の各サンプルに取得時刻を付ける．完成した意味情報のキャッシュには，
その計算で使った観測の取得時刻と基準姿勢を対応させる．
キャッシュの古さは `current_time - reference_capture_time` であり，
推論時間と結果を再利用している時間の両方を含む．直近の推論呼び出しの所要時間だけを測らない．

同じホストで経過時間を測るときは単調増加時計を使う．センサーと推論が別ホストにある場合，
時刻を引き算する前に時計の対応を確立する．キャッシュと付随情報は一組として更新する．
次の推論を開始しても，使用中のキャッシュの基準姿勢を変更しない．

各接続部の座標系，軸の向き，単位，四元数の成分順，時刻の意味を記録する．
世界座標系の位置と機体座標系の速度は，そのまま交換できない．
カメラと機体の間の座標変換を明記する．出力を実機に接続する前に，
静止，直進，旋回の記録を使って変換を確かめる．

## モデルと機体の接続

確認した[上流の推論実装](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/ticvla.py)は，
2成分の出力層を作る．パッケージの推論は，現在の座標系から見た将来のXY位置を累積和なしで返すが，
論文は3成分の増分と積算を説明する．非同期推論の入口は6成分の状態を受け取り，
5成分に変換してから遅延を追加する．組み込み前に，固定したコードの版とチェックポイントに対して
接続仕様を検証する．論文中の記号だけでは，互換性のある入力テンソルは決まらない．

固定したコードとチェックポイントの定義に従って軌道を解釈する．現在の座標系を基準とする位置に，再度累積和を適用しない．
検証済みの追従制御で並進速度と旋回角速度に変換する．
位置・姿勢の増分を速度指令として直接渡さない．
[B2のSDKクライアント](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/b2/sport/sport_client.py)には
`Move(vx, vy, vyaw)` と `StopMove()` がある．APIが存在することだけでは，対象機体のファームウェアが
指令を受け付け，安全に実行する証拠にはならない．

## 実行状態

最初の実装では，観測のみ，準備完了，明示的に移動を有効にした状態，停止・異常状態を区別する．
観測のみの状態では移動指令を送らない．推論の初期化やエラーを契機に移動を有効にしない．

画像・機体状態の鮮度と意味情報のキャッシュの古さは，別々に確認する．意味情報の遅延は想定内でも，
現在の観測が古いと制御の前提が崩れる．非有限値や不正な形の出力を拒否し，速度と加速度を制限し，
古い指令を失効させる．異常後の再開には明示的な操作を必要とする．
具体的なしきい値は，遅延の測定結果と研究室の運用上限から決める．

ソフトウェアからの停止は通信と機体の制御に依存し，独立した非常停止ではない．
モデルによる移動の前に，操作者による介入と指令途絶時の機体の挙動を確認する．

## B2への適用

カメラの高さと画角，機体の占有範囲，指令への追従応答，停止距離は，論文の評価機体と異なる可能性がある．
これらは研究で確認する変数であり，モデル名から推定できる設定値ではない．
[段階的な検証手順](development.ja.md)から始め，実際の失敗を記録してから，調整や追加学習の必要性を判断する．

## 現在の実装範囲

失敗箇所を切り分けられるよう，次の処理を独立させている．

```text
inspect_target.py -> installed-system inventory (no SDK imports)
ZedCamera -> JPEG + receipt time + unverified source time
UnitreeStateReader -> finite state + receipt time + unverified frames
                  -> observation.json + frame.jpg
                  -> TicVlaPredictor -> offline future XY plan (no motor output)
synthetic replay fixture -> PathTracker -> candidate velocity + acceptance reason
```

| ファイル | 役割 |
|---|---|
| `tools/inspect_target.py` | Python 3.8以上の単独調査スクリプト．インストール・機体指令なし |
| `src/b2_tic_vla/types.py` | 画像，状態，計画，速度の明示的なデータ形式 |
| `src/b2_tic_vla/hardware.py` | 必要時だけ読み込むZED画像取得とUnitree状態購読 |
| `src/b2_tic_vla/recording.py` | 検証付きの移植可能な観測記録．上書きなし |
| `src/b2_tic_vla/inference.py` | ローカルファイルの厳密な照合と上流パッケージの同期呼び出し |
| `src/b2_tic_vla/checkpoint_conversion.py` | 新しいCPU環境で制限付き復元，全tensor名の維持，safetensorsのbit単位の読戻し照合 |
| `tools/acquire_model_assets.py` | 既定は計画表示のみ．明示的に承認したHub資材の版・容量・digestを照合して取得 |
| `tools/verify_checkpoint_conversion.py`，`tools/verify_tensor_loading.py` | 生成fixtureによるCPU変換と旧環境のtensor専用読戻し |
| `tools/verify_model_load.py` | 厳密なオフラインGPU読込．生成画像の推論には明示的なflagが必要 |
| `tools/predict_image.py`，`tools/render_prediction.py` | 保存画像・明示的な静止仮定での予測レポートと，一致する画像を内包した単独HTML経路表示．robot I/Oなし |
| `tools/profile_model_runtime.py` | 保存画像・仮定した状態を明示した段階別計測．機体の入出力なし |
| `deploy/checkpoint-converter.Dockerfile`，`deploy/converter-requirements.lock` | GPU環境を維持した，hash固定の独立したCPUソフトウェア環境 |
| `src/b2_tic_vla/semantic_cache.py` | 参照観測とcacheの一体公開，時刻・座標の検査．workerは始めない |
| `tools/record_camera_stream.py`，`tools/observe_async.py` | 時間制限付きの実カメラ・非同期cache実験．状態は仮定，移動指令なし |
| `deploy/unitree-state.Dockerfile`，`tools/verify_unitree_sdk.py` | 別のSDK・DDS状態環境と，通信を初期化しない合成符号化検査 |
| `src/b2_tic_vla/control.py` | 鮮度，座標系，制限値を確認する候補速度の計算 |
| `src/b2_tic_vla/cli.py` | 個別確認，記録，再生，推論の各コマンド |
| `examples/` | 合成データ，未検証の制限値，空の現地記録欄 |
| `tests/` | 合成データと模擬ベンダーライブラリによる単体・コマンドテスト |
| `deploy/Dockerfile` | 互換ベースの明示が必要な，ソースのみのテンプレート |

新しい予測アダプタは，非同期のDynaNav入口ではなく，
`ticvla.models.ticvla.TICVLA.predict`を呼ぶ．状態は`[vx, vy, yaw_rate, 0, 0]`，遅延はゼロ
とする．最後の二つは相対変位であり，この同期確認ではゼロになる．期待する出力形状は
`[1, horizon, 2]`で，返された相対XY位置に累積和を取らない．点列の時刻は確認した実装に
基づき0.1秒間隔とする．固定した版・重みの厳密な読込と生成画像の1回の推論は通ったが，
実際の時間対応は未検証である．[オフラインモデル確認](model-runtime.ja.md)を参照する．
現在のCLIは，一枚の画像を現在観測と意味情報の参照観測の両方に使う．複数画像を持つ
非同期観測履歴は再現していない．

`PathTracker`は評価用の基本的な前進限定の先読み追従器である．現在の機体座標系の目標
`(x, y)`から曲率`2*y/(x*x+y*y)`を求め，`yaw_rate = vx*curvature`を計算する．旋回速度の
上限を満たすよう前進速度を下げ，前進速度と旋回速度の変化も制限する．横速度は常にゼロ
とする．欠損，古い値，非有限値，不整合，未対応の入力に対しては，理由とゼロの候補速度を
返す．合成データで直進，曲線，古い画像のケースを確かめる．障害物との離隔，停止距離の
モデル，目標到達判定，時間最適な追従は実装していない．B2のナビゲーションとして検証済み
ではない．

ホストの受信時刻には単調時計を使い，ベンダーの時計は別のメタデータとして残す．撮影時刻を
検証済みとして扱う前に，同じホスト時計へ変換する必要がある．撮影時刻が未確認の場合，
他の確認を通過しても候補に`shadow_only_capture_time_unknown`と表示する．受信が新しい
ことだけでは，画像が直前に撮影されたとはいえない．保存データの再生は新しい時間区間で行い，
記録時刻を付け替えただけで新鮮なライブ入力として扱うことはできない．

現在の実装は`SportClient`の作成，`Move`の呼び出し，モーター指令の送信を行わない．
したがって，拒否時にゼロとなるのは**候補値**であり，物理的な停止ではない．今後の実機接続には，
時計・座標変換の検証，非同期キャッシュと参照情報の一体更新，制御権の管理，独立した指令の
期限切れ処理，受信側の挙動，操作者による介入の確認が必要である．
[現地手順](onsite.ja.md)に沿って，必要な証拠を集めてから接続する．
