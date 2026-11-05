# ケーブル接続からロボットへの要求まで

[English](network-topology.md) · [ドキュメント](../README.ja.md)

> 文書種別：**解説**．通信の仕組みを説明する．機器の構成，実行したコマンド，測定結果は[接続調査記録](../records/b2-connection-2026-11-03.ja.md)，実行する確認操作は[接続手順](../how-to/field-network.ja.md)に記す．

## 1．プログラムをどこで動かすか

SSH接続は，別の計算機へログインし，そこでコマンドを実行する操作である．Jetsonの端末からi7へログインしてPythonを起動すると，
そのPythonはi7のネットワーク接続を使う．キー入力がJetsonから届いたからといって，Jetsonの接続を使うわけではない．

二つの構成を比較する．

```text
A. Jetson application -> Jetson network -> B2 robot service
B. Jetson SSH client -> i7 SSH server -> start an application ON i7
                                      i7 application -> B2 robot service
```

robot serviceは，姿勢変更などの要求を受け付ける実行中のプログラムを指す．AではJetsonがロボット用のデータを作り，送受信する．
BではSSHがプログラムの起動操作を運び，起動されたi7のプログラムがロボット用のデータを作り，送受信する．
Bでは，Jetsonのロボット通信をi7の向こうへ転送する必要がない．SSHでi7へ入り，ROS 2のプログラムを起動するのはBであり，
Jetson上のROS 2から直接通信するAとは異なる．

このマニュアルで「直接」とは，アプリケーションの通信相手の関係を指す．ケーブルが一本で直結するという意味ではない．
途中にスイッチや適切に設定したルーターがあっても，Jetson自身をロボットAPIの利用側にできる．

## 2．USB Ethernetアダプターは何につながるか

USB Ethernetアダプターは，USB側につながる計算機へ，ネットワークの接続口であるinterfaceを追加する．
USB側をi7へ挿せば，そのEthernet端子はi7の接続口になる．B2の中にある他のEthernet接続へ，自動的につながる機器ではない．

```text
Jetson -- Ethernet cable -- USB Ethernet adapter -- USB -- i7
                                                        |
                                      another i7 Ethernet interface
                                                        |
                                               robot internal LAN
```

LANはローカルなネットワークである．この章で「機体内部LAN」とは，機体の状態・動作要求のプログラムがデータをやり取りする
ネットワークを指す．i7がJetson向けと内部LAN向けの接続を持っていても，転送する仕組みを設定するまでは別々の接続である．

図のアダプターについて，メーカー名そのものを理由に使えないと判断するものではない．別のEthernet接続から内部LANへ入る方法も，
i7を経由してつなぐ方法もある．端子の形だけでは，どのLANにつながるか分からない．**機体内部LANへのEthernet接続**とは，そのLANへデータを送受信できる接続を指す．実際の端子との対応は配線の確認で決める．

## 3．同じケーブルで使うIPv4とIPv6

IPは，ネットワーク上の宛先とデータの配送を扱う仕組みである．送るデータを区切った一単位をpacketと呼ぶ．
IPv4とIPv6はIPの異なる版である．

| 項目 | IPv4 | IPv6 |
|---|---|---|
| 表記の例 | `192.0.2.10` | `fe80::1234` |
| アドレスの長さ | 32 bit | 128 bit |
| Ethernetケーブルでの利用 | 使える | 使える．同じinterfaceで両方使える |
| 接続成功から分かること | 試したIPv4の経路が通る | 試したIPv6の経路が通る．未試験のIPv4経路の成功は示さない |

IPv6のlink-localアドレスは`fe80::`で始まり，直接つながる範囲で使う．internetを経由する経路ではない．
`fe80::1234%eth0`の`%eth0`は，同じ種類のアドレスが複数の接続に存在し得るため，送信側の出口を選ぶ指定である．
既存IPv4のアドレス・返信経路が合わなくても，IPv6の設定ではローカルなSSH接続ができる場合がある．
IPv4をIPv6へ翻訳したり，IPv4の機体通信を直したりする操作ではない．[IPv6アドレスの仕様](https://www.rfc-editor.org/rfc/rfc4291)を参照する．

どちらのIPでも，経路設定が送信するinterfaceや次のルーターを選び，相手側にも返信経路が必要である．
外側のinterfaceへ内部側と似たアドレスを割り当てても，物理的にネットワークが結合するわけではない．
例えば，外付け計算機のアドレスが内部側へ直接つながる範囲に見えると，i7はUSB側から届いた通信の返信を内部側へ出してしまうことがある．
これは往路と復路が一致しない状態である．

物理的なEthernet端子と，TCP・UDPのport番号も別である．端子はケーブルを挿す口で，port番号は受信したIP通信を
ソフトウェアへ届けるための番号である．IPやport番号から，物理端子の場所は分からない．

## 4．DDSは二つのプログラムの間で何をするか

ある機体プログラムが速度を繰り返し測定し，別のアプリがその値を受け取る場合を考える．ケーブル以外にも，
共通のデータ形式，相手プログラムを見つける方法，更新の受け取り方が必要になる．
DDSは**Data Distribution Service**の略で，別々に動くプログラムのために，これらの仕組みを定義する規格である．

messageは，項目と値を持つ一件のデータである．*topic*は，決まった型のmessageを流す名前付きのデータ列である．
*publisher*はそこへ書き込む側，*subscriber*は受信を申し込む側を指す．別の計算機の名前ではなく，プログラムの役割である．
次は仕組みを説明する例で，B2の実データ形式ではない．

```text
Topic: example/velocity
Record fields: forward_mps, lateral_mps, yaw_rate_rps
Producer: writes {0.20, 0.00, 0.05}
Consumer: receives those three numbers and updates its latest state
```

通信ライブラリが具体的に行う仕事は，次のとおりである．

1. 相手を発見し，どのtopic・型を配信するか，受信したいかを知らせる．domain番号で参加する論理的なgroupを分ける．
2. 対応する送受信側を組み合わせる．欠落しても次の値を使うか，再送して届けるかなどの受渡し条件も合わせる．
3. messageの各項目を，共通形式のbyte列へ変換する．これをserializeという．
4. 選択したネットワークinterfaceから送る．受信側はbyte列からmessageを復元し，利用するプログラムへ渡す．

topic名が同じでも，アドレスへ届かなければ通信できない．相手の発見には，複数の受信者へまとめて送るmulticastを使う場合がある．
SSHは通るが，発見用や実データのpacketはルーター・firewallで止まることもある．DDSが後の通信先として知らせるアドレスにも届く必要がある．
したがって，ping，SSH，DDSの受信は別々に確認する．

**Cyclone DDS**は，このDDSの仕事を実行するライブラリの製品名である．「Cyclone」は別の通信層や計算機を指さない．
プログラムがライブラリを読み込み，ライブラリが通信の接続先を作ってmessageを運ぶ．DDSには複数の実装があり，Cyclone DDSはその一つである．
[Cyclone DDSの公式実装](https://github.com/eclipse-cyclonedds/cyclonedds/tree/0.10.2)を参照する．

## 5．SDK2とROS 2がその通信を使う方法

APIは，プログラムが要求できる操作と，入力・出力の形式を決めたものである．Unitree SDK2は，機体のAPIを関数で使うための
開発用ライブラリである．B2用の`Damp()`を呼ぶと，対応する要求データを作り，DDSで送り，返答を処理する．SDK自体が脚を動かす歩行制御器なのではない．

ROS 2は，ロボット用プログラムを組み立てる枠組みである．実行中の構成要素をnodeと呼ぶ．ROS 2はCyclone DDSを使って
node間でmessageを運べる．`rmw_cyclonedds_cpp`は，ROS 2の通信窓口をこのライブラリへつなぐアダプターである．
Unitreeのmessage packageは，状態やAPI要求の各項目を定義する．対応するROS 2プログラムなら，SDKの便利な関数を呼ばずに，
その定義を使って必要なmessageを交換できる．

```text
Application -> Unitree SDK2 -> Cyclone DDS -> network -> robot API endpoint
Application -> ROS 2 + Unitree messages -> Cyclone DDS -> network -> same API
```

Unitreeはこの[ROS 2とDDSの互換通信](https://github.com/unitreerobotics/unitree_ros2)を説明している．
ROS 2の任意の版，message定義，ネットワーク設定を自由に組み合わせられるという意味ではない．型・通信設定・実際の要求応答を含めて確認する．

## 6．二つのネットワークをつなぐ三つの方法

USB接続を残すこともできる．違いは，i7を**どの仕組みで**越えるかであり，USB Ethernetがネットワーク機器として不適格かという話ではない．

| 方法 | i7を何が越えるか | 成立させる条件 |
|---|---|---|
| Ethernet bridge | 二つのinterface間でEthernetのデータを転送 | driver・interfaceの対応，アドレスを置く場所，multicast，転送filterの確認．既存通信に影響し得る |
| IPルーティング | 別subnet間でIP packetを転送 | 往復の経路，filter，DDSの発見と通知された宛先への到達性．転送有効化だけでは足りない |
| アプリケーション中継 | 一つのプログラムが内部データを受信し，定義した別messageをJetsonへ送る | データ形式，時刻の意味，接続・再接続，異常時の挙動を定義 |

bridge・ルーティングでは，ネットワークとDDSの宛先へ届けば，JetsonをSDK・ROS 2の利用側にできる．
アプリケーション中継では，一方の通信を受け取り，別の通信を作る．例えばi7の受信部が機体速度を読み，値と時刻をまとめてJetsonへ送る．
Jetsonが内部DDSの全topicへ参加する必要はない．指令も中継するなら，受け付ける操作，制御権，期限，異常時の処理も定義する．
SSHで一時起動しただけのプログラムが，自動でこの中継機能になるわけではない．

内部LANへ既につながる外部Ethernet端子があれば，i7のbridge・ルーター機能を使わず，そこへJetsonを参加させる別の物理構成もある．
その端子の同定は有用だが，USB経由の方法が不可能という証拠ではない．この解説だけでbridge，経路変更，中継のいずれかを採用したことにはしない．

## 7．Dockerとpacketのfilter

Dockerは，アプリのファイル・processをコンテナへ分離する．通常のコンテナbridgeでは，別のnetworkやアドレス変換が加わる場合がある．
Linuxの`--network host`では，hostのinterfaceを直接使う．物理interface同士をbridgeしたり，返信経路を追加したり，hostのfilterを無視したりはしない．
[Dockerのhost network](https://docs.docker.com/engine/network/drivers/host/)を参照する．

firewallは条件に応じてpacketを通す・落とす仕組みである．計算機上のアプリが受信する通信，そのアプリが送る通信，計算機を通過する通信は
別の扱いになる．Dockerが設定する転送ruleによって，hostがルーターとして働けなくなる場合もある．
したがって，i7自身のROS 2は動く一方，bridge・ルーティングは動かないこともある．Dockerが原因と決める前に，実際の通信経路とruleの件数を読む．
[Dockerのfirewall文書](https://docs.docker.com/engine/network/packet-filtering-firewalls/)はこの挙動を説明する．firewall全体の無効化は原因調査の代わりにならない．

## 大学Wi-Fiを離れた運用

機体のローカル通信と，Macの管理接続は別である．Macと切れてもJetsonと機体のEthernet経路が消えるとは限らない．
ただし，監督が必要な実験では，運用方針として停止が必要になることもある．ローカルアプリ自身に寿命とデータ途絶の処理を実装する必要があり，
SSH画面がその代わりにはならない．[オフラインの操作手順](../how-to/offline-operation.ja.md)でローカル接続を，
[制御周期の説明](control-loop.ja.md)で遅い推論と観測・制御を分ける理由を扱う．
