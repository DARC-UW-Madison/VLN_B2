# マイルストーン：2026-11-03までの外付けJetson構築

[English](milestone-2026-11-03.md) · [ドキュメント](../README.ja.md) · [最新状態](../status.ja.md)

> 文書種別：**実験・構築記録**．コマンド・計測は記録時の環境を示す．現在の操作には手順書を使う．

## 1．この時点の判定

**B2の初回Ethernet接続と，指令を送らない状態受信の調査へ進めます．モデルによる歩行はまだできません**．
外付けJetsonは外付けZEDのRGB画像を取得し，承認済みローカルTIC-VLAをGPUへ読み込み，
将来XY位置30個を予測して，入力画像と経路を単独HTMLで表示できます．
別途，限定時間の非同期shadow実験も，モーター出力なしで実行しました．

B2は未接続です．内蔵計算機，Ethernet構成，状態topic，座標，操作権，停止挙動は未測定です．
実装に`SportClient`作成，`Move`呼び出し，モーター指令publishはありません．
オフライン追従器のゼロ候補は物理停止ではなく，ケーブルを挿しても歩行は始まりません．

本書は今日までの準備，判断，失敗，到達範囲を固定した記録です．操作には
[初期構築](../how-to/setup-from-scratch.ja.md)と[カメラから経路表示まで](../how-to/run-camera-demo.ja.md)を使います．
仕組みと根拠の詳細は各リンク先に置き，生の証拠は各機器のGit対象外に保管します．
以前のホスト時計修正があるので，古いログの全行へ厳密な実時刻を割り振らず段階で整理します．

## 2．研究目的，レポジトリ，協働方針

対象は車輪のない**Unitree B2**で，B2-WやGo2-Wではありません．
言語条件付き経路予測と意味推論の遅延を研究し，既存の歩行・関節制御は維持する設計です．
Go2-Wでの苦労は調査項目に反映しますが，IP，firmwareの挙動，SDK改変をB2へ流用しません．

研究室の保存先は[DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2)です．
ソースはローカルコミットとJetsonへのハッシュ照合付き同期が済んでいますが，**未push**です．
GitHubは推論の依存先ではありません．範囲を区切ったブランチとレビューを使い，テストと実機検証を
区別します．公開の基本は英語，日本語版を対にして`，`／`．`を使い，目次を別ファイルにします．
root READMEはプロジェクト説明に限定します．公開対象へ個人用agentファイル，ラベル，認証情報，
室内画像，モデル重み，vendorコードを含めません．AI出力は確認が必要で，実験証拠にはなりません．
[協働ルール](../../CONTRIBUTING.ja.md)と[開発手順](../reference/development.ja.md)を参照します．

独自コード・文書は寄与者を権利者とするMITですが，**TIC-VLAをMITへ変更していません**．
上流の独自学術条件はソース，重み，派生物にも関係します．承認は今回の非公開学術試用であり，
結合イメージや重みの再配布ではありません．InternVL，SDK，依存物の表示は別管理です．
将来の独自研究には使えますが，論文，改変上流資材，データセット，画像，学習重みの公開ごとに
権利と条件の確認が必要です．独自ライセンスを作ったり，MITで他者の権利まで与えたとはしていません．
[利用条件](../reference/licensing.ja.md)と[第三者資材](../../THIRD_PARTY.ja.md)を参照します．

## 3．外付け計算機とストレージの実測

| 項目 | 調査・確認した内容 |
|---|---|
| モジュール | Jetson AGX Orin 64 GB級，ARM64 |
| CPU | Arm Cortex-A78AE 12コア |
| GPU | Ampere，CUDA 2,048コア，Tensor 64コア，compute capability 8.7 |
| メモリ | Linuxで約61.3 GiBの統合RAM．GPUと共有し，別に64 GBのVRAMがあるわけではない |
| OS系 | Ubuntu 20.04.6，L4T 35.4.1／JetPack 5.1.2，CUDA 11.4，TensorRT 8.5.2 |
| OS保存先 | 約64 GB eMMC |
| 大容量保存先 | Samsung 990 PRO NVMe SSD 2 TBが1台．既存の研究室データ約1 TBは維持 |
| 既存ソフト | ROS 2 Foxy，ZED SDK，以前のデスクトップ・遠隔ツールを維持 |
| 外付けセンサ | ZED 2iは実撮影済み．Livox Mid-360は利用可能との情報のみで未統合・未試験 |

ハードウェアと構成の事実であり，TOPS実測，推論性能，常時接続，電池持続時間ではありません．
元の調査条件は[対象機の基準構成](target-baseline.ja.md)にあります．

SSDはext4が`needs_recovery`だったため，最初は`ro,noload`で調査しました．
通常のread-onlyでもジャーナル再生で書き得るため，承認前は`noload`で防ぎました．
操作者がリスクを了承した後，通常の書き込みマウントで再生し，観測したext4エラーはありません．
2台目のSSDやフォーマット操作ではなく，既存データも削除していません．
`/mnt/b2-research/VLN_B2`の下に専用領域を作りました．

Dockerは旧保存先が空であることを確認して専用SSD領域へ移し，旧設定と旧保存先は残しました．
SSD未接続時にOS領域を埋めないよう，serviceのマウント依存と確認を追加しました．
標準`~/.cache/huggingface`は専用SSDへ向け，その`hub`が公式Hub保管先です．
プロジェクトの`models`はSSD上の非公開派生物を参照します．ソース，`.venv`，非公開`local/`は
`~/Developer/Projects/Robotics/b2/VLN_B2`以下に分けてあります．

## 4．アカウント，隔離，ホストに加えた変更

研究用ログインでホーム，ファイル，Python設定を既存研究室アカウントから分けました．
ただし完全な隔離ではありません．kernel，デバイス，service，root管理，ディスク，統合メモリは共有です．
管理者やDocker権限はホストへ影響できます．Unixユーザー，pyenv，Dockerを絶対的なsandboxとはしません．

| 層 | 導入・設定したもの |
|---|---|
| 研究ユーザー | `~/Developer`内の固定pyenv・処理系，Python 3.11.18の専用venv，ソース・非公開記録 |
| ホストservice／保存先 | SSDマウント・リンク，Docker保存先・マウント確認，管理接続設定 |
| GPUイメージ | 独立したPython／Torch／vision／モデル依存環境．ソースビルドと一覧を保管 |
| CPU変換イメージ | 新しいCPU Torchと形式変換だけ．ホスト・GPU Torchの置換なし |
| カメラprefix | 専用pyzed／Cythonと校正．既存ネイティブSDK・ライブラリは読取専用 |
| Unitreeイメージ | 別のCycloneDDS・ネイティブライブラリと状態用Pythonソース |
| RDPホストprefix | `/opt/b2-remote`に別ビルドのxrdp／xorgxrdp．GNOME／GDM／NVIDIAは維持 |

モデル導入のためにホストPython 3.8，ROS Foxy，CUDA／JetPack，既存SDKの所有者を置換していません．
venvがGPU Torchやカメラbindingを供給するわけではなく，選んだコンテナが実行します．
イメージは準備済みファイルシステム，コンテナ起動は実際のプロセス作成です．
`--rm`終了で一時書込層は消えますが，明示したbind mountへの出力は残ります．
ビルド・取得と推論は別操作です．[ビルドの基礎](../explanations/build-fundamentals.ja.md)，
[実行の流れ](../reference/runtime-flow.ja.md)，[構成一覧](../reference/system-overview.ja.md)に境界と復旧を説明しています．

## 5．遠隔接続，起動時通信，発生した問題

eduroamはGUIログイン前に使えるシステム用NetworkManager接続として，自動接続と
root保護された認証情報の保存を設定しました．ID所有者は操作者本人です．
過去のソフトウェア再起動ではWi-Fi，Tailscale，SSH，RDPが復旧し，操作者が画面操作を確認しました．
試験した起動の証拠であり，全AP，認証期限切れ，電源断，大学側障害からの復旧保証ではありません．

Tailscaleは下位回線が使えるときの認証済みoverlay経路です．SSHでは追加本人確認が必要な場合があり，
Wi-Fi障害を直す機能ではありません．xrdpはJetsonのTailscaleアドレスの3389だけで待ち受け，
非tailnetからの入力制限と起動時確認・再試行を設けました．Windows Appから直接接続します．
以前のMac側SSH転送・接続プロファイル・常駐補助は撤去し，いまMacトンネルや常駐jobは不要です．
利用時にはMacがRDP／SSHクライアントであること自体は変わりません．

RDPは物理画面と別の仮想Xorg／GNOME sessionなので，dockや見た目が異なり得ます．
同じユーザーの物理GUIとRDPの並存で画面競合が発生しました．依頼により対象の物理GUIだけを
ログアウトし，SSH／RDPを残して，操作者が再接続を確認しました．物理自動ログインは当初既存の
研究室ログインを維持し，操作者が研究用へ変更しました．再起動で競合が再発する可能性は残ります．
GUI自動ログインはheadless通信には不要です．既存NoMachineは維持し，RDPとの性能比較はしていません．
VNCは導入していません．

後の到達不能をpersistent syslogと現serviceで調べました．保存認証が存在する状態でも，
Wi-Fi接続／EAPのtimeoutと追加secret要求が繰り返されていました．成功した起動ではGUI前に
保存済みprofileでEAP認証しています．パスワード消失，Tailscale自体のcrash，AP原因の解決は断定できません．
journalは前回起動を完全に再構成できず，時計修正もあったため，長いsleep表示だけでsuspendと判断しません．
再発調査のため不確実性を残します．

実際の「System program problem detected」は`update-notifier`の汎用画面で，
残ったcrashは以前のChrome SIGTRAPでした．正確な原因は未解明です．
以前のreadiness helperの意図的失敗試験もApport記録を作ったため，正常な失敗コードを返すよう直し，
その古い自己生成記録だけをarchiveしました．どちらもTIC-VLA／GPU推論のcrash証拠ではありません．
エージェントは報告を送信しておらず，今回の試用で外部報告は不要です．

操作者の承認で更新とcrashの両GUI通知を止めました．研究ユーザーのautostart上書きで
`update-notifier`を`Hidden=true`にし，そのユーザーのnotifierを終了しました．
システム元ファイル，他ユーザー，ローカルcrash記録，手動APTは残しています．
全crash serviceを無効化したり診断記録を削除したわけではありません．
共有・返却時には本人のWi-Fi秘密情報と，以前の研究室ログインで使ったUWNet portal／browser cookieも
確認します．一括削除や認証共有は行っていません．
[遠隔画面](../how-to/remote-desktop.ja.md)と[構成一覧](../reference/system-overview.ja.md)を参照します．

## 6．2026-11-03に適用した保守更新

APT索引の更新に成功し，シミュレーションを確認して既存4パッケージだけを更新しました．追加・削除はありません．

| パッケージ | 前 | 後 |
|---|---|---|
| `openssh-client`，`openssh-server`，`openssh-sftp-server` | `1:8.2p1-4ubuntu0.12` | `1:8.2p1-4ubuntu0.13` |
| `google-chrome-stable` | `156.0.8078.47-1` | `156.0.8078.79-1` |

SSH設定を保存・backupし，`sshd -t`成功，`dpkg --audit`不整合なし，SSH／Tailscale／RDP稼働を確認しました．
全パッケージ一覧の比較で，他の版は変わっていません．L4T，kernel，CUDA，TensorRT，Docker，
モデルイメージはこの保守処理で更新・再ビルドしていません．既に実行中のChromeで新しい実行ファイルを使うには
通常の再起動が必要ですが，ブラウザsessionを強制終了していません．
[Chromeの公開リリース](https://chromereleases.googleblog.com/2026/?amp=1)も確認しました．

Tailscale 1.104.4とxrdp 0.10.6.1は，
[security bulletin](https://tailscale.com/security-bulletins)と
[xrdp advisory](https://github.com/neutrinolabs/xrdp/security/advisories)を確認して維持しました．
全候補の更新やUbuntu 20.04の最新保護を保証する調査ではありません．追加修正には
研究室のUbuntu Pro／ESM権利が必要なものがあり，例えば
[USN-8804-1](https://ubuntu.com/security/notices/USN-8804-1)は今回の公開版より新しいESM版を示します．
契約の追加・購入はしていません．OSの保守方針は
[Jetsonの更新制約](https://docs.nvidia.com/jetson/archives/r35.4.1/DeveloperGuide/text/SD/SoftwarePackagesAndTheUpdateMechanism.html)も踏まえ，
研究室で別に判断する必要があります．

## 7．GPU実行環境のビルドと互換性対処

まず小さいネイティブCUDA FP32検査が最大誤差0で成功しました．L4T対応NVIDIA baseをdigest固定し，
CPython 3.11.18を別stageで構築，Torch 2.2.2とtorchvision 0.17.2をCUDA 11.4／sm_87向けに
ソースコンパイルしました．上流学習環境に合わせるためだけに共有ホストを置換していません．
PyTorch／vision，FP32／BF16計算，Transformers 4.44.2，Lightning，timm，上流importと`pip check`が通りました．

初期ビルドではTorchのRPC availabilityの不一致でimportに失敗し，ハッシュ確認付きパッチで未使用RPCを止め，
Glooを残しました．ビルドツールwheelのmetadata問題は，最終検査前にビルド専用CMake／Ninjaを除去して対処しました．
ソフト互換性への修正で，モデル品質やcheckpoint読込の安全性修正ではありません．
直接pinは全間接依存・APTのロックではなく，再構築時は一覧と検査を取り直します．

参照GPUイメージは`vln-b2-runtime:jp5`，IDは
`sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a`です．
小さいPython stageも別に残しています．コマンド，制限，一覧，失敗は
[実行環境構築](jetson-runtime.ja.md)と[互換性](runtime-compatibility.ja.md)に記録しました．
環境構築だけでは重み取得や実モデル読込を証明しません．

## 8．承認済み取得，別環境での変換，厳密な読込

上流ソースはレポの外で版`9fa6f8b66b9e121d5df5df071297bba8e5353ebb`を使用しています．
17ファイル計3,827,163,803バイトの取得を操作者が承認し，公式clientが固定metadata，容量，digestを確認しました．
個人の認証情報は渡さず，推論はローカルcacheだけで行います．起動時の自動取得はありません．

| 資材 | 固定した版・結果 |
|---|---|
| TIC原本 | dataset `handsomeYun/TIC-VLA`，版`671de608f39ccae41b66cbb24ab923c0275f8fb4`，1,938,501,547バイト |
| InternVL3-1B | `OpenGVLab/InternVL3-1B`，版`4415a3b810e636d11dfa86b0e9ba40bb00535aa8`，選択16ファイル，1,888,662,256バイト |
| TIC派生safetensors | 3,773,492,276バイト，SHA256 `2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4` |

古いGPU Torch 2.2.2で原本pickleを復号する経路は禁止しています．別のCPU専用Torch 2.15.0+cpu環境に
12個のhash固定ソフトを入れました．生成fixtureでBF16，alias，転置，scalar，空tensor，NaNのpayload，
signed zeroを確認し，非対応metadataは失敗させます．旧GPU環境でのtensor専用読戻しも成功しました．
最初のBuildKit試行はbuildx不足で失敗し，既存legacy builderで成功しました．buildx追加は不要でした．

実変換は全1,324 tensor名，形状，dtype，バイトを保持しました．alias実体化でファイルが大きくなりました．
原本と変換物のhash・履歴は非公開です．その後GPUが1,324 key，固有948,462,978 parameter，
30点horizon，action layer 3層を厳密に読み込みました．不足・余分なkeyの黙認はありません．
上流とsnapshotのPythonは実行され，ローカル限定読込でもコードのsandboxにはなりません．
[資材](../reference/model-artifacts.ja.md)，[変換](../reference/checkpoint-conversion.ja.md)，[GPU検査](model-runtime.ja.md)を参照します．

## 9．外付けZEDと同期予測

既存ZED SDK 4.1.2は研究ログインから読めませんでした．ホスト所有者・所属を変えず，
SDKを数値group付きで読取専用マウントし，専用prefixの公式pyzed 4.1／CPython 3.11 ARM64と
Cython 3.0.12を使いました．不足するturbojpeg共有ライブラリだけを別にマウントします．
NumPy 1.26.4はGPUイメージに残し，host Python／venvへpyzedを入れていません．

直接接続したZED 2iの映像側は5 Gbpsでした．識別したvideo／USBだけを渡し，一致する工場校正を専用の
書込領域へコピーしました．深度は無効，AIモデル取得なしです．最初の1280×720左補正JPEGは空でなく向きも
目視確認しました．撮影時刻と受信時刻は分離し，B2上の視野・幾何・時計同期は未確認です．
再接続でUSB番号が変わったため，以前の番号を無条件にコピーできません．

| 検査 | 実測 | 証明しないこと |
|---|---|---|
| 最初の合成画像推論 | 13.64秒，有限XY 30点 | 実カメラ，実状態，ナビゲーション品質 |
| 保存ZED画像の2回推論 | 全体12.0005／9.9308秒 | 静止仮定でありライブ制御ではない |
| その意味生成 | 11.5729／9.5657秒 | 診断の同期処理によるoverheadあり |
| cache用forward | 0.2248／0.2165秒 | 意味更新全体ではない |
| 現在画像の特徴 | 0.0893／0.0892秒 | 同じ保存画像 |
| action decoder | 0.00582／0.00569秒 | 意味生成・撮影を含まない |
| 短いSDK stream | 90/90成功，29.99 grabs/秒 | 毎画像のJPEG保存，長時間，推論周期ではない |
| 今回のcamera→HTML | load 13.109秒，推論13.290秒，30点 | 新しい机上画像，状態仮定，経路品質未評価 |

保存画像2回の計測はPython／NumPy／Torch seed 0，上流sampling温度0.7，最大200 tokenです．
実生成token数や強制的な決定論実行ではありません．最初の合成試行はseed未記録です．
profile用スクリプトが最初`profile.py`で標準ライブラリを隠し，推論前に失敗したため改名しました．
profilingのallocator peakはTorch割当であり，統合メモリ総使用量ではありません．

今回のデモはソース`6900bfc`で撮影・推論・描画が全て終了コード0でした．
非公開`local/camera-demo-01/`に`frame.jpg`218,278バイト，`frame.jpg.json`，
`prediction.json`5,081バイト，`prediction.html`299,580バイトを保存しました．
HTMLは描画・目視済みで，元画像，別枠SVG俯瞰経路，座標表，静止仮定・指令なしの表示を含みます．
画像hashの照合で別フレームの表示を防ぎます．serverや外部資材なしでJetson／Macで開けます．
画像に研究室の非公開情報があるため公開文書には含めません．

## 10．非同期cacheとライブshadow実験

同期デモは現在画像と意味参照画像に同じ1枚を使い，論文の非同期systemを再現しません．
独立実装`semantic_cache.py`は意味payloadと参照の原子的な組，request ID，古い要求の置換・reset，
撮影／受信時計の分離，座標・age検査を管理します．平面body変位は参照yaw基準で，実機座標との一致や
完全なSE(3)は未確認です．このモジュールだけではthreadを起動しません．

数値再利用試験は24層，6,721,536バイトのcacheを保持し，zero delay出力の最大差0
（許容0.001 m），同じ画像と状態仮定で3回0.1186／0.1183／0.1181秒でした．
cacheのバイトは不変ですが，ライブ並行性や走行品質の評価ではありません．

shadowは予測を計算・記録するだけで機体へ送らない試験です．
別ツールでカメラ・意味・actionの2コンテナ限定実験も行いました．

| 項目 | 実際の観測 |
|---|---|
| camera producer | 55秒，目標5 fps，JPEG 275枚，39,668,458バイト |
| observer | load 9.354秒後に25秒観測，異なる最新観測126個 |
| 意味計算 | 2要求完了，最初のcache公開12.659秒 |
| 2回目の意味計算 | 12.815秒，観測終了後に完了したため破棄 |
| shadow action | 35出力，全て次の意味計算中 |
| action所要時間 | 最小0.1308秒，中央値0.15594秒，最大0.28275秒 |
| 出力欠落 | cacheなし65回，診断用20秒上限超過26回skip |
| 採用した意味age | 受信時計による下限13.05–19.98秒 |
| error／遅い完了の破棄 | error報告0，終了後完了1件破棄 |

producerは不変JPEGと原子的なlatest manifestを使い，observerは限定された意味workerと
現在actionをCUDA streamで分けます．全て静止仮定です．actionが短くても，
**中断なく6 Hzで制御できた証明ではありません**．意味計算の初回・更新待ちと古いcache拒否で空白がありました．
20秒は診断用で，20秒前の意味情報による走行承認ではありません．
実時計・座標・状態との接続，劣化時の処理は残っています．DynaNav全体，学習整合，論文の実機結果の再現でもありません．
[非同期実行](../reference/asynchronous-runtime.ja.md)に契約と証拠があります．

## 11．SDK準備と4計算機の構成

確認済みUnitree SDK2ソースとCycloneDDS 0.10.2のnative／Pythonで，別の
`vln-b2-unitree:jp5`を構築しました．最初はbuildツールmetadataがruntimeの`pip check`を汚染して失敗し，
build venvを分けて解決しました．offline verifierは固定ソースhash，native mapping，license／build情報と
516バイトの合成`SportModeState`の正確なserialize／deserializeを確認します．
**DDS entity，network，robot clientを初期化していません**．受信専用CLIのhelpも通りました．

小さいイメージではSDK全体の宣言依存を満たしていません．state／IDL経路だけならCycloneDDSと標準ライブラリで
動く点を明記し，全カメラ・配列依存を入れて隠していません．合成serializeでは実B2のtopic／型／domain／QoSを
証明できません．固定ソース・イメージは[Unitree環境](../reference/unitree-runtime.ja.md)を参照します．

| 計算機・接続 | 現状の証拠と意図した役割 |
|---|---|
| Mac→外付けJetson | 利用可能な回線とTailscaleによるSSH／RDP管理．任意の開発・結果表示 |
| ZED→外付けJetson | 直接USB，SDK／binding→RGB→GPUモデル→ローカル経路・表示を検証済み |
| 外付けJetson→B2 | 直接Ethernet／IP／DDS／SDK2の予定．実リンク・実状態はまだなし |
| 本体内の利用者用Jetson | 別計算機との情報のみ．実型番，センサ，service，転送経路は未確認 |
| ブラックボックス制御機 | 既存歩行制御器との情報のみ．実hardware／API／操作権／指令断挙動は未確認 |

ROS 2はtopic，ツール，sensor統合に使えますが，SDKを使うから必要になるものではありません．
SDK2の予定経路はDDSです．ROS 2も多くはDDSを使いますが，middlewareが同じだけでは
型，domain，topicが一致しません．コンテナ間も，選んだnetwork／IPC／fileで明示的に接続します．
現在の推論は`--network none`で，状態受信には別途robot向け設定が必要です．
大学回線をB2へbridgeしたり，Ethernetを通すため管理用default routeを置き換えたりしません．
[通信構成](../explanations/network-topology.ja.md)，[現地手順](../how-to/field-network.ja.md)，[配置設計](../explanations/deployment-design.ja.md)を参照します．

外付けUSBは独立に検証できる最初の入力として選び，本体カメラ・内蔵計算機の永久不使用を決めたわけではありません．
内蔵sensorは内蔵Jetson上のservice／streamとEthernet転送が必要かもしれず，外付けJetsonのUSBとしては扱えません．
Livox・内蔵camera経路は未設定です．今後，取得可能性，時刻，幾何，帯域，研究目的で判断します．

将来の中核loopはMac，eduroam，Internetなしで機体側だけで動かす設計です．
APなしで任意監視するJetson hotspot案はありますが未設定・未試験です．
B2リモコンは独立した操作者経路として使う意図ですが，優先順位・停止挙動は研究室手順で観測する必要があり，
「リモコン」という名前だけでは保証しません．

## 12．検証と証拠の範囲

この時点で**MacとJetsonの双方で170テスト成功**です．検査，模擬vendor，replay／追従，時刻・cache契約，
変換・tool，表示を扱います．実走行，camera長時間信頼性，停止性能の認証ではありません．
ローカルcommit／同期前に構文・diff，文書の対・link，非公開情報を確認します．
重み，生画像，native SDK，上流モデルソースは追跡しません．新tool・文書でMac serviceや
自動モデル／制御起動jobは追加していません．

再現用にsource revision，不変image ID，資材hash，実験ごとの非公開invocation／provenanceを保管します．
有効な出力とは期待した形の有限数値であり，navigation指示の成功ではありません．
過去の再起動・撮影は限定的な観測で，未検証の故障が不可能になったとはしません．

## 13．残るmilestoneと初回接続の合格条件

| 次の段階 | 先へ進む前に必要な証拠 |
|---|---|
| M1：Ethernet・状態だけ | cable端点・内蔵hostを特定，管理route維持，明示interface／domain／topicで実B2有限状態を受信，motor指令0 |
| M2：実観測の整合 | camera搭載，視野，機体軸，単位，速度・位置frame，timestamp，画像と状態の対応 |
| M3：実状態shadow | 整合した実状態でライブ予測を反復，開始・更新空白，stall，古い／欠落入力，計算・温度特性を測定 |
| M4：制御・停止統合 | 操作権，リモコン優先，受信側expiry・通信断を確認，制限送信器，独立stop／expiry，介入を実装 |
| M5：限定走行・研究 | 研究室手順で立会い低速試験，停止距離・障害物確認，事前定義した反復評価 |

初回現地で識別，service，状態対応が未解決ならM1で止めます．[現地カード](../how-to/field-card.ja.md)，
準備済みSDK image，非公開visit notesを使い，調査用にSDK移動exampleを実行しません．
Ethernet接続は通信状態を変えるだけで，制御実装の境界は変わりません．
M1～M4を進める間も，[操作ガイド](../how-to/run-camera-demo.ja.md)でcamera推論を独立に実演できます．
