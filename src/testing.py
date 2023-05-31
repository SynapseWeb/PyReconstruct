from modules.backend.threading import ThreadPoolProgBar

from PySide6.QtWidgets import QApplication

import time

app = QApplication([])
def f(n):
    time.sleep(0.2)
    print(f"yeet{n}")
tp = ThreadPoolProgBar()
for n in range(100):
    tp.createWorker(f, n)
tp.startAll("loading this bitch up!")