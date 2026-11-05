# ドキュメント目次

[English](README.md) · [プロジェクト](../README.ja.md)

## 読む目的から選ぶ

- 仕組みを理解する：下の**解説**を読む．用語をその場で定義し，入力から出力まで説明する．
- 手を動かす：**操作手順**を使う．前提，実行場所，コマンド，期待する結果，終了・復旧を記す．
- 実装や設定値を調べる：**参照資料**を使う．コードの担当，データ形式，環境・設定の条件をまとめる．
- 何を実行し，何が起きたか調べる：[実験・構築記録](records/README.ja.md)を読む．日時，版，手法，結果，限界を保存する．
- 現在の到達点と次の作業を確認する：[進捗](status.ja.md)を読む．履歴の代用にはしない．

## 初めて読む順序

1. [モデル内部](explanations/ticvla-explained.ja.md)：画素と指示のトークンから，文章生成，数値の意味特徴，30個の予測位置まで追う．
2. [学習の仕組み](explanations/ticvla-training.ja.md)：お手本，ラベル，文章の教師学習，遅延付き模倣学習，強化学習を，実行時と区別する．
3. [経路からB2の動作へ](explanations/control-loop.ja.md)：一点から速度・旋回を計算し，要求の符号化，通信，測定の戻り，Go2とB2の違いを追う．
4. [計算機間の通信](explanations/network-topology.ja.md)：SSH，IPv4・IPv6，DDS，ネットワーク転送の選択肢をさらに詳しく読む．
5. [短いカメラデモ](how-to/live-camera-demo.ja.md)：準備済みJetsonで実行する．新規導入なら[初期構築](how-to/setup-from-scratch.ja.md)を先に行う．

最初の三章は起動コマンドではなく，仕組みを説明する．具体例を使い，論文，固定した公開版，この実装，設計案のどれを述べているか区別する．
表示された経路を機体指令と解釈する前に，順に読む．

## 仕組みを学ぶ

| 文書 |
|---|
| [ビルドで何を作り，どう実行するか](explanations/build-fundamentals.ja.md) |
| [予測経路からB2が動くまで](explanations/control-loop.ja.md) |
| [配置方針：計算機，コンテナ，ROS，センサー](explanations/deployment-design.ja.md) |
| [用語：Pythonパッケージからロボットまで](explanations/glossary.ja.md) |
| [ケーブル接続からロボットへの要求まで](explanations/network-topology.ja.md) |
| [TIC-VLAの中で画像と指示が経路になるまで](explanations/ticvla-explained.ja.md) |
| [TIC-VLAはどうやってナビゲーションを学習するのか](explanations/ticvla-training.ja.md) |
| [遠隔操作の画面・ログイン・通信](explanations/remote-access.ja.md) |

## 操作する

| 文書 |
|---|
| [内蔵センサー画像の表示と取得](how-to/built-in-sensors.ja.md) |
| [次回のB2訪問：構成を調べ，Jetsonで状態を受信する](how-to/next-visit.ja.md) |
| [B2訪問の確認表](how-to/field-card.ja.md) |
| [現地作業：Ethernet・内蔵計算機・独立した運用](how-to/field-network.ja.md) |
| [Jetsonのアカウント，Tailscale SSH，作業環境の分離](how-to/jetson-bootstrap.ja.md) |
| [操作手順：カメラと予測経路を確認する短いデモ](how-to/live-camera-demo.ja.md) |
| [別のAPを使わないオフライン運用](how-to/offline-operation.ja.md) |
| [現地での確認手順](how-to/onsite.ja.md) |
| [Macからのリモートデスクトップ](how-to/remote-desktop.ja.md) |
| [ZED画像をTIC-VLAに入力し，予測経路を表示する](how-to/run-camera-demo.ja.md) |
| [JetsonでTIC-VLAを動かすための初期構築](how-to/setup-from-scratch.ja.md) |

## 設定・仕様を調べる

| 文書 |
|---|
| [構成と仕組み](reference/architecture.ja.md) |
| [非同期推論：workerの前に参照情報を整える](reference/asynchronous-runtime.ja.md) |
| [外付けZEDカメラの準備](reference/camera-runtime.ja.md) |
| [ローカルでのチェックポイント変換](reference/checkpoint-conversion.ja.md) |
| [導入前に集める情報](reference/deployment-intake.ja.md) |
| [開発と実験の手引き](reference/development.ja.md) |
| [独自成果物と上流の研究用ソフトウェアのライセンス](reference/licensing.ja.md) |
| [モデル資材と検証した読込経路](reference/model-artifacts.ja.md) |
| [リポジトリのファイルから機体の動作まで](reference/runtime-flow.ja.md) |
| [システム全体像と無人起動](reference/system-overview.ja.md) |
| [Unitree状態受信用の独立した環境](reference/unitree-runtime.ja.md) |

## 記録と共同開発

[実験・構築記録の一覧](records/README.ja.md) · [共同開発ルール](../CONTRIBUTING.ja.md) · [第三者資料と利用条件](../THIRD_PARTY.ja.md)

英語版を公開の基本とし，日本語版を同時に維持する．文書種別と記述の分け方は共同開発ルールに従う．
