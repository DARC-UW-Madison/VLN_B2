# 外部資料と利用条件

[English](THIRD_PARTY.md)

以下は参考資料と任意の実行時依存先である．このリポジトリには同梱せず，自動導入もしない．
独立して実装したアダプタは既存の公開APIを呼ぶ．模擬テストでは実際の外部実行環境を
読み込まない．更新確認日：2026-10-23．既定ブランチへのリンク先は変更されるため，
実モデルや実機での実験前に正確な版を固定する．

| 資料 | 出典 | 現在の扱い |
| --- | --- | --- |
| TIC-VLA論文 | [arXivの第2版](https://arxiv.org/abs/2602.02459v2) | 手法の出典として引用する．論文の結果をB2での検証と扱わない |
| TIC-VLAのソフトウェア | [リポジトリ](https://github.com/ucla-mobility/TIC-VLA)と[ライセンス](https://github.com/ucla-mobility/TIC-VLA/blob/main/LICENSE.md) | 実現性の調査で参照した．このプロジェクトへのコードのコピーはない |
| TIC-VLAのチェックポイント | [公式リポジトリが案内する配布先](https://huggingface.co/datasets/handsomeYun/TIC-VLA/blob/main/TIC-VLA-model.ckpt) | 未取得．利用前に対象物の条件を確認する |
| InternVL3-1B | [モデルの配布先](https://huggingface.co/OpenGVLab/InternVL3-1B) | ベースモデルの候補．組み込みに必要な利用条件と版の確認は未実施 |
| Unitree SDK2 Python | [B2クライアント](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/b2/sport/sport_client.py) | APIを確認した．パッケージのライセンス，版，ファームウェアとの互換性は未確認 |

確認したTIC-VLAのソフトウェアライセンスは，学術・非営利研究者による所定の教育・学術研究用途を認め，
派生物を含むソフトウェアの第三者への移転を禁止している．研究利用できることは，
改変した上流コードを公開してよいことを意味しない．利用や共有の前に該当する許可を確認する．
このリポジトリはその許可を付与しない．上流の利用条件の全文を読むこと．

チェックポイントの配布ページにはデータセット単位のライセンス表示がある．
その表示がソフトウェアの条件を上書きしたり，すべての成果物を包含したりすると仮定せず，
対象の重みと依存先に適用される条件を記録する．

実際に採用する依存先には，正確な版，ライセンスの出典，用途，再配布の有無，
必要な表示，確認結果を追記する．制限付きの成果物は承認された保管先に置く．

このプロジェクトで独自に作る成果物のライセンスと権利者は未定である．
依存先のライセンスを，リポジトリ全体のライセンスとしてコピーしない．

## 準備ツールの依存先

| 資料 | 出典 | 用途と配布 |
|---|---|---|
| ZED SDK／Pythonバインディング | [公式画像取得手順](https://docs.stereolabs.com/docs/tutorials/image-capture)，[Jetson Docker手順](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson) | 任意の`pyzed.sl`呼び出し．SDK，ドライバ，イメージ，ベンダーモデルは非同梱．導入・共有前に選択したSDK・イメージの条件を確認する |
| PyTorch | [公式文書](https://docs.pytorch.org/docs/stable/index.html) | 任意の重み読み込みと推論．未導入・非同梱．Jetsonに対応するビルドを選び，利用条件と表示事項を記録する |
| Transformers／InternVL実行環境 | [Transformers文書](https://huggingface.co/docs/transformers/index)，[InternVL3-1B](https://huggingface.co/OpenGVLab/InternVL3-1B) | 上流モデルの任意のローダー．ローカルのみ参照するが，信頼したモデルのPythonコードは実行する．ソースと成果物の版を固定する |
| Livoxドライバ | [公式ドライバ](https://github.com/Livox-SDK/livox_ros_driver2) | 参照のみで，実装上の依存先ではない．ソースは非同梱 |
| ベースコンテナイメージ | [NVIDIAのJetson資料](https://developer.nvidia.com/embedded/jetson-cloud-native/) | 未選択・未取得・非同梱．テンプレートでは互換イメージの明示と，内容・条件の別途確認が必要 |

標準ライブラリによる再生とテストにはベンダー環境は不要である．パッケージのビルドには
`setuptools>=68`を宣言しているが，`PYTHONPATH=src`での実行はビルドや導入を必要としない．
独立したアダプタへのベンダーコードのコピーはない．後から導入する依存先には推移的な依存が
加わる可能性があり，この表は再配布監査の完了や公開許可を意味しない．
