# ローカルでのチェックポイント変換

[English](checkpoint-conversion.md) · [文書一覧](../README.ja.md) · [モデル資材の計画](model-artifacts.ja.md)

> 文書種別：**参照資料**．

独自ツール，生成fixtureの検査，その後の承認した実チェックポイントの変換を記録する．取得には
正確なファイルの承認と条件の確認が必要で，記録した17ファイルは2026-10-29に承認された．
変換しても元の制約は消えず，公開配布の許可にはならない．GPU読込と1回の生成画像推論は別の実行確認である．

## CPU変換を分ける理由

既存のJetson GPU環境はCUDA 11.4に合わせたTorch 2.2.2を使い，接続部ではチェックポイントの復元を
拒否している．新しい変換部は別のコンテナのvenvでTorch 2.15.0+cpuを使う．ナビゲーションの推論ではなく，
CPUのtensorを復元・コピーするため，新しいCUDAドライバとの互換性は不要である．ホストのPythonと
GPU環境は維持する．

ビルドはファイルシステムを作り，ツールを導入する．変換の実行は，そのツールを使う別のプロセスを
開始する操作である．イメージを作っても，ロボットの起動，モデル重みの取得，ファイルの自動変換は行わない．

## ビルドの入力と範囲

`deploy/checkpoint-converter.Dockerfile`は，確認したローカルのPython段階のイメージを完全なIDで
再利用する．`deploy/converter-requirements.lock`はCPython 3.11，aarch64，glibc 2.31向けの
全12パッケージと公式wheelのhashを固定する．Torchは公式CPU版のURLを明示し，通常のPyPI版から
CUDA依存を持ち込まない．確認したwheelの合計は197,569,238バイトで，導入後の容量，ベースの層，
ビルドキャッシュは別である．条件と表示は[外部成果物](../../THIRD_PARTY.ja.md)に記す．

Jetsonのプロジェクトルートで，ベースイメージと保存容量を確認して実行する．

```sh
sudo env DOCKER_BUILDKIT=0 docker build --pull=false \
  --build-arg BASE_IMAGE="$(sudo docker image inspect vln-b2-python:jp5 --format '{{.Id}}')" \
  -f deploy/checkpoint-converter.Dockerfile -t vln-b2-converter:cpu-v1 .
```

既存のビルド方式を使うため，ホストへbuildx pluginを追加しない．初回のBuildKitによる試行は，
そのpluginがなく導入前に停止したため，ログを維持する．ビルド時のインターネットは固定した
ソフトウェアの取得にだけ使う．hash，バイナリwheel，`pip check`，CPU版Torchの検査を要求し，
導入報告とfreezeを残す．成果物のイメージIDを保存する．ファイル名の一致やimportの成功だけでは，
モデル変換の検証にはならない．

## 生成fixtureの受入確認

新しいGit対象外の作業領域で実行する．再試行には別の番号を使い，過去の試行を削除・上書きして
失敗を隠さない．

```sh
mkdir -m 700 local/converter-fixture-01
sudo docker run --rm --runtime runc --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 2g --cpus 2 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/tools/verify_checkpoint_conversion.py,dst=/workspace/probe.py,readonly" \
  --mount "type=bind,src=$(pwd)/local/converter-fixture-01,dst=/work" \
  -e PYTHONPATH=/workspace/src --entrypoint python \
  vln-b2-converter:cpu-v1 /workspace/probe.py --workspace /work/fixture
```

試験は自分で小さなTorchチェックポイントを作って変換し，BF16の共有alias，転置したtensor，scalar，
空のtensor，NaNのpayload，符号付きゼロのバイトを確認する．未対応の直列化メタデータは，制限のない
pickleへ戻らず失敗する必要がある．公開されたモデルのチェックポイントを試すものではない．

次に，生成したsafetensorsを古いGPUイメージでも読めるか確認する．ここでもCPUのtensorを使い，
GPUは渡さない．

```sh
sudo docker run --rm --runtime runc --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 2g --cpus 2 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/tools/verify_checkpoint_conversion.py,dst=/workspace/probe.py,readonly" \
  --mount "type=bind,src=$(pwd)/local/converter-fixture-01,dst=/work,readonly" \
  -e PYTHONPATH=/workspace/src -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3.11 \
  vln-b2-runtime:jp5 /workspace/probe.py --verify-only /work/fixture/converted
```

`--runtime runc`でGPU連携を使わない．両方ともネットワークなし，通常のUID，capabilityの削除，
no-new-privileges，読み取り専用のroot，CPU・メモリ・プロセス数・一時領域の上限を設定する．
渡すのは確認したソース，試験ツール，fixtureだけで，2回目はfixtureも読み取り専用にする．ホーム，
機体のdevice，認証情報，モデルキャッシュ，Docker socketは渡さない．2 GiBはfixture試験の上限で，
実チェックポイントやモデル推論の必要量の見積もりではない．

## 記録したfixtureの結果

この結果・経緯は[記録](../records/conversion-checks.ja.md)を参照する．

## 承認した実チェックポイントの結果

この結果・経緯は[記録](../records/conversion-checks.ja.md)を参照する．

## 実際の変換の契約

別途承認した後，そのチェックポイントだけを読み取り専用，新しいプロジェクト用の出力領域を
書き込み可能でマウントする．ネットワーク・deviceなし，確認したメモリ・CPU・時間の上限，固定した
CPUイメージIDで実行する．入口は`python -m b2_tic_vla.checkpoint_conversion`で，期待するSHA256，
公開リポジトリと種別，固定版，新しい出力ディレクトリが必要である．未承認モデルの取得・変換コマンドは示さない．

1. 既存の出力，不正な来歴，通常ファイル以外の入力，容量超過，checksum不一致は復元前に拒否する．
   入力の既定上限は3 GiBである．復元後もhashを照合し，変更されない入力マウントを使う．
2. CPU版Torchと接続部の安定版の検査を要求し，CPU配置・`weights_only=True`で復元する．
   公開ファイルのメタデータが未対応でも，globalsを追加したり無制限のpickleを再試行したりしない．
3. 空でないtensor辞書かLightningの`state_dict`を受け付ける．対応するCPUのdenseなdtype・layoutと，
   キー数・名前の長さの上限を要求する．raw tensorの既定上限は4 GiBで，aliasも名前ごとに数える．
4. 元の全キーと値を残し，共有aliasは別々の連続したコピーにする．名前の削除，prefixの正規化，
   dtypeの変更は行わない．出力は元のチェックポイントより大きくなる場合がある．
5. `model.safetensors`を書いて読み戻し，全ての名前・dtype・shape・raw tensorのSHA256を比べる．
   バイトの比較により，NaNと符号付きゼロの違いも維持する．直列化のheaderはrawの上限に加え最大128 MiBを許容する．
6. 完了の印として`manifest.json`を最後に書く．元の識別情報，hash・容量，ツールのhash，ソフトウェアの版，
   上限，aliasの扱い，tensor別のhash，存在すれば正の整数の2項目の構成情報を残す．その他の学習用
   メタデータはコピーしない．検証済みmanifestのない失敗出力は未完了で，推論に使わない．

manifestは確認した呼び出し元の来歴と整合性を記録するもので，署名付きの真正性証明や再配布の許可ではない．
全状態の実際の互換性，基盤モデルのコード，記録済み画像による推論は別の受入確認である．
変換した実モデルとmanifestはGit対象外の承認した保存先へ置き，小さな生成fixtureの領域を
実モデルの保存場所として使わない．
