import json
import sys
import logging

import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from PyQt6.QtGui import QPixmap, QFont, QIcon, QImage
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize, pyqtSlot
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QProgressBar, \
    QListWidgetItem, QListWidget, QHBoxLayout, QFormLayout, QInputDialog, QFileDialog, QCheckBox, QMessageBox

from download_music import download_song

# REPLACE WITH YOUR CLIENT ID
SPOTIFY_CLIENT_ID = '002461729b8b438a8e5fbea705fd7b7f'
SPOTIFY_CLIENT_SECRET = 'cc1ace707d904439b85c304d0641c71e'
SOUNDCLOUD_CLIENT_ID = 'YOUR_ID_HERE'

VERSION = '0.0.1a'
LOG_FILE = 'logs.log'
process_thread = None


def setup_logging() -> None:
    """Sets up logging for the script."""
    open(LOG_FILE, 'w').close()
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')


class SpotifySearchThread(QThread):
    """Searching on Spotify"""
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.query = ""
        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
        self.stopped = False  # Flag to indicate if the thread should stop

    def stop(self):
        self.stopped = True

    @pyqtSlot()
    def run(self):
        try:
            logging.info("Initiating Spotify search...")
            print("Initiating Spotify search...")
            results = self.spotify.search(q=self.query, limit=20)
            logging.info("Processing Spotify results...")
            print("Processing results:")

            for track in results['tracks']['items']:
                if self.stopped:  # Check if the thread should stop
                    logging.info(f"Current processing: {track['name']}")
                    return  # Exit the thread gracefully
                if 'album' in track and 'images' in track['album'] and track['album']['images']:
                    response = requests.get(track['album']['images'][0]['url'])
                    img = QImage.fromData(response.content)
                    pixmap = QPixmap.fromImage(img).scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio,
                                                           Qt.TransformationMode.SmoothTransformation)
                    icon = QIcon(pixmap)
                    title = track['name']
                    artist = track['artists'][0]['name']
                    platform = "Spotify"
                    item = QListWidgetItem()
                    item.setData(Qt.ItemDataRole.UserRole, track['external_urls']['spotify'])
                    item.setSizeHint(QSize(38, 65))

                    self.signal.emit((item, title, artist, platform, icon))
            self.signal.emit((None, None, None, None, None))
        except Exception as e:
            self.signal.emit((f"Error: {str(e)}",))
            logging.error(f"An error occurred on Spotify connection, maybe you should try to use a VPN?: {e}")
            print(f"An error occurred, maybe you should try to use a VPN?: {e}")


class SoundcloudSearchThread(QThread):
    """Searching on Soundcloud"""
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.query = ""
        self.client_id = SOUNDCLOUD_CLIENT_ID
        self.stopped = False  # Flag to indicate if the thread should stop

    def stop(self):
        self.stopped = True

    @pyqtSlot()
    def run(self):
        try:
            api_url = f'https://api.soundcloud.com/tracks?q={self.query}&client_id={self.client_id}&limit=20'
            logging.info("Sending request to Soundcloud...")
            print("Sending request to Soundcloud...")
            response = requests.get(api_url)

            if response.status_code == 200:
                logging.info("Processing Soundcloud data...")
                print("Processing data...")
                tracks = response.json()

                for track in tracks:
                    if self.stopped:  # Check if the thread should stop
                        return  # Exit the thread gracefully
                    if 'title' in track and 'artwork_url' in track:
                        response = requests.get(track['artwork_url'])
                        img = QImage.fromData(response.content)
                        pixmap = QPixmap.fromImage(img).scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio,
                                                               Qt.TransformationMode.SmoothTransformation)
                        icon = QIcon(pixmap)
                        title = track['title']
                        artist = track['user']['username']
                        platform = "Soundcloud"
                        item = QListWidgetItem()
                        item.setData(Qt.ItemDataRole.UserRole, track['permalink_url'])
                        item.setSizeHint(QSize(38, 65))

                        self.signal.emit((item, title, artist, platform, icon))
                self.signal.emit((None, None, None, None, None))
            else:
                error_message = f"Request failed with status code {response.status_code}"
                self.signal.emit((error_message,))
                print(error_message)
        except Exception as e:
            self.signal.emit((f"Error: {str(e)}", ))
            logging.error(f"An error occurred on SoundCloud connection: {e}")
            print(f"An error occurred: {e}")


# Create global variables
search_thread_spotify = None
search_thread_soundcloud = None

def search_musics():
    global search_thread_spotify, search_thread_soundcloud

    list_widget.clear()
    error_label.clear()
    progress_bar.show()
    query = entry.text()

    if SPOTIFY_CLIENT_ID != 'YOUR_ID_HERE' and SPOTIFY_CLIENT_SECRET != 'YOUR_ID_HERE':
        search_thread_spotify = SpotifySearchThread()
        search_thread_spotify.query = query
        search_thread_spotify.signal.connect(handle_results)  # connect to handle_results
        search_thread_spotify.start()
    else:
        logging.warning("Please enter a Spotify client ID (free to have) in order to use Spotify search.")
        print("WARNING: Please enter a Spotify client ID (free to have) in order to use Spotify search.")

    if SOUNDCLOUD_CLIENT_ID != 'YOUR_ID_HERE':
        search_thread_soundcloud = SoundcloudSearchThread()
        search_thread_soundcloud.query = query
        search_thread_soundcloud.signal.connect(handle_results)
        search_thread_soundcloud.start()
    else:
        logging.warning("Please enter a Soundcloud client ID (free to have) in order to use Soundcloud search.")
        print("WARNING: Please enter a Soundcloud client ID (free to have) in order to use Soundcloud search.")

    download_button.hide()


app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle(f"Music Search {VERSION}")
window.setGeometry(500, 500, 600, 700)

layout = QVBoxLayout()

entry = QLineEdit()
entry.setPlaceholderText("Enter artist, song or album...")
entry.setFont(QFont("Arial", 16))
layout.addWidget(entry)

download_button = QPushButton()
download_button.setText("📦 Download")
download_button.setFixedHeight(40)
download_button.hide()
layout.addWidget(download_button)

list_widget = QListWidget()
list_widget.setStyleSheet("""
    QListWidget::item:selected {
        background-color: #52577C;
    }
""")
list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
layout.addWidget(list_widget)

error_label = QLabel()
error_label.setFont(QFont("Arial", 12))
layout.addWidget(error_label)

progress_bar = QProgressBar()
progress_bar.setRange(0, 0)
layout.addWidget(progress_bar)
progress_bar.hide()

search_thread = SpotifySearchThread()

selected_titles = []
selected_links = []


@pyqtSlot('PyQt_PyObject')
def handle_results(item_tuple):
    item, title, artist, platform, icon = item_tuple
    if item is not None:
        list_widget.addItem(item)
        widget = QWidget()
        layout = QHBoxLayout()

        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(67, 67))
        layout.addWidget(icon_label)

        right_layout = QFormLayout()
        right_layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("padding: 0; margin: 0;")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        right_layout.addWidget(title_label)

        artist_platform_label = QLabel(f"{artist}, {platform}")
        artist_platform_label.setStyleSheet("padding: 0; margin: 0;")
        artist_platform_label.setFont(QFont("Arial", 12))
        artist_platform_label.setStyleSheet("color: gray")
        right_layout.addWidget(artist_platform_label)

        layout.addLayout(right_layout)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)
        widget.setMinimumHeight(30)
        list_widget.setItemWidget(item, widget)

        download_button.show()
    else:
        progress_bar.hide()


class ProcessingThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')
    cancelled = pyqtSignal()

    def __init__(self, links):
        QThread.__init__(self)
        self.links = links

    def run(self):
        try:
            for link in self.links:
                if self.isInterruptionRequested():
                    self.cancelled.emit()
                    break
                download_song(link)
            if not self.isInterruptionRequested():
                self.signal.emit((True, "Download Complete"))
        except Exception as e:
            self.signal.emit((False, str(e)))

    def cancel_download(self):
        self.requestInterruption()


class DownloadManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.download_list = QListWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.download_list)
        self.setLayout(layout)

        self.direct_download_button = QPushButton("Direct Download")  # Create the button
        self.direct_download_button.clicked.connect(self.direct_download)  # Connect the button to direct_download method
        layout.addWidget(self.direct_download_button)  # Add the button to the layout

    def add_download(self, item, title, artist, platform, icon):
        widget_item = QListWidgetItem()
        widget_item.setSizeHint(QSize(38, 80))

        widget = QWidget()
        layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(67, 67))
        layout.addWidget(icon_label)

        right_layout = QFormLayout()
        right_layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("padding: 0; margin: 0;")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        right_layout.addWidget(title_label)

        artist_platform_label = QLabel(f"{artist}, {platform}")
        artist_platform_label.setStyleSheet("padding: 0; margin: 0;")
        artist_platform_label.setFont(QFont("Arial", 12))
        artist_platform_label.setStyleSheet("color: gray")
        right_layout.addWidget(artist_platform_label)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)
        right_layout.addWidget(progress_bar)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(lambda: self.cancel_download(widget_item, title))
        right_layout.addWidget(cancel_button)

        layout.addLayout(right_layout)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)

        self.download_list.addItem(widget_item)
        self.download_list.setItemWidget(widget_item, widget)

    def cancel_download(self, item, title):
        global process_thread
        item_widget = self.download_list.itemWidget(item)
        progress_bar = item_widget.findChild(QProgressBar)
        progress_bar.setRange(0, 0)
        item_widget.setEnabled(False)
        item_widget.setStyleSheet("background-color: #500000;")
        process_thread.cancel_download()

    def direct_download(self):
        music_link, ok = QInputDialog.getText(self, "Direct Download", "Enter the music link or name (No API key needed:)"
                                                                       "\n(YT Music, Spotify, "
                                                                       "Soundcloud, ...)")

        if ok and music_link:
            download_song(music_link)


@pyqtSlot('PyQt_PyObject')
def handle_downloads(result_tuple):
    success, message = result_tuple
    if success:
        download_button.setEnabled(True)
    else:
        error_label.setText(message)
        logging.error(message)


download_manager = DownloadManagerWidget()
manage_downloads_button = QPushButton("Manage Downloads")
manage_downloads_button.clicked.connect(download_manager.show)
layout.addWidget(manage_downloads_button)


class UserPreferencesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Preferences")
        self.setFixedSize(400, 300)

        if sys.platform == 'darwin':
            self.is_macos = True
        else:
            self.is_macos = False

        layout = QVBoxLayout()

        # Song Output Folder
        output_folder_layout = QFormLayout()
        output_folder_label = QLabel("Song Output Folder:")
        self.output_folder_lineedit = QLineEdit()
        self.output_folder_lineedit.setPlaceholderText("Select Folder")
        output_folder_button = QPushButton("Browse")
        output_folder_button.clicked.connect(self.select_output_folder)
        output_folder_layout.addRow(output_folder_label, self.output_folder_lineedit)
        output_folder_layout.addWidget(output_folder_button)
        layout.addLayout(output_folder_layout)

        # Add checkbox for open in Apple Music option
        self.auto_add_music_checkbox = QCheckBox("Auto add Music app (MacOS) (BROKEN)")
        self.auto_add_music_checkbox.setDisabled(not self.is_macos)
        layout.addWidget(self.auto_add_music_checkbox)

        # Add checkbox for one-threaded option
        self.one_threaded_checkbox = QCheckBox("Run in one thread (NOT IMPLEMENTED YET)")
        layout.addWidget(self.one_threaded_checkbox)

        # Display Client IDs
        self.client_ids_show_button = QPushButton("Display Client IDs")
        self. client_ids_show_button.clicked.connect(self.show_clients_id)
        layout.addWidget(self.client_ids_show_button)

        # Client IDs
        self.client_ids_label = QLabel("Client IDs:")
        self.client_ids_label.hide()
        layout.addWidget(self.client_ids_label)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_preferences)
        layout.addWidget(save_button)

        self.setLayout(layout)


    def select_output_folder(self):
        if folder := QFileDialog.getExistingDirectory(
            self, "Select Song Output Folder"
        ):
            self.output_folder_lineedit.setText(folder)

    def show_clients_id(self):
        QMessageBox.about(self, "Your actual API keys", f"SPOTIFY Client ID: {SPOTIFY_CLIENT_ID}\n"
                                      f"SPOTIFY Secret Client ID: {SPOTIFY_CLIENT_SECRET}\n\n"
                                      f"Soundcloud Client ID: {SOUNDCLOUD_CLIENT_ID}")

    def select_output_folder(self):
        if folder := QFileDialog.getExistingDirectory(
            self, "Select Song Output Folder"
        ):
            self.output_folder_lineedit.setText(folder)

    def save_preferences(self):
        # Save the current preferences to the dictionary
        self.preferences['output_folder'] = self.output_folder_lineedit.text()
        self.preferences['auto_add_music'] = self.auto_add_music_checkbox.isChecked()
        self.preferences['one_threaded'] = self.one_threaded_checkbox.isChecked()

        # TO DO: Load preferences on script init
        with open('preferences.json', 'w') as file:
            json.dump(self.preferences, file)

        self.close()


user_preferences = UserPreferencesWindow()
user_preferences_button = QPushButton("User preferences")
user_preferences_button.clicked.connect(user_preferences.show)
layout.addWidget(user_preferences_button)


@pyqtSlot()
def save_selected_items():
    global selected_titles, selected_links, process_thread
    selected_titles = []
    selected_links = []

    for item in list_widget.selectedItems():
        selected_titles.append(item.text())
        selected_links.append(item.data(Qt.ItemDataRole.UserRole))

        title = item.text()
        artist = item.data(Qt.ItemDataRole.UserRole)
        icon = item.icon()

        download_manager.add_download(item, title, artist, "Spotify", icon)

    process_thread = ProcessingThread(selected_links)
    process_thread.signal.connect(handle_downloads)
    process_thread.cancelled.connect(lambda: handle_downloads((False, "Download Cancelled")))
    process_thread.start()
    download_button.setEnabled(False)


entry.returnPressed.connect(search_musics)

search_thread.signal.connect(handle_results)

download_button.clicked.connect(save_selected_items)

setup_logging()

window.setLayout(layout)
window.show()

sys.exit(app.exec())
