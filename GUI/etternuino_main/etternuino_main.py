import os
from fractions import Fraction

from PyQt5 import QtCore, QtWidgets

from GUI.etternuino_main.etternuino_gui import Ui_etternuino_window
from chart_player import ChartPlayer
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, BYTE_UNCHANGED, LANE_PINS, \
    SNAP_PINS, capture_exceptions, in_reduce
from simfile_parsing.basic_types import Time
from simfile_parsing.chart_parser import parse_simfile


class EtternuinoMain(QtWidgets.QMainWindow, Ui_etternuino_window):
    def __init__(self):
        super().__init__(self)
        self.setup_ui()

        self.active_threads = []
        self.player = None
        self.arduino = None

        self.show()

    @QtCore.pyqtSlot(int)
    def change_current_time(self, new_value):
        if self.player:
            self.player.mixer.current_frame = new_value

    @QtCore.pyqtSlot()
    def update_player(self):
        self.player.need_to_update_position = True

    @capture_exceptions
    def chart_selected(self, parsed_simfile, chart_num):
        if chart_num < 0:
            return
        self.player = ChartPlayer(
            simfile=parsed_simfile, chart_num=chart_num,
            sound_start_delta=Time(Fraction(0, 1)),
            arduino=self.arduino,
            music_out=self.play_music_checkbox.isChecked(),
            clap_mapper=None,
            progress_slider_output=self.progress_slider
        )

        self.progress_slider.setMaximum(self.player.mixer.data.shape[0])
        self.progress_slider.setValue(0)

        self.player.on_start.connect(lambda: self.set_play_group_visibility(False))
        self.player.on_start.connect(lambda: self.set_control_group_visibility(True))
        self.player.on_start.connect(self.virtual_arduino.show)

        self.player.chart_obtained.connect(self.virtual_arduino.analyze_chart)
        self.player.time_arrived.connect(self.virtual_arduino.rewind_to)

        self.player.on_end.connect(lambda: self.set_play_group_visibility(True))
        self.player.on_end.connect(lambda: self.set_control_group_visibility(False))
        self.player.on_end.connect(self.virtual_arduino.close)

        player_thread = QtCore.QThread()
        player_thread.start()
        self.player.moveToThread(player_thread)
        self.player.start.emit()
        self.active_threads.append(player_thread)
        self.player.on_end.connect(lambda: self.active_threads.remove(player_thread))
        self.player.on_end.connect(self.cleanup)

    @QtCore.pyqtSlot()
    @capture_exceptions
    def play_file(self):
        sm_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose SM file...', os.getcwd(),
                                                           'Simfiles (*.sm)')
        if sm_file == "":
            return
        parsed_simfile = parse_simfile(sm_file)
        self.chart_selection.chart_list.clear()
        for index, chart in enumerate(parsed_simfile.charts, 1):
            self.chart_selection.chart_list.addItem(f'{index}: {chart.diff_name}')
        self.chart_selection.on_selection.connect(lambda chart_num: self.chart_selected(parsed_simfile, chart_num))
        self.chart_selection.on_cancel.connect(self.cleanup)
        self.chart_selection.show()

    @QtCore.pyqtSlot()
    def pause(self):
        self.player and self.player.pause()
        self.unpause_btn.setVisible(True)
        self.pause_btn.setVisible(False)

    @QtCore.pyqtSlot()
    def unpause(self):
        self.player and self.player.unpause()
        self.unpause_btn.setVisible(False)
        self.pause_btn.setVisible(True)

    @QtCore.pyqtSlot()
    def stop(self):
        self.player.die()

    @QtCore.pyqtSlot()
    def cleanup(self):
        if self.chart_selection:
            self.chart_selection.on_selection.disconnect()
            self.chart_selection.on_cancel.disconnect()
        if self.player:
            self.player.cleanup()
        if self.arduino:
            self.arduino.write(BYTE_FALSE * ARDUINO_MESSAGE_LENGTH)

    @QtCore.pyqtSlot(bool)
    def play_music(self, new_state):
        if not self.player:
            return
        self.player.mixer.muted = not new_state

    @QtCore.pyqtSlot(bool)
    def signal_arduino(self, new_state):
        if not self.player:
            return
        self.player.arduino_muted = not new_state

    @QtCore.pyqtSlot(bool)
    def add_claps(self, new_state):
        pass

    @QtCore.pyqtSlot(bytes)
    @capture_exceptions
    def interpret_message(self, message: bytes):
        if in_reduce(all, message, (BYTE_UNCHANGED,)):
            return

        self.virtual_arduino.toggle_lanes([message[LANE_PINS[i]] for i in range(4)])
        self.virtual_arduino.toogle_snap([
            snap
            for snap in [
                message[SNAP_PINS[possible_snap]] and possible_snap or None
                for possible_snap in [4, 8, 12, 16, 24]
            ]
            if snap is not None
        ])


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    the_app = EtternuinoMain()

    sys.exit(app.exec_())
