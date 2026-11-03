# モデル資材と検証した読込経路

[English](model-artifacts.md) · [文書目次](README.ja.md) · [実行環境の互換性](runtime-compatibility.ja.md) · [ライセンス](licensing.ja.md)

メタデータ調査は**2026-10-28**，取得・変換・実行の確認は**2026-10-29**である．
操作者は以下の正確な17ファイルを非公開の学術研究用として承認した．全ての容量・digestを照合し，
実際のチェックポイントを新しいCPU Torchで変換して，古いJetson GPU環境で厳密に読み込めた．
生成画像の1回の推論で有限なXY座標30個が返った．再配布の許可，実カメラの検証，実時間制御の成功ではない．

Torch 2.2.2に元のpickleチェックポイントは復元させない．GPU側は検証した変換済みsafetensorsと，
確認済みのローカル基盤snapshotを使う．独自ツールは実装済みで，結果・失敗・限界は
[オフラインモデル確認](model-runtime.ja.md)，変換の詳細は[変換の手引き](checkpoint-conversion.ja.md)に記す．
本家・構成要素の条件は元と変換物にも適用され，モデル本体はGitに入れない．

## 1．入力は別々の成果物である

確認したTIC-VLA実装の版は`9fa6f8b66b9e121d5df5df071297bba8e5353ebb`である．
[パッケージの情報](https://raw.githubusercontent.com/ucla-mobility/TIC-VLA/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/pyproject.toml)は
Python 3.10以降を要求する．[学習用依存](https://raw.githubusercontent.com/ucla-mobility/TIC-VLA/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/requirements-train.txt)は
Torch 2.8.0・cu128を指定するが，推論の最低版を示す証拠ではない．
[VLMのloader](https://raw.githubusercontent.com/ucla-mobility/TIC-VLA/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/vlm.py)は，
BF16，FlashAttention無効，信頼した独自Pythonコードを使って基盤モデルを作る．
学習済みモデルの利用には，コード，設定・tokenizer，基盤の重み，ナビゲーションの
チェックポイントが必要で，一つのインストールファイルではない．

| 入力 | 役割 | 現在の状態 |
|---|---|---|
| 確認した本家Python | TIC-VLAとモデル呼出しを定義 | 以前のimport検査用に，別の場所へソースだけを配置済み |
| InternVLの基盤snapshot | 学習済み視覚・言語モデルと文章・画像処理を定義・初期化 | 固定した承認済み資材を取得し，digestを照合済み |
| TIC-VLAチェックポイント | 学習済みナビゲーション・モデル状態を供給 | 承認した本体を取得・hash照合し，CPU変換済み |
| CPU変換環境 | 別に確認した実行環境で元を復元し，tensorデータを出す | CPUソフトウェアを固定して構築し，生成データの変換と旧環境の読戻しが成功 |
| 変換したtensorとmanifest | 変換の来歴を伴う，将来のJetson loaderの入力 | 実変換物と検証済みmanifestをSSDへ非公開で保存済み |

現在の独自アダプターは本家モデルを作った後，厳密に検査した全モデルの状態辞書を読み込む．
基盤とチェックポイントのサイズが似ていても，基盤重みを省ける証拠にはならない．
設定だけから構築する最適化は，本家・APIと完全な状態一致の確認を含む別の作業であり，今回は選んでいない．

## 2．公式メタデータから確認した正確な候補

次の識別子と想定サイズ・digestは，公式の[TIC-VLA dataset API](https://huggingface.co/api/datasets/handsomeYun/TIC-VLA?blobs=true)と
[InternVL model API](https://huggingface.co/api/models/OpenGVLab/InternVL3-1B?blobs=true)から得た．
承認した取得を準備する際は，変化する`main`ではなく固定した版を解決する．LFSの公開digestは
初期のmetadata調査時には照合用の想定値だった．その後の承認済み取得では，
冒頭に記したとおりローカル本体との一致も検証した．

| リポジトリ・ファイル | 固定候補版 | 想定バイト数 |
|---|---|---:|
| Dataset `handsomeYun/TIC-VLA`，`TIC-VLA-model.ckpt` | `671de608f39ccae41b66cbb24ab923c0275f8fb4` | 1,938,501,547 |
| Model `OpenGVLab/InternVL3-1B`，`model.safetensors` | `4415a3b810e636d11dfa86b0e9ba40bb00535aa8` | 1,876,463,472 |

想定するSHA256は次のとおりである．

```text
TIC-VLA-model.ckpt
376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036

model.safetensors
a8b67c54568417f3631723e6b3e120720eaa638e03e62dc25666c70e3ae3e484
```

TIC側で確認した一覧には
`.ckpt`があるが，公式のTIC safetensors版はなかった．InternVLには既に公式のsafetensorsがあり，
この案でpickle形式の基盤重みを別に取る理由はない．最初の推論に，TICリポジトリ内の
大きな学習データアーカイブは取得しない．

### InternVLの取得候補一覧

上記の固定版での取得候補は次の組である．条件と文脈の確認用にREADMEを含める．
実行入力として例示画像，動画，Git属性は不要である．重みと並べて配布されていても，
独自Pythonは実行コードとしてレビューする．

| ファイル | 想定バイト数 |
|---|---:|
| `README.md` | 35,849 |
| `added_tokens.json` | 790 |
| `config.json` | 6,326 |
| `configuration_intern_vit.py` | 5,548 |
| `configuration_internvl_chat.py` | 4,036 |
| `conversation.py` | 15,309 |
| `generation_config.json` | 69 |
| `merges.txt` | 1,671,853 |
| `model.safetensors` | 1,876,463,472 |
| `modeling_intern_vit.py` | 18,099 |
| `modeling_internvl_chat.py` | 15,971 |
| `preprocessor_config.json` | 287 |
| `special_tokens_map.json` | 613 |
| `tokenizer.json` | 7,033,297 |
| `tokenizer_config.json` | 7,330 |
| `vocab.json` | 3,383,407 |
| **合計** | **1,888,662,256** |

二つの取得候補の合計は**3,827,163,803 bytes**，約**3.83 GB・3.56 GiB**である．
実行用パッケージ，イメージのレイヤ，変換結果，一時ファイル，録画，ログは含まない．
変換後の容量，変換・推論時の最大メモリは実測まで未確認とする．
取得・変換前に，現在の空き容量を調べ，資源上限を定める．

### 承認された取得

2026-10-29に，操作者は上の固定した二つのリポジトリ，17ファイル，合計3,827,163,803バイトを，
SSD上の標準Hubキャッシュへ非公開の学術研究用として取得することを明示的に承認した．
再配布，機体の移動，無制限の読込の許可ではない．本家・構成要素の条件を維持し，
取得の照合，独自コードの確認，実際の推論を別の確認として扱う．

`tools/acquire_model_assets.py`は既定ではHub clientのimportや通信をせず，計画だけを表示する．
明示的な`--download`にはキャッシュと非公開の報告先が必要で，公式clientをtoken利用なしで使い，
固定したリポジトリの版，承認した容量，重みのSHA256，小さなファイルのGit blobを照合する．
許可リストだけを取得し，モデルコードは実行しない．通信しない4件を追加し，ローカルは125件になった．
ホーム，認証情報，GPUは渡さず，標準Hubキャッシュ，確認したスクリプト，専用の非公開報告先だけを渡す．

## 3．利用条件と取得承認は別の条件

[確認したTIC-VLA Academic Software License](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/LICENSE.md)は，
研究利用と，派生物を含む再移転を制限する．Dataset APIのCC-BY-4.0表示だけでは，
このチェックポイントと依存先の条件を解決しない．InternVLの情報にはApache-2.0表示と
Qwenのライセンス名・リンクが共存するため，バッジだけで全構成要素を確認済みとしない．
固定したmodel card，各部品の条件，用途を確認する．追加の著者許可や，成果物ごとの
条件確認の完了は主張しておらず，著者への連絡もしていない．

取得前に，正確なリポジトリ・種別，版，ファイル一覧，想定バイト数，キャッシュ先，適用条件を示し，
ユーザーの承認を得る．環境構築や一般的な準備の許可を，これらのモデルファイルの取得承認と
読み替えない．Import，変換テスト，最初の推論でモデルを自動取得しない．

## 4．別のCPU変換環境を使う理由

公式の[2025年のweights-only問題](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6)は
Torch 2.5.1まで，[2026年の問題](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p)は
2.9.1までを対象とする．記載された修正版はそれぞれ2.6.0と2.10.0である．既存の2.2.2で
`weights_only=True`を使うだけでは足りない．[PyTorchの方針](https://github.com/pytorch/pytorch/security/policy#backporting-security-fixes)は，
古い版へセキュリティ修正を戻さないと明記する．今回の候補について，完全なローカル修正を
レビューできたわけではない．

チェックポイントからtensorへの変換にはCPU演算があればよく，新しいCUDA環境は不要である．
別のCPU実行環境で一度だけ元を復元し，既存GPU環境へはtensorデータだけを渡す案である．
古いTorch全体が安全になる，モデルPythonの信頼が不要になる，他の部品も全て安全になるという
意味ではない．この特定の復元経路を限定する．

### 固定したCPUパッケージとfixtureの検証

確認時の[PyTorch公式CPU索引](https://download.pytorch.org/whl/cpu/torch/)には次の候補があった．

```text
torch-2.15.0+cpu-cp311-cp311-manylinux_2_28_aarch64.whl
Expected bytes: 170730380
SHA256: 97dc6b0a7cbad2109e615da3eac03df626c61e821e9486438b0248ba896178c6
```

最初のHEAD・メタデータの調査で容量とCPU・Pythonの対象を確認した．2026-10-29に，確認済みの
Focal・Python段階のイメージを再利用し，そのwheelと11個のhash固定の依存を
`vln-b2-converter:cpu-v1`へ導入した．`pip check`，CPU専用の検査，生成チェックポイントの変換，
Torch 2.2.2による読戻しが通った．記録したfixtureの経路の検証であり，実モデルの成功や，永久に現行な
ソフトウェアの選定を保証しない．手順，完全なイメージID，初回の失敗，上限は変換の手引きに記す．

通常のPyPI版ARM64 Torchへ置き換えない．確認した2.15.0の情報ではLinuxのCUDA 13.2依存が
宣言されていた．ARM64・Pythonのファイル名が合うだけではCPU専用配布と判断できない．
CPU用の取得元・版を明示し，変換のためにGPU構成まで変更することを避ける．
[CPU wheelの正確な参照](https://download-r2.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp311-cp311-manylinux_2_28_aarch64.whl)と
[小さなパッケージ情報](https://download-r2.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp311-cp311-manylinux_2_28_aarch64.whl.metadata)は
導入したソフトウェアの識別用で，承認したモデル資材は別途取得した．

## 5．読込の順序と検証の境界

1. 許可を確認し，正確な資材の取得承認を得る．変換レシピ・依存の計画は別にレビューする．
   現在のイメージとホスト環境を維持し，変換はLightning・古いGPU Torchと分ける．
2. CPU専用変換環境を作り，まず自作した小さなtensorで試す．NVIDIA runtime・GPU，機体，
   Docker socket，個人認証，書込可能なホームは渡さない．実変換は通信を無効にし，一般権限，
   メモリ・CPU・時間の上限を使い，確認した一つのチェックポイントだけを読取専用で渡し，
   専用の出力先を用意する．コンテナは影響を狭めるが，任意のコード実行が無害という証拠ではない．
3. 確認したCPU環境で，`weights_only=True`とCPU配置を使って復元する．Lightningの
   `state_dict`ラッパーを明示的に扱い，文字列キーの空でないtensor辞書を要求する．未対応の
   直列化メタデータ・型は拒否し，危険なglobalを自動許可したり，無制限pickleで再試行したりしない．
4. 全キー，各tensorのdtype・shape・値を維持する．保存領域を共有するtensorは，個別の連続した
   コピーを作るなど，方針を決める．受信側は全モデルのキーの厳密一致を要求するため，
   tied・重複名を黙って消さない．確保・書込前に，出力サイズと対応するtensor配置を検査する．
5. Safetensorsへ保存し，読み直してキー・dtype・shape・値の全てを抽出状態と比較する．
   元のリポジトリ・種別・版・digest，変換コード・イメージ・依存の版，出力digest，tensor一覧，
   aliasの扱い，検証結果を，秘密情報のないJSONへ残す．必要な構造メタデータは明示保存し，
   新しいmanifestにpickleを使わない．
6. 独自アダプターに，レビューしたsafetensors専用経路を追加する．厳密なキー・shape検査と，
   状態からhorizon・layer数を推定・検査する処理を維持する．予期しない形式を拒否し，
   古いGPU環境の`torch.load`へ戻さない．
7. 基盤モデルも，ローカルsafetensorsを使い，pickleへ戻らないことを強制する．現在の本家は
   `use_safetensors=True`を明示していない．独自loader wrapperで，本家実装をコピーせずに
   引数を渡せる可能性があるため，固定版のライブラリで実際の効果を確認する．本家のローカル
   改変が必要なら，その改変と移転の許可を別に確認し，来歴・条件を維持する．制限されたソースや
   結合イメージを，独自部分のMIT表示で公開しない．
8. Jetsonで，機体接続・指令送信なし，オフラインでモデル構築と一つの記録済み観測を試す．
   状態の厳密一致，期待するshapeの有限なwaypoint，実測メモリ・遅延を要求し，失敗も記録する．
   その後にライブ観測，さらに後に非同期・移動の結合を検討する．

独自アダプターには，手順6・7のアプリケーション側の読込部とwrapperを実装した．
`.safetensors`はCPUで`safetensors.torch.load_file`を使い，解析失敗時にpickleへ戻らない．
全キーのprefix正規化，構成の推定，全モデルのキー・shapeの厳密検査を維持する．それ以外の入力では，
`torch.load(weights_only=True)`を呼ぶ前に，安定版として解析できるTorch 2.10.0以上を要求する．
古い版，不明な版，プレリリースは復元前に拒否する．この最低版は記録した脆弱性への対応であり，
現在・将来の全ての脆弱性に対する保証ではない．

TransformersのAutoModel wrapperは，呼び出し元が別の指定をしても`use_safetensors=True`と
`local_files_only=True`を強制する．tokenizerとprocessorはローカル限定を維持する．OSの
ネットワーク隔離や，信頼した独自Pythonコードからの保護ではないため，固定版のコードを確認し，
実際の推論はネットワークなしで行う．モックを使った契約の検査を含め，ローカルの**全113件が成功**した．
実環境向けには，外部資材やモデル構築を使わない，生成tensorによる別の確認として
`tools/verify_tensor_loading.py`を用意した．その後，独自のCPU変換部でも，生成チェックポイントの
変換と異なる実行環境での読戻しが通った．実際の元ファイル，構成・読込の厳密な照合，1回の生成画像推論も通ったが，実入力の精度と非同期動作は未検証である．

### Jetsonで完了した生成tensorの検証

2026-10-29に既存のTorch 2.2.2イメージで実際の読込部の試験が成功した．生成したファイルは
4,504バイトで，もともとstorageを共有していた二つの名前を含む4キーである．FP32・BF16の
値・shape・dtypeを維持し，重複した両方の名前も残った．壊れたsafetensorsと古いTorchの
チェックポイント復元を拒否し，`torch.load`は呼ばなかった．通常の113件のテストもJetsonで成功した．
検査した入出力の境界の証拠であり，変換処理，実チェックポイント，基盤モデルの構築，ナビゲーション推論の成功ではない．

Jetsonのプロジェクトルートで，次のコマンドで再現できる．

```sh
sudo docker run --rm --runtime runc --network none --read-only \
  --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 1g --cpus 2 \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/tools/verify_tensor_loading.py,dst=/workspace/verify_tensor_loading.py,readonly" \
  -e PYTHONPATH=/workspace/src -e PYTHONDONTWRITEBYTECODE=1 \
  --entrypoint python3.11 vln-b2-runtime:jp5 /workspace/verify_tensor_loading.py
```

`runc`でNVIDIA runtimeを使わず，`--network none`でネットワークをなくす．読み取り専用のroot・
ソースマウント，通常のUID，capabilityの削除，`no-new-privileges`で処理の権限を制限する．
CPU，メモリ，プロセス数，一時領域にも小さな試験向けの上限がある．マウントするのは確認した
アプリケーションソースと検査ツールだけで，モデルキャッシュ，ホーム，Docker socket，センサー，
認証情報は渡さない．新しいイメージのビルドやパッケージ追加は不要だった．イメージID，ソースの版と
hash，報告のhash，上限と出力は，JetsonのGit対象外`local/access-setup`へ非公開で記録した．
再試験に失敗したら古い試行を残し，制限を無条件に緩めずに原因を調べる．

## 6．公式変換ツールも自動的な承認にはならない

Hugging Faceの[変換ガイド](https://huggingface.co/docs/safetensors/en/convert-weights)には公式converterがある．
その[実装](https://github.com/safetensors/safetensors/blob/main/bindings/python/convert.py)も元を読む際に
`torch.load`を使うため，適切に確認した環境で実行する必要がある．重複tensorの名前を除く方針もあり，
全状態の厳密検査をする独自loaderとの関係を調べる必要がある．

Hosted Convert Spaceは取得・変換の後，結果をアップロードするPRを作る．適用される許可なしに，
制限のあるTIC-VLA資材を渡したり，その公開動作を使ったりしない．来歴を確認した独立の
ローカルconverterは生成fixtureと承認した実チェックポイントで検証したが，本家提供・著者認定のconverterではない．
変換した重みにも，該当する本家の条件が残る．

## 7．保存先と再現性

承認したHugging Face入力は，公式Hubクライアントと固定した取得一覧を使い，
標準の`~/.cache/huggingface`へ取得する．準備済みJetsonでは，このパスはSSD上の
`/mnt/b2-research/VLN_B2/huggingface`を参照している．キャッシュの内部へ手でファイルを
置いたり，元のキャッシュ内容を変更したり，公開用プロジェクトへ大きな入力をコピーしたりしない．
必要なsnapshotだけを読取専用で渡し，取得後のファイルhashも保存する．

プロジェクトで変換した成果物は，Git対象外のプロジェクト内`models/`へ，ローカルmanifestと
作成したコマンド・レシピとともに置く．実際のファイルシステムと空き容量を確認する．SSDへの
配置が必要なら，コピーを散らす前に専用の保存計画を明示する．公開文書には版・想定hash・方法を
残せるが，重み，変換結果，非公開の許可文書はGitへ含めない．

本作業では，キャッシュ内のソース・重み・変換結果を公開したり，他の人へ再配布したりしていない．研究室での引継ぎ・
イメージ共有前に，相手への移転許可を確認する．実験記録は[開発の手引き](development.ja.md)，
実際に通った作業は[進捗](status.ja.md)を参照する．
