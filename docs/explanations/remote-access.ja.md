# 遠隔操作の画面・ログイン・通信

[English](remote-access.md) · [ドキュメント](../README.ja.md) · [画面接続の手順](../how-to/remote-desktop.ja.md)

> 文書種別：**解説**．サーバー設定と実行した変更は[デスクトップの記録](../records/desktop-history.ja.md)に記す．

## クライアント，サーバー，protocol

クライアントはMac側で操作するアプリである．サーバーはJetson側で接続を受け，ログインを認証し，デスクトップを提供するソフトである．
protocolは，その間で交換するデータの形式・手順を定める．Windows Appはクライアント，xrdpはサーバー，RDPはprotocolである．
アプリの計算は接続先で実行し，クライアントは画面の更新を受け取り，キー・マウス操作を送る．

IPアドレスは通信先を指定し，認証はどのLinuxユーザーがログインできるかを確認する．Windows AppやMicrosoftのアカウントが，
そのままJetsonのLinuxログインになるわけではない．IPへ届くこと，認証が通ること，デスクトップが使えることは別の条件である．

## RDP，VNC，NoMachine

| 名前 | 指すもの | 評価すること |
|---|---|---|
| RDP | Remote Desktop Protocol．Windows Appなどのクライアントとxrdpなどのサーバーが対応 | sessionの作成，画面の符号化，遅延，対応する追加channel |
| VNC | 画面データを遠隔で扱うクライアント・サーバーの一群 | どの画面を共有するか，圧縮と更新の方式 |
| NoMachine | NX技術を使う遠隔操作製品 | 導入したedition，物理・仮想sessionの対応，クライアントの挙動 |

名前だけで，ある作業にどれが速いかは決まらない．画像の複雑さ，符号化，通信帯域，実際のサーバー・クライアント設定が影響する．
対応機能は[Microsoftのクライアント文書](https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps)，
[xrdpの実装](https://github.com/neutrinolabs/xrdp)，[NoMachineの文書](https://www.nomachine.com/documents)を参照する．

## 物理画面と遠隔session

デスクトップsessionは，あるユーザーの画面アプリと設定をまとめた実行環境である．サーバーによって，物理画面を共有する方式と，
別の仮想sessionを作る方式がある．仮想sessionの配置がHDMI画面と完全に同じである必要はない．
サーバーと画面環境によっては，同じアカウントの同時sessionが競合する．ログアウトはそのsessionのアプリを閉じる操作であり，画面を隠すだけではない．

clipboard，音声，機器の転送は追加のchannelである．画面・マウスが動いても，全channelが使える証拠にはならない．
clipboardには，両側で互換性のある機能と有効な設定が必要である．

## SSHトンネルが加えるもの

SSHトンネルは，手元のTCP接続を，認証したSSH接続の中へ通して，接続先のTCP窓口へ届ける仕組みである．
例えばクライアントがMac内の待受へ接続し，SSHがそのデータをJetson内のRDP待受へ運ぶ．この方式にはMac上の転送processが加わる．
サーバーへその経路でしか届かない場合には有用だが，RDP自体の必須条件ではない．

RDPサーバーが，到達可能で適切にアクセス制限されたアドレスで待ち受ければ，クライアントは直接そこへ接続できる．
これは画面通信を運ぶ方法の違いであり，モデル推論の実行場所を変えたり，Macを機体内部DDSへ参加させたりするものではない．
現在どちらを設定しているかは，操作手順に記す．
