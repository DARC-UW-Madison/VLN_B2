# 推論ランタイムの互換性

[English](runtime-compatibility.md) · [実機の基準情報](target-baseline.ja.md)

調査日：**2026-10-27**．候補と検証手順の資料であり，動作確認済みの構成ではありません．実施したホスト側の作業と保存先の前提は[実行環境構築](jetson-runtime.ja.md)に記します．コンテナとモデルは未検証です．

## 推奨する候補

Ubuntu 20.04，L4T 35.4.1，CUDA 11.4，ROS Foxy，ZED を維持し，**`nvcr.io/nvidia/l4t-jetpack:r35.4.1` を基底とした ARM64 コンテナ内で，Python 3.11.18 とソースビルドした PyTorch 2.2.2 を検証**します．ビルドと GPU 動作試験が必要な限定候補です．現時点の根拠から，ホスト OS や JetPack の更新が不可避とは言えません．

[実機](target-baseline.ja.md)ではネイティブ CUDA ドライバの問い合わせと GPU の数値演算に成功していますが，コンテナ内 GPU や PyTorch は未検証です．Docker はホストのカーネルとドライバのインターフェースを使用します．新しい CUDA イメージを選ぶだけで互換性が成立するわけではありません．

## 確認した制約

| 項目 | 根拠と判断 |
|---|---|
| Python | 本プロジェクトと [upstream](https://github.com/ucla-mobility/TIC-VLA/blob/main/pyproject.toml) は 3.10 以上を要求します．ホスト既定は 3.8.10 なので，アプリ用インタープリタをコンテナ内に用意します．候補は [3.11.18](https://www.python.org/downloads/release/python-31118/) とし，サポートが終了した [3.10 系列](https://www.python.org/downloads/release/python-31019/) を新規採用しません． |
| JetPack 5 の公式 wheel | [NVIDIA](https://developer.nvidia.com/embedded/downloads) の JetPack 5.1.2 用は `torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl` です．ARM64 GPU 向けですが，CPython 3.8 の ABI なので 選定した Python 3.11 では利用できません． |
| 一致する公式基底 | [NGC](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-jetpack/tags) で `nvcr.io/nvidia/l4t-jetpack:r35.4.1`，`linux/arm64`，圧縮 **4.9 GB** を確認しました．digest は `sha256:d1c8e971ab994235840eacc31c4ef4173bf9156317b1bf8aabe7e01eb21b2a0e` です．JetPack のライブラリを含みますが，提案する Python/PyTorch 構成は別途必要です． |
| 既製 PyTorch イメージ | [NGC](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch/tags) で確認できたタグは `nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3`，`linux/arm64`，圧縮 **5.66 GB** です．古い L4T タグであり，本件の Python 3.11 環境を保証しません．全条件を満たす公式完成イメージは確認できていません． |
| 学習用の指定 | [学習依存](https://github.com/ucla-mobility/TIC-VLA/blob/main/requirements-train.txt)の Torch 2.8.0/cu128 は，推論の最低条件と実証されたものではありません．[NVIDIA の Tegra 互換表](https://docs.nvidia.com/cuda/cuda-for-tegra-appnote/)では JetPack 5 の CUDA upgrade package は 11.8–12.2 が対象で，12.3 以降は非対応です．現在の CUDA 11.4 の確認結果から cu128 の実行可否を推定しません． |
| FlashAttention | [TIC-VLA](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/models/vlm.py) は `use_flash_attn=False` を明示しています．[InternVL3-1B](https://huggingface.co/OpenGVLab/InternVL3-1B/blob/main/modeling_internvl_chat.py) はこれにより言語側を eager attention にし，視覚側の FlashAttention も無効にします．初回候補には導入しません．旧 [FlashAttention 2.3.6](https://github.com/Dao-AILab/flash-attention/blob/v2.3.6/README.md) でも CUDA 11.6 以上が必要です． |
| 推論時の依存 | `ticvla.models.vlm` は `ticvla.data.vlm_data` を import し，そこから Lightning を import します．別途レビューした upstream 修正で切り離す場合を除き，モデルの import にも Lightning とその依存が必要です．学習・ロボット用依存を一括導入しません． |
| TensorRT | 現在の同期アダプタは PyTorch/Transformers を使用します．導入済み TensorRT 8.5.2 だけでは，この経路用の変換，キャッシュ API，エンジンは揃いません． |

## 検証範囲を限定したビルド案

ストレージ準備の後に，上記 digest の基底を使用します．イメージ層，ビルドキャッシュ，成果物は専用の SSD 領域に置きます．基底と依存の利用条件を確認してから利用します．

1. コンテナ内に独立した **CPython 3.11.18** と ARM64 wheelhouse を作ります．ホストとコンテナの vendor Python を置き換えません．
2. **PyTorch v2.2.2** と submodule のリビジョンを固定し，CUDA 11.4 と基底の cuDNN に対してビルドします．[CUDA の CMake 検査](https://github.com/pytorch/pytorch/blob/v2.2.2/cmake/public/cuda.cmake)は 11.0 以上を許容し，[ビルド設定](https://github.com/pytorch/pytorch/blob/v2.2.2/CMakeLists.txt)は 11.6 未満の fused attention を無効にします．これはソース上の候補条件であり，Jetson での全ビルド成功の証明ではありません．GCC 9.4 以上，C++17，`TORCH_CUDA_ARCH_LIST=8.7`，`USE_FLASH_ATTENTION=0`，`USE_MEM_EFF_ATTENTION=0`，`USE_DISTRIBUTED=1`，`USE_NCCL=0`，Gloo 有効，初回 `MAX_JOBS=4` を使います．Lightning と InternVL の `torch.distributed.is_initialized()` 呼び出しのため distributed API を残します．分散実行は不要です．
3. 同じ Torch と Python に対して **torchvision v0.17.2** をビルドします．初回の互換性試験では **Transformers 4.44.2**，**pytorch-lightning 2.2.5**，**torchmetrics 1.2.1**，**NumPy 1.26.4**，**timm 0.9.12**，**einops 0.7.0** を候補とし，Torch を置き換えずに推移依存も固定します．試験用の指定であり，検証済み lockfile ではありません．[Lightning 2.2.5](https://github.com/Lightning-AI/pytorch-lightning/blob/2.2.5/requirements/pytorch/base.txt) は Torch 2.3 未満，torchmetrics 1.3 未満を指定しています．InternVL の Transformers 4.37 以上と，TIC-VLA の 4.40 以上・5 未満の範囲にも合います．
4. TIC-VLA と将来取得する基底モデルの Python/config のリビジョンを固定し，import，processor/tokenizer の引数，実際のキャッシュ形式を確認します．同期 [`predict()`](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/models/ticvla.py) は従来の tuple または `layers` のあるキャッシュを扱い，[Transformers 4.44.2](https://github.com/huggingface/transformers/blob/v4.44.2/src/transformers/models/qwen2/modeling_qwen2.py) には従来形式を返す経路があります．学習側の厳しいキャッシュ処理は今回の対象外です．ビルド・import・キャッシュで失敗したら原因を記録し，限定した修正や指定変更を検討します．ホスト更新や際限のない依存探索へ拡張しません．

PyTorch 2.2.2 にはアダプタが必要とする [`torch.load(weights_only=True)`](https://github.com/pytorch/pytorch/blob/v2.2.2/torch/serialization.py) がありますが，公式の [2025 年の weights-only 脆弱性](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6)と [2026 年の weights-only 脆弱性](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p)の対象です．フラグの存在だけで安全なデシリアライズとは扱えません．初回候補は以下のモデル不要試験に限定します．外部チェックポイントを読む前に，レビューした修正のバックポート，または safetensors などへの変換・専用読込経路を別途検証する必要があります．いずれも今回未実装です．厳密なキー・形状検査と，制限のない pickle へのフォールバックをしない方針も維持します．

## 次の動作試験と合格条件

まず既存のローカルイメージとランタイムを調べます．適切なものがなければ，保存先を準備してから取得・ビルドします．これらの作業は未実施です．ビルドとイメージの確認後は `--pull=never`，`--runtime=nvidia`，`--network=none` と Hugging Face のオフライン設定で実行し，ロボットのデバイスやソケットを接続しません．次の確認にはモデル不要です．

- ARM64，Python 3.11，各ライブラリの指定バージョン，`torch.version.cuda == "11.4"`，CUDA 利用可否，compute capability 8.7 を確認します．
- FP32/BF16 の行列積，畳み込み，layer normalization，multihead attention を GPU で実行して synchronize し，有限の出力を要求します．BF16 対応，最大割り当てメモリ，実行時間を記録します．
- torchvision，Transformers，Lightning，`ticvla.models.ticvla` の import と，`torch.load` の `weights_only` 引数を確認します．`cuInit` や `import torch` の成功だけでは合格にしません．

合格し，上記チェックポイント読込の問題を解決した後に，基底モデルとチェックポイントのファイル，リビジョン，条件，容量，公式キャッシュの保存先を別途承認して取得します．信頼したローカル資産をオフラインで読み込み，厳密なチェックポイント互換性を要求し，記録済み画像列を同期アダプタへ渡します．有限の `(1, horizon, 2)` 出力と遅延・メモリを確認します．これはパッケージ推論の確認であり，非同期キャッシュ，制御，実時間性能の成立は未検証です．いずれの試験も OS/ROS/ZED の変更を含みません．
