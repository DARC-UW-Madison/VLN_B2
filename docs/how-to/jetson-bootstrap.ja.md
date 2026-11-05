# Jetsonのアカウント，Tailscale SSH，作業環境の分離

[English](jetson-bootstrap.md) · [ネットワーク設計](../explanations/network-topology.ja.md) · [ホーム](../../README.ja.md)

> 文書種別：**操作手順**．

インターネット接続と既存の管理者ログインがある，Ubuntu／systemdのJetsonを前提にした
操作者向けの手順である．操作者が初期設定を完了し，その後のSSH調査を
[確認済み構成](../records/target-baseline.ja.md)に記録した．以下のアカウント・導入コマンドは参照用であり，
既存ログインの作り直しを求めるものではない．設定中は画面・キーボードを使える状態にする．アカウント名，パスワード，認証URL，tailnetの識別情報，
実際のアドレスは，このリポジトリではなく承認されたローカル保管先で管理する．

## 1．ホストのログインを新しく作る

以下の`RESEARCH_USER`を全て，使用するアカウント名へ置き換える．Jetsonの既存の管理者
セッションから，アカウントとホームの両方が未作成の場合だけ作成する．

```sh
if getent passwd RESEARCH_USER >/dev/null || [ -e /home/RESEARCH_USER ] || [ -L /home/RESEARCH_USER ]; then
    echo "Account or home already exists; stop and inspect before continuing."
else
    sudo adduser RESEARCH_USER && sudo usermod -aG sudo RESEARCH_USER
fi
```

既存のアカウントやホームが見つかった場合は止める．その再利用では新しい作業領域にならない．
最初のsudoの入力は，現在の管理者のパスワードである．その後のパスワード入力で，新しい
ログインのパスワードを対話的に設定する．コマンドやスクリプトには書かない．任意の個人情報欄は
空欄にする．施設のパスワード規則で拒否されたら，システム全体の規則を弱めず，表示を確認する．
sudoグループへの追加はホストの管理権限を与えることであり，安全上の隔離ではない．
[Ubuntuのユーザー管理](https://ubuntu.com/server/docs/how-to/security/user-management/)を参照する．

作成に成功したら切り替える．

```sh
sudo -iu RESEARCH_USER
whoami
pwd
```

新しいログインとホームになったことを確認してからファイルを作る．既存アカウントとファイルは
そのまま残す．以前の利用者のホーム全体やシェル設定を，新しい環境へ丸ごとコピーしない．

## 2．既存のTailscaleを確認する

アプリケーションのコンテナ内ではなく，Jetsonホスト上で実行する．

```sh
command -v tailscale
```

導入済みなら，変更前に`tailscale status`を現地で確認する．Linuxユーザーを増やしても，
Tailscaleの登録は別にならない．既にtailnetへ参加している場合や他の利用者が使っている場合は，
登録先と既存設定を確認する．勝手にログアウト，初期化，登録のやり直しをしない．

未導入のホストには，公式のLinuxインストーラーを使える．

```sh
curl -fsSL https://tailscale.com/install.sh | sh
```

curlがなければ，`sudo apt update`と`sudo apt install curl`でその前提だけを導入し，再実行する．
インストーラーはホスト共通のパッケージとシステムサービスを変更するもので，新しいホーム内に
隔離されるものではない．手動でパッケージリポジトリを設定する方法も
[公式Linux手順](https://tailscale.com/docs/install/linux)にある．

## 3．登録してTailscale SSHを有効にする

新規導入の場合，Jetsonで以下を実行する．

```sh
sudo systemctl enable --now tailscaled
sudo tailscale up
```

認証URLを自分で開き，Macが使う研究室で認められたtailnetへ参加する．ログインURLや認証キーを
チャットへ送ったり，コミットしたりしない．登録後に以下を実行する．

```sh
sudo tailscale set --ssh
tailscale ip -4
```

今回は**Tailscale SSH**を選ぶ．SSH接続はtailnetの認証と規則で許可し，Linuxのパスワードは
ローカルログインやsudoで使う．この機能はホストのTailscaleアドレスを対象とし，この経路のために
OpenSSHサーバーを追加する必要はない．tailnetの規則では，ネットワーク接続と対象Linuxユーザーへの
SSH接続の両方を許可する必要がある．拒否された場合は，管理者に該当する規則を確認してもらう．
共有の規則全体を無制限な許可へ置き換えない．[Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh)を参照する．

この管理用経路では，サブネットの公開やexit nodeを有効にしない．Jetson自身へ到達できればよく，
機体向けEthernetは別の接続である．

## 4．Macから接続する

導入済みのTailscaleがあれば再利用する．Macを同じ承認済みtailnetへ接続し，端末で以下を実行する．
二つのプレースホルダーを置き換える．

```sh
ssh RESEARCH_USER@JETSON_TAILSCALE_IP
```

ブラウザで認証を求められる場合がある．接続したJetsonのシェルで確認する．

```sh
whoami
pwd
cat /etc/nv_tegra_release
```

ログインとホームが新しいアカウントのものであることを確認する．ここでは機体や内蔵Jetsonへ
SSHするわけではない．実際の機器の接続状態とアドレスは公開文書の外に保管する．

## 5．ファイルと依存環境を分ける

| 層 | 分けるもの | 境界 |
|---|---|---|
| ホストのユーザー | ホーム，シェル設定，認証情報 | OSとシステムパッケージは共通．sudoでホストを管理できる |
| pyenv | そのユーザーが使うPythonのバージョン | パッケージやGPUドライバの隔離ではない |
| プロジェクトの`.venv` | そのプロジェクトのPythonパッケージ | 選択したPythonを使い，OSのライブラリは分離しない |
| Dockerイメージ・コンテナ | アプリケーションのパッケージとプロセス環境 | ホストのカーネルと，明示的に渡したファイル・デバイス・ネットワークを共有する |

新しいホーム内の`~/Developer/Projects/Robotics/b2/b2-tic-vla`をプロジェクトの場所とする．
既存の仮想環境ではなくソースを転送する．必要に応じてpyenvをユーザー単位で置き，Pythonは
プロジェクトごとに選び，ホストのツールには`.venv`を使う．メーカーのバインディングやPyTorchとの
互換性を調べずに最新のPythonを選ばない．`sudo pip`によるプロジェクトのパッケージ導入や，
システムPythonの置き換えは行わない．[pyenvの説明](https://github.com/pyenv/pyenv)，
[Pythonの仮想環境](https://docs.python.org/3/library/venv.html)，
[Dockerのコンテナの仕組み](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/)を参照する．

推論は，互換性のあるコンテナに実行環境をまとめる方針を優先する．イメージ内にPythonがある場合，
通常はさらにpyenvを重ねる必要はない．必要なプロジェクト・データのパスだけを渡し，別のユーザーの
ホーム全体はマウントしない．ドライバ，JetPack，デバイスへのアクセスはホストとの互換性が必要である．
B2へ接続できる段階でSDKの状態受信を最初にホストで確認し，その後に選んだコンテナで確かめる．

## 6．リモート接続が通ってからGUI起動を任意にする

CLIでの開発と現在の観測ツールは，Jetsonのデスクトップセッションを必要としない．初期設定中は
デスクトップを残す．起動方式を変える前に，リモートログイン，起動時のWi-Fi接続，tailscaledの
自動起動を確認する．Wi-Fi設定によってはユーザーのGUIセッションに依存する場合がある．

現在の起動先を`systemctl get-default`で確認してローカルに記録する．ログイン操作なしで
ネットワークへ接続できることを確認した後，CLI起動を選ぶ場合は以下を使う．

```sh
sudo systemctl set-default multi-user.target
```

現在のデスクトップではなく，次回以降の起動先が変わる．以前の起動先がgraphicalで，その環境が
残っている場合は，`sudo systemctl set-default graphical.target`で戻せる．アカウントとTailscaleの
初期設定には，再起動やデスクトップの削除は含めない．
