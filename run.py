#!/usr/bin/env python3
"""Frozen and source entry point; explicit diagnostics for GUI CI self-tests.

PyInstaller windowed executables on Windows have no usable stdout/stderr.
For --self-test we log failures to MICRO_DOWNLOADER_SELF_TEST_LOG before
importing Qt, then capture exceptions raised by Qt signal callbacks too.
"""
import os
import sys
import traceback
from pathlib import Path


def main():
    self_test = '--self-test' in sys.argv
    report_path = os.environ.get('MICRO_DOWNLOADER_SELF_TEST_LOG', '').strip()
    report = Path(report_path) if self_test and report_path else None
    callback_errors = []

    def write_report(message):
        if not report:
            return
        try:
            report.parent.mkdir(parents=True, exist_ok=True)
            with report.open('a', encoding='utf-8') as f:
                f.write(message.rstrip() + '\n')
        except OSError:
            # Never mask the actual app failure with a reporting failure.
            pass

    if self_test:
        write_report(f'START: Python {sys.version.split()[0]}, executable={sys.executable}, frozen={getattr(sys, "frozen", False)}')
        write_report(f'QT_QPA_PLATFORM={os.environ.get("QT_QPA_PLATFORM", "<default>")}')
        old_hook = sys.excepthook

        def self_test_excepthook(etype, value, tb):
            message = ''.join(traceback.format_exception(etype, value, tb))
            callback_errors.append(message)
            write_report('UNHANDLED QT CALLBACK EXCEPTION:\n' + message)
            if sys.stderr is not None:
                old_hook(etype, value, tb)

        sys.excepthook = self_test_excepthook

        # Capture errors from the Qt plugin system, including fatal QPA notices,
        # which are otherwise invisible in a Windows --windowed build.
        try:
            from PySide6.QtCore import qInstallMessageHandler

            def qt_message_handler(mode, context, message):
                write_report('Qt message: ' + str(message))

            qInstallMessageHandler(qt_message_handler)
            write_report('QtCore imported successfully')
        except BaseException:
            write_report('QtCore import / message-handler install failed:\n' + traceback.format_exc())
            return 1

    try:
        from micro_downloader.ui import launch
        write_report('UI import succeeded')
        result = launch(self_test=self_test)
        if callback_errors:
            write_report('FAIL: one or more Qt callbacks raised an exception')
            return 1
        if result:
            write_report(f'FAIL: Qt event loop exit code {result}')
            return int(result)
        write_report('PASS: Qt window opened and exited successfully')
        return 0
    except BaseException:
        message = traceback.format_exc()
        write_report('FAIL: application raised an exception:\n' + message)
        if sys.stderr is not None:
            sys.stderr.write(message)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
