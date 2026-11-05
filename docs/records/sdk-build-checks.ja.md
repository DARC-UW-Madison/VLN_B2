# SDK状態イメージの検査記録

[English](sdk-build-checks.md) · [記録目次](README.ja.md)

> 文書種別：**記録**．実行した設定・検査の証拠を保存する．現在の操作手順とは区別する．

## ローカルで確認した結果

改訂buildとオフライン検査は外付けJetsonで成功した．イメージは`vln-b2-unitree:jp5`，IDは
`sha256:4a61fa33e9c016b8cc21829c3b254553e20b75379fcda83ff64592529fe72f1b`である．
Python source 202個，実際に読み込んだ専用ネイティブlibrary，合成SportModeStateの
516バイトへの符号化・復元一致を確認した．DDS entity・robot clientは作っていない．
build試行02と`local/unitree-check-01`に呼出し，報告，成功の終了コードを維持する．
受信試験に向けたソフトウェアの準備であり，実B2への接続結果ではない．
