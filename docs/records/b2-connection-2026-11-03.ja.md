# B2接続・要求応答の調査記録

[English](b2-connection-2026-11-03.md) · [記録目次](README.ja.md)

**記録対象：2026-11-03の接続調査と，2026-11-04までに追記したDamp・センサー結果**．
手順書ではない．以下は実行場所・結果・未確認事項の記録である．

## hardwareの同定

調査した開発用PCはIntel i7だった．[公式のB2標準構成](https://www.unitree.com/b2/)は機体機能用i5と開発用i7だが，この個体の機体機能用host・追加Jetsonは未調査である．

| 項目 | 結果 |
|---|---|
| CPU | Intel Core i7-1265U，x86_64．Linuxから論理CPU 12個が見える |
| メモリ | Linuxから見える容量は約15.22 GiB |
| ストレージ | NVMe，512,110,190,592 byte，約512 GB |
| グラフィックス | PCI機器一覧にIntel graphicsあり．このPCにNVIDIA GPUは見つからなかった |
| OS・kernel | Ubuntu 20.04.6，Linux 5.15.76-rt53 |
| ネットワーク | 機体内部向けEthernet，USB Ethernet，Wi-Fi |
| その他のソフト | Dockerが稼働していた．コンテナの内容と全firewall ruleは未調査 |


## 5．バージョンは何で，何が動いたのか

| 要素 | 確認した版・状態 | 動いた根拠と未確認点 |
|---|---|---|
| i7のROS 2 | Foxyと既存Unitree message workspace | 状態受信と一回のAPI要求が動作 |
| i7でROSに使ったPython | system Python 3.8 | `/usr/bin/python3`で実行．別のconda Python 3.11へ置換していない |
| i7のDDS実装 | `rmw_cyclonedds_cpp`経由のCyclone DDS | 通信は成功．実際に読まれたlibraryの厳密な版・source revisionは未記録 |
| i7の独立Unitree SDK | 導入状況・版は未確定 | ROS messageによる診断には不要だった．構成調査は残る |
| B2のsport service API | `1.0.0.1` | 版照会への返答．robot firmware版やSDK package版ではない |
| 外付けSDK状態イメージ | 固定SDK source `814556d…`，SDK宣言版1.0.1，Cyclone DDS 0.10.2 | source・native library・合成状態の検査は成功．直接の実機状態検査は受信0件 |
| 外付けモデルイメージ | Python 3.11.18，PyTorch 2.2.2，Transformers 4.44.2 | GPUのmodel loadと実カメラ予測が別に成功 |

UnitreeのROS 2文書でもUbuntu 20.04・Foxyは試験した組合せに挙げられている．今回の限られた通信については，
推奨一覧と同じはずと仮定するより，実際にmessageが通ったことが根拠になる．全APIや継続運用を検証したわけではない．
別々の計算機でmessageを交換するPythonの版は，同じでなくてもよい．各processが，自分のPythonに対応するbindingを
使う必要がある．モデルコンテナに合わせてi7を更新するのではなく，動いた既存環境を保ち，不明な版を調べる．


## 6．具体的に何を実行したのか

完了した操作は次の順序だった．

1. 外付けJetsonから，USB Ethernetでつながるi7へSSH接続した．確認済みIPv6 link-local addressと固定したSSH host keyを使った．
2. i7の一時shellで，`/opt/ros/foxy/setup.bash`と既存Unitree message workspaceの`install/setup.bash`を読み込んだ．
   そのshellのlibrary・module検索先を設定する操作で，ソフトのインストールではない．
3. Cyclone DDSの出口にi7の内部Ethernetを，domainに観測済みの0を指定した．system Python 3.8で，ROS 2のPython library
   `rclpy`と既存Unitree message型を使った．
4. 名前付きの状態streamを購読した．12秒の試行で通常sport状態5,994件・低頻度状態240件を受信した．後の受信専用購読では，
   IMU・関節情報と，復号可能な前後カメラ画像も得た．
5. sport serviceのAPI版を照会した．後に，操作者の依頼と新しい状態の確認に従い，既にダンピング中の機体へ
   ROSの要求・応答messageで**API 1001のDampを一回だけ**要求した．要求に対応する返答を照合し，status 0を得た．立上がり・移動は要求していない．
6. 前後の状態がmode 7・error 0のままと確認し，一時プログラムを終了した．操作者も，変化なし・ダンピングのままと報告した．

この操作には，**別々の二つの通信**がある．

```text
External Jetson <-- SSH --> temporary program ON the i7
                                  |
                       ROS 2 / Cyclone DDS
                                  |
                         B2 internal service
```

外付けプログラムのモーター指令を，i7の導入済み中継機能がSSHから自動転送したわけではない．SSHで**i7上に**一時プログラムを
起動し，そのプログラムがi7で要求を作った．このプロジェクトが導入した常駐中継serviceはない．

i7から見えるB2 serviceまではEthernet・IP・DDSで通信した．serviceは応答したが，それが動く物理hostや，そこからモーター制御基板までの
経路は調べていない．関節driverへアクセスしたり，内部の制御基板とモーターの接続方法を同定したりはしていない．
APIの応答からそこまでは推測できない．

i7上で計ったAPI往復は約1.34 msだった．SSH起動やJetsonからi7までの時間は含まず，実際の姿勢変化の時間でもない．
既にダンピング中の要求は，立位からダンピングへ移る試験にはならない．


## 最初の移動試験の境界

操作者は立上がり，小さな前後移動，伏せを希望したが，転倒や想定以上の動きへの余裕はないと確認した．
**立上がり・移動の試験は実施していない**．後に，既にダンピング中と確認してからDampを一回だけ要求した．
操作者は変化なし・予期しない動きなしと報告した．姿勢遷移を試したわけではない．現在の場所で進めるのは観測と通信の切り分けであり，歩行の立上げではない．
短い移動要求でも，脚の可動域，胴体移動，追従誤差，転倒の範囲は制限できない．

現在公式から案内される[B2リモコン説明書](https://marketing.unitree.com/article/en/B2/Remote_Control.html)の8ページは，
ダンピングを**L2長押し＋Bクリック**，立位ロック・伏せの切替を**L2長押し＋Aクリック**とする．
別の文書・版から今回の個体のL1＋Aを確定しない．実際のリモコン・firmwareと研究室の手順を照合してから動かす．
ダンピングは支持を弱めて胴体が下がる・倒れる場合があり，安定した立位を保つことと異なる．

後に適切な場所を用意できたら，観察しながら段階を分ける．

1. 選んだ外付け経路で安定した状態受信と読取専用service応答を確立する．内蔵i7でAPI版の応答は得たが，外付け直接DDSは現在0件である．SSHで一時的な内蔵clientを起動し，条件確認付きDamp一回と別の受信専用センサー調査を行った．継続的な中継・制御の配置は，別途検討・検証する．
2. 十分な空間と現地操作者を確保し，研究室の手順で現地停止，リモコン優先，指令断の挙動を確認する．
3. まず姿勢だけの試験を検討し，立位の安定と制御した伏せへの復帰を観察してから移動へ進む．一連の要求をまとめて予約しない．
4. 後の前後試験では変位，速度，時間，独立した期限切れ，中止基準を定める．SDKの`Move`は歩数ではなく速度を受け取る．速度×時間は目安であって，実変位の保証された上限ではない．
5. モデルを使わないSDK試験として行う．TIC-VLAの予測品質は，通信・実行・物理的停止を検証した後の別の実験にする．

[B2 SDK](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/unitree_sdk2py/b2/sport/sport_client.py)には，
StopMove，StandDown，Dampが別の要求としてある．名前や返り値だけでは物理的な挙動を検証できない．
本プロジェクトに実機で調整済みの送信部や，姿勢・移動の自動連続処理はない．汎用exampleの既定速度を狭い場所の試験へ使わない．
