import subprocess
import os
import sys


def download_song(query):

    if isinstance(query, list):
        len_query = len(query)
        for i in range(len_query):
            query = query[i].replace("'", " ").replace('"', ' ')
            print(f"{i+1}/{len_query}")
            download_command = f'spotdl "{query[i]}" --output {os.path.abspath("Musics")}'

            # Execute the command in the shell
            subprocess.run(download_command, shell=True)
    else:
        query = query.replace("'", " ").replace('"', ' ')
        if query.startswith("https"):
            download_command = f'spotdl "{query}" --output {os.path.abspath("Musics")}'
        else:
            download_command = f'spotdl \'{query}\' --output {os.path.abspath("Musics")}'

        # Execute the command in the shell
        subprocess.run(download_command, shell=True)

#TO DO: if sys.platform == 'darwin':
#            add_to_music_app_and_delete(music_file_path)

# Add the music to Music App then delete
def add_to_music_app_and_delete(music_file_path):
    # Use AppleScript to add the song to the Music App Library
    applescript = f"""
    tell application "Music"
        add POSIX file "{music_file_path}"
    end tell
    """
    subprocess.call(["osascript", "-e", applescript])

    # Use os module to delete the music file
    os.remove(music_file_path)


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
