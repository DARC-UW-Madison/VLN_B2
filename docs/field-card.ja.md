# 初回訪問の確認カード

[English](field-card.md) · [詳しい手順と問題の切り分け](onsite.ja.md)

プロジェクトをJetsonにコピーし，ルートフォルダで端末を開きます．SSHやGitHubのURLは
不要です．以下のコマンドはモーターへ指令を送りません．

1. **導入済み環境を調べる** — Python 3.8以上，追加の依存なし．

   ```sh
   python3 tools/inspect_target.py --output local/target-inventory.json
   ```

2. **カメラ画像を一枚取得する** — Python 3.10以上，動作するZED SDKと`pyzed.sl`が必要．

   ```sh
   PYTHONPATH=src timeout -k 5s 30s python3 -m b2_tic_vla camera --output local/camera-01/frame.jpg
   ```

   JPEGを現地で開き，実際の前方の写り方と取付けを確認します．

3. **B2の状態を受信する** — SDK2／DDSが必要．`IFACE`を実際の有線インターフェースに置換．

   ```sh
   PYTHONPATH=src timeout -k 5s 15s python3 -m b2_tic_vla state --interface IFACE --seconds 3 --output local/state-01.json
   ```

   有効受信数とトピックを確認します．受信できても座標系の規約は未確認です．

4. **結果をローカルに残す** — `examples/onsite-notes.json`を`local/`へコピーし，既存の手動操作・
   停止手順，通信断時の挙動，座標系，カメラの取付け・時刻の情報を記録します．未確認はnullの
   ままにします．[詳細な記録項目](onsite.ja.md#3実物が必要な事実だけ記録する)を参照します．

依存環境が不足していたら，調査結果を保管し，対応する導入手順で準備してから再試行します．
コマンドを動かすためだけにシステムPythonを置き換えたり，Jetsonを書き直したり，Go2-Wの
SDK改変をコピーしたりしません．既存ファイルを上書きしないため，試行ごとに番号を変えます．

二つの確認が通ったら，[組にした記録とオフライン推論](onsite.ja.md#4画像と状態を組にして保存する)へ
進みます．非同期ライブ推論と実機への指令送信は別の作業です．生のレポートや記録はGit対象外の
`local/`に保管し，共有前に確認します．
