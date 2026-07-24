# EML Newsletter Filter

ローカルの `.eml` を `newsletter`、`suspected_newsletter`、`not_newsletter` に分類する Python 3.11+ CLIです。元ファイルは変更・削除しません。

## セットアップ

```bash
python -m venv .venv
.venv/bin/pip install -e '.[test]'
```

## 実行

```bash
python -m eml_newsletter_filter classify --input ./input --config ./config.yaml --output ./output
python -m eml_newsletter_filter classify --input ./input/example.eml --config ./config.yaml --output ./output --dry-run
```

`newsletter` は強い特徴または高スコア、`suspected_newsletter` は中間スコア、`not_newsletter` はそれ以外です。`--dry-run` でもレポートは作成されますが、分類フォルダへのコピーは行いません。

キーワードは `force_not_newsletter`、`force_newsletter`、`exclude_from_newsletter`、`add_as_newsletter` の順に評価します。加点キーワードは1件以上一致した場合に一度だけ加点します。

入力と出力が同一の場合は終了コード2で拒否します。出力を入力ディレクトリ配下に置くことは可能ですが、出力ツリーは次回以降も入力として再処理されません。設定値が不正な場合も、処理開始前に終了コード2で停止し、コピーやレポートは作成しません。解析不能なメールは `not_newsletter` として記録され、`parse_error` 列で区別されます。
