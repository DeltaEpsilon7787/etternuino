from PyQt5 import QtCore, QtWidgets

from GUI.dial_group.dial_group_gui import Ui_dial_group


class DialGroup(QtWidgets.QFrame, Ui_dial_group):
    def __init__(self, name, minimum=0, maximum=1, divisor=0.01, slot=None):
        super().__init__()
        self.setupUi(self)

        self.meaning_label.setText(name)
        self.slider.setMinimum(minimum // divisor)
        self.slider.setMaximum(maximum // divisor)
        self.divisor = divisor
        self.slot = slot

    @QtCore.pyqtSlot(int)
    def valueChanged(self, new_value):
        self.value_out.setText(str(new_value / self.divisor))
        self.slot and self.slot(new_value / self.divisor)
