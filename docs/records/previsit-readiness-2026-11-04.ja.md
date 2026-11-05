# 次回訪問に向けた準備確認：2026-11-04

[English](previsit-readiness-2026-11-04.md) · [記録一覧](README.ja.md) · [次回手順](../how-to/next-visit.ja.md)

> 文書種別：**記録**．対象はリポジトリ・文書の確認，外付けJetsonの実行確認，受信専用の現地診断の準備である．B2は停止したままで，接続しなかった．

## 見つかった点と変更

| 確認で見つかった点 | 変更と理由 |
|---|---|
| 既存の現地カードに，一般的な接続設定と今回の個体の次回作業が混在 | 短い確認表と，既存USB・Anker接続で実行する独立した手順へ分けた |
| 文書目次の表の一行が分離していた | 日英双方を修正し，表示構造・到達性を再検査する |
| i7のSDK・library・filterの不足情報が，その場のコマンド操作に依存 | 期限付きinventoryを追加．版を推測せず，権限・metadata不足を明記する |
| 従来の状態検査では，Jetsonに届くstreamの継続性を確認できていなかった | Jetson受信時刻付きJSONL記録，完了・件数の照合，継続性診断を追加 |

新しい`field_visit.py`は固定鍵を照合するSSHで標準libraryのPythonを実行し，`inspect_onboard.py`はinventoryと状態購読だけを行う．
指令publisherやrobot clientを作らない．firewallは対話しないsudoで読み，拒否は未解決として残す．
状態記録では，実際に読み込まれたDDS binaryのファイル・hashを識別できる場合があるが，source版を保証しない．
bridge，経路，firewall rule，system service，package，機体firmwareは変更していない．
以前に確認したi7のlink-local宛先二つのprofileをJetsonの非公開領域へ準備し，パスワードは含めなかった．

## 訪問前に実行した確認

| 確認 | 結果と意味 |
|---|---|
| 公開Gitの参照 | 更新して確認．公開mainは取込済みで，現地準備の作業branchは別である |
| 外付けJetsonの接続・保存先 | SSH成功，Tailscale・RDP service稼働，root・SSD空き容量を確認 |
| カメラ・モデル事前確認 | 既存path，重みdigest，image，ZED device割当ての検査が成功 |
| 実カメラ・モデルの時間制限付き実行 | JPEG 20枚，有限XY 30点の予測1回．読込11.362秒，推論12.640秒 |
| 終了処理 | カメラ・モデル両containerの終了コード0，cleanup errorなし，移動送信なし |
| SDK・DDS image | networkを無効化し読取専用にしたcontainerで，合成データのimport・符号化検査が成功 |
| ローカルのソフト試験 | 201件成功．不正・途中で切れた出力，timeout，受信0件，空白，一括到着，鍵・profileの範囲，metadata権限を検査 |
| 対象機のテスト・準備profileのplan | Jetsonでも201件成功．二つのprofileの接続しないplan確認が成功 |

新しいモデル試行は静止仮定で，ナビゲーション精度や継続制御を評価していない．既存の確認済みGPU imageを使った．
非公開の証拠はJetsonの`local/previsit-camera-check-01`と`local/previsit-sdk-check-01`にあり，画像・生成文はMacへ移していない．
SDK検査の隔離確認flagは未検証と報告される．隔離の根拠は，Python検査自身ではなく，実行したDockerの`--network none`指定である．

## 現地に残る確認

新toolをB2に対して実行する試験は，まだ行っていない．訪問時にi7アクセス，導入・実行版，ruleを確認し，実際の状態の継続受信へ進む．
記録する値の軸・取得元時計・画像との対応は未検証である．外付けからの直接DDS，bridge・router設定，アプリケーション中継，
実状態のモデル結合，物理的フィードバック・停止が，この確認で完成したわけではない．

[次回手順](../how-to/next-visit.ja.md)に従い，成功だけでなく失敗も記録する．報告を読めることや合成テストの成功を，未試験の物理経路の合格にはしない．

## 対象機での追記

source `cedb622`の176ファイルをhash照合して配置し，Jetsonで通常テスト201件を実行して成功した．
さらにsystem Python 3.8.10で両profileのplanとinventoryを自己検査した．自己検査の対象は外付けJetsonだけで，i7の構成・ROS状態受信を試した記録ではない．
結果は非公開`local/previsit-tool-check-01`にある．B2への接続・動作要求は行っていない．
