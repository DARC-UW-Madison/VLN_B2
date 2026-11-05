# B2内蔵センサーの受信

[English](built-in-sensors.md) · [ドキュメント](README.ja.md) · [ネットワーク手順](field-network.ja.md)

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

## B2を起動せず保存画像を見る

**外付けJetsonのデスクトップ**で端末を開き，次を実行する．

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
xdg-open "$PWD/local/b2-damping-sensors-01/retry-01/index.html"
```

保存済みの前後画像が開く．一つ上の階層の`index.html`は最初の試行で，復号できた後方画像だけを含む．
どちらもlive映像やTIC-VLAの予測ではない．B2，internet，Web server，model loadは不要である．
次の訪問で操作者と実際の視野，向き，画質を照合する．

## 受信専用の取得を再実行する

公開[probe](../tools/probe_onboard_sensors.py)にはPython 3.8以上，対応するROS 2・message binding，
映像復号には既存のPillow・FFmpegが必要である．依存関係をインストールする機能はない．projectのvenvや
GPUモデルコンテナに内蔵側Foxyのbindingがあるとは限らない．単独probeは，Python 3.10以上を要求する
本体packageとは独立に実行できる．

次は**雛形**であり，新しく実行した記録ではない．B2を起動し，正規アクセスと標準interface・domain・workspaceを
再確認した後に，外付けJetsonで実行する．remote command内のpathを含め，全ての`VERIFIED_*`を置き換える．
固定したhost keyは非公開inventoryを参照し，照合を無効化しない．接続先は，標準LANのIPv4ではなくscope付きの
link-local addressの場合もある．認証は端末で対話入力し，ファイルに書かない．

```sh
bash --noprofile --norc <<'SH'
set -e
cd ~/Developer/Projects/Robotics/b2/VLN_B2
umask 077
mkdir local/built-in-sensors-02
B2_TARGET='VERIFIED_AUTHORIZED_SSH_TARGET'
B2_KNOWN_HOSTS='VERIFIED_PRIVATE_KNOWN_HOSTS_FILE'
ssh -T -o StrictHostKeyChecking=yes -o ConnectTimeout=5 \
  -o UserKnownHostsFile="$B2_KNOWN_HOSTS" "$B2_TARGET" \
  'bash --noprofile --norc -c "
set -e
export PATH=/usr/bin:/bin:/opt/ros/foxy/bin PYTHONDONTWRITEBYTECODE=1
source /opt/ros/foxy/setup.bash
source VERIFIED_MESSAGE_WORKSPACE/install/setup.bash
exec /usr/bin/python3 - --interface VERIFIED_NATIVE_INTERFACE --domain-id 0 --seconds 15 --include-images
"' \
  < tools/probe_onboard_sensors.py \
  > local/built-in-sensors-02/sensors.json
SH
```

domain 0は今回の個体で実測した．検証したdomainが違えば置き換える．このコマンドはB2上へソース・取得ファイルを
書き込まず，最後のredirectで外付けJetsonに非公開JSONを保存する．SSHの終了状態，topicの件数，
`not_subscribed`・`decode_error`を確認する．空・不正なJSONは失敗であり，正常な観測ゼロとは区別する．
認証・workspace・復号のエラーを読めるよう標準エラーは表示したままにする．試行ごとに新しい出力先を使い，証拠を上書きしない．

probeは約2秒の発見後，最大15秒購読し，streamごとに8秒の上限で復号を試す．圧縮bufferは各stream 8 MiBまでである．
`--include-images`を外すと件数・状態だけを報告し，映像を保持・復号しない．全購読はbest-effort，volatile，depth 1を使う．
指令publisherやrobot service要求は作らない．DDSの発見では通信するため，標準interfaceの明示指定によって大学Wi-Fiへ
この診断を流さないようにする．

成功した新しい非公開JSONからJPEGを取り出すには，次を実行する．

```sh
python3 - <<'PY'
import base64
import hashlib
import json
from pathlib import Path

folder = Path('local/built-in-sensors-02')
report = json.loads((folder / 'sensors.json').read_text())
assert report['actuation_requests_sent'] is False
for topic, item in report.get('previews', {}).items():
    if not item.get('decoded'):
        print(topic, item.get('decode_error', 'No decoded preview'))
        continue
    payload = base64.b64decode(item['jpeg_base64'], validate=True)
    assert hashlib.sha256(payload).hexdigest() == item['jpeg_sha256']
    assert topic in ['/front_videohub/videostream', '/back_videohub/videostream',
                     '/panorama_videohub/videostream']
    path = folder / (topic.split('/')[1] + '.jpg')
    with path.open('xb') as output:
        output.write(payload)
    path.chmod(0o600)
    print(path, item['width'], item['height'])
PY
```

表示されたJPEGのpathをJetsonのfile managerで開く．JSONには画像や非公開の状態が入り得るため，
出力先全体をGit対象外に保つ．公開issueの添付にも使わない．

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
