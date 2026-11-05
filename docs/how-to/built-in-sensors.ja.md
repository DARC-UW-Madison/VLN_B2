# 内蔵センサー画像の表示と取得

[English](built-in-sensors.md) · [手順一覧](../README.ja.md)

> 文書種別：**操作手順**．

保存済み結果の表示と，次の起動時に行う受信専用の再取得を分けて説明する．測定値は[センサー調査記録](../records/built-in-sensors.ja.md)にある．

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

公開[probe](../../tools/probe_onboard_sensors.py)にはPython 3.8以上，対応するROS 2・message binding，
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
