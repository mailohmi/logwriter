============
logwriter
============

1. 概要
   ログの記録を行います。

2. 必要なシステム
  * six
    > python -m pip install six

3. 機能
  * ログの記録
    * logging.Loggerを継承する。
    * confファイルから入力されたログ設定の型の変換を行う(str->int)。
    * debugメッセージにてファイル名と行番号を付加する。

  * デバッグ用関数アノテーションを行う。
    * @logwriter.obsolete

4. インストール方法
  ビルドは、setup.pyを実行します。
  $ python setup.py bdist_wheel --universal
