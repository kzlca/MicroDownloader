"""Dependency-free, rolling Steam-style neon transfer speed history graph."""
from collections import deque
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient
from PySide6.QtWidgets import QWidget
from .sparse import format_bytes

class SpeedChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = deque([0.0]*70, maxlen=140)
        self.setMinimumHeight(76)
        self.setMaximumHeight(115)
        self.setToolTip('Recent combined download speed (green = throughput)')

    def push(self, bytes_per_sec):
        self.history.append(max(0.0, float(bytes_per_sec)))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)
        if r.width() < 15 or r.height() < 20:
            p.end(); return
        p.fillRect(r, QColor('#101b26'))
        left, right = r.left()+8, r.right()-9
        top, bottom = r.top()+12, r.bottom()-11
        for a in (0.25, 0.5, 0.75):
            y = top + int((bottom-top)*a)
            p.setPen(QPen(QColor('#20354a'), 1))
            p.drawLine(left,y,right,y)
        values = list(self.history)
        peak = max(max(values,default=0), 1024)
        # Keep peaks visible without expanding/clipping every smaller sample.
        scale = peak * 1.12
        path = QPainterPath()
        for i, value in enumerate(values):
            x = left + i * (right-left) / max(1,len(values)-1)
            y = bottom - (min(value,scale)/scale) * (bottom-top)
            if i == 0: path.moveTo(x,y)
            else: path.lineTo(x,y)
        fill = QPainterPath(path)
        fill.lineTo(right,bottom); fill.lineTo(left,bottom); fill.closeSubpath()
        grad = QLinearGradient(0,top,0,bottom)
        grad.setColorAt(0,QColor(32,235,164,85))
        grad.setColorAt(1,QColor(32,235,164,3))
        p.fillPath(fill,grad)
        p.setPen(QPen(QColor(30,229,169,38), 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
        p.setPen(QPen(QColor('#58f5bf'), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
        p.setPen(QColor('#95acbf'))
        p.drawText(right-128,r.top()+11,124,13,Qt.AlignRight, 'PEAK  '+format_bytes(int(peak))+'/s')
        p.end()
