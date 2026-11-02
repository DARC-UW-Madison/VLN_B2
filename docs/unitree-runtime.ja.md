# Unitree状態受信用の独立した環境

[English](unitree-runtime.md) · [文書一覧](README.ja.md) · [現地のnetwork](field-network.ja.md)

## 目的と範囲

B2訪問前に，状態受信に必要なソフトウェアを準備する．調査済みJetsonのPython段階のイメージから，
ARM64・Python 3.11の別イメージを作る．ホストPython・ROS，検証済みGPUイメージは変更せず，
Torch，モデルの重み，カメラ，動作サービスも追加しない．

オフライン検査はネイティブDDS libraryとSDKの状態定義を読み，合成状態をserialize・deserializeする．
SDK channel factory，DDS participant，robot clientは初期化しない．network隔離はDocker側の前提で，
Pythonのflagだけで証明しない．成功してもB2のfirmware・topic・domain・QoSの互換性や，移動の許可にはならない．

## 固定した入力とライセンス

| 要素 | 固定した入力 |
|---|---|
| ローカルPython基盤 | `sha256:7bf4dcefa6ffc9448f910caa9192e559502062aa742baf8d10b95f6931c7381e` |
| CycloneDDS C core | 0.10.2，commit `9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd` |
| CycloneDDS Python | 0.10.2，lockにhashを固定したsource archive |
| Unitree SDK2 Python | source版`814556d15970dd2ecf1c9984e845ca02ab07e206`，元の宣言version 1.0.1 |
| その他のソフト・build tool | 合計12個の正確な入力を`deploy/unitree-requirements.lock`に固定 |

SDKは[BSD-3-Clause](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/LICENSE)である．
CycloneDDS C・PythonはEPL-2.0またはEDL-1.0を選べるため，EDLを選び表示を維持する．
[C coreの条件](https://github.com/eclipse-cyclonedds/cyclonedds/blob/0.10.2/LICENSE)と
[Pythonの条件](https://github.com/eclipse-cyclonedds/cyclonedds-python/blob/0.10.2/LICENSE)を参照する．
本レポのMITで再ライセンスしない．本家source，build情報，導入した表示は非公開イメージ内に維持し，
本レポで配布するのは独自のレシピ・検査で，バイナリイメージではない．

## SDKをsource importにする理由

SDK全体の変更していないsetup宣言は，CycloneDDS，NumPy，OpenCVを要求する．状態channel・IDL経路は
CycloneDDSと標準libraryを使うため，このイメージはSDKのdistributionを導入せず，固定sourceを
`PYTHONPATH`から読む．NumPy・OpenCVや無関係な画像・動画の部品を追加しない．SDK全体の宣言依存を
満たしたとは扱わず，`pip check`は導入済みCycloneDDS環境だけを確認する．他のSDK機能は依存・APIを別途確認する．

検査結果には`sdk_import_mode="pinned source; state path only"`と
`declared_full_sdk_dependencies_satisfied=false`を明記し，SDKのdistributionとの混在は拒否する．
sourceの実際の読込先，detachedした正確な版，元のsetup・licenseと全Python sourceのhash，
setupのAST literalを，setup.pyを実行せず確認する．ネイティブlibraryのパスと`/proc/self/maps`も，
専用の`/opt/cyclonedds`を使っている必要がある．

## Jetsonでビルドする

[レシピ](../deploy/unitree-state.Dockerfile)を使い，既存の基盤イメージを先に調べる．
以下はJetsonのコマンドであり，Macの設定作業ではない．

```sh
sudo env DOCKER_BUILDKIT=0 docker build --pull=false \
  --memory 4g --cpu-period 100000 --cpu-quota 200000 \
  --build-arg BASE_IMAGE=sha256:7bf4dcefa6ffc9448f910caa9192e559502062aa742baf8d10b95f6931c7381e \
  -f deploy/unitree-state.Dockerfile -t vln-b2-unitree:jp5 .
```

調査したホストにはbuildx pluginがないため，既存のlegacy builderを使う．どちらの計算機にも
新しいbuilderを導入しない．CMakeはC coreを2並列で`/opt/cyclonedds`へbuildする．
examples・tests・ddsperf，任意のSSL・security・SHM部品は，この独立候補内で無効にする．
ホストROS・networkの方針を無効にするわけではない．Python bindingは固定sourceから，このprefixに対して
buildする．CMakeは`/opt/sdk-build-tools`へ分け，`/opt/unitree`の実行用メタデータと混ぜない．

最初の候補はcore，Python binding，SDK wheelを作れたが，CMake 3.27.9のWHEEL情報により
`pip check`が失敗した．実行ファイルは動作し，互換性のあるTagも空のheader区切りの後に存在した．
成功した環境とは扱わず，失敗した試行を維持する．改訂レシピではbuildだけの道具を分け，SDKの状態sourceだけを
読む．本家メタデータを書き換えたり，実行用の依存検査を省いたりしない．正確なコマンド，ログ，終了コードは
Git対象外の`local/unitree-build`へ残す．

`/opt/runtime-metadata`には，固定版，元のライセンス全文，CMake cache，runtime・build toolのfreeze，
導入報告，Debian構成，SDK source manifestを置く．レシピがGitにあるだけでイメージを公開・共有しない．

## オフラインの受入検査

build成功後，新しい非公開の報告先を選ぶ．

```sh
mkdir -m 700 local/unitree-check-01
sudo docker run --rm --pull never --runtime runc --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/local/unitree-check-01,dst=/reports" \
  --entrypoint /opt/unitree/bin/python vln-b2-unitree:jp5 \
  /opt/runtime-tools/verify_unitree_sdk.py --report /reports/unitree-sdk-offline.json
```

Dockerの呼出し・image IDもJSONとともに残す．`CYCLONEDDS_PYTHON_NO_IMPORT_LIBS`は設定しない．
ネイティブの読込を省くと検査にならない．報告は0600で新規作成し，既存ファイル・symlinkを上書きしない．
失敗は記録し，勝手に固定版を変えない．

## ローカルで確認した結果

改訂buildとオフライン検査は外付けJetsonで成功した．イメージは`vln-b2-unitree:jp5`，IDは
`sha256:4a61fa33e9c016b8cc21829c3b254553e20b75379fcda83ff64592529fe72f1b`である．
Python source 202個，実際に読み込んだ専用ネイティブlibrary，合成SportModeStateの
516バイトへの符号化・復元一致を確認した．DDS entity・robot clientは作っていない．
build試行02と`local/unitree-check-01`に呼出し，報告，成功の終了コードを維持する．
受信試験に向けたソフトウェアの準備であり，実B2への接続結果ではない．

## 最初の機体接続

[現地手順](field-network.ja.md)でケーブル・ポート，subnet，未使用IP，interface，domain，復旧経路を
確認するまではB2へ接続しない．その後，確認したinterface・domainを明示し，本プロジェクトとSDK sourceを
マウント・`PYTHONPATH`で指定して，状態の購読を行う．これは別の受信専用network試験で，
DDSの発見・購読の通信は送るが，モーター指令は送らない．実際のmessageの項目，単位，軸，時刻を確認してから
画像と組にする．制御権，リモコンの優先順位，指令断，停止は後の受入検査であり，Ethernet接続だけで導入完了とはならない．

### 準備した受信専用コマンド

現地のnetwork確認後，実際の有線`IFACE`と研究室の`DOMAIN_ID`を代入する．
これは**雛形であり，機体で実行した記録ではない**．オフライン検査と違い，機体LANへの到達に
`--network host`を使い，SDK初期化では明示したinterfaceを選ぶ．管理Wi-Fiを維持し，機体LANを大学へ
bridge・NATしない．状態の件数と実際の有限sampleを確認する．終了コードゼロだけでは受信の証明にならない．
測定前のframe名はunknownのままにする．新しい出力フォルダを使い，image ID・実際の呼出しも報告と一緒に残す．

```sh
mkdir -m 700 local/state-visit-01
sudo docker run --rm --pull never --runtime runc --network host --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/local/state-visit-01,dst=/reports" \
  -e HOME=/tmp -e PYTHONPATH=/workspace/src:/opt/vendor/unitree_sdk2_python \
  --entrypoint timeout vln-b2-unitree:jp5 -k 5s 15s \
  /opt/unitree/bin/python -m b2_tic_vla state \
  --interface IFACE --domain-id DOMAIN_ID --seconds 3 --output /reports/state.json
```
