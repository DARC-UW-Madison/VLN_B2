# 計算機と通信を順に理解する

[English](network-topology.md) · [ドキュメント](README.ja.md) · [接続コマンド](field-network.ja.md)

この章は，外付けJetsonからプログラムを起動し，B2内蔵Intel PCで状態を受信して，ダンピングを一回要求した実験を
順に説明する．使う部品や用語は，その場で説明してから次へ進む．次の訪問で使うコマンドは
[接続手順](field-network.ja.md)，完了した調査の結果は[進捗](status.ja.md)にある．

## 1．それぞれの計算機は何をするのか

外付けJetsonと内蔵Intel PCは別の計算機である．モデルは外付けJetsonのNVIDIA GPUで動かしている．
内蔵Intel PCには，このモデルを導入・実行していない．

Unitreeの[B2公式仕様](https://www.unitree.com/b2/)は，標準構成を「機体機能用Core i5，ユーザー開発用Core i7」とし，
追加の計算機にはOrin NXなどの選択肢を挙げる．これは製品の構成説明であり，研究室の個体の全基板を調査した結果ではない．
今回ログインしたのは内蔵i7一台である．機体機能用i5の正確な型番・OSや，追加の内蔵Jetsonの有無は確認していない．

| 計算機 | 確認できたこと | このプロジェクトでの役割 |
|---|---|---|
| Mac | 外付けJetsonをSSHで操作できる | 編集，実験開始，結果の表示 |
| 外付けJetson | AGX Orinの64 GBクラス．GPUでTIC-VLAの読込・予測が成功 | カメラ取得とモデル推論．今後は経路追従も担当 |
| 内蔵開発用PC | Core i7-1265U．既存Ubuntu・ROS 2で動作した | 内部の状態・映像を受信し，一時的な調査プログラムを実行 |
| 機体機能用計算機 | 公式の標準構成はCore i5．実個体のhardwareは未調査 | メーカー既存の機体機能を維持する |
| 追加の内蔵Jetson | 未確認 | 搭載・必要性を仮定しない |

内蔵i7は，ユーザーがアプリケーションを開発するための汎用PCである．センサー処理，自己位置推定，記録，通信などに
使えるが，導入済みの各プログラムが元々何のために使われていたかは確定していない．これらの処理にTIC-VLAが必須な
わけではない．今回の大きなモデルにはNVIDIA GPUが有用だが，メッセージの送受信や制御プログラムの実行に，同じGPUが
必須とは限らない．B2の既存歩行制御が内部でどのような推論をするかも，今回は調査していない．

実測したi7の詳細は次のとおりである．

| 項目 | 結果 |
|---|---|
| CPU | Intel Core i7-1265U，x86_64．Linuxから論理CPU 12個が見える |
| メモリ | Linuxから見える容量は約15.22 GiB |
| ストレージ | NVMe，512,110,190,592 byte，約512 GB |
| グラフィックス | PCI機器一覧にIntel graphicsあり．このPCにNVIDIA GPUは見つからなかった |
| OS・kernel | Ubuntu 20.04.6，Linux 5.15.76-rt53 |
| ネットワーク | 機体内部向けEthernet，USB Ethernet，Wi-Fi |
| その他のソフト | Dockerが稼働していた．コンテナの内容と全firewall ruleは未調査 |

## 2．今回のケーブルは何につながったのか

USB Ethernet adapterは，接続先の計算機へEthernetの通信口を追加する機器である．今回はAnker adapterの
USB側をB2へ挿したため，**内蔵i7にネットワークinterfaceを一つ追加した**形になった．

```text
External Jetson Ethernet
          |
      LAN cable
          |
Anker Ethernet socket
          |
       USB-C
          |
Onboard i7
  A: USB Ethernet interface <---- external Jetson
  B: internal Ethernet interface ----> B2 internal network
```

ネットワークinterfaceとは，計算機がデータを送受信する接続口である．Linuxの`eth0`などはinterfaceの名前で，
IPアドレスではない．図のAとBは同じPCの一部だが，別の接続である．両者をつなぐnetwork bridgeは見つからなかった．
bridgeはinterface間でEthernetの通信を転送し，向こう側の機器とも通信できるようにする仕組みである．

今のケーブルでも**内蔵PCとの通信は既にできている**．実際にi7へログインできた．i7の向こうにある機体serviceまで
通信が届くかは別の問題である．PCにネットワークinterfaceが二つあっても，両者の通信を自動で転送するとは限らない．

Intel基板そのもののRJ45端子を外へ出す必要がある，と確認されたわけではない．内部Ethernetへ実際につながる外部端子
でも通信できる可能性がある．公式にはEthernet interfaceが記載されているが，今回の個体で，どの外部端子・adapter・
pin配列が内部networkへつながるかは未照合である．見慣れない多pin端子を，形だけでEthernet用と判断できない．
推測でadapterを購入したり，汎用USB hubを未確認のEthernet変換品の代用としたりしない．次回，研究室と端子ラベル・
該当マニュアル・付属品一覧を照合する．メーカーの取扱手順に従い，通電した不明端子を抜き差しして調べない．

## 3．IPv4，IPv6，interfaceごとのアドレス

**IPv4は，四つの数を点で区切るIPアドレスの方式である**．`192.168.10.20`はIPv4アドレスそのもので，
IPv4とは別物ではない．`192.168.0.0`から`192.168.255.255`は私設network用の範囲だが，`192`で始まる全アドレスが
私設用という意味ではない．[RFC 1918](https://www.rfc-editor.org/rfc/rfc1918)に定義されている．

IPアドレスは，interfaceの通信上の宛先を識別する．subnet prefixは，どの宛先を直接つながる範囲と扱うかを示す．
例えば`/24`なら，先頭の三つの数が共通の範囲である．route，つまり経路設定は，宛先に応じてどのinterface・次のrouterを
使うかを決める．ケーブルが物理経路を作っても，互いのアドレス設定と返信経路が成立している必要がある．

説明用に，あるPCの内部interfaceを`192.0.2.20/24`，USB側を`198.51.100.20/24`とし，外部計算機をUSB側へつなぐ．
外部計算機に`192.0.2.10/24`を割り当てても，ケーブルが内部側へ移るわけではない．PCは，返信先が内部側へ直接つながる
宛先だと判断して，内部側へ返してしまう場合がある．これらは説明用アドレスで，実機設定ではない．

B2でもこの種類の返信経路の不一致を確認した．ケーブルはUSB側へ入るが，i7は外付けJetsonへ返信するIPv4経路に内部側を
選んでいた．USB側にはIPv4設定の重複もあった．直接のIPv4試験は失敗した．アドレス・経路の問題を示す結果であり，
追加のfilteringやDDSの問題まで否定する結果ではない．

**IPv6**は，コロンで区切って表記する別のIP方式で，同じケーブルで使える．`fe80::`で始まる*link-local*アドレスは，
直接つながる機器間で使えるため，既存のIPv4設定を先に修理しなくても通信できる場合がある．末尾の`%INTERFACE`は送信側の
出口を選ぶ指定である．今回はこれでi7へSSH接続できた．internetの経路やB2上のTailscale，機体IPv4のIPv6変換は使っていない．

SSHはSecure Shellの略で，相手へ認証付きでログインし，プログラムを実行する仕組みである．実行場所は接続先である．
そのため，外付けJetsonが内部networkへ直接届かなくても，SSHでi7へ入って実行したプログラムは，**i7自身の内部Ethernet**を使える．

物理的な差込口と，TCP・UDPの*port番号*も別である．ソフトウェアのport番号は，IP通信でどのアプリケーションが受け取るかを
区別する番号で，ケーブルの差込口を指定しない．serviceのIPやport番号が分かっても，物理端子の位置は特定できない．

## 4．ROS 2，DDS，Cyclone DDS，SDKの関係

まず行いたいのは，プログラムで機体の状態を読み，動作を要求することである．そのために，データ形式と運び方を相手と合わせる．

**DDS（Data Distribution Service）**は，プログラム間でデータをやり取りする仕組みである．messageは構造を持つデータ一件である．状態の場合，配信側が
messageをpublish，つまり配信し，受信側が*topic*という名前付きstreamをsubscribe，つまり購読する．相手を発見して，合うデータを
交換する．topic名とmessageの構造を合わせる必要がある．DDSのdomainは通信相手の論理的なgroupを番号で分けるもので，
内部networkではdomain 0を観測した．同じ番号にするだけで物理経路やIP通信が成立するわけではない．

**Cyclone DDS**は，DDSの仕組みを実装したソフトウェアの一つである．通信を担当するもので，モデル，robot driver，
追加の計算機ではない．

**ROS 2**は，ロボット用ソフトを組み立てる枠組みである．実行中の構成要素を*node*と呼び，nodeがtopicへ配信・購読できる．
今回の環境では，ROS 2は`rmw_cyclonedds_cpp`という通信adapterを介してCyclone DDSを使った．message workspaceは，構築済みのメーカー用message packageと環境設定ファイルを含むディレクトリである．Unitreeのmessage定義は，
機体速度やAPI要求のheaderなど，データにどんなfieldが入るかを決める．ROS 2を入れるだけで，全メーカーの定義が入るわけではない．

**Unitree SDK2**は，Unitreeが用意したSoftware Development Kit，つまり開発用libraryである．
APIはプログラムから使う操作と要求・応答の形式を決めたもので，ここでいうrobot serviceは，その要求を受け付ける実行中の
プログラムを指す．ROS 2の`service/srv`機能を使うという意味ではない．今回のUnitree APIは，topic上の要求・応答messageで通信する．B2用clientには`Damp()`や
`Move(vx, vy, yaw_rate)`などの関数があり，必要な要求を作ってDDSで送る．例えば固定版の
[B2 client実装](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/unitree_sdk2py/b2/sport/sport_client.py)では，
`Damp()`が対応するAPI番号と空の引数で要求を送る．

同じ公開robot interfaceへ，互換性のあるプログラムから到達する方法が二通りある．

```text
Application -> Unitree SDK2 -> Cyclone DDS -> robot service
Application -> ROS 2 + Unitree message definitions -> Cyclone DDS -> robot service
```

これはアプリケーションから通信する二つの方法であり，SDKの下にROS 2を入れる，またはROS 2の下にSDKを入れるという
必須の関係ではない．Unitreeの[ROS 2文書](https://github.com/unitreerobotics/unitree_ros2)も，SDKを包まずに互換messageで通信できると説明する．
今回のi7の実験は**二つ目の方法**だった．i7に独立したSDK一式が導入されているかは確定していない．外付けJetsonには別の
SDK状態受信コンテナを準備してあり，通信経路が成立すれば直接通信用にSDKを使う候補は残っている．

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

## 7．Dockerと，以前のfirewall問題

Dockerは，依存ソフトをコンテナへまとめる仕組みである．コンテナはprocess・filesystemなどを隔離するが，Linux hostのkernelを共有する．
robot通信のprotocolではないが，ネットワーク設定が通信に影響する場合はある．

firewallはnetwork packetを条件に応じて通す・落とす仕組みである．Linuxの`FORWARD` ruleは，計算機の接続口から別の接続口へ
**通過するpacket**を扱う．その計算機自身が受信・送信する通信とは別である．以前のGo2-Wの記録では，Wi-FiとEthernetのbridgeを
通過する通信が，Dockerに関係する`FORWARD DROP` ruleで落ちていた．参考になる過去の失敗だが，今回も同じ原因だと証明するものではない．

今回成功したB2診断は，i7の既存ROS 2環境で直接実行し，新しいDockerコンテナ内では動かしていない．SSHはi7で一度受け取り，
i7のプログラムが内部interfaceから新しくDDS通信を送った．外付けJetsonのDDS packetをi7の向こうへ転送する必要はなかった．

外付けSDKコンテナの試験用設定はLinuxの`--network host`を使い，別のコンテナbridgeや，アドレスを書き換える転送（NAT）を作る経路ではなく，Jetsonの
interfaceを共有する．ただし，i7の二つのinterfaceをつないだり，hostのfirewallを無視したり，返信経路を修復したりはしない．
Dockerの[host networkの説明](https://docs.docker.com/engine/network/drivers/host/)と
[firewallの挙動](https://docs.docker.com/engine/network/packet-filtering-firewalls/)を参照する．

i7ではDockerが稼働していた．転送rule全体の監査や，正しいIP経路を確立した上での外付けSDK購読のhost直接実行・container実行の
比較はまだ行っていない．したがって，Docker・firewallの問題を全て排除したとは言えない．確定したのはi7内で始まる経路が通り，
外付けからの直接経路は通らなかったことまでである．この試験のためにfirewallを無効化したり，Go2-Wの転送ruleをコピーしたりはしていない．

## 8．次に何をするのか

まず，i7の未記録のソフト・library版を調べ，firewall ruleを変更せず読む．次の起動時に，端子ラベルと内部networkへアクセスする
実際の接続先も確認する．その上で，次の二方式を選ぶ．

| 方式 | 仕組み | 残る作業 |
|---|---|---|
| 外付けSDKから直接通信 | Jetsonが，同定した内部networkへの接続を通してrobot serviceへ届く | 端子・経路，IPv4返信経路，host・containerでの受信，DDS設定を確認 |
| i7上のアプリケーション中継 | 小さなi7プログラムが内部状態を読み，決めた形式でJetsonへ送る．後には制限付き指令を受け取る候補 | protocol，時刻，通信断，制御権，指令期限を定めて検証 |

アプリケーション中継は，i7を汎用network bridgeにすることとは違う．アプリケーションのデータを受け取り，意図して定義した新しい
messageを作る．現在のUSB接続でも，内部DDS通信を丸ごと外へ公開せずに実現できる候補である．提案段階で，導入済みserviceではない．

最初は**状態の継続受信だけ**を確立し，動作済みの外付けZED画像と実状態を対応付け，指令なしでTIC-VLA予測を評価する．
状態をモデル入力へ使う前に，単位・軸・時刻の対応を確認する．実際の姿勢変更・停止・移動試験は，適切な場所で別に行う．
保存・合成データを使うソフト開発中はB2を停止したままでよい．[現在の進捗](status.ja.md)，
[センサー取得](built-in-sensors.ja.md)，[現地コマンド](field-network.ja.md)を参照する．

## 大学Wi-Fiを離れた運用

Macの管理通信と，robotのローカルな観測・制御通信は別の接続である．目指すモデル・制御アプリはJetsonで動くため，
将来の指令ごとにMacのSSH画面を開き続ける構成にはしない．アプリの寿命や操作者と切れたときの対応は，まだ実装・検証が必要である．
Tailscaleには下になるnetworkが必要で，Wi-Fiの電波は作れない．[オフライン運用](offline-operation.ja.md)に，
ローカルhotspot，直接SSH，通信断の確認を記す．管理アクセスは[アカウント・構築](jetson-bootstrap.ja.md)と
[リモートデスクトップ](remote-desktop.ja.md)を参照する．
