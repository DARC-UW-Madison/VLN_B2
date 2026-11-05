# 進捗

[English](status.md) · [ドキュメント](README.ja.md)

## 現在の段階

**2026-11-04時点**で，モデル・カメラの観測と，B2内蔵側の診断は別々の実験として動いている．
それらを結合したナビゲーション制御器にはなっていない．B2は操作者が停止し，実機以外の準備作業では機体設定を変更していない．

| 機能 | 現在の範囲 | 根拠 |
|---|---|---|
| 外付けZEDとTIC-VLA | 動きをゼロと仮定した画像・経路の表示が動作 | [デモ記録](records/camera-demo-checks.ja.md) |
| 内部の状態・映像 | 一時的なi7上のROS 2プログラムで受信 | [接続](records/b2-connection-2026-11-03.ja.md)，[センサー](records/built-in-sensors.ja.md) |
| 一回のDamp要求 | 既にダンピング中の要求に応答．操作者は変化なしと確認 | [接続記録](records/b2-connection-2026-11-03.ja.md) |
| 外付けSDK・ROS 2の機体通信 | USB接続での直接受信は未成功 | [接続記録](records/b2-connection-2026-11-03.ja.md) |
| 実状態のモデル入力 | 未結合．単位・座標系・時刻の検証が必要 | [状態の仕様](reference/asynchronous-runtime.ja.md) |
| 行動予測の反復 | 指令を送らない実験で予測したが，予測が出ない区間あり | [非同期の記録](records/async-shadow.ja.md) |
| 経路追従と指令 | オフライン候補追従器あり．実機移動用の送信部は未完成 | [構成の参照資料](reference/architecture.ja.md) |
| 実際のフィードバック・停止・走行 | 未検証 | [開発手順](reference/development.ja.md) |

準備再確認で実カメラ予測を一回実行し，現地診断を追加した．通常テスト201件がMac・Jetsonで成功し，接続しないprofile確認とnative Pythonでの自己検査も完了した．
実行条件・結果は[訪問前確認の記録](records/previsit-readiness-2026-11-04.ja.md)に記す．通常テストは実機動作を測らない．
配置したソースの版は非公開の`local/source-revision.txt`に記録する．ソースは研究室の公開リポジトリ[DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2)で共有している．
公開済みの`main`，作業ブランチ，Jetsonへ配置した版は別に確認する．
重み，画像，生ログ，実際のnetwork識別子はGitへ入れない．

## 次の作業

1. 次の起動時に，i7の未確認SDK・library版，経路，firewall ruleを変更せず調べ，外部端子の配線を同定する．
   bridge・ルーティング，アプリケーション中継，別の内部LAN接続を，同じ明示した受入試験で比較する．
2. Jetsonへの状態の継続受信を確立し，単位・軸・時刻・画像との対応を確認する．値を受信しただけでモデル入力として有効と扱わない．
3. その入力を，指令を送らない予測へ結合する．遅い意味情報の更新，最新観測による行動更新，開始・更新時の空白，異常を測定する．
4. 適切な場所で追従・指令期限・現地介入を別々に実装・検証してから，モデルによる移動へ進む．

[通信の仕組み](explanations/network-topology.ja.md)は接続方式を，[制御ループ](explanations/control-loop.ja.md)は状態・尺度・
フィードバック・推論時間を説明する．操作には[現地コマンド](how-to/field-network.ja.md)，実行済みの内容には[記録一覧](records/README.ja.md)を使う．

次回の操作は[実行手順](how-to/next-visit.ja.md)を入口にする．
