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

`config.yaml` の `keywords` にキーワードを追加・削除できます。`feature_weights`、`newsletter_threshold`、`suspected_threshold`、`add_keyword_score`、`many_links_threshold` で判定を調整できます。
