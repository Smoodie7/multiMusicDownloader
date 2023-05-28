import os
import shutil
import subprocess
import sys
import logging

def download_song(query):
    # Create a hidden temp directory and delete if exists
    temp_dir = os.path.join(os.getcwd(), 'temp')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    def process_query(query_item):
        query_item = query_item.replace("'", " ").replace('"', ' ')
        if query_item.startswith("https"):
            download_command = f'spotdl "{query_item}" --output {temp_dir}'
        else:
            download_command = f'spotdl \'{query_item}\' --output {temp_dir}'

        # Execute the command in the shell
        logging.info(f"Executing: {download_command}")
        subprocess.run(download_command, shell=True)

        if sys.platform == 'darwin':
            add_to_music_app_and_sync(temp_dir)

        # Move the downloaded file to Musics folder
        for filename in os.listdir(temp_dir):
            shutil.move(os.path.join(temp_dir, filename), os.path.join(os.getcwd(), "Musics", filename))

    if isinstance(query, list):
        len_query = len(query)
        for i, query_item in enumerate(query, start=1):
            print(f"{i}/{len_query}")
            process_query(query_item)
    else:
        process_query(query)

    # Delete the temp directory
    shutil.rmtree(temp_dir)


def add_to_music_app_and_sync(temp_folder_path):
    # Iterate over all files in the given folder
    for filename in os.listdir(temp_folder_path):
        # If it is, add it to the Music app
        music_file_path = os.path.join(temp_folder_path, filename)
        print(f"Transferring {music_file_path} to Music App..")
        logging.info(f"Transferring {music_file_path} to Music App..")

        # Use AppleScript to open the file with the Music app
        applescript_open_music_app = [
            "osascript",
            "-e",
            f'tell app "Music" to add POSIX file "{music_file_path}"'
        ]
        subprocess.run(applescript_open_music_app)

    # Get device name
    try:
        print("Trying to find devices..")
        result = subprocess.run(["osascript", "-e",
                                 """
                                 do shell script "system_profiler SPUSBDataType | awk -F': ' '/iPhone|iPad/{getline; print $2}'"
                                 """
                                 ], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            device_name = result.stdout.strip()
        else:
            device_name = None

        if not device_name:
            print("Didn't find connected device, trying wireless..")
            # Attempt to get the name of a wireless connected device
            # Here we are running a shell script that will time out after 5 seconds
            result = subprocess.run(['sh', '-c',
                                     """
                                     timeout 5 dns-sd -B _raop._tcp local | grep 'iPhone' | head -1 | awk '{print $7}' | cut -d '.' -f 1
                                     """
                                     ], capture_output=True, text=True)
            if result.returncode == 0:
                device_name = result.stdout.strip()

        if device_name:
            print(f"Found {device_name}, trying to sync Music Library..")
        else:
            logging.error('Failed to retrieve connected device name')
            return
    except subprocess.TimeoutExpired:
        logging.error('Failed to retrieve connected device name')
        return

    # If device is found, attempt to sync
    if device_name:
        applescript_sync = f"""
            tell application "System Events"
                tell process "Finder"
                    set frontmost to true
                    click menu item "Sync {device_name}" of menu 1 of menu bar item "File" of menu bar 1
                end tell
            end tell
            """
        try:
            subprocess.call(["osascript", "-e", applescript_sync])
            print(f"Synchronized with {device_name} successfully!")
            logging.info(f"Synchronized with {device_name} successfully!")
        except subprocess.CalledProcessError:
            print(f'Failed to sync with device: {device_name}')
            logging.error(f'Failed to sync with device: {device_name}')


# DO NOT PAY ATTENTION HERE
def command():
    while True:
        command = input('Enter command: ').split(' ', 1)

        if len(command) < 2:
            print("Invalid command, please provide arguments.")
            continue

        action, argument = command[0].lower(), command[1]

        if action == 'download':
            # Download by link or by name
            if not argument.startswith('https'):
                # Use spotDL to download by name
                download_song(argument)
        elif action == 'exit':
            # Exit the program
            break
        else:
            print(f"Unknown command: {action}")
