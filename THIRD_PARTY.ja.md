# 外部資料と利用条件

[English](THIRD_PARTY.md)

以下は参考資料と任意の実行時依存先である．外部コード，モデル，パッケージは同梱しない．
ホストやコンテナの構築を明示的に実行した場合に，外部ソフトウェアを別途導入する．
独立して実装したアダプタは既存の公開APIを呼ぶ．模擬テストでは実際の外部実行環境を
読み込まない．更新確認日：2026-10-27．既定ブランチへのリンク先は変更されるため，
実モデルや実機での実験前に正確な版を固定する．

| 資料 | 出典 | 現在の扱い |
| --- | --- | --- |
| TIC-VLA論文 | [arXivの第2版](https://arxiv.org/abs/2602.02459v2) | 手法の出典として引用する．論文の結果をB2での検証と扱わない |
| TIC-VLAのソフトウェア | [リポジトリ](https://github.com/ucla-mobility/TIC-VLA)と[確認した版のライセンス](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/LICENSE.md) | `9fa6f8b`のAcademic Software Licenseを確認した．import検査用のソースだけをプロジェクト外へ取得した．本プロジェクトへのコードのコピーはない |
| TIC-VLAのチェックポイント | [公式リポジトリが案内する配布先](https://huggingface.co/datasets/handsomeYun/TIC-VLA/blob/main/TIC-VLA-model.ckpt) | 未取得．利用前に対象物の条件を確認する |
| InternVL3-1B | [モデルの配布先](https://huggingface.co/OpenGVLab/InternVL3-1B) | ベースモデルの候補．組み込みに必要な利用条件と版の確認は未実施 |
| Unitree SDK2 Python | [B2クライアント](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/b2/sport/sport_client.py)，[BSD-3-Clauseライセンス](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/LICENSE) | APIと`814556d`のライセンスを確認した．実行に使う版，依存先，ファームウェアとの互換性は未確認 |

確認したTIC-VLAのソフトウェアライセンスは，学術・非営利研究者による所定の教育・学術研究用途を認め，
派生物を含むソフトウェアの第三者への移転を禁止している．研究利用できることは，
改変した上流コードを公開してよいことを意味しない．利用や共有の前に該当する許可を確認する．
このリポジトリはその許可を付与しない．上流の利用条件の全文を読むこと．

チェックポイントの配布ページにはデータセット単位のライセンス表示がある．
その表示がソフトウェアの条件を上書きしたり，すべての成果物を包含したりすると仮定せず，
対象の重みと依存先に適用される条件を記録する．

実際に採用する依存先には，正確な版，ライセンスの出典，用途，再配布の有無，
必要な表示，確認結果を追記する．制限付きの成果物は承認された保管先に置く．

[MITライセンス](LICENSE)の対象は本プロジェクトの独自コードと文書に限る．
依存先，上流ソフトウェア，モデルの重み，データの利用条件を変更しない．
依存先のライセンスを，リポジトリ全体のライセンスとして採用するものでもない．

## 将来の研究と共有

独立して作成する接続部，評価ツール，文書はMITを継続できる．上流コードの改変，変換・追加学習した
重み，データセット，録画は，元の利用条件と適用される研究契約に基づき，公開を別途判断する．
学習や変換だけで元の制限がなくなるわけではない．利用制限のある成果物を再配布できると仮定せず，
手法と独自の成果を公開する．未公開の結果や個人を識別できる録画は，認められた研究室の保存先で管理する．

## 準備ツールの依存先

| 資料 | 出典 | 用途と配布 |
|---|---|---|
| ZED SDK／Pythonバインディング | [公式画像取得手順](https://docs.stereolabs.com/docs/tutorials/image-capture)，[Jetson Docker手順](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson) | 任意の`pyzed.sl`呼び出し．SDK，ドライバ，イメージ，ベンダーモデルは非同梱．導入・共有前に選択したSDK・イメージの条件を確認する |
| PyTorch | [公式文書](https://docs.pytorch.org/docs/stable/index.html) | ローカルの候補イメージ内で版を固定してソースビルドする．ホストのvenvにはなく，リポジトリのソースに非同梱．イメージの表示事項を維持し，互換性調査の制約により重みの読込は保留する |
| Transformers／InternVL実行環境 | [Transformers文書](https://huggingface.co/docs/transformers/index)，[InternVL3-1B](https://huggingface.co/OpenGVLab/InternVL3-1B) | 上流モデルの任意のローダー．ローカルのみ参照するが，信頼したモデルのPythonコードは実行する．ソースと成果物の版を固定する |
| Livoxドライバ | [公式ドライバ](https://github.com/Livox-SDK/livox_ros_driver2) | 参照のみで，実装上の依存先ではない．ソースは非同梱 |
| ベースコンテナイメージ | [NVIDIAのJetson資料](https://developer.nvidia.com/embedded/jetson-cloud-native/)，[提供元のJetPack EULA](https://docs.nvidia.com/jetson/jetpack/eula/index.html) | L4Tに一致する基底をOrinでのローカル利用用に取得し，Python段階をビルドした．イメージと各構成物の条件は引き続き適用される．バイナリイメージは同梱・公開しない |

標準ライブラリによる再生とテストにはベンダー環境は不要である．パッケージのビルドには
`setuptools>=68`を宣言しているが，`PYTHONPATH=src`での実行はビルドや導入を必要としない．
独立したアダプタへのベンダーコードのコピーはない．後から導入する依存先には推移的な依存が
加わる可能性があり，この表は再配布監査の完了や公開許可を意味しない．

## 任意のホスト管理・Pythonツール

Tailscaleは確認済みのホスト管理用SSH経路として利用し，アプリケーションには同梱しない．
Linuxクライアントのソースは[BSD-3-Clause](https://github.com/tailscale/tailscale/blob/main/LICENSE)であり，
tailnetへの登録，ホストされたサービスの条件，研究室のアクセス規則は別に扱う．
[公式インストーラー](https://tailscale.com/docs/install/linux)を使う．対象機へのTailscale経由のSSHは
確認済みで，クライアントの正確な版は未調査である．[pyenv](https://github.com/pyenv/pyenv)は
[MITライセンス](https://github.com/pyenv/pyenv/blob/master/LICENSE)の任意のユーザー用Python管理ツールであり，
同梱する依存先やGPU実行環境の隔離ではない．いずれも本Pythonパッケージから導入しない．
ホスト構築では，公式pyenvの`v2.8.14`，コミット`3fb25668b463ad38ac2db6092dbf476ef744c0ca`をGit管理外で使う．
[CPython 3.11.18](https://www.python.org/downloads/release/python-31118/)を，
[PSF License Agreementと同梱の表示事項](https://github.com/python/cpython/blob/v3.11.18/LICENSE)に従って
ユーザー用に導入した．インタープリタのバイナリは再配布しない．[実行環境構築](docs/jetson-runtime.ja.md)を参照する．
これらの参照の更新確認日：2026-10-27．
