#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ログの記録を行います。
"""

# Compatible module
from __future__ import absolute_import
from __future__ import unicode_literals
import six

# Buitin module
import collections
import datetime
import functools
import inspect
import logging.handlers
import os
import stat
import sys
import unittest
import cProfile
import pstats
import io

# Global variable
__author__ = "Kazuyuki OHMI"
__version__ = "4.0.0"
__date__ = "2017/04/05"
__license__ = "MIT"

CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET

class LogWriter(logging.Logger):
    """
    ロガー
        * confファイルから読み込んだ型を修正します。
        * debug()関数に行番号を追加します。
        * levelでは以下の値を使用します。
            CRITICAL    50
            ERROR       40
            WARNING     30
            INFO        20
            DEBUG       10
            NOTSET      0
        * ディレクトリセパレータを変換します。
    """

    formats = ["%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s",
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        "%(asctime)s %(message)s",
        "%(message)s",]

    conf = {
        "level": logging.INFO,      # Set the root logger level to the specified level.
        "format": formats[2],       # Use the specified format string for the handler (Default).
        "format_stdout": formats[3],# Use the specified format string for stdout handler.
        "stdout": True,             # Add stdout handler.
        "filename": None,           # Add add RotatingFileHandler.
        "maxBytes": 1024 * 1024,    # max bytes of log file.
        "backupCount": 2,           # backup count of log file.
        }

    path_main = ""                  # main mulude path

    @property
    def version(self):
        return __version__

    class TimeFormatter(logging.Formatter):
        converter = datetime.datetime.fromtimestamp

        def formatTime(self, record, datefmt=None):
            ct = self.converter(record.created)

            if datefmt:
                s = ct.strftime(datefmt)
            else:
                t = ct.strftime("%Y/%m/%d %H:%M:%S")
                s = "%s,%03d" % (t, record.msecs)
            return s

    def __init__(self, name="root", level=logging.INFO, **kwargs):
        """
        Constructor
        Adding object to LOGWRITERS list.

        :param str name:        ログ名称
        :param int level:       ログレベル
        :param bool stdout:     標準出力に出力する。
        """

        # 引数を取り込みます。
        self.conf.update({"name": name})
        self.conf.update({"level": level})
        self.conf.update(**kwargs)

        # confファイルから読み込んだ型を修正します。
        # level
        if not isinstance(self.conf.get("level"), int):
            self.conf["level"] = int(self.conf["level"])

        if not isinstance(self.conf.get("stdout"), bool):
            self.conf["stdout"] = bool(self.conf["stdout"])

        filename = self.conf["filename"]
        if filename is not None:
            self.conf["filename"] = self.conf.get("filename").replace("/", os.path.sep)

            prefix = self.conf.get("prefix")
            if prefix is not None:
                self.conf["filename"] = os.path.join(prefix, self.conf["filename"])
                self.conf["filename"] = os.path.realpath(self.conf["filename"])

        # maxBytes
        if not isinstance(self.conf.get("maxBytes"), int):
            self.conf["maxBytes"] = int(self.conf["maxBytes"])

        # backupCount
        if not isinstance(self.conf.get("backupCount"), int):
            self.conf["backupCount"] = int(self.conf["backupCount"])

        # ベースクラスのコンストラクタを呼び出します。
        logging.Logger.__init__(self, self.conf["name"], level=self.conf["level"])

        # 標準出力のハンドラを登録します。
        if self.conf["stdout"]:
            self.add_stdout_handler()

        # ファイルハンドラを登録します。
        if self.conf["filename"]:
            filename = self.conf["filename"]
            maxBytes = self.conf["maxBytes"]
            backupCount = self.conf["backupCount"]

            self.addRotateFileHandler(filename,maxBytes,backupCount)

        # ロガー配列に登録します。
        import __main__
        self.path_main = __main__.__file__
        if not hasattr(__main__, 'LOGWRITERS'):
            __main__.LOGWRITERS = []
        __main__.LOGWRITERS.append(self)

    def __str__(self):
        return str(__dict__)

    def __repr__(self):
        values = self.__dict__
        values["conf"] = self.conf
        return str(values)

    def setLevel(self, level, *args, **kwargs):
        """
        ログレベルを設定します。
        レベルは、logging.getLevelName('INFO')から取得できます。

        :param int level:       ログレベル
        :rtype:                 None
        """

        self.conf["level"] = level
        logging.Logger.setLevel(self, level)
        for handler in self.handlers:
            handler.setLevel(level)

        return

    def add_stdout_handler(self, dest=sys.stdout):
        """
        標準出力のハンドラを登録します。

        :param file dest:   ログの出力先のストリーム
        :rtype:             None
        """
        fmt = self.conf.get("format_stdout",self.conf.get("format"))

        stdout_handler = logging.StreamHandler(dest)
        stdout_handler.setLevel(self.level)
        stdout_handler.setFormatter(self.TimeFormatter(fmt))
        self.addHandler(stdout_handler)

        return

    def add_syslog_handler(self, dest=None):
        """
        ログを転送する。
        :param str/tupple dest: 転送先のホスト
            /dev/log:           Linux
            /var/run/log:       Darwin
        :rtype:                 None
        """

        # 送信先を設定する。
        if not dest:
            path_list = ["/dev/log", "/var/run/syslog"]
            for path in path_list:
                mode = os.stat(path).st_mode
                if stat.S_ISSOCK(mode):
                    dest = path
                    break

            if not dest:
                dest = ("localhost", logging.handlers.SYSLOG_UDP_PORT)

        handler = logging.handlers.SysLogHandler(dest, logging.handlers.SysLogHandler.LOG_USER)

        handler.setFormatter(self.TimeFormatter(self.conf["format"]))
        handler.setLevel(self.conf["level"])
        self.addHandler(handler)

    def addRotateFileHandler(self, filename, maxBytes=0, backupCount=0):
        """
        ファイルに出力します。

        :param str filename:    出力ファイル名
        :rtype:                 RotatingFileHandler
        :return:                追加したハンドラ
        """

        # 変数を初期化します。
        if sys.version_info >= (3, 0):
            encoding = sys.getdefaultencoding()
        else:
            encoding = None
        handler = logging.handlers.RotatingFileHandler(filename, maxBytes=maxBytes, backupCount=backupCount,
                encoding=encoding)

        handler.setLevel(self.level)
        handler.setFormatter(self.TimeFormatter(self.conf["format"]))

        if handler:
            self.addHandler(handler)

        return handler

    def debug(self, message=u"", frame=None):
        """
        行番号付きでデバッグログを出力します。

        :param u message:       出力するテキスト
        :param Traceback frame: 呼び出し元のフレーム
        :rtype:                 None
        """

        if not self.isEnabledFor(logging.DEBUG):
            return

        # 変数を初期化します。
        msg = message
        if frame is None or not isinstance(frame, inspect.Traceback):
            frame = stack_frame(2)

        if frame is not None:
            path = frame.filename
            file_base, _file_ext = os.path.splitext(os.path.basename(path))
            msg = "%s (%05d) %s" % (file_base, frame.lineno, msg)

        # logging 出力を行う。
        logging.Logger.debug(self, msg)

        return

    def debug_anchor_begin(self, *args, **kwargs):
        """
        開始ログを出力します。
        関数は、 _func_name で指定します。
        フレームは、 _frame で指定します。

        :rtype:               None
        """

        if not self.isEnabledFor(logging.DEBUG):
            return

        # 変数を初期化します。
        args_txt = self.get_argtext(*args, **kwargs)
        frame = kwargs.get("_frame")
        if frame is None:
            frame = stack_frame(2)

        # メッセージを設定します。
        func_name = kwargs.get("_func_name", frame.function)
        msg = "anchor begin: %s(%s)" % (func_name, args_txt)

        # 行番号付きでデバッグログを出力します。
        return self.debug(msg, frame=frame)

    def debug_anchor_end(self, result=None, *args, **kwargs):
        """
        終了ログを出力します。
        関数は、 _func_name で指定します。
        フレームは、 _frame で指定します。
        経過時間は、 _time_elapsed で指定します。

        :param object result:   戻り値
        :rtype:                 None
        """

        if not self.isEnabledFor(logging.DEBUG):
            return

        # 変数を初期化します。
        frame = kwargs.get("_frame")
        if frame is None:
            frame = stack_frame(2)

        argments = self.get_argtext(*args, **kwargs)

        values = {u"result":result}

        time_elapsed = kwargs.get(u"_time_elapsed")
        if time_elapsed is not None:
            if isinstance(time_elapsed, (str, float)):
                time_hour, time_rest = divmod(time_elapsed, 3600)
                time_min, time_sec = divmod(time_rest, 60)
                time_elapsed = u"{:0>2}:{:0>2}:{:06.3f}".format(int(time_hour),int(time_min),time_sec)

            values[u"time_elapsed"] = time_elapsed

        # メッセージを設定します。
        func_name = kwargs.get("_func_name", frame.function)
        values_txt = self.get_argtext(**values)
        msg = u"anchor end: %s(%s) %s" % (func_name, argments, values_txt)

        # 行番号付きでデバッグログを出力します。
        return self.debug(msg, frame=frame)

    def get_argtext(self, *args, **kwargs):
        """
        引数をテキストにします。
        変数名が "_" で始まる変数はスキップします。

        :rtype:         str
        :return:        変換したテキスト
        """

        # 変数を初期化します。
        args_txt = u""

        # argsを展開します。
        for value in args:
            if args_txt != u"":
                args_txt += u", "
            args_txt += repr(value)

        # kwargsを展開します。
        for key, value in kwargs.items():

            # 変数名が "_" で始まる変数はスキップします。
            if key.startswith("_"):
                continue

            if args_txt != u"":
                args_txt += u", "
            args_txt += u"%s=%s" % (decode(key).text, decode(value).text)

        return args_txt

def getLogger(name=None, *args, **kwargs):
    """
    LogWriter を取得します。

    :param u name:      ロガーの名前
    :rtype:             LogWriter
    :return:            ロガー
    .. note::           引数からLogWriterを検索します。
    .. note::           ロガーオブジェクト配列から最後に初期化したLogWriterを検索します。
    """

    # 変数を初期化します。
    logger = None

    while True:
        # args から Logger を取得します。
        for arg in args:
            if isinstance(arg, LogWriter):
                logger = arg
                break

        # kwargs から Logger を取得します。
        for _key, value in kwargs.items():
            if isinstance(value, LogWriter):
                logger = value
                return logger

        # find logwriter from main module
        import __main__
        if not hasattr(__main__, 'LOGWRITERS'):
            break
        logwriters = __main__.LOGWRITERS
        if name is None:
            logger = logwriters[-1]
            break

        for logwriter in reversed(logwriters):
            if logwriter.name == name:
                logger = logwriter
                break

        break

    if logger is None:
        sys.stderr.write(u"LogWriter was not found at %s.\n" % __main__.__file__) 
        logger = LogWriter()

    return logger

def stack_frame(context=2):
    """
    スタックフレームを取得します。

    :param int stackIndex:      スタック番号
    :rtype:                     Taceback
    :return:                    スタックの内容
    """
    stacks = inspect.stack()
    if context >= len(stacks):
        return None

    callerframerecord = stacks[context]
    framerecord = callerframerecord[0]
    frameinfo = inspect.getframeinfo(framerecord)

    return frameinfo

def obsolete(fname):
    """
    廃止予定の警告を表示する。
    表示する関数に関数デコレータ"@logwriter.obsolete"をつけます。

    :param function fname: 関数
    :rtype:                object
    :return:               関数の戻り値
    """

    @functools.wraps(fname)
    def wrapper(*args, **kwds):

        sys.stderr.write(u"%s %s is obsolete function. %s" % ("%" * 10, fname.__name__, "%" * 10))
        sys.stderr.write(os.linesep)

        # 関数を実行する。
        ret = fname(*args, **kwds)

        return ret

    return wrapper

def print_profile(command, max_ratio=1.0, filter_text=None):
    """
    集計します。

    :param u command:       実行するコマンド ex. test()
    :param float max_ratio: 表示する上限 < 1.0
    :rtype:                 None
    """

    # 変数を初期化します。
    logger = getLogger()
    prof = cProfile.Profile()

    # 速度を計測します。
    prof = prof.run(command)

    #stream = io.StringIO()
    stream = io.BytesIO()
    stats = pstats.Stats(prof, stream=stream)

    # time で sort します
    stats.sort_stats(u"time")

    # 表示する上限まで出力します
    if filter_text is None:
        stats.print_stats(max_ratio)

    else:
        stats.print_stats(filter_text, max_ratio)

    # 結果を出力します。
    logger.info("Profile Result:\n%s", stream.getvalue())

    return

def decode(raw):
    """
    ユニコードに変換します。

    :param b raw:           データ
    :rtype:                 named tuple
    :return:                (text, encoding)
    """

    # 変数を初期化します。
    text = None
    encoding_result = collections.namedtuple("result", "text encoding")
    encodings = ['utf_8',
                 'euc_jp',
                 'euc_jis_2004',
                 'euc_jisx0213',
                'shift_jis',
                'shift_jis_2004',
                'shift_jisx0213',
                'iso2022jp',
                'iso2022_jp_1',
                'iso2022_jp_2',
                'iso2022_jp_3',
                'iso2022_jp_ext', 'latin_1',
                'cp923',
                'cp437',
                'ascii',
                ]

    if not hasattr(raw, "decode"):
        result = encoding_result(raw, None)
        return result

    # 文字のエンコーディングを取得します。
    if six.PY2:
        if isinstance(raw, unicode):
            return encoding_result(raw, None)
    else:
        if isinstance(raw, str):
            raw = raw.encode("cp437")

    for encoding in encodings:
        try:
            text = raw.decode(encoding)
            break
        except Exception as _ex:
            pass

    result = encoding_result(text, encoding)

    return result

def basename(path):
    """
    path の末尾のファイル名部分を返します。

    :param u path:          パス
    :rtype:                 named tuple
    :return:                (text, encoding)
    """

    # 変数を初期化します。
    File = collections.namedtuple("File", "dir filename basename extension")

    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    fileitem = os.path.splitext(filename)

    result = File(dirname, filename, fileitem[0], fileitem[1])

    return result

def parse_second(second, *args, **kwargs):
    """
    秒を時分秒に変換します。

    :rtype:             bool
    """

    # 変数を初期化します。
    result = {}
    time_days, time_rest = divmod(second, 86400)
    result["days"] = int(time_days)
    time_hour, time_rest = divmod(time_rest, 3600)
    result["hours"] = int(time_hour)
    time_min, time_sec = divmod(time_rest, 60)
    result["minutes"] = int(time_min)
    result["seconds"] = time_sec
 
    return result

class TestLogWriter(unittest.TestCase):
    """
    テストケース
    """

    filename = "LogWriter.log"
    logger_conf = {
        "name": os.path.splitext("TestLogWriter"),
        "level": logging.DEBUG,
        }
    logger = None

    def setUp(self):

        # 変数を初期化します。
        self.logger = LogWriter(**self.logger_conf)

    def tearDown(self):
        self.logger = None

    def test_debug(self):
        sys.stdout.write(os.linesep)

        result = self.logger.debug("デバッグ")
        self.assertEqual(result, None)

    def test_debug_anchor_start(self):
        sys.stdout.write(os.linesep)

        # 変数を初期化します。
        arg = "test"

        result = self.logger.debug_anchor_begin(arg=arg)
        self.assertEqual(result, None)

    def test_debug_anchor_end(self):
        sys.stdout.write(os.linesep)

        result = self.logger.debug_anchor_end()
        self.assertEqual(result, None)

@obsolete
def test_dummy(*args, **kwargs):
    return 0

class Test(unittest.TestCase):
    """
    テストケース
    """

    logger_conf = {
        "name": os.path.splitext(os.path.basename(__file__))[0],
        "level": logging.DEBUG,
        }

    def setUp(self):

        # 変数を初期化します。
        global logger
        logger = LogWriter(**self.logger_conf)

    def tearDown(self):
        self.logger = None

    def test_getLogger(self):
        sys.stdout.write(os.linesep)
        logger = LogWriter(__file__)

        result = getLogger()
        self.assertTrue(isinstance(result, LogWriter))

        result = getLogger(__file__)
        self.assertEqual(result.name, __file__)

    def test_obsolete(self):
        sys.stdout.write(os.linesep)

        result = test_dummy()
        self.assertEqual(result, 0)

    def test_decode(self):
        sys.stdout.write(os.linesep)

        result = decode(b"\xE2\x98\x85")
        self.assertEqual(result.text, u"★")
 
def test(*args, **kwargs):
    """
    test entry point
    """
    # 単体テストを実行します。
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLogWriter)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)

    return 0

if __name__ == "__main__":
    """
    self entry point
    """

    # logger for test
    _logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s"))
    _logger.setLevel(logging.DEBUG)
    _logger.addHandler(handler)

    sys.exit(test())
