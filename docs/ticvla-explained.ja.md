# TIC-VLAの仕組み

[English](ticvla-explained.md) · [ホーム](../README.ja.md)

本稿は独自にまとめた解説であり，実験報告ではない．出典の確認日は2026-10-22．既定ブランチのコードは変わり得る．
説明中の例は理解のためのものである．対象機体は車輪のないB2である．

## 課題と構成要素

VLAはVision，Language，Actionの略である．ここでの課題はナビゲーションであり，
観測と言語指示を局所的な移動計画に変える．歩行制御は別の役割として残る．
チェックポイントには学習済みパラメータが保存されており，推論を実行するだけで自動的に更新されるわけではない．

[プロジェクトの説明](https://ucla-mobility.github.io/TIC-VLA/)では，遅い画像言語推論と速い行動予測が視覚エンコーダを共有する．
行動側は，現在の画像，機体状態，保存された意味情報の特徴，その時刻に関する情報を受け取る．
そのため，新しい意味推論が終わる前でも，現在の視覚情報を利用できる．

```text
Historical images + instruction -> VLM -> cached semantic features
                                                 |
Current image -> vision encoder -----------------+--> action expert
Robot state + cache age + motion since reference -+         |
                                                     local plan
                                                         |
                                               trajectory tracking
                                                         |
                                            robot walking controller
```

図の上段は過去の画像と言語指示から意味情報を作る経路，中段は最新画像の経路，下段は機体状態と遅延の経路である．
行動予測に集めた情報から局所計画を作り，追従制御を通じて機体の歩行制御につなぐ．

## 推論，特徴，行動予測

上流のVLMはInternVL3-1Bである．画像を数値の特徴に変換し，言語生成によって場面と課題についての推論を行う．
「歩行者が横切っている」といった文は生成された内容であり，検証済みの物理的事実ではない．
[VLMの接続実装](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/ticvla_vlm.py)で，画像と言語を扱う入口を確認できる．

TransformerのKVキャッシュは，attentionで使われる数値の内部状態である．
確認した[行動モデル](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/models/ticvla.py)は最終層のvalue特徴を使い，
現在の視覚特徴とともに射影し，符号化した機体状態とcross-attentionで組み合わせる．
学習可能なaction queryは，将来の各出力位置を表す．
行動は数値として学習・予測されるのであり，推論文を手書きの規則で操舵に変換するわけではない．

## なぜ時刻を入力するのか

10秒時点の画像に対する推論が13秒時点で完成し，14秒時点の制御で使われるとする．
その意味情報は1秒前ではなく，4秒前のものである．その4秒間に機体は移動・旋回した可能性もある．
キャッシュの古さと基準時点からの移動が，古い情報を使う際の手がかりになる．
ただし，それによって見えていない歩行者の後の動きが分かるわけではない．

非同期ループでは，次のキャッシュを計算している間，最新の完成済みキャッシュを再利用する．
各キャッシュに，それ自身の基準時刻と基準姿勢を対応させて保持する．
[実行時の接続実装](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/ticvla.py)には，
バックグラウンド生成と完了確認があり，最初のキャッシュは完成まで待つ処理になっている．
初期化中は移動を無効にしておく．両方の処理を1つのGPUで実行できるが，非同期にしただけで計算資源の競合が消えるわけではない．

## 出力と閉ループ実行

論文と現在の実装を区別する必要がある．[論文](https://arxiv.org/html/2602.02459v2)は3成分の移動増分と，
その積算を説明する．現在のパッケージのコードは2成分の出力層を作り，
現在の座標系から見た将来のXY位置を，累積和を取らずに返す．
[学習設定](https://github.com/ucla-mobility/TIC-VLA/blob/main/configs/train_action.yaml)では将来の出力数は30である．
出力の解釈方法を選ぶ前に，コードの版を固定し，チェックポイントを調べる．

例えば相対位置の（1.0 m，0.2 m）は位置であり，速度ではない．
追従制御が局所経路から並進・旋回の指令を選ぶ．
[Spotのシミュレーション用接続部](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/behavior/spot_test_ticvla.py)には，
前方の目標点を使う追従と指令の平滑化がある．将来の経路を予測しても，全経路を変更せずに実行する必要はない．
再び観測して，直近の指令を更新する．このフィードバックによって閉ループになる．

## 学習の方法

1. **VLMの教師あり学習：** ラベル付きの記録から，移動に関する推論文と経由点の文章を学ぶ．
   [ラベル作成処理](https://github.com/ucla-mobility/TIC-VLA/blob/main/data/s03_batch_annotate.py)ではGPT-5を利用する．
   これは機上での推論とは別の処理である．
2. **模倣学習：** 実演された軌道から移動を予測する方法を学ぶ．
   [データ読み込み処理](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/data/policy_data.py)は，
   行動側の現在画像を保ちながら，意味情報の遅延を最大10秒まで変える．
   [学習処理](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/training/train.py)ではVLMを固定し，
   予測したXY位置と教師データをSmooth L1で比較する．
3. **強化学習：** シミュレーションで行動した結果を使い，PPOで行動を改善する．
   [RL実装](https://github.com/ucla-mobility/TIC-VLA/blob/main/rl/fine_tuning/train_rl.py)は，
   行動モデルの一部のパラメータと，学習中に使う価値推定器を学習する．
   現在の[方策の定義](https://github.com/ucla-mobility/TIC-VLA/blob/main/rl/fine_tuning/ticvla.py)では，
   VLMを固定し，行動側の最後のcross-attention blockだけを更新する．
   [報酬の定義](https://github.com/ucla-mobility/TIC-VLA/blob/main/rl/env/rewards.py)では，
   到達・進捗に報酬を与え，衝突と不適切な速度に罰則を与える．

模倣学習では実演を見るが，実行時の方策は自分の誤差によって変わった状況に遭遇する．
閉ループの学習は，この違いに対応するために行う．ラベル作成やシミュレーションの学習中に将来の情報や特権的な情報を使っても，
実行中の方策がそれを観測できるわけではない．通常の導入では学習済みの重みを使い，B2でPPOを継続することはない．

論文の遅延インターフェースには向きの変化も含まれるが，確認したパッケージの行動入力は，
速度，XY変位，遅延で構成され，独立した角度差の成分はない．再現するときはこの違いを保つ．

## 評価とB2への接続

DynaNavは評価・学習用の環境であり，機上で常時動かす必要がある処理ではない．
動的なナビゲーション課題を繰り返し試すために使う．報告された成功率は課題の定義と評価機器に対する結果であり，
無衝突やB2への適用成功を保証するものではない．

今回の接続作業は，時刻付きの観測・状態の供給，キャッシュの付随情報の整合性，互換性のあるモデルの実行，
B2向けの制限付き指令への変換，停止と操作者の制御の検証である．
カメラの幾何条件，機体の通過余裕，追従応答，計算遅延は測定する必要がある．
深度，LiDAR，SLAM，独立した障害物監視を周辺システムに使うことは考えられるが，モデルのRGB・状態入力とは役割が異なる．

接続部の計画は[構成と仕組み](architecture.ja.md)，段階的な検証は[開発の手引き](development.ja.md)を参照する．
このリポジトリではB2での推論・移動はまだ確認していない．
