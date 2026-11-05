# 2026-11-04までの進捗記録

[English](project-history-through-2026-11-04.md) · [ホーム](../../README.ja.md)

> **履歴の固定記録**．文書再編前のsource `b981bab`にあった進捗・判断を保存したもの．ここにある「次の作業」は記録時点のもので，現在の一覧は[進捗](../status.ja.md)を使う．

> 公開状態の訂正（2026-11-04）：この固定記録には「公開保留中」という誤記が残っている．研究室のリポジトリは既に公開済みで，公開・clone手順の修正はGitHubのPR #1・#2でマージ済みだった．以下の元の記述は履歴として残し，現在の公開状態は進捗を参照する．

## 現在の段階

更新日：**2026-11-04**．調査後に操作者がB2をシャットダウンした．その後の作業は外付けJetsonだけへ接続し，
追加の実機要求は送っていない．Tailscaleの再本人確認後，Jetsonのソース141ファイル全てのhashを照合し，
通常テスト184件も成功した．Mac・Jetsonの双方で同じ184件が通っている．配置したソースの版は非公開の
`local/source-revision.txt`へ記録し，取得ファイルと操作者の目視結果もJetsonの非公開領域に保存した．GitHub公開は保留中である．

先の版照会の後，既にダンピング中の機体へ**Damp要求（API 1001）を一回だけ**送り，status 0の応答を得た．
送信前に新しい状態を確認し，前後61件ずつの状態はmode 7，error 0を維持した．操作者は**変化なし・ダンピングのまま**，
予期しない動きなしと確認した．立上がり・復帰・移動は要求していない．**i7上のAPI往復は1.34 ms**で，
JetsonからのSSH経路を含まず，姿勢変化・停止に要する時間でもない．要求は外付けJetson → SSH → i7 →
native ROS 2・DDS → B2 serviceを通った．固定版の[B2 API定義](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/unitree_sdk2py/b2/sport/sport_api.py)がDampを1001，
公式[ROS 2状態の説明](https://github.com/unitreerobotics/unitree_ros2)がmode 7をダンピングと定義する．一時clientは終了し，常駐する移動送信部は配置していない．
証拠はJetsonの非公開`local/b2-damping-sensors-01`にある．

別の受信専用購読で，最後の試行では内蔵の前後画像を1280×720・640×360へ復号し，IMU・関節・sport・odometry状態を
受信した．その区間でpanorama・wireless controller・LIOは受信なし，利用可能な点群は未確認である．
[センサー結果・保存画像の表示・再取得](built-in-sensors.ja.md)を参照する．内蔵画像をTIC-VLA入力にはまだ使っていない．
外付けからの直接DDSは未解決である．

希望された最初の姿勢・前後移動試験は，操作者が十分な空間を確保できないと確認したため保留した．その移動前調査では作動要求を送っていない．
その後の単発Damp検査は上記に記す．
新しい3秒の外付けSDK状態検査は受信0件だった．標準LANのi7側では，版情報だけの照会が成功し，status 0，API版
`1.0.0.1`を返し，同時に有限な状態162件を受信した．内蔵側のservice応答を確認した結果であり，物理的な制御準備の完了ではない．
i7はIPv4返信にUSB経路ではなく標準Ethernetを選んでいた．[現地カード](../how-to/field-card.ja.md)に最初の移動の段階と，
現在公式が案内する説明書のL2＋Bによるダンピングを記す．実個体の停止・介入は未検証である．
非公開の証拠は`local/b2-pre-motion-01`に置く．

操作者がカメラ画像・経路表示とVS Code利用を確認した．**2026-11-03**，起動済みB2への
初回接続を調べた．USB-C／Anker Ethernet hubの接続先は，内蔵の**Intel Core i7-1265U開発用PC**だった．
Jetsonや動作制御器と同定したわけではない．許可された既存の認証でscope付きIPv6からログインできた．
動作制御器へのSSHログインは試していない．このPCは論理CPU 12個，Linuxから見えるRAM約15.22 GiB，
512 GBクラスのNVMe，Ubuntu 20.04.6とRT kernelだった．追加の内蔵Jetsonの有無・型式は未確認である．

このPCの機体側の標準EthernetでRTPSの発見情報からdomain **0**を観測し，12秒の受信専用ROS 2試験で
`/sportmodestate`を**5,994件**，`/lf/sportmodestate`を**240件**受信した．検査した位置・速度・yaw速度・姿勢は
全件で有限だった．これは**内蔵PCでの状態受信**であり，外付けJetsonのSDK直接受信やモデル入力との結合ではない．
USB Ethernetはブリッジされていない別interfaceで，IPv4経路にも重複があった．外付け側linkは1 Gbps full duplexだが，
回数を制限したIPv4試験では標準の機体serviceへ届かなかった．外付けJetsonだけで標準LAN用profileを試し，
初回試験の最後に元の有効profileへ戻した．後の再確認では新profileが有効・自動接続ありだった．操作者の依頼に従い，
現在使っていない古い有線設定二つを退避して削除し，`b2-research-link`だけを残した．Wi-Fiはdefault routeを維持する．
B2側の設定・package・firmwareは変更せず，その初回調査ではモーター要求は送っていない．非公開の証拠は`local/b2-connection-01`に置く．
[実測構成と次の接続手順](../how-to/field-network.ja.md)を参照する．

[短い操作デモ](../how-to/live-camera-demo.ja.md)に確認・起動・表示・終了コマンドを用意した．
実cameraで60枚を取得し，model load 1回で入力画像対応の予測5回が完了し，両containerも正常終了した．
状態は静止仮定，Webサーバーなし，robot指令なしである．

[モデルの解説](../explanations/ticvla-explained.ja.md)は，画素，CoT・KV特徴，二種類の目標点，metreの座標，遅延，追従式，
B2で検証する項目まで順に説明する．新しい報告は同じ呼出しのVLM文章を残し，終点・経路の距離とともに表示する．
network隔離した保存画像の試験は30点と返答412文字を返し，load 11.158秒，推論11.384秒だった．
prompt・生成設定は変更せず，実状態や移動は使っていない．証拠は非公開`local/model-response-validation-01`に置く．

全体の固定記録は[2026-11-03マイルストーン](milestone-2026-11-03.ja.md)にある．
操作には[初期構築](../how-to/setup-from-scratch.ja.md)と[カメラ・経路表示の実行手順](../how-to/run-camera-demo.ja.md)を使う．
新しい一連の試験でZED画像を撮影し，load 13.109秒後に13.290秒でXY 30点を予測し，
単独HTMLへ描画して目視確認した．その記録時は静止仮定・B2未接続だった．その後の内蔵側の状態受信は上記に記す．
Ethernet・状態受信の調査には進めるが，歩行できる段階ではない．

更新日：**2026-11-03**．外付けJetsonのGPUでTIC-VLAを読み込み，生成画像による1回の
オフライン推論が成功した．1,324個のtensorキー，948,462,978個の重複を除いたパラメータ，
horizon 30，action 3層を厳密に照合した．生成画像の1回の処理は**13.64秒**で，有限なXY座標30個を返した．
予測対象が3秒先までであることと，実時間の制御ができることは異なる．この生成画像の試験は実カメラ，B2状態，
ナビゲーション課題を評価せず，モーター指令も送っていない．その後，ZEDのRGBを初めて取得できた．
[カメラの準備](../reference/camera-runtime.ja.md)を参照する．

その後，保存した1280×720のZED実画像を，明示的に仮定した静止状態で二回処理し，
全体12.00秒・9.93秒で成功した．意味情報の生成は11.57秒・9.57秒，行動decoderは約0.006秒だった．
別の短い連続取得はSDKのgrabが90/90回成功し，約30 grabs/sだった．上限を設けた互換性の検査で，
継続ライブ制御や走行品質の検証ではない．限界・失敗は[実行時の計測](model-runtime.ja.md)に記す．

ホストはAGX Orinの64 GBクラス，Ubuntu 20.04，L4T 35.4.1，CUDA 11.4のままである．
既存のGPUコンテナはPython 3.11.18，Torch 2.2.2，Transformers 4.44.2を使う．別の
Torch 2.15.0+cpuコンテナで承認済みチェックポイントをsafetensorsへ変換し，古いGPU環境へ
元のpickleを復元させていない．追加後の**184件はMac・Jetsonの双方で成功**した．
[モデル資材と読込](../reference/model-artifacts.ja.md)と[変換](../reference/checkpoint-conversion.ja.md)に手順，証拠，限界を記す．

時間制限付きの実カメラ非同期shadow試験は，仮定した静止状態で35回の行動予測を完了した．
準備待ち・cache期限切れの空白も出た．別の状態専用SDK・DDSイメージは，source・ネイティブlibrary・
合成符号化のオフライン検査を通った．[cache実験](../reference/asynchronous-runtime.ja.md)と
[SDK環境](../reference/unitree-runtime.ja.md)に記す．どちらも実機の移動を検証したものではない．

内蔵PCでの状態受信は成功したが，外付けJetsonへの直接受信，実状態を使う非同期制御の結合，
継続的な指令送信，物理的停止，ナビゲーション評価は未検証または未実装である．ソースは研究室の
[DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2)に置かれている．
今回の接続調査の変更はpushしていない．
[MITライセンス](../../LICENSE)は独自のコード・文書だけを対象とし，本家コード，重み，変換物を再ライセンスしない．

2026-11-03の現地再起動後，eduroam・Tailscaleは復帰した．保存ログには，認証情報が存在していても
再起動前にWi-Fi認証タイムアウトが起きていた記録があり，AP・認証側・端末のどこが原因かは未確定である．
GUI初期化の警告は別に調べる．エージェントはRDP起動待ちの想定例外を修正し，自分の試験報告だけを退避した．
Wi-Fi・GDM設定はエージェントから変更していない．[接続障害の調査](../reference/system-overview.ja.md#接続断とデスクトップ不調の切り分け)を参照する．
その管理接続の復帰を，実機制御の準備完了とは扱わない．

その後，操作者がWindows Appの直接画面接続を確認した．明示的な選択に従い，研究用GUIの
更新・クラッシュnotifierの自動起動を抑止した．クラッシュ記録・手動APTは維持した．通知だけの変更ではpackage更新・削除や自動更新service追加は行っていない．
その後のSSH・Chrome保守とeditor導入は別に記録している．
[手動更新と通知](../reference/system-overview.ja.md#手動更新とデスクトップ通知)を参照する．

## 対象の構成

| 要素 | 確認したこと | 残る作業 |
|---|---|---|
| 機体 | 操作者から車輪のないUnitree B2との報告 | firmware，実際の計算機・サービス，制御権，停止 |
| 外付けJetson | AGX Orinの64 GBクラス，ネイティブCUDA・コンテナのGPU演算，実モデル読込，保存画像の計測，時間制限付きのカメラshadow推論 | 実B2状態，時計・座標の対応，cacheの継続的な可用性，長時間運用 |
| 内蔵開発用PC | Intel i7-1265U，x86_64，論理CPU 12個，RAM約15.22 GiB，512 GBクラスNVMe．標準LANのROS 2状態受信に成功 | センサー所有関係，外付け側への検証済みDDS経路．追加Jetsonは未確認 |
| 機体機能用計算機・動作制御の実装 | 公式標準構成は機体機能用Core i5．今回の個体では未調査 | 実hardware・OS，serviceのhost，モーターへの経路，制御権 |
| カメラ | ZED 2i，USB 5 Gbps，SDK・bindingと1280×720の左RGB取得が一回成功 | 取付後の視野，継続取得，撮影時計の対応 |
| LiDAR | Livox Mid-360との報告 | 既存driver・networkと，RGBモデル入力以外での用途 |
| 管理接続 | HDMIなしでeduroam・Tailscale・SSH・RDPのソフトウェア再起動後の復帰が成功 | 物理的な電源の入れ直し，移動時の通信復旧，node keyの方針 |

機器があることと，センサー・ナビゲーションの検証は異なる．初回の構成調査は
[基準情報](target-baseline.ja.md)，現在の保存先と隔離の境界は[システム全体像](../reference/system-overview.ja.md)に記す．

| 成果物 | 状態 | 根拠・完了条件 |
|---|---|---|
| 日英の手引きと共同開発ルール | 維持中 | 目次，開発ルール，構成，実験手順 |
| 再生と制限付きの追従計算 | オフラインで実装済み | 合成再生，古い入力の拒否，速度制限．送信部はない |
| モデル資材の取得 | 照合済み | 承認した17ファイル，固定版，3,827,163,803バイトとdigest |
| CPU変換 | 実チェックポイントで検証済み | 1,324個の名前を維持し，3,773,492,276バイトの出力と読戻しmanifest |
| GPUモデル読込 | 成功 | キー・shapeの厳密照合，パラメータ・device確認，元のpickleは渡さない |
| オフラインの数値推論 | 生成画像一回・保存した実画像二回が成功 | 各回で有限な30点．実画像の状態は仮定で，B2からは受信していない |
| 実画像・状態の観測 | 制限付き試験でJPEG 275枚，別試験で内蔵PCのB2状態受信に成功 | 取付後の視野，長時間取得，状態，時計，座標系，組の記録を確認 |
| 一体のcacheと非同期observer | 実験的なshadow試験が成功 | 行動35回．仮定した静止状態，未検証の撮影時計，cacheの大きな空白 |
| 外付けUnitree状態専用環境 | build・オフライン検査は成功 | SDK・DDS固定，source hash 202個，合成516バイトの往復一致．外付けcontainerのB2受信は未検証 |
| 移動指令送信 | 未実装 | 実状態の結合，独立した指令期限，watchdog，制御権 |
| 物理的停止とB2評価 | 未検証 | 移動前に段階的な実機試験を確認・実施する |

## 決めていること

- ホストのOS，JetPack，ROS，既存の研究室データを維持する．Dockerと標準HubキャッシュはSSDの
  専用領域を使い，既存データはformatしていない．
- 元のHugging Face資材はSSD上の標準キャッシュへ置く．変換したsafetensorsとmanifestはSSDの
  非公開models領域へ置き，Git対象外のプロジェクトの`models` symlinkから参照する．重み，モデルの
  独自Python，生ログはGitやMacに置かない．分離は[実行の流れ](../reference/runtime-flow.ja.md)に記す．
- 古いTorchでの元チェックポイントの復元は拒否し続ける．CPU変換部は制限付きの読込，上限，checksum，
  alias名の完全な維持，ビット単位の読戻しを使う．変換しても本家の条件はなくならない．
- GPU試験はネットワークなし，通常のUID，capabilityなし，ソース・重みは読み取り専用，一時的なmodule
  cacheで行った．GPU deviceのvideoグループだけをコンテナ内に追加し，ホストの所属・権限は変更していない．
  モデルだけの検査は機体・USB・profilingをmountしなかった．カメラ検査は別途，確認したvideo・USB nodeと
  読み取り専用SDKを渡し，そのグループをコンテナ内だけへ加えた．NVIDIA runtimeがGPU interfaceを供給する．
  ホーム・認証情報は渡していない．
- HDMIなしのeduroam再起動と，その後のRDP操作は成功した．Wi-Fiの秘密情報の保存にGUI自動ログインは
  不要で，既存のGDMの対象は維持する．GUI編集はpolkitが拒否したため，所有者の端末で保存した．
  返却確認は新しい研究用ログインだけでなく，UWNetのポータル認証を行った既存の研究室ログインも対象とする．
  整理・削除はまだ行っていない．
- 現在の候補からVNCを除外する．既存NoMachineは変更せず，xrdpの方が速いという比較結果はない．
  過去の画面接続手順は[リモート画面](../how-to/remote-desktop.ja.md)に記す．
- 操作者の依頼で，JetsonのTailscale IPv4への直接RDPを準備した．MacのTCP・RDP・TLS・証明書一致は通った．
  操作者が2026-11-03に直接画面の表示を確認した．最新設定での機器全体の再起動は別の確認項目とし，
  Windows Appの登録は操作者が管理する．
  Macのtunnel・自動起動は追加せず，前景の作業SSHは終了する．ホスト側の追加は，
  [遠隔画面ガイド](../how-to/remote-desktop.ja.md)の対象を絞ったRDP guard・drop-inだけである．
- カメラSDK・bindingの読込と依存検査は，専用の非公開配置先・コンテナで成功した．ホストの所属やGPU
  イメージは変えていない．USB取得の確認は[カメラの準備](../reference/camera-runtime.ja.md)に記す．

## 次の成果物

1. 次の起動時に，未記録のi7のSDK・DDS版を調べ，firewall ruleを変更せず読み，端子ラベルをマニュアルと照合する．
   その上で，標準LANの正規接続か，明示的に検討したi7中継を選ぶ．
   [現地カード](../how-to/field-card.ja.md)と[Ethernet手順](../how-to/field-network.ja.md)で，B2の実際のnetwork，計算機，
   センサー，受信専用SDK経路を調べる．管理用Wi-Fiを維持し，機体LANと大学を分ける．
   必要イメージ・ローカル資材を再確認し，変換重みのSHA256一致と新しいオフラインSDK検査も通った．
   [訪問カード](../how-to/field-card.ja.md)にケーブル・電源・リモコンと，状態コンテナの実行経路を記す．
2. ZEDの初回RGBと短い連続取得は通った．指令なしでB2状態を確認する．実際の経路を解釈する前に，軸，単位，取得元・受信の時刻，
   odometry，校正を確認する．
3. 制限付きの非同期shadow試験へ，実際に検証した状態・時計・座標系を加える．準備待ち・更新待ちの空白，
   推論停止，古い・欠落した観測を調べる．行動計算の中央値0.156秒は，途切れない制御や古い意味情報での
   正しい走行を証明しない．
4. 制御権，リモコンの優先順位，実際の停止を確認してから，保護された低速移動と事前定義した評価へ進む．

初回の生成画像の試験は，本家のサンプリング設定（最大200 token，temperature 0.7）を使い，seedは
固定・記録していない．CPU・資源上限下の単発の時間で，平均値のbenchmarkではない．PyTorchのGPU
allocatorのpeakはCPU RAM，driverの確保，unified memory全体を含まない．実時間性，走行品質，
物理的安全の証明にはならない．

## 作業を再開する方法

最初にこのページ，対象の手引き，Git diffを読む．範囲を区切ったbranchで作業し，日英の結論を合わせる．
対象機で使う前に，確認したソースをローカルでcommitし，Jetsonのarchiveへhash照合して同期する．
配置した版は非公開の`local/source-revision.txt`に記録する．GitHub公開は保留中である．
詳細な構築・取得・読込・推論の記録は，失敗した試行も含め，JetsonのGit対象外`local/`へ置く．
ソースの版，image ID，hash，入力，上限，限界を残し，このページをチャットの履歴にしない．
