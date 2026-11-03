# 操作手順：カメラと予測経路を確認する短いデモ

[English](live-camera-demo.md) · [ドキュメント](README.ja.md) · [初期構築](setup-from-scratch.ja.md)

## 1．目的と前提

準備済み外付けJetsonを，自分で動かすための**順番どおりの操作手順書**です．
モデルを1回読み込み，カメラ表示の変化，保存画像ごとの予測更新を確認して終了します．
B2は未接続とし，モーター指令機能はありません．Internet，ROS 2，MacのDocker，Webサーバー，
SSHトンネルは不要です．既存RDPでJetson画面を見られます．計算と撮影は両方Jetsonで行います．

**ZED 2iを1台だけUSB 3で接続**し，他のカメラ利用を閉じ，[初期構築](setup-from-scratch.ja.md)の
ローカル入力を揃えます．既定は現在の研究用配置で，ZED SDK 4.1.2，
`local/camera-runtime/attempt-01/python`の専用API，同じattemptの`settings`にある一致する校正，
既存GPUイメージ，確認済み外部source，承認済み基盤snapshot，hash検証済み派生safetensorsを使います．
起動時のインストール・取得はなく，rootで実行しません．

**静止状態を仮定した画像応答の実演**であり，走行試験ではありません．
手持ちcameraを動かすと画像は変わりますが，実測の機体変位・yawは入力されません．
経路は未校正で，通行可能性や指示への正しい追従を示しません．現在のpreviewと過去の予測入力を分けて表示します．

## 2．端末A：既存入力を確認する

SSHまたはGUI端末で，**Jetson上**で実行します．

```bash
cd ~/Developer/Projects/Robotics/b2/VLN_B2
sudo -v
python3 tools/camera_demo.py check
```

`sudo -v`は端末内で認証します．パスワードをコマンド，設定，チャットへ書きません．
Pythonは研究ユーザーのままで，既存Docker engineの操作だけを`sudo -n`で行います．

成功時は`prepared_inputs_verified: true`，不変image ID，実cameraノード，
`model_loaded: false`，`camera_opened: false`，`motion_sent: false`が表示されます．
source・cacheの存在，3.77 GBの派生重みhash，sysfs上のZEDを確認します．
モデル読込・camera openは行わないため，実際の校正・GPU実行・撮影は次で確認します．
hash計算には数秒かかる場合があります．

USB番号は前日のものを流用せず毎回識別します．対応cameraがない，または複数なら失敗し，
適当な`/dev/video0`を選びません．初期構築で別のAPI／settings配置にした場合は第8節を使います．

## 3．端末A：カメラとモデルを起動する

**新しい**出力先を指定します．既存実験フォルダは再利用しません．

```bash
python3 tools/camera_demo.py run \
  --output local/live-camera-demo-03 \
  --duration 60 \
  --instruction "Move straight ahead."
```

`file:///.../index.html`が表示されます．端末は開いたままにします．
前面で動く時間制限付きコマンドであり，常駐serviceではありません．一時コンテナを2個起動し，
片方が毎秒1枚を目標に撮影，もう片方がTIC-VLAを1回読み込んで，新しい直近画像ごとに同期予測します．
ロード・待機・失敗も表示するHTMLはすぐに作られます．

予測側の60秒にはモデル読込を含みます．撮影側はcamera open後，最大60秒記録します．
既に開始した推論は入力期間後に終わる場合があります．native処理にはコンテナの120秒期限と
supervisorの125秒上限もあり，これは所要時間の見込み値ではありません．通常は約1分とその後の終了待ちです．

最初の結果は**ロード＋推論**が必要です．以前はそれぞれ約13秒だったので，
すぐ経路が出るとは考えず，25～35秒程度待ちます．以後はモデルを再ロードしませんが，
同期の意味計算を繰り返すため経路更新は約10～15秒かかり得ます．
高速cache再利用実験とは別で，動画の速度で経路を出すデモではありません．実時間は実行条件によります．

## 4．RDP画面の端末B：表示を開く

**JetsonのGUI内**で別の端末を開きます．

```bash
cd ~/Developer/Projects/Robotics/b2/VLN_B2
xdg-open "$PWD/local/live-camera-demo-03/index.html"
```

または端末Aのアドレスを**Jetsonの**ブラウザへ貼り付けます．通常のSSH端末にはGUI sessionがなく，
そこで`xdg-open`が動くとは限りません．Macの設定，トンネル，port公開，Webサーバーは不要です．
local fileをsupervisor実行中は2秒ごとに読み直します．

更新後の予測には**Generated VLM response**，終点座標，終点までの直線距離，点列の経路長も表示します．
返答は`model.vlm_response`へ保存し，青いaction経路を文章から読み取って描くことはありません．
埋込み枠内をscrollするか，完全レポートを開いて読みます．更新後は新しい出力先を使ってください．
古い報告から捨てた文章を復元することはできません．読解演習は[TIC-VLAの仕組み](ticvla-explained.ja.md)にあります．

準備済みJetsonでは，GUI内の端末から完成済みの保存画像の例も開けます．モデルの再読込は不要です．

```bash
cd ~/Developer/Projects/Robotics/b2/VLN_B2
xdg-open "$PWD/local/model-response-validation-01/results/prediction.html"
```

これは準備済み対象機だけにある任意の例です．新規構築では自分で報告を生成します．この手順のライブコマンドは
新しい`03`フォルダを使います．既に存在する場合は別の未使用番号を選んでください．

画面は次を示します．

1. **段階と指示**．loading，画像待ち，predicting，finished，stopped，failedを表示します．ロード中に経路がないのは正常です．
2. **現在のカメラpreview**．取得目標は毎秒1枚，画面更新は2秒ごとです．frame名と受信からのageを示します．撮影時計の対応は未確認で，古い画像を新しいと偽りません．
3. **最後に完了した予測と，その正確な入力**．保存した入力画像とモデル相対経路，frame名，推論時間を示します．previewは既に別の場面かもしれません．
4. **完全レポートへのlink**．別tabで開けば，デモ画面の再読込でscrollを戻されずに全30点の座標を読めます．

赤が仮定原点，青がメートル単位の将来相対位置です．x前方を上，y左方を左に描きます．
XYは位置なので**累積和を取りません**．時刻の0.1秒刻みは仮定で，B2の検証済み周期ではありません．
B2とcameraの幾何が未測定なので，写真への投影ではありません．

## 5．短い実演の進め方

cameraを安定させて静止した場面を見ます．最初の経路が出たら，向きをゆっくり別の視野へ変え，
次の予測まで静止させます．少し左右を向ける程度で十分です．抜線や激しい振り回しは避けます．
比較中は同じ指示を使います．

最初に**preview画像の変化**を確認します．次に，完了予測の**入力frame名と写真**が変わるまで待ちます．
以前の保存レポートと経路・座標を比べます．古いframeを示す予測のまま，新しい場面に反応したと扱いません．
短い実行では結果が2～3回程度になる場合があります．

指示を変える場合は，新しい実験先で再起動します．上流はsamplingを行い，camera移動に対応する実odometryも
ないので，経路の差だけで正しい指示追従を証明できません．不自然な経路も検査を緩めず，証拠として残します．
これらの操作でrobotへ指令が送られることはありません．

## 6．終了と結果の保存

自動終了を待つか，**端末A**で次を押します．

```text
Ctrl+C
```

supervisorは自分の2コンテナだけを削除し，client processの終了を待ちます．
最後の画面は終了表示となり，再読込を止めます．画像，結果，log，最終画面は残ります．
ブラウザを閉じるだけでは推論は止まりません．端末を閉じる操作も推奨しません．
後片付けに失敗した場合は，止まったと偽らず失敗を報告します．

必要なら終了記録とコンテナ一覧を確認します．

```bash
python3 -m json.tool local/live-camera-demo-03/summary.json
python3 -m json.tool local/live-camera-demo-03/predictions/status.json
sudo docker ps --format '{{.Names}}'
```

自然終了の成功は`outcome: "finished"`，`cleanup_errors`が空，予測1件以上と`passed: true`です．
`stopped_by_operator`は中断した意味で，予測完了前かもしれません．両方に
`motion_sent: false`と`robot_connected: false`を記録します．
今回の`b2-demo-camera-`／`b2-demo-predict-`で始まる2つの名前は終了後の一覧から消えます．
無関係なコンテナは削除しません．これは計算の停止であり，robot非常停止ではありません．robot接続自体がありません．

| 指定した`local/`の下の出力 | 内容 |
|---|---|
| `index.html` | 実行中のpreview・結果表示，終了後の最終保存表示 |
| `camera/frames/frame-*.jpg`，`frame-*.json` | 不変の撮影画像と時刻・digest情報 |
| `camera/frames/latest.json`，`summary.json` | 原子的な最新camera参照とcamera終了記録 |
| `predictions/prediction-*.jpg` | 各推論が使った正確な入力の不変コピー |
| `predictions/prediction-*.json`，`*.html` | 経路，時刻・履歴，単独で開ける入力・経路表示 |
| `predictions/status.json` | 予測側の現状・終了段階，完了数，最後の結果識別子 |
| `invocation.json`，`camera.log`，`predict.log`，`summary.json` | 実image・コマンド，診断，supervisor結果 |

HTMLにも人物・画面を含む室内画像が入るため，非公開で保管します．毎秒1枚のcamera取得は
30 fps動画ではありません．推論・開始時間は，この取得目標とも別です．

## 7．B2を動かすコマンドは何か

**ロボット指令用CLIはまだありません**．`check`は入力調査，`run`は撮影・予測・表示，
Ctrl+Cはそのprocess停止です．local viewerや経路レポートは操縦画面ではありません．
架空のdriveコマンドを手順へ書いたり，次の近道としてvendorの移動exampleを実行したりしません．

次は[現地カード](field-card.ja.md)で，別のUnitree環境からEthernetと受信専用の状態調査をします．
実座標，時計・状態の対応，操作権，リモコン優先，受信側の指令断挙動，制限付き送信器，独立した停止・expiryは
移動の前に残る作業です．実装・検証後に，前提，開始・操作・終了コマンド，期待応答を操作書へ追加します．
それまでは予測と物理制御を別の段階とします．

## 8．問題の切り分けと別の非公開camera配置

| 症状 | 対応 |
|---|---|
| Dockerを調べられない | 研究ユーザーで`sudo -v`し，既存image・保存先を確認 |
| cameraなし／曖昧 | ZED 2iを1台にし，USB 3 cable・電源・識別を確認 |
| previewが空のまま | `camera.log`，競合利用，一致する校正を確認 |
| previewは変わるが経路なし | load＋推論を待ち，stageと`predict.log`を読む |
| 経路が変わらない | 完了数と正確な入力frameを確認．無関係な新previewと比較しない |
| 実行失敗 | log／statusを残し，原因を直して新しい出力先へ |
| local fileが再読込されない | 手動更新する．端末とstatus fileが状態の根拠 |
| 新規実行が拒否される | 過去の証拠を残して新しい名前を使う |

初期構築書で別のprefix／settingsを作った場合は，**checkとrunの両方**へ指定します．

```bash
python3 tools/camera_demo.py check \
  --camera-api local/camera-runtime/rebuild-01/python \
  --settings-dir local/camera-settings-01
python3 tools/camera_demo.py run \
  --camera-api local/camera-runtime/rebuild-01/python \
  --settings-dir local/camera-settings-01 \
  --output local/live-camera-demo-02 --duration 60 \
  --instruction "Move straight ahead."
```

global設定は保存しません．一枚ずつ切り分ける[保存画像の推論手順](run-camera-demo.ja.md)も残っています．
モデル・ソース・ソフトの固定情報と全体の到達範囲は[マイルストーン](milestone-2026-11-03.ja.md)を参照します．

## 9．準備済みJetsonでの実測確認

2026-11-03にsource `9fe752c`，既存参照GPU image，承認済み資材で実camera試験を完了しました．
producerは毎秒1枚の目標で**60/60枚**取得し，モデルは**11.235秒で1回だけload**しました．
frame 13，26，36，46，57で**5回の予測**が完了し，全て30点でした．
推論時間は**12.617，10.435，10.243，11.034，10.446秒**です．
各レポートに正確な入力画像・digestと単独HTMLを残しています．

両containerは終了コード0，supervisorは`finished`，cleanup errorは空で，残る実行containerもありませんでした．
最終画面を描画・目視確認し，**Mac・Jetson双方で177テスト成功**です．
準備済み手順の検証であり，正しいnavigationや論文結果の再現ではありません．
この自動確認中に操作者がcameraの向きを変える実験は記録していません．第5節の視野比較は実際に行って確認します．

実行中の別試験でCtrl+Cを送り，`stopped_by_operator`，cleanup errorなし，残存containerなし，
最終画面の再読込指定なしを確認しました．この中断でのcontainer終了137は意図的な強制削除の結果であり，
予測成功やモデルcrashを診断した意味ではありません．

2026-11-03に操作者もcamera画像と予測経路の表示を確認し，その後に起動済みB2の接続を報告した．
viewer手順の確認であり，経路品質，camera移動補償，実状態との結合の検証ではない．
[初回接続の現状](status.ja.md)を参照する．
