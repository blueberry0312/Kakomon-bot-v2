# Kakomon-BOT v2.0

長岡高専「新過去問DB」(約1,031人)向けDiscord BOT。旧BOT停止を受けての再設計版。

## Ver.2.0の方針

旧DBは既にDiscordの投稿+タグ絞り込み(前期中間/前期期末/後期中間/後期期末/夏休み明け/冬休み明け/その他)が機能しているため、
「検索機能の追加」ではなく **過去問の情報をDBで一元管理する仕組みへの移行** を目的にしている。

## 設計上の工夫

- **画像を自前保存しない**: 添付ファイルのDiscord CDN URLのみDBに保持。ストレージコスト・情報漏洩リスクを最小化。
- **個人情報を持たない**: 投稿者情報はDiscordユーザー名のみ。学籍番号・本名は保存しない。
- **重複チェック**: 年度+科目+試験区分(+学科)の組み合わせが既存なら登録時に警告。
- **権限を2段階に分離**: `/remove` `/edit` は「Admin」ロール(または「サーバー管理」権限)限定。`/add`(登録)だけは「Contributor」ロールでも実行可能にして、有志に登録作業を頼みやすくしている。
- **著作権対応**: `/report` で誰でも削除依頼ができ、管理者が確認して `/remove` で対応するフローを用意。

## ロールの設定

1. サーバー設定 > ロール で「Admin」ロールを作成し、自分と信頼できる運営メンバーに付与
2. 同様に「Contributor」ロールを作成し、登録作業を手伝ってくれる有志に付与
   (`/edit` `/remove` は使えず、`/add` だけ実行できる)
3. ロール名を変えたい場合は `cogs/admin.py` の `ADMIN_ROLE_NAME` / `REGISTRAR_ROLE_NAME` を書き換える

## 常時稼働化(Railwayへのデプロイ)

自分のPCを閉じてもBOTを動かし続けたい場合、Railway(無料枠あり)へのデプロイがおすすめです。

1. **GitHubにコードをpush**(`.env`は`.gitignore`で除外済みなので安全)
   ```bash
   git init
   git add .
   git commit -m "Kakomon-BOT v2.0"
   git remote add origin <あなたのリポジトリURL>
   git push -u origin main
   ```

2. **Railwayでプロジェクト作成**
   - https://railway.app にログイン(GitHubアカウントでOK)
   - 「New Project」→「Deploy from GitHub repo」で先ほどのリポジトリを選択

3. **環境変数を設定**
   - プロジェクトの「Variables」タブで `DISCORD_TOKEN` を追加し、値にトークンを貼る
   - `.env`ファイルはpushしていないので、ここで設定しないとBOTが起動しません

4. **起動確認**
   - `Procfile`(`worker: python bot.py`)を自動認識してデプロイが始まります
   - 「Deployments」タブのログで `Logged in as Kakomon-BOT-v2` が出れば成功

5. **PostgreSQLを追加(データ永続化)**
   - Railwayプロジェクト画面で「+ New」→「Database」→「Add PostgreSQL」
   - 追加すると同じプロジェクト内に `DATABASE_URL` という環境変数が自動生成され、BOTのサービスからも参照できる
   - BOTのサービスの Variables タブで `DATABASE_URL` を `${{Postgres.DATABASE_URL}}` のように参照設定(Railwayが候補を出してくれる)
   - これでSQLiteのファイルに依存しなくなり、再デプロイしてもデータが消えなくなる

## セットアップ(ローカル開発用)

```bash
pip install -r requirements.txt
cp .env.example .env
# .env に DISCORD_TOKEN=あなたのトークン を記入
# ローカルでPostgreSQLを試すなら DATABASE_URL も記入(下記参照)
python bot.py
```

ローカルにPostgreSQLが無い場合は、Docker等で一時的に立てるか、Railway上のPostgreSQLの外部接続用URL(`DATABASE_PUBLIC_URL`)を使ってローカルから接続することもできます。

## コマンド一覧

### レガシー(旧BOT互換、DM/サーバー内でprefixコマンド)
| コマンド | 説明 |
|---|---|
| `$cmd` | コマンド一覧を表示 |
| `$rule` | ルールを表示 |
| `$invite` | 招待リンクを表示 |
| `$usage` | 使い方を表示 |
| `$welcome` | 参加時メッセージを再表示 |

### Ver.2.0(スラッシュコマンド)
| コマンド | 説明 | 権限 |
|---|---|---|
| `/search` | 科目・年度・試験区分・学科で検索 | 全員 |
| `/latest` | 最近登録された過去問を表示 | 全員 |
| `/add` | 過去問を登録(ファイル添付+項目入力、重複チェックあり) | Admin or Contributor |
| `/edit` | 登録済み過去問の情報を修正 | Admin |
| `/remove` | 過去問を削除(著作権削除依頼への対応など) | Admin |
| `/report` | 著作権等の理由で削除を依頼 | 全員 |

## データ構造

過去問1件を以下のメタデータとして管理(PostgreSQLの`exams`テーブル):
- 年度 / 学年 / 学科(M, EE, EC, MB, CI) / 科目 / 試験区分 / ファイルURL / 投稿者 / 投稿日時

## 今後の拡張アイデア

- OCRで画像から科目名・年度を自動抽出(卒研の画像処理の知見を流用できそう)
- `/report` を管理者用チャンネルへ自動転送(現状はコンソール出力のみ)
- 削除依頼の対応履歴を別テーブルで管理
- 科目名の表記ゆれ対策(「微積分1」「微積分I」を同一視するなど)
<!-- PostgreSQL移行テスト -->