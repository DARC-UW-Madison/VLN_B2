# 別のAPを使わないオフライン運用

[English](offline-operation.md) · [文書目次](README.ja.md) · [現地手順](field-network.ja.md)

## 運用の前提と完了状況

持ち運べる研究室APは利用できないものとする．中核処理は外付けJetsonで，ローカルの資材，
センサー入力，有線のB2接続を使って実行する設計である．Macとインターネットは任意の管理手段にする．
これは目標構成であり，ライブアプリ，指令送信，armed管理，watchdogは未実装である．
ホットスポットの設定・試験，オフラインの実機運転も行っていない．

計算がネットワークに依存しないことと，無人実験が可能なことは異なる．確認済みの操作者による
制御・停止手順と，実験区域の定義は必要である．B2には既存のリモコンがあるとの報告がある．
Macの端末だけを停止手段にせず，その実際の動作を特定する．

## 1．実行中にMacをつなぐ理由

開始・停止の要求，状態・映像の表示，試行間での将来のタスク変更，ログの取得には便利である．
ただし，画像ごとの処理，推論，歩行要求のたびに必要な計算機ではない．将来Macへ画像を送り
推論する設計なら通信への依存を作るが，ここで提案している構成ではない．

実験前にJetsonへ，承認済みのコードと実行環境，モデル・tokenizer・設定資材，指示，
センサー校正，既知のB2ネットワーク設定，ログ空き容量，ローカルの起動・終了設定を用意し，記録する．
ライブ処理中の取得，GitHub pull，クラウドモデル呼出しは組み込まない．現在のツールは，
まだそのオフライン自律サービスではない．

将来のローカル監督部は，観測・disarm状態から起動する．Armedは別の明示操作で許可する．
SSHを閉じることがプロセスの寿命を決めてはならず，サービス再起動で再armedしてもならない．
切り離したDockerプロセスは端末を閉じても動かせるが，それだけでは入力鮮度の検査や
B2の実際の停止動作を用意できない．

## 2．二つのネットワークと，任意の別経路

```text
                  OPTIONAL MANAGEMENT
Mac -- Wi-Fi --> external Jetson acting as local AP
                       |
                       | local Python / inference / supervision
                       |
                       +-- Ethernet --> B2's supported user network
                       |
                       +-- USB --> external ZED candidate

B2 remote controller -- its existing independent radio path --> B2 control
                        actual arbitration/stop behavior to verify
```

ローカルAPを作っても，インターネットは生まれない．後述する手動IPの構成では，
Mac・JetsonともにそのAP経由のインターネットを持たず，Wi-Fiと機体Ethernet間の
ルーティング・NATも追加しない．既存の転送・firewall・bridge設定も確認し，この雛形だけで
ホスト全体の隔離が成立したと扱わない．B2は別の確認済みサブネットに残す．カメラとローカル処理は
インターネットなしで動かせる．図の観測・制御経路の実際の利用可否は，まだ検証が必要である．

一つのWi-Fi無線をeduroamのクライアントからAPへ切り替える際は，現在のeduroam・
Tailscale SSH経路が切れると考える．AP・クライアントの同時利用は前提にしない．
ホットスポットは既存の無線の役割を変えるもので，ハードウェアが増えるわけではない．
ドライバのAP対応，使用可能なチャネル・帯域，実際の端末接続を確認する．機種名だけでは足りない．

確認したAPのローカルIPへ，通常のOpenSSHで接続する．Tailscale SSHはそのoverlay経路を扱い，
全てのLANアドレスを自動的に扱うわけではない．通常のローカルOpenSSH用の認証を用意し，
待受・firewallを先に確認する．Tailnetの認証だけで新しいオフラインLANのSSHへ入れるとも，
Tailscaleの新しい接続調整が常にインターネットなしで成功するとも仮定しない．

## 3．読み取りだけの準備

Jetsonに接続できるときに実行する．プロファイルは有効化しない．

```sh
ip -br address
ip -4 route
nmcli -f DEVICE,TYPE,STATE device status
nmcli -f GENERAL.DEVICE,WIFI-PROPERTIES.AP device show wlan0
command -v iw
ss -lnt '( sport = :22 )'
```

`wlan0`は以前の調査で見た名称で，普遍的な名前ではない．`iw`があれば，`iw list`で
対応モード・組合せを調べられる．個体の識別情報は公開せずに手元で確認する．ツールがなければ
それを結果とし，唯一の通信経路を遠隔から変更する理由にはしない．APのサブネットを決める前に，
Dockerの既存のアドレス範囲も確認する．

切替え前に，Macに承認したローカルSSH認証情報があり，JetsonのホストSSHが適切なローカル
インターフェースで受け付けることを検証する．既存のfirewallとホスト鍵照合も確認する．
認証なしのログインや，firewall全体の緩和で解決しない．秘密鍵・ホットスポットのパスワードを
Git，Dockerイメージ，チャットへ置かない．

## 4．未実行のホットスポット設定例

最初の切替えは，現地端末か，別に確認済みの復旧経路が必要である．同じWi-Fiに依存する
遠隔シェルは復旧手段にならない．AP対応を確認し，B2，Docker，Tailscale，他の接続先と
重ならない未使用のアドレス・サブネットを選ぶ．以下は確認した実値への置換が必要であり，
機体やネットワークの既定値ではない．

```sh
AP_IFACE='VERIFIED_WIFI_INTERFACE'
AP_JETSON_CIDR='VERIFIED_UNUSED_JETSON_AP_ADDRESS/PREFIX'
EDUROAM_PROFILE_UUID='VERIFIED_EXISTING_EDUROAM_PROFILE_UUID'
```

`b2-local-management`が未使用のプロファイル名であることを確認する．この例は，
Jetsonの固定IPを持つWPA2-Personal APの設定を保存し，手動で起動する．
DHCP，DNS転送，NAT，大学・機体ネットワークのbridgeは作らない．

```sh
sudo nmcli connection add type wifi ifname "$AP_IFACE" \
  con-name b2-local-management ssid B2-Research \
  connection.autoconnect no 802-11-wireless.mode ap \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.proto rsn \
  802-11-wireless-security.psk-flags 0 \
  ipv4.method manual ipv4.addresses "$AP_JETSON_CIDR" \
  ipv4.never-default yes ipv6.method link-local ipv6.never-default yes
sudo nmcli --ask connection up b2-local-management
```

適用前に対象機の`nmcli`のヘルプを確認する．`--ask`は不足したAPのPSKを対話入力し，
コマンド履歴への記載を避ける．eduroam・Linuxとは別の強い秘密情報にする．
`psk-flags 0`はシステム保存を要求するため，後でrootだけが読める設定ファイルと
実際の保存を検証する．大学のパスワードをこのAPへコピーしない．SSIDは汎用の例であり，
導入前に変更できる．[NetworkManagerのCLI説明](https://networkmanager.dev/docs/api/latest/nmcli.html)を参照する．

通常は共有接続を作る`nmcli device wifi hotspot`と異なり，この手動アドレス案では
インターネット共有を自動設定しない．そのため，Macにも**手動IP設定**が必要になる．
同じサブネットの別のホストアドレスを使い，このオフライン接続にはルーター・DNSを入れない．
切替え前に両方の値を非公開で記録する．MacがオフラインSSIDへ接続し，Jetsonへの直接SSHが
動くことを試す．Macが別のネットワークへ戻った状態を，ローカル接続の成功と取り違えない．

設定後，Macから実際のローカル宛先・ポートと，通常のSSH用認証情報で接続する．

```sh
ssh RESEARCH_USER@JETSON_AP_ADDRESS
```

`connection.autoconnect no`なので，保存しただけでは次回起動時にAPを選ばない．
机上のクライアント／実験中のAPという起動方針は，確認後に別に決める．
意図せずeduroamよりAPが起動時に優先される設定にしない．最初の現地試験で戻すには，
追加した設定だけを停止し，確認した元の設定を有効化する．

```sh
sudo nmcli connection down b2-local-management
sudo nmcli --ask connection up uuid "$EDUROAM_PROFILE_UUID"
```

モードを変えるだけのためにeduroamを削除・再作成しない．大学Wi-Fiへ戻す際はMacの
通常のIP設定も戻す．保存したAPの秘密情報も将来の引継ぎで確認する．
ここにある有効化コマンドは，どれもまだ実行していない．

## 5．B2のリモコンは別の制御経路

既存のリモコンは，初期姿勢，手動の位置調整，操作者の介入，文書化された停止手順に使う候補になる．
Mac，eduroam，Tailscale，モデルのプロセスに依存させない．ただし，実際の受信機・制御系の関係は
確認が必要である．一つの無線が別であることは，内部の全制御系の独立性まで証明しない．

現地では機種，pairing，電池，状態表示，正式なボタン・モード，制御の優先順位，運用上限を記録する．
訓練済みの操作者に，研究室の機体取扱い規則で既存手順を確認してもらう．研究用の移動を始める前に，
手動介入でSDK要求が禁止されるか，研究ソフトが新しい許可までdisarmを保つかを確認する．
操作者が手を離した直後に，背景の指令送信が勝手に再開する構成にしない．

速度ゼロの要求，姿勢・モーターモードの変更，damping，電源遮断，実際の非常停止機能は区別する．
立っている四足ロボットへの影響は異なる可能性がある．名称からボタン操作を想像したり，
どれかを認証済み非常停止と扱ったりしない．SDKの停止要求が返ることも，実際の停止の計測ではない．
実験の独立した停止手段を選ぶ前に，適用する正式手順，観測結果，限界を記録する．

## 6．障害ごとに合格条件を分ける

| 事象 | 移動前に必要な方針・証拠 |
|---|---|
| Macの画面・SSH切断 | ローカルプロセスの寿命が端末から独立し，選んだ操作者監督の規則も維持 |
| Mac・AP通信断 | 操作者リンクが必須ならdisarm・停止．継続する場合は別に承認した独立の監督が必要 |
| カメラ・機体状態が古い | 該当の経路・指令を拒否・期限切れにし，確認した停止経路を使う |
| モデルが遅い・停止 | 有効なキャッシュ・期限を守り，古い経路を無期限に使わない |
| プロセス・コンテナ故障 | ローカルで検知し，機体の指令断応答を実測．再起動後もdisarm |
| 機体Ethernet断 | 切れたケーブルへ停止要求を送るだけでは止められない．B2のtimeoutと独立の操作者応答を測る |
| B2リモコン断 | 確認した受信機動作・実験方針に従う．手動の制御権が無期限に残ると仮定しない |
| インターネットなし | 準備したローカル推論・記録・制御が通信を要求しない．まず移動なしでネットワークを外して検証 |

現在の純粋なソフトウェア上の期限検査だけでは，この全体を実装・証明していない．
最初はオフライン再生と観測だけの起動・終了試験を行い，実際の制御権・停止は別の管理された段階で
検証する．通信断を伴うロボット試験はまだ実施していない．

## 7．合格条件と記録

APのドライバ対応，非公開のアドレス計画，ローカルSSH認証，保護した設定，復旧方法を記録する．
まず移動しないオフライン処理で，Macを切断しても続き，再接続でログを取れることを示す．
RDPサーバーの導入確認後，同じローカルSSHトンネルでも試す．その後，電源投入からの
プロファイル選択，ログイン前の接続，指定したdisarm起動を確認する．初回は現地の復旧手段を残す．

最終的な移動の合格には，センサー・時刻・座標系，制御権，停止動作の計測と，範囲を限定した
実験計画も必要である．生の記録はGit対象外の`local/`へ置き，レビューした説明だけを公開する．
Mac不要，インターネット不要，適切な操作者の監督という三つは別の主張であり，それぞれ証拠が必要である．
