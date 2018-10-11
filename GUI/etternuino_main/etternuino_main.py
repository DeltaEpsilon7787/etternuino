from fractions import Fraction

from PyQt5 import QtCore, QtWidgets

from GUI.etternuino_main.etternuino_gui import Ui_etternuino_window
from GUI.visuterna_window.visuterna_window import VisuternaWindow
from chart_player import ChartPlayer
from chart_selection_dialog.chart_selection import ChartSelectionDialog
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, capture_exceptions
from simfile_parsing.basic_types import Time
from simfile_parsing.simfile_parser import Simfile, SimfileParser


class EtternuinoMain(QtWidgets.QMainWindow, Ui_etternuino_window):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.player: ChartPlayer = None
        self.arduino = None
        self.threads = []
        self.visuterna_window: VisuternaWindow = None
        self.chart_selection: ChartSelectionDialog = None

        self.show()

    @QtCore.pyqtSlot(int)
    def change_current_time(self, new_value):
        self.player.mixer.current_frame = new_value

    @QtCore.pyqtSlot()
    def update_player(self):
        self.player.need_to_update_position = True

    @QtCore.pyqtSlot()
    def play_file(self):
        # sm_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose SM file...', os.getcwd(),
        #                                                   'Simfiles (*.sm)')
        sm_file = r"Q:\Games\Rhythm Games\Etterna\Songs\Singles\KABOOM!! (DeltaEpsilon)\chart.sm"
        if sm_file == "":
            return

        simfile_parser = SimfileParser()
        parsing_thread = QtCore.QThread()
        parsing_thread.started.connect(lambda: self.threads.append(parsing_thread))
        parsing_thread.started.connect(lambda: self.play_button.setEnabled(False))
        parsing_thread.started.connect(lambda: simfile_parser.parse_simfile(sm_file))
        parsing_thread.finished.connect(lambda: self.play_button.setEnabled(True))
        simfile_parser.simfile_parsed.connect(self.select_chart)
        simfile_parser.moveToThread(parsing_thread)
        parsing_thread.start()

    @QtCore.pyqtSlot(object)
    def select_chart(self, parsed_simfile: Simfile):
        self.chart_selection = ChartSelectionDialog()
        self.chart_selection.chart_list.clear()
        for index, chart in enumerate(parsed_simfile.charts, 1):
            self.chart_selection.chart_list.addItem(f'{index}: {chart.diff_name}')
        self.chart_selection.on_selection['int'].connect(lambda chart_num: self.chart_selected(parsed_simfile,
                                                                                               chart_num))
        self.chart_selection.on_cancel.connect(self.cleanup)
        self.chart_selection.show()

    @QtCore.pyqtSlot()
    def open_visuterna(self):
        self.visuterna_window = VisuternaWindow(4)
        self.player.on_write[object].connect(self.visuterna_window.receive_event)
        self.player.on_end.connect(self.visuterna_window.close)
        self.visuterna_window.show()

    @capture_exceptions
    def chart_selected(self, parsed_simfile: Simfile, chart_num: int):
        if chart_num < 0:
            return

        chart = parsed_simfile.charts[chart_num]

        self.player = ChartPlayer(
            chart=chart,
            audio=parsed_simfile.music,
            sound_start_delta=Time(Fraction(0, 1)),
            arduino=self.arduino,
            clap_mapper=None,
        )

        player_thread = QtCore.QThread()
        player_thread.started.connect(lambda: self.threads.append(player_thread))
        player_thread.started.connect(self.player.play)
        player_thread.finished.connect(self.cleanup)
        self.player.on_start.connect(self.open_visuterna)
        self.player.moveToThread(player_thread)
        player_thread.start()

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

        self.threads.clear()

    @QtCore.pyqtSlot(bool)
    def play_music(self, new_state):
        if not self.player:
            return
        new_state and self.player.mute_music() or self.player.unmute_music()

    @QtCore.pyqtSlot(bool)
    def signal_arduino(self, new_state):
        if not self.player:
            return
        new_state and self.player.mute_arduino() or self.player.unmute_arduino()

    @QtCore.pyqtSlot(bool)
    def add_claps(self, new_state):
        pass
