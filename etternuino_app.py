import sys

from PyQt5 import QtWidgets

import GUI.etternuino_main.etternuino_main

app = QtWidgets.QApplication([])
main = GUI.etternuino_main.etternuino_main.EtternuinoMain()
main.show()

sys.exit(app.exec_())
