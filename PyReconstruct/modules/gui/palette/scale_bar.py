from PySide6.QtGui import QPainter, QColor, QFontMetrics, QFont
from PySide6.QtCore import QRect

from PyReconstruct.modules.gui.utils import drawOutlinedText

from .buttons import MoveableButton

class ScaleBar(MoveableButton):

    def __init__(self, parent, manager, length, height, scale):
        """Create the scale bar.
        
            Params:
                parent (QWidget): the parent of the scale bar
                manager (QMainWindow): the manager of the scale bar
                length (int): the max pixel length of the scale bar
                height (int): the max pixel height of the scale bar
                scale (float): the number of real-world units per pixel
                ticks (bool): True if ticks should be shown on the scale bar
        """
        super().__init__(parent, manager, "sb")
        self.scale = scale
        self.resize(length, height)
    
    def setScale(self, scale):
        self.scale = scale
        self.update()
    
    def paintEvent(self, event):
        # get the max scale bar size that fits 0.25, 0.5, or 1 (and so on)
        l = self.width() * self.scale

        # multiply the number by a power of ten so that it is in between 10 and 100
        if l <= 10: inc = 1
        elif l > 100: inc = -1
        else: inc = 0
        p = 0
        while not (10 < l * 10**p <= 100):
            p += inc
                
        # get the max scale bar size that should be used
        if 10 < l * 10**p < 25:
            n = 10
        elif 25 <= l * 10**p < 50:
            n = 25
        elif 50 <= l * 10**p < 100:
            n = 50
        else:
            n = 100
        
        real_len = round(n * 10 ** (-p), 10)
        pix_len = int(real_len / self.scale)

        # check text and tick preferences
        draw_text = self.manager.series.getOption("show_scale_bar_text")
        draw_ticks = self.manager.series.getOption("show_scale_bar_ticks")

        # draw the scale bar
        r_x = 0
        r_y = self.height() / 2
        r_w = pix_len
        r_h = self.height() / 2
        painter = QPainter(self)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRect(r_x, r_y, r_w, r_h)
        painter.setBrush(QColor(0, 0, 0))
        painter.drawRect(r_x + 1, r_y + 1, r_w - 2, r_h - 2)

        # draw text
        if draw_text:
            font = QFont("Courier New", 12)
            font.setBold(True)
            small_font = QFont("Courier New", 9)  # used for ticks
            l_text = str(real_len) + " µm"
            painter.setFont(font)
            drawCenteredText(
                painter, 
                r_x + r_w/2, 
                r_y / 2, 
                l_text,
                outlined=True
            )

        # draw ticks if requested
        if draw_ticks:
            subdivs = 5
            for i in range(1, subdivs):
                t_x = r_x + r_w/subdivs * i
                painter.drawLine(t_x, r_h, t_x, r_h + 4)
                if draw_text:
                    painter.setFont(small_font)
                    t_text = str(round(real_len * i/subdivs, 10))
                    drawCenteredText(
                        painter,
                        t_x,
                        r_h + 8,
                        t_text
                    )
        
        painter.end()

def drawCenteredText(painter, x, y, text, outlined=False):
    font_metrics = QFontMetrics(painter.font())
    text_rect = font_metrics.boundingRect(text)
    adjusted_x = x - text_rect.width() / 2
    adjusted_y = y + text_rect.height() / 2
    if outlined:
        drawOutlinedText(
            painter,
            adjusted_x,
            adjusted_y,
            text
        )
    else:
        painter.drawText(adjusted_x, adjusted_y, text)


