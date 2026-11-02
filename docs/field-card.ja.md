# B2接続訪問の確認カード

[English](field-card.md) · [Ethernetの詳細手順](field-network.ja.md) · [現在の進捗](status.ja.md)

次回は外付けJetsonとB2を接続し，状態を受信する．本ソフトウェアは**移動指令を送らない**．
外付けカメラの取得・モデル予測は通っているが，ケーブルが通るだけでモデルによる歩行まで完成するわけではない．

## 出発前

- 外付けJetsonと現在の電源，Macと充電器，研究室の**実際のB2ユーザー向けnetwork端子**に合う
  Ethernetケーブル・adapterを用意する．端子・breakoutを研究室で確認し，全拡張端子を通常のRJ45と仮定しない．
  今回の静止したnetwork調査ではJetsonを専用電源で使い，機体からの給電は別作業にする．
- 充電・pairing済みのB2リモコンと研究室の通常操作・停止手順を用意し，現在の制御sessionの所有者を確認する．
- 記録があれば，研究室で使っている機体subnet・service IPと，許可された内蔵計算機へのアクセスを用意する．
  Go2-Wや販売元の既定例ではなく，個体の事実である．なければ現地の設定から確認してからIP割当・状態購読へ進む．
- Wi-Fi断時の現地の復旧手段を確保する．Macの画面は必要時に既存Tailscaleと直接RDPを使い，
  Macのtunnel・新しい常駐serviceは不要である．[Windows App設定](remote-desktop.ja.md#windows-appから直接つなぐ)を参照する．
- 公式の[B2マニュアル・リモコン案内](https://www.unitree.com/app/b2/)と
  [B2開発portal](https://support.unitree.com/home/en/B2_developer)を参照する．
  研究室の該当版を使い，車輪なしの本B2へB2-W手順を適用しない．
  公式B2ユーザー・リモコン文書は，Jetsonの非公開`local/reference-manuals/unitree-b2-01`にも保存した．
  各文書の`index.html`を開くとオフラインで読める．画像23・14ページと出典・SHA256 manifest，
  合計約29.35 MBで，Git対象外とし再配布しない．

## 準備済みのソフトウェア

| 項目 | 準備・根拠 | 現地で必要なこと |
|---|---|---|
| ソース | `~/Developer/Projects/Robotics/b2/VLN_B2`へhash照合して同期済み | ルートで端末を開く |
| カメラ | 非公開binding・校正，USB 5 Gbps，制限付き試験でJPEG 275枚 | 使う場合はUSB・電源・取付後の視野を確認 |
| モデル | 固定base・本家source・変換済み重みがローカルにあり，実画像の予測成功 | 追加download，MacのDocker・モデル実行は不要 |
| GPU環境 | 既存`vln-b2-runtime:jp5`イメージの存在を照合 | ホストvenvではなく，確認したカメラ・モデルmountを使う |
| 状態環境 | 既存`vln-b2-unitree:jp5`，今回もnetwork隔離した検査に成功 | 確認した機体側interface・DDS domainを設定 |
| 直接RDP | tailnet専用listenerとMacのTCP・RDP・TLS確認が成功 | 操作者がWindows Appへ登録．新経路のGUI確認は残る |

事前確認では，変換済み重みのSHA256と，固定base snapshot，本家package，カメラbindingの存在を再確認した．
非公開結果は`local/field-ready-01`に置く．Mac・Jetsonで通常テスト162件が成功する．
これらは実B2のfirmware・topic・座標系の互換性を証明しない．

## 機体の前で

1. 該当B2，通常の操作・停止手順，ユーザー向けEthernet端子，ケーブル両端を確認する．内蔵service・firmwareは変更しない．
2. [Ethernet手順1〜2](field-network.ja.md#1ケーブルを挿す前)を開く．
   **接続前に**外付け側のinterface・経路を保存し，既存profileを確認する．調査時の物理ポートは
   carrierなしの`eth0`だったが，再確認する．eduroam・Tailscaleを維持し，大学へbridgeしない．
3. 確認したsubnetと未使用の外付け側IPを使い，carrier，IP，既知serviceへの経路を確認する．
   DHCP・VLAN・bridgeの構成なら，固定IPの雛形ではなく研究室の構成に従う．
4. 確認したinterface・domainで，[準備した状態コンテナ](unitree-runtime.ja.md#準備した受信専用コマンド)を実行する．
   実際の受信・有効件数とsampleを読む．終了コードゼロ・pingだけでは足りない．モデル・移動clientは不要である．
5. 研究室の正規アクセスで到達できる内蔵計算機を調べ，実際のhost，service，sensor配信，protocol・topic・domain，
   所有者を残す．一つのEthernet端子から到達できても，動作制御計算機と内蔵ユーザーJetsonを同じhostとして扱わない．
6. 単位，軸，時刻の意味，世界・機体速度の規約，カメラと機体の取付けを記録する．内蔵stream・Mid-360配線は，
   動いている外付けUSBカメラと別に調べる．確立前のframe・時計は未検証のままにする．
7. 結論・次の作業を保存する．その後，実状態をモデル入力へ結合し，cache更新待ちの空白，保護した送信部を扱い，
   指令断・リモコン介入・停止を検証してから，モデルによる移動へ進む．

試行ごとに新しい番号の非公開出力先を使う．[空の訪問記録](../examples/onsite-notes.json)を
Git対象外の`local/`へコピーし，実IP，アカウント，生報告，画像はGitへ入れない．
不明なnetwork・DDS受信ゼロは切り分ける対象であり，移動サンプルを走らせる理由にはしない．
全手順と復旧コマンドはEthernetのガイドに記す．
