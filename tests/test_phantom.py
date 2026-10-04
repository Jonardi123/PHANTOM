import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from phantom import Pane, Phantom, password_estimate


class CommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait_for_operation(self, pane):
        deadline = time.monotonic() + 5
        while pane.busy and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertFalse(pane.busy, 'Command did not finish')
        # Let the thread shutdown and deferred deletion finish, including on old versions.
        for _ in range(5):
            self.app.processEvents()
            time.sleep(.01)

    def test_results_and_callback_run_on_gui_thread(self):
        pane = Pane('Test', 'Local test command')
        threads = []
        original = pane.show_result
        def record_result(*args):
            threads.append(QThread.currentThread() == self.app.thread())
            original(*args)
        pane.show_result = record_result
        pane.execute('Test', [sys.executable, '-c', 'print("complete")'],
                     callback=lambda *args: threads.append(QThread.currentThread() == self.app.thread()))
        self.wait_for_operation(pane)
        self.assertEqual(threads, [True, True])
        self.assertIn('complete', pane.last_output)
        pane.deleteLater()

    def test_window_cannot_close_while_command_thread_is_running(self):
        window = Phantom()
        window.show()
        pane = window.panes[0]
        pane.execute('Test', [sys.executable, '-c', 'import time; time.sleep(.15)'])
        with patch('phantom.QMessageBox.information'):
            accepted = window.close()
        self.wait_for_operation(pane)
        self.assertFalse(accepted)
        self.assertTrue(window.close())
        window.deleteLater()


class PasswordTests(unittest.TestCase):
    def test_normal_estimate(self):
        result = password_estimate(2, 3, 1)
        self.assertIn('Search space: 8', result)
        self.assertIn('Average (uniform random password)', result)

    def test_largest_supported_search_space_and_tiny_rate_do_not_overflow(self):
        result = password_estimate(1000, 128, '1e-320')
        self.assertIn(f'Search space: {1000 ** 128:,}', result)
        self.assertNotIn('Infinity', result)

    def test_invalid_and_nonfinite_rates_are_rejected(self):
        for speed in ('nan', 'inf', '-inf', '0', '-1', 'not a number'):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                password_estimate(62, 16, speed)


if __name__ == '__main__':
    unittest.main()
