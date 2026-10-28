# ドキュメント目次

[English](README.md) · [プロジェクト](../README.ja.md)

研究の目的，ソフト・機器の仕組み，実際に行ったこと，次に行うことを説明するマニュアルである．
チャットの履歴ではなく，学習・運用の目的ごとに整理する．提案・雛形と記したコマンドは実行記録ではない．
個別の計測は承認した非公開の保存先へ置き，レビューした結論を該当する日英ガイドへ反映する．

## 推奨する読む順序

1. [配置方針](deployment-design.ja.md)で，各計算機の役割と，Docker・ROS・センサー配置が別の選択である理由を読む．
2. 不慣れな言葉は[用語集](glossary.ja.md)を参照し，[TIC-VLAの仕組み](ticvla-explained.ja.md)でモデルと遅延の処理を理解する．
3. [実行の流れ](runtime-flow.ja.md)と[ビルドの基礎](build-fundamentals.ja.md)で，ファイル・依存先・GPU実行・将来の機体要求を結び付ける．
4. 設計を実装済みと扱う前に，[実測構成](target-baseline.ja.md)，[システム全体像](system-overview.ja.md)，[進捗](status.ja.md)を確認する．
5. 現地では[確認カード](field-card.ja.md)を開き，詳細な[Ethernet手順](field-network.ja.md)に従う．移動は後の検証段階とする．
6. 共同開発・公開の前に，[開発](development.ja.md)，[共同開発ルール](../CONTRIBUTING.ja.md)，[ライセンス](licensing.ja.md)を読む．

## 概念と設計

| ガイド | 答える問い |
|---|---|
| [配置方針](deployment-design.ja.md) | 各計算機の役割は何か．Macにソース・重み・Dockerが必要か．コンテナの理由，ROS・センサーの配置，コンテナ間通信はどうするか |
| [用語集](glossary.ja.md) | PyTorch，HF，wheel，pyenv，venv，CUDA，checkpoint，image，SDK，DDS，watchdogとは何か |
| [TIC-VLAの仕組み](ticvla-explained.ja.md) | 言語・画像の推論，行動予測，学習，遅延補償はどう関係するか |
| [ファイルから動作まで](runtime-flow.ja.md) | 独自レポ，本家・モデルの別入力，コンテナのプロセス，通信はどう結び付くか |
| [ビルドの基礎](build-fundamentals.ja.md) | コンパイル，結合，wheel，CUDAコンパイル，イメージレイヤ，再ビルドとは何か |
| [構成と仕組み](architecture.ja.md) | 時刻，座標系，経路追従，制御境界の提案は何か |
| [計算機とネットワーク](network-topology.ja.md) | Ethernet・IP，SDK2・DDS，ROS 2，管理通信はどう違うか．B2内部の何が未確認か |
| [別のAPなしのオフライン運用](offline-operation.ja.md) | なぜMacを任意にできるか．Jetsonのホットスポット案，B2リモコン，通信断時の方針に何が必要か |

## 確認済み状態と導入

| ガイド | 答える問い |
|---|---|
| [進捗](status.ja.md) | 完了したこと，障害・未検証事項，次の成果は何か |
| [Jetsonの実測構成](target-baseline.ja.md) | CPU・GPU，メモリ，保存先，OS，SDK，通信のどの事実を確認したか |
| [システム全体像と無人起動](system-overview.ja.md) | 何のパス・設定を変えたか．何を分離したか．起動通信，認証情報，共有・返却はどうするか |
| [Jetsonの初期設定](jetson-bootstrap.ja.md) | ユーザー，SSH・Tailscale，Python，依存の境界をどう準備するか |
| [Jetsonの実行環境構築](jetson-runtime.ja.md) | SSD・Docker保存先，ネイティブCUDA，Python，実行環境をどうビルド・復旧したか |
| [実行環境の互換性](runtime-compatibility.ja.md) | 候補の版とモデル不要の検査は何が通ったか．なぜチェックポイント読込が保留か |
| [Macからの遠隔画面](remote-desktop.ja.md) | Windows App・RDP・xrdpのセッションはVNCと何が違うか．通常のHDMI利用を省く前に何を確認するか |

過去の調査日付を，現在も同じ状態であるという主張へ自動的に読み替えない．SSH・GPUの過去の
成功は，その検査の証拠であり，常時の到達性やTIC-VLA・実機の性能を示すものではない．

## 現地作業と実験手順

| ガイド | 答える問い |
|---|---|
| [初回訪問カード](field-card.ja.md) | 操作者は機体の前でどの順序で進めるか |
| [Ethernet・内蔵調査](field-network.ja.md) | ケーブル，IP，経路，DDS，内部サービスの所有者をどう調べるか |
| [現地での準備](onsite.ja.md) | 画像・状態，組にした記録，任意のオフライン推論をどう実行し，結果を読むか |
| [導入前に集める情報](deployment-intake.ja.md) | 推測した既定値を使わず，研究室・実機から何を得る必要があるか |
| [開発と実験の手引き](development.ja.md) | ツールの実行，段階的検証，失敗の記録，実験の再現をどう行うか |

次の雛形はGit対象外の保存先へコピーしてから使う．
[空の訪問記録](../examples/onsite-notes.json)，
[commissioning例](../examples/commissioning.json)，
[合成再生入力](../examples/replay.json)．
値は実機の運転許可やB2の上限を示すものではない．

## 共同開発，利用条件，ソースの案内

| 文書・ソース | 用途 |
|---|---|
| [共同開発ルール](../CONTRIBUTING.ja.md) | Gitのブランチ・コミット・レビュー，日英文書，AIレビュー，範囲を区切った並行作業 |
| [ライセンスの説明](licensing.ja.md) | 独自部分のMITと別に制限された本家の条件が共存する理由．コピー・派生物，将来の研究，成果物の公開 |
| [外部資料の一覧](../THIRD_PARTY.ja.md) | 確認した正確な出典，条件，来歴，未解決の許可 |
| [独自部分のライセンス](../LICENSE) | 本プロジェクトの独自部分に対する実際のMIT許諾本文 |
| [Pythonパッケージ](../src/b2_tic_vla/) | 独立したアダプター，CLI，推論検査，再生，追従候補 |
| [ツール](../tools/) | 対象機調査と，操作者が実行するWi-Fiヘルパー |
| [配置用レシピ](../deploy/) | 候補環境の定義と，モデル不要の検査 |
| [テスト](../tests/) | 合成・模擬入力の動作検査．実機の検証ではない |

公開の基準言語は英語とし，日本語版は`.ja.md`と`，`・`．`を使う．前提，コマンド，
不確実性，限界を含め，両言語を同時に更新する．ガイドを追加したらこの目次へ登録し，
プロジェクトREADMEへ別の一覧を増やさない．各仕組みの詳しい説明は担当する文書にまとめて
関連項目へリンクし，増え続けるチャット記録を複写しない．
