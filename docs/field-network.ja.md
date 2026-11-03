# 現地作業：Ethernet・内蔵計算機・独立した運用

[English](field-network.md) · [確認カード](field-card.ja.md) · [ネットワークの考え方](network-topology.ja.md)

**2026-11-03**に初回の物理接続を調査した．内蔵PCでの状態受信は成功したが，外付けJetsonからの
DDS直接通信と移動は未検証である．番号付きの節は操作手順であり，全項目の完了記録ではない．
研究室の取扱い・停止手順を使い，復旧用アクセスを維持する．

## 実測したUSB接続とその境界

```text
Mac -- existing Wi-Fi/Tailscale SSH --> external AGX Orin
                                        |
                                  Ethernet (1 Gbps)
                                        |
                             Anker USB Ethernet hub
                                        |
                                B2 USB-C host port
                                        |
                            onboard i7 development PC
                       USB Ethernet       native Ethernet
                             |                   |
                     separate interface   robot service network
                     no bridge found      state DDS domain 0
```

この図は今回の配線であり，全B2共通の構成図ではない．到達したPCは**Intel Core i7-1265U，x86_64，
論理CPU 12個**，Linuxから見えるRAM約**15.22 GiB**，**512,110,190,592バイトのNVMe**だった．
Ubuntu 20.04.6，kernel 5.15.76-rt53である．このhostのPCI検査にはIntel graphicsがあり，NVIDIA GPUは
表示されなかった．B2内部の他の計算機まで調べた結果ではない．公式の
[B2ハードウェア説明](https://support.unitree.com/home/en/B2_developer/About%20B2)は，機体機能用・利用者開発用の
計算機と追加のOrinを区別する．今回のi7は開発用の役割に整合するが，動作制御器と同定したものではない．
制御器へのSSHは試していない．

scope付きIPv6でUSB側の相手へ届き，許可された既存の認証でログインできた．i7のUSB adapterと別のadapterには，
同じIPv4アドレス・subnetと異なる経路metricが設定されていた．標準Ethernetとのbridgeはなかった．
IP forwardingが有効なだけではDDS経路は完成しない．返信経路，発見情報のlocator，multicastも通る必要がある．
これらの内蔵設定は変更していない．

外付けJetsonだけに，新しい`b2-research-link`で資料の標準LAN用client IPを一時設定した．重複検査には応答が
なかったが，停止中の重複機器まで否定できない．このUSB経路では標準serviceのIPv4試験が失敗した．最後に元の
有効な有線profileへ戻し，新profileは自動接続を無効にして保存した．Wi-Fiはdefault routeを維持した．
資料と似たsubnetだからという理由だけで，別の保存済みprofileを有効にしない．

i7の標準Ethernetからは資料のservice IPへpingが通り，RTPSの発見情報でdomain **0**を観測した．
既存のFoxy／Cyclone DDSによる12秒の受信専用検査で，`unitree_go/msg/SportModeState`型の
`/sportmodestate`を**5,994件**，`/lf/sportmodestate`を**240件**受信した．検査した位置・速度・yaw速度・姿勢は
全件で有限だった．証明したのは内蔵PCでの受信であり，座標規約，取得元の時計との対応，経路品質，
外付け側の受信，指令の受理は別である．カメラ・odometryのtopic名の発見だけでは中身や所有関係を確認できない．
生の構成・状態の証拠は非公開`local/b2-connection-01`へ置く．

外付けSDKを直接使うには，標準の機体LANへつながる正規の**Network／Ethernet／GbE変換ケーブル**を特定する．
操作者は現在の付属品から見つけられなかった．USB hubだけでは代用できない．別案として，i7上の明示的な
プログラム・routerで状態や要求を中継できるが，構成変更として別途検討するものであり，まだ導入していない．
bridge，NAT，指令中継を自動的な対処として有効にしない．公式資料は航空コネクターの通電中の抜き差しを禁止する．
その種の端子を変更する場合は研究室の電源を切った取扱い手順に従う．この図は内部のモーターバスを表していない．

## アドレスとprofile：この接続の読み方

IPアドレスはinterfaceに付けるもので，通信の方向を決めない．外付けJetsonのclient IPは送信にも受信にも使う．
内蔵PCはEthernetごとに別のアドレスを持てる．標準LAN側とUSB側のIPは，同じPCの異なる接続口を識別する．
USBケーブル側のJetsonへ標準LANのsubnetを設定しても，そのケーブルが標準switchへ接続されたことにはならない．

説明用にJetsonが`192.0.2.10/24`，i7の標準側が`192.0.2.20/24`，USB側が`198.51.100.20/24`とする．
最初の二つは数値上同じsubnetでも，実際の配線・転送経路が必要である．USBと標準LANが同じhostにあるだけでは通らない．
ここは例示であり，個体の実アドレスは非公開の記録に置く．

IPv4とIPv6は，同じEthernetケーブルで使える二種類のIPアドレス・通信の仕組みである．`192.0.2.10`のような形式はIPv4で，
`fe80::…`はIPv6のlink-localである．今回のIPv6にinternet・Wi-Fi・VPNは必要ない．物理的につながるだけでは目的のIP経路は
完成しない．送信元IP，宛先のinterface，返信経路，filterも関係する．

scope付きIPv6 link-localなら，内蔵側のIPv4設定を変更せず直結の開発PCへ届く場合がある．
`fe80::…%INTERFACE`の末尾は，**接続元**の出口を指定する．直結区間の通信であり，Macから大学経由でrouteするIPではない．
後の確認では，同じi7が既に持つ別のIPv6へ，保存済みSSH host keyと既存認証を照合して接続できた．
古いIPも割当は残っており，到達性が違った理由は未確定である．IPだけで別の計算機と判定しない．

NetworkManagerの**profile**は保存した設定の組で，`eth0`はinterfaceである．保存設定が複数あっても端子や通信路は増えない．
整理前には有線設定が三つあり，古い二つも自動接続候補だった．操作者の許可で，使っていない古い設定をバックアップ後に削除した．
残る有線設定は`b2-research-link`一つで，有効・自動接続あり，標準subnetの固定client IPv4，IPv6 link-local，
default gatewayなしである．Wi-Fiはdefault routeを維持する．これは後の再確認時点で，以下の初回試験終了時には一度
元の設定へ戻していた．内蔵側のアドレス・routeは変更していない．

当面はこの一つを有効なまま使う．現在のUSB管理接続はIPv6を利用し，保存した標準subnetのIPv4だけではSDK直接到達を
証明しない．標準の機体接続か，検証した中継が引き続き必要である．復元用keyfileとmanifestは非公開
`local/network-profile-cleanup-01`に残す．管理者は`nmcli connection load`で戻し，自動接続を確認してから有効にできる．
通常起動で古い二つを両方読み戻さない．

その後の移動前調査では，具体的な返信経路の問題を確認した．ケーブルはUSB Ethernetへ入るが，i7は外付けJetsonの
標準subnetのIPv4へ返す際に**機体側の標準Ethernet**を選ぶ．ARPでMACが分かっても，IPで正常に往復できるとは限らない．
直接のIPv4 pingは失敗し，外付け状態containerの3秒の検査も両sport状態topicで受信**0件**だった．移動要求は送っていない．
SDK接続が完成した結果と扱わない．

scope付きSSHでi7へ入り，一時的な標準interfaceのROS 2診断で有限な状態162件を受信した．sport serviceへ版情報だけを
読む要求を一回送り，status 0，API版`1.0.0.1`の返答を得た．ID 1は固定版の[SDK内部API](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/unitree_sdk2py/rpc/internal.py)と
[版情報の照会実装](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/unitree_sdk2py/rpc/client.py)に基づく．
内蔵側の要求・応答が通る根拠であり，外付け直接DDS，firmware版，移動の受理，停止挙動の確認ではない．
lease・mode・姿勢・移動・停止の要求は送らず，内蔵設定も変更していない．証拠は非公開`local/b2-pre-motion-01`に置く．
一時的なclientは終了した．

## 1．ケーブルを挿す前

B2の利用者向けEthernetポートと，ケーブルの反対側を確認する．内部スイッチやゲートウェイへ
つながる場合もあり，全計算機が見えるとは限らない．研究室で動くサービスのIP・サブネット，
未使用の接続用IP，DDSドメイン，インターフェース，現在の制御権を確認する．内蔵の開発用計算機へ
入れるなら，正規の接続方法も確認する．不明な値をGo2-W，販売店の例，既定ドメイン0で埋めない．

挿す前に既存のEthernet設定を調べる．自動のDHCP・プロファイル起動で経路が変わることがある．
未設定の接続では，可能なら配線前に以下の確認済みプロファイルを用意する．研究室の動く設定を上書きしない．
今回の訪問では，現在のWi-Fi管理接続を維持する．

訪問ごとに新しい番号の保存先を使い，前回の結果を上書きしない．

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
mkdir -m 700 local/field-visit-01
ip -br link > local/field-visit-01/link-before.txt
ip -br address > local/field-visit-01/address-before.txt
ip -4 route show table main > local/field-visit-01/routes-before.txt
ip rule show > local/field-visit-01/rules-before.txt
nmcli -f DEVICE,TYPE,STATE device status > local/field-visit-01/devices-before.txt
python3 tools/inspect_target.py --include-network --output local/field-visit-01/external-before.json
```

相手へ接続せず，ローカルの設定を調べる．非公開のネットワーク情報を含むためGitの外へ置き，
ケーブルの行き先は実物でも記録する．

## 2．ローカルなIP経路を作る

以下は研究室で確認した値に置き換える．機体の既定値ではない．

```sh
ROBOT_IFACE='VERIFIED_INTERFACE'
JETSON_ROBOT_CIDR='VERIFIED_UNUSED_ADDRESS/PREFIX'
ROBOT_SERVICE_IP='VERIFIED_SERVICE_ADDRESS'
DDS_DOMAIN_ID='VERIFIED_DOMAIN_ID'
```

`JETSON_ROBOT_CIDR`は機体のIPではなく，外付けJetsonに付けるIPとプレフィックスである．
プレフィックスは同じサブネットの範囲，インターフェースはローカルのポート・論理デバイス，
経路は宛先ごとの出口を表す．先にブリッジ所属を調べ，アドレスをブリッジが持っている場合は，
所属する物理ポートを勝手に独立した接続へ設定しない．

**同じIPv4サブネットで静的IPを使うことが確認できた場合**のひな形を示す．
まず`b2-research-link`という既存プロファイルがないことを確認する．新しく作り，ケーブルを挿してから
明示的に有効にする．

```sh
sudo nmcli connection add type ethernet ifname "$ROBOT_IFACE" \
  con-name b2-research-link connection.autoconnect no \
  ipv4.method manual ipv4.addresses "$JETSON_ROBOT_CIDR" \
  ipv4.never-default yes ipv6.method link-local ipv6.never-default yes
sudo nmcli connection up b2-research-link
```

変更するのは外付けJetsonだけである．`manual`で合意したIPを設定し，プレフィックスから同じサブネットへの
経路ができる．機体側にインターネット用のゲートウェイ・DNSは設定しない．`never-default`はこの接続を
既定の出口にしない指定，`autoconnect no`は最初の起動を明示的に行う指定である．
[NetworkManagerのIPv4設定](https://networkmanager.dev/docs/api/latest/settings-ipv4.html)を参照する．
プロファイルはホストOSへ保存し，`up`で今有効にする．`autoconnect no`なので，次の起動時は自動で有効にしない．
構成を検証した後，接続の自動起動，アプリの起動，移動の許可は別々に確認する．
研究室がDHCP，ゲートウェイ，VLAN，既存ブリッジを使う場合は，その構成に合わせ，このひな形をそのまま実行しない．
不明な構成をひな形へ合わせるために，接続共有，Wi-FiとB2のブリッジ，内蔵IPの変更は行わない．

配線後，次を調べる．

```sh
ip -br link
ip -br address
ip route get "$ROBOT_SERVICE_IP"
ip -4 route show default
```

物理リンク，目的のローカルIP，機体向けインターフェースと送信元IPを確認する．
Macの別の端末でも管理接続が続くことを調べる．Wi-Fi，Tailscale，Dockerを通る経路は，
目的の機体直結経路を確認したことにはならない．サブネットが重なる場合は研究室と整理してから進める．

経路が正しいことを確認してから，許可された既知のサービスIPへ限定して試す．

```sh
ping -c 3 -W 1 "$ROBOT_SERVICE_IP"
ip neigh show dev "$ROBOT_IFACE"
```

pingはICMPを送り，近隣表示はキャッシュを読む．pingが失敗してもフィルターの可能性があり，
成功しても相手の実体やDDSは確認できない．サブネットの全探索は不要である．
今回の観測だけの訪問では，経路が誤っていたら新しいプロファイルだけを無効にする．設定は検査用に残る．

```sh
sudo nmcli connection down b2-research-link
```

## 3．B2の状態を購読する

準備済みの[状態専用イメージ](unitree-runtime.ja.md)を使い，SDK・DDS依存のないホストvenvは使わない．
オフラインのimport・符号化は通った．実測したUSB経路での外付け初回購読は0件だったため，目的の経路を確立してから
以下のひな形を再実行する．確認したinterface・domainと，
上で作った新しい非公開フォルダを使う．オフライン検査の`--network none`と違い，選んだ機体側interfaceへ
到達するためhost networkingを使う．networkを共有する設定であり，ホストのファイル・認証情報の共有やbridgeではない．

```sh
sudo docker run --rm --pull never --runtime runc --network host --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/local/field-visit-01,dst=/reports" \
  -e HOME=/tmp -e PYTHONPATH=/workspace/src:/opt/vendor/unitree_sdk2_python \
  --entrypoint timeout vln-b2-unitree:jp5 -k 5s 15s \
  /opt/unitree/bin/python -m b2_tic_vla state \
  --interface "$ROBOT_IFACE" --domain-id "$DDS_DOMAIN_ID" \
  --seconds 3 --output /reports/state-01.json
```

DDSの相手の発見・購読の通信は送るが，モーター指令は送らない．トピック，有効数と受信数，挙動，
配信元の実体を記録する．有限の値を受信しても，軸，単位，時計の対応，実際に動かせる状態は未確認である．
pingが通ってDDSが0件なら，インターフェース・ドメイン・型・QoS・ファイアウォールを調べる．
無作為なIP変更や，移動を始めるサンプル実行で対処しない．

## 4．内蔵計算機とサービスを特定する

研究室の既知の接続先・認証方法と，通常のホスト鍵確認を使う．SDKのサービス実行先がSSHを提供するとは限らず，
内蔵Jetsonと同じとも限らない．SSH不可だけでは移動サービスが使えないと判定できない．
アカウントの推測やファームウェアの交換は行わない．

正規に入れる各内蔵計算機で，以下の読み取り情報を承認された非公開の記録へ残す．

```sh
uname -m
cat /etc/os-release
test ! -r /etc/nv_tegra_release || cat /etc/nv_tegra_release
ip -br address
ip route
lsusb
ps -e -o comm=
systemctl list-units --type=service --state=running --no-pager
```

専用の制御器にはコマンドがない場合もある．その事実を残し，導入して埋めない．
プロセスは名前だけを表示し，秘密情報が入り得る引数全体は出さない．必要なら研究室と既存Docker・ROSの
起動設定を確認し，生の結果は非公開にする．ROS 2では，動作実績のある環境，インターフェース・発見設定，
ドメイン，メッセージパッケージを特定した後で，該当するトピック・サービスを調べる．
大学のWi-Fi上で既定設定のROS探索を広く行うことを調査方法にしない．

実在する各ホストについて，実体，インターフェース，到達先，稼働サービス，提供元・利用側，
プロトコル・トピック・ドメイン，根拠の表を作る．推定の役割は推定として残す．
公開された歩行サービスから実際の歩行制御までの接続は，研究室・メーカーの資料で調べる．
外側のIPへ到達したことから，内部モーターのバスを推定で決めない．

### 内蔵PCで受信専用の検査を再現する

これは**許可されたi7へのSSH端末の中**で行う任意の診断である．Macや外付けJetsonで実行しない．
既存packageと子shellを使い，ROSの新規導入や機体launchの起動はしない．先に非公開の構成記録で
workspaceのsetupファイルと標準の機体側interfaceを確認し，以下の二つのplaceholderを置き換える．
domain 0は今回の個体で測定した値なので，別個体では再確認する．interfaceを明示して大学Wi-Fiでの探索を避ける．
system Python 3.8がFoxy bindingに対応する．既存conda Python 3.11とのABI互換性を仮定しない．

```sh
bash --noprofile --norc <<'SH'
set -e
export PATH=/usr/bin:/bin:/opt/ros/foxy/bin
UNITREE_ROS_SETUP='VERIFIED_WORKSPACE/install/setup.bash'
ROBOT_IFACE='VERIFIED_NATIVE_ROBOT_INTERFACE'
source /opt/ros/foxy/setup.bash
source "$UNITREE_ROS_SETUP"
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="<CycloneDDS><Domain><General><NetworkInterfaceAddress>${ROBOT_IFACE}</NetworkInterfaceAddress><AllowMulticast>true</AllowMulticast></General></Domain></CycloneDDS>"
/usr/bin/python3 - <<'PY'
import json
import math
import time
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from unitree_go.msg import SportModeState

rclpy.init(args=['--ros-args', '--disable-rosout-logs', '--disable-external-lib-logs'])
node = rclpy.create_node('b2_read_only_state_check', enable_rosout=False,
                         start_parameter_services=False)
report = {'received': {}, 'finite': {}}
qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                 durability=DurabilityPolicy.VOLATILE)

def receive(message, topic):
    values = [float(v) for v in message.position]
    values += [float(v) for v in message.velocity]
    values += [float(v) for v in message.imu_state.rpy]
    values += [float(message.yaw_speed)]
    report['received'][topic] = report['received'].get(topic, 0) + 1
    report['finite'][topic] = report['finite'].get(topic, 0) + int(
        all(math.isfinite(v) for v in values))

subscriptions = []
try:
    for topic in ['/sportmodestate', '/lf/sportmodestate']:
        subscriptions.append(node.create_subscription(
            SportModeState, topic, lambda msg, t=topic: receive(msg, t), qos))
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
    print(json.dumps(report, allow_nan=False))
finally:
    node.destroy_node()
    rclpy.shutdown()
PY
SH
```

受信した各topicで`received`が正数になり，`finite`と一致することを確認する．空の件数は受信なしを意味し，
正常終了だけでは成功としない．作るのは購読とDDS発見通信だけで，指令publisher，ROS daemon，モーターservice呼出しはない．
状態streamの保存，時計同期，モデルへの実状態の結合は行わない．調べたCyclone DDSは
`NetworkInterfaceAddress`を非推奨の警告付きで受理した．警告を消すために既存の導入を交換しない．
子shellを閉じるとその環境設定は失われる．結果は非公開にする．

## 5．センサーの経路を記録する

外付けZED 2iは，外付けJetsonへUSB接続できると操作者が確認している．
B2内蔵のカメラ・センサーは，今回の構成では外付けJetsonへ直接USB接続できない．別の取得経路として扱う．

| 入力元 | 現地で行うこと | 確認する根拠 |
|---|---|---|
| 外付けZED 2i | 電源のあるUSB接続，USBリンクとSDK権限の確認，バインディング導入後にRGBを一枚取得 | 正しいカメラ・視野，リンク，画像寸法，周期，バッファ，取得元・受信の時刻，取付け |
| 内蔵カメラ・センサー | 接続先の内蔵ホスト，既存ドライバと外部配信サービスを特定 | ストリーム・トピック，型，形式・圧縮，周期，座標，時刻の意味，権限，到達する通信方式 |
| Livox Mid-360 | Ethernet，電源，受信するホスト・ドライバをたどる | 実際のサブネット，配信元，点群・姿勢の接続方法，時計の基準 |

現在のZED取得部は，深度を無効にして左RGBだけを要求する．RGB-Dの能力があるだけで，深度を既に
使っているわけではない．複数台ある場合は，SDKの既定のカメラを信用する前に選択方法を確認する．
内蔵センサーには対応する外部配信・購読経路が必要であり，EthernetだけでUSB機器を転送できない．
既存サービスを止めたり，所有関係が不明なまま競合する利用側を追加したりしない．

以下のホスト用カメラ例にはSDK・bindingが必要である．準備した対象機では[隔離カメラ環境](camera-runtime.ja.md)・
[時間制限付きの観測](asynchronous-runtime.ja.md)を使い，裸のホストvenvの依存不足をカメラ故障と解釈しない．

```sh
PYTHONPATH=src timeout -k 5s 30s python3 -m b2_tic_vla camera \
  --output local/field-visit-01/camera-01/frame.jpg
```

LiDARには別のEthernetアダプターや，構成を確認した共通スイッチ・サブネットを使う可能性があるが，未選定である．
センサーを増やすために，機体LANと大学LANをブリッジしない．本プロジェクトには深度・点群処理の直接の
接続部がないため，自己位置・通行可能性の役割はTIC-VLAのRGB入力とは別に決める．

## 6．アクセス・起動・大学Wi-Fiなしの運用

- 完了した[起動・認証情報の確認](system-overview.ja.md#個人の認証情報と共有返却)を読む．
  eduroamのシステム保存，HDMIなしのソフトウェア再起動，その後のSSH・RDPは成功した．
  現地での復旧を確認した後，GUIへログインせず，電源投入からSSHまでを試す．
- Macから[リモートデスクトップ](remote-desktop.ja.md)を試す．HDMIあり・なし，
  ログアウト・再起動後を確認し，実際に使える画面，認証，アクセス制限を検証する．パッケージの存在だけでは成功ではない．
  直接tailnet RDPは準備済みで，MacのSSH転送は不要である．復旧手段を保ち，新経路のGUIログインを確認し，動作中のSSHを維持する．
  Tailscale・eduroamの再起動復帰は以前に通ったが，新RDP guardはservice再起動までで，変更後の機器全体の再起動は未確認である．
- 別のAPは利用できない前提で，[オフライン運用](offline-operation.ja.md)に従い，JetsonのAP候補と直接OpenSSHを調べる．
  現地の復旧手段を確保して切り替え，インターネットやeduroam・APの同時利用を仮定しない．中核処理のMacは任意とする．
  B2リモコンの手動介入，停止，研究用指令の禁止は別に確認し，ボタンの挙動を想定で決めない．
- SSHを閉じてもアプリの寿命がそれに依存しないことを調べる．現段階では，指令のないオフライン再生と，
  切り離したプロセスの演習だけを使う．ロボットの監視・停止試験とは別である．
- 将来の移動前には，管理接続断，画像・状態の途絶，推論停止，指令プロセスの異常，機体Ethernet断を別々に検証する．
  各場合の続行・停止の方針と実際の受信側の動作を残す．オフラインで計画できるだけで，無人運用が成立するわけではない．

将来の実時間プログラムは，確認したローカルのコード・ファイル・設定とB2へのEthernetを使い，
外付けJetsonの監督プロセスの下で動かす．Macは管理用で，推論の必須経由点にしない．
その実機アプリ・サービスと監視は未実装・未有効化である．明示的な移動許可と停止動作を検証するまでは，
起動時を観測のみ・移動無効の状態に保つ．[移動中の運用](network-topology.ja.md#大学wi-fiを離れた運用)を参照する．

`examples/onsite-notes.json`をGit管理外の場所へコピーして埋める．実IP，認証ID，センサー記録，
生のサービス調査結果は公開Gitへ入れない．
