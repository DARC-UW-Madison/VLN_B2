# 初回訪問の確認カード

[English](field-card.md) · [詳しい手順と問題の切り分け](onsite.ja.md)

プロジェクトをJetsonにコピーし，ルートフォルダで端末を開きます．SSHやGitHubのURLは
不要です．以下のコマンドはモーターへ指令を送りません．

準備済みの外付けJetsonにはソースがある．以下のプロジェクト用コマンドの前に，ホストのvenvを
有効にする．システムPythonは3.8のままで，このvenvにもカメラ・Unitreeの依存先はまだない．
現地の起動試験と個人の認証情報の確認には，[システムのガイド](system-overview.ja.md#個人の認証情報と共有返却)を使う．

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
source .venv/bin/activate
python3 --version
```

## 今回の現地作業

[Ethernet・内蔵調査の手順](field-network.ja.md)を，次の順で進める．

1. 現地の復旧方法と，B2リモコンの位置調整・介入・停止手順を確認する．将来のSDK指令に対する優先順位も調べる．
2. Ethernetを挿す前に，外付けホストのインターフェース・経路を保存する．
3. B2のポート，既知のサブネット，未使用の接続IP，DDSドメインを確認する．
   管理接続を維持してリンクを作り，経路と到達性を調べる．
4. モーター指令なしでB2状態を受信し，研究室の正規アクセスで内蔵計算機，実際のサービス，制御権を特定する．
5. 外付けZED 2iをUSB接続し，内蔵カメラ・センサーの配信とMid-360の配線は別に調べる．
   内蔵USBをこのJetsonへ直接つなぐ経路はない．
6. 起動・認証情報を試し，HDMIあり・なしでWindows App・RDPを検証する．
   別のAPなしを前提に，復旧手段を確保してJetsonのAP・直接SSHを調べる．Macなしのオフライン処理の寿命も確認する．
7. 軸・時刻，センサーの元，残る依存先，次の行動を残す．移動，操作者との通信断時，実際の停止は後の検証とする．

準備した手順であり，実行済みではない．以下の確認にもSDK・カメラのバインディングが必要である．
個別の値と結果は`local/`へ置く．

## 観測の確認

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
   PYTHONPATH=src timeout -k 5s 15s python3 -m b2_tic_vla state --interface IFACE --domain-id DOMAIN_ID --seconds 3 --output local/state-01.json
   ```

   `DOMAIN_ID`を確認した研究室の値へ置き換え，有効受信数とトピックを調べる．
   DDSの発見・購読の通信は送るが，モーター指令は送らない．受信できても座標系の規約は未確認である．

4. **結果をローカルに残す** — `examples/onsite-notes.json`を`local/`へコピーし，既存の手動操作・
   停止手順，通信断時の挙動，座標系，カメラの取付け・時刻の情報を記録します．未確認はnullの
   ままにします．[詳細な記録項目](onsite.ja.md#3実物が必要な事実だけ記録する)を参照します．

依存環境が不足していたら，調査結果を保管し，対応する導入手順で準備してから再試行します．
コマンドを動かすためだけにシステムPythonを置き換えたり，Jetsonを書き直したり，Go2-Wの
SDK改変をコピーしたりしません．既存ファイルを上書きしないため，試行ごとに番号を変えます．

二つの確認が通ったら，[組にした記録とオフライン推論](onsite.ja.md#4画像と状態を組にして保存する)へ
進みます．非同期ライブ推論と実機への指令送信は別の作業です．生のレポートや記録はGit対象外の
`local/`に保管し，共有前に確認します．
