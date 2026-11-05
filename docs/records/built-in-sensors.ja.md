# B2内蔵センサーの受信

[English](built-in-sensors.md) · [ドキュメント](../README.ja.md) · [ネットワーク手順](../how-to/field-network.ja.md)

> 文書種別：**実験・構築記録**．コマンド・計測は記録時の環境を示す．現在の操作には手順書を使う．

## 確認できたこと

内蔵センサーの初回調査で，移動を要求せずに前後の映像，慣性・関節の情報，sport・odometry状態を受信した．
i7に既にあるROS 2 Foxyとmessage workspaceを使った．B2のpackage，driver，service，network，firmwareは変更していない．

```text
Existing B2 camera/state producers
                | native robot Ethernet / DDS domain 0
Onboard i7: temporary ROS 2 subscriptions + existing video decoder
                | authenticated SSH stdout over USB Ethernet
External Jetson: private JSON, derived JPEGs and standalone HTML
```

SSHはi7で動くプログラムの結果を運んだ．DDSの発見通信を転送したわけではなく，外付けSDKコンテナが
標準機体LANへ直接参加できたわけでもない．スクリプトはSSHの標準入力から渡し，取得後に終了した．
i7へ調査ソースや取得ファイルは配置していない．Macは管理コマンドの開始にだけ使い，画像は外付けJetsonに保存した．

| 入力元 | 最後の15秒の購読区間で得た結果 |
|---|---|
| `/front_videohub/videostream` | 21メッセージ．1280×720のJPEGへ復号できた |
| `/back_videohub/videostream` | 21メッセージ．640×360のJPEGへ復号できた |
| `/lf/sportmodestate` | 14メッセージ |
| `/lf/odommodestate` | 13メッセージ |
| `/lf/lowstate` | 13メッセージ．IMUと関節情報を取得 |
| panorama映像，wireless controller，LIO odometryのtopic | この区間では受信なし |
| 点群・`/pctoimage_local` | 利用可能なpayloadは未確認．driverの所有関係とmessage互換性は継続調査 |

先の8秒の取得では，後方だけ1920×1080へ復号できた．前方もbyte列は受信したが，その試行では復号できず，
取得区間を延ばすと前後とも復号できた．最初の失敗の厳密な原因は未確定である．どちらも`video720p`という
fieldを選んだが，**名前だけで解像度を確定できない**．実際の寸法は試行間で異なった．
固定の解像度設定や，topicと物理カメラの対応はまだ確立していない．

件数は**DDSメッセージ数**であり，映像frame数やcameraの実測frame rateではない．LowStateは関節状態のslotを
20個持っていたが，これはmessageの配列形式で，実関節数が20という意味ではない．受信ゼロだけでセンサーがないとは
いえない．配信の稼働，QoS，message bindingを別々に確認する．topic名だけで所有する機器も確定しない．
保存した発見情報では，panorama・LIOのpublisherは0，wirelessは1だった．`/pctoimage_local`は既存Python環境に
`unitree_interfaces`がなく購読できず，publisherも0だった．それぞれ別の事実であり，hardwareの不存在を確認したわけではない．

## 操作手順

保存画像の表示・再取得は[操作手順](../how-to/built-in-sensors.ja.md)にある．

## TIC-VLAへ使う前に必要なこと

モデルのデモは引き続き**外付けZED**を使う．今回，内蔵カメラへ入力を切り替えたり，内蔵画像で推論したりはしていない．
まずcameraの同定，取付変換，視野，露光の時刻，buffer，復号画像の形式を確認する．生の`time_frame`は単位と時計の原点が
未検証で，Jetson時刻との差を計算できない．圧縮列から復号した画像は，最初に受信したframeとは限らない．

次に，検証した時計・座標系で実状態と画像を対応付け，観測adapterを実装し，指令なしで予測を評価する．
LiDARの自己位置・障害物処理は別の役割で，点群を受信するだけでTIC-VLAのRGB入力へ追加されるわけではない．
継続的な状態・制御経路，指令期限，物理的停止の立上げとも別に扱う．

公式の[映像message定義](https://raw.githubusercontent.com/unitreerobotics/unitree_ros2/master/cyclonedds_ws/src/unitree/unitree_go/msg/Go2FrontVideoData.msg)は
byte配列と時刻fieldを定義するが，codec，時刻単位，今回の個体の物理cameraとの対応は説明していない．
公式[ROS 2レポジトリ](https://github.com/unitreerobotics/unitree_ros2)はnative interfaceを説明する．
上記の結果の根拠は，今回の受信と復号である．
