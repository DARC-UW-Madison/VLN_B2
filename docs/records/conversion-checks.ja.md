# 重み変換の検査記録

[English](conversion-checks.md) · [記録目次](README.ja.md)

> 文書種別：**記録**．実行した設定・検査の証拠を保存する．現在の操作手順とは区別する．

## 記録したfixtureの結果

2026-10-29に試行02の構築が成功し，全hashの照合，`pip check`，CPU専用のimport検査が通った．
試行01はbuildxがなく導入前に停止し，記録を維持している．`vln-b2-converter:cpu-v1`のIDは次である．

```text
sha256:fbb182b51c0e6aee011dc43c4b7f1405493f9b17113531ea2d30a330525dc98c
```

論理サイズは11,073,891,434バイトで，再利用した既存Pythonベースを含み，取得量や追加ディスク使用量ではない．
Torch 2.15.0+cpu，safetensors 0.8.0，NumPy 2.4.6を含む．CPUのfixture試験と旧Torchの読戻しは
ともに終了コード0だった．元の6個の名前，BF16のalias，scalar・空・転置のtensor，NaNと符号付きゼロの
バイトを維持し，未対応globalは無制限に再試行せず拒否した．自作の元ファイルは2,799バイト，tensor出力は
512バイトだった．学習メタデータを省いた比較なので，実モデルの出力容量の見積もりには使えない．
このfixture試験では実モデルを取得・構築・推論していない．その段階で**MacとJetsonの全121件のテストが成功**した．

90秒上限の試験で，ネットワーク・GPUなし，通常のUID，rootとソースは読み取り専用，capabilityなし，
no-new-privileges，メモリ2 GiB，CPU二つ，プロセス128，一時領域64 MiBを使った．fixtureの報告，
イメージ・ソースのhash，資源設定の来歴は，Git対象外`local/cpu-converter-build/verification-01`へ
非公開で置き，ビルドの各試行も隣に維持する．公開ソースにはfixtureや個体の生の記録を入れない．
このfixtureの検査は実チェックポイントの検証ではなく，その後に承認・実施した結果を次に記す．


## 承認した実チェックポイントの結果

操作者が承認したTIC-VLAの元チェックポイントを公式Hub clientで取得し，hashを照合して，
2026-10-29にオフラインで変換した．元の1,324名と値・dtype・shapeの読戻しが通り，構成情報も
horizon 30・action 3層と一致した．元は1,938,501,547バイト，変換物は3,773,492,276バイトである．
aliasを実体化すると大きくなるが，重複を除いたモデルのパラメータが増えた証拠ではない．

元は標準Hubキャッシュに維持する．変換物とmanifestは，SSDの非公開領域
`/mnt/b2-research/VLN_B2/models`へのGit対象外symlinkを通し，`models/tic-vla-671de608-01`で参照する．
実際の実行はCPU専用Torch 2.15.0+cpu，ネットワーク・device・ホーム・認証情報なし，通常UID，
元は読み取り専用，CPU二つ，メモリ32 GiB，監視1,200秒の上限で成功した．この上限はpeak RAMの実測値ではない．

その後，変換物の厳密なGPU読込と生成画像の推論も成功した．結果，イメージ・ファイルのhash，
GPU権限，上限は[オフラインモデル確認](model-runtime.ja.md)に記す．元・変換物ともGitへ入れず，
Jetsonに置き，本家の条件を維持する．
