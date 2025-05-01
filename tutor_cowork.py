import eventlet
eventlet.monkey_patch()

from datetime import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

audio_folder = 'audio_files'
current_line = {}
lines = []

# Get the absolute path to master.txt
base_dir = os.path.dirname(os.path.abspath(__file__))
master_path = os.path.join(base_dir, 'master.txt')

def load_lines():
    with open(master_path, 'r', encoding='utf-8') as file:
        return [line.strip().split('\t') for line in file if line.strip()]

# ✅ Load lines immediately at module load time (so they’re available under Gunicorn)
lines = load_lines()
if not lines:
    print("⚠ WARNING: No lines loaded from master.txt!")

def select_random_line():
    if not lines:
        return ["No lines loaded in master.txt", "", "", "", "", "", ""]
    return random.choice(lines)

@app.route('/')
def index():
    global current_line
    current_line = select_random_line()
    return render_template('index.html', english=current_line[0])

@socketio.on('show_translation')
def handle_show_translation(data):
    lang = data['language']
    if lang == 'italian':
        emit('update_translation', {'language': 'italian', 'text': current_line[1]})
        filename_stem = current_line[2]
    elif lang == 'spanish':
        emit('update_translation', {'language': 'spanish', 'text': current_line[5]})
        filename_stem = current_line[6]
    else:
        return
    file_path = f'/static/audio_files/{filename_stem}.mp3'
    emit('play_audio_file', {'file_path': file_path})

@socketio.on('save_translation')
def handle_save_translation(data):
    lang = data['language']
    new_text = data['text']
    index = 1 if lang == 'italian' else 5
    current_line[index] = new_text

    with open(master_path, 'r', encoding='utf-8') as file:
        all_lines = file.readlines()

    for i, line in enumerate(all_lines):
        fields = line.strip().split('\t')
        if fields[0] == current_line[0]:
            fields[index] = new_text
            all_lines[i] = '\t'.join(fields) + '\n'
            break

    with open(master_path, 'w', encoding='utf-8') as file:
        file.writelines(all_lines)

    with open(os.path.join(base_dir, 'translation_log.txt'), 'a', encoding='utf-8') as log_file:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"{timestamp}\t{current_line[4]}\t{current_line[0]}\t{lang}\t{new_text}\n")
    emit('save_success', {'language': lang})

@socketio.on('play_audio')
def handle_play_audio(data):
    lang = data['language']
    filename_stem = current_line[2] if lang == 'italian' else current_line[6]
    file_path = f'/static/audio_files/{filename_stem}.mp3'
    emit('play_audio_file', {'file_path': file_path})

@socketio.on('next_sentence')
def handle_next_sentence():
    global current_line
    current_line = select_random_line()
    emit('new_sentence', {'english': current_line[0]}, broadcast=True)

@socketio.on('edit_translation')
def handle_edit_translation(data):
    lang = data['language']
    text = data['text']
    emit('update_translation_live', {'language': lang, 'text': text}, broadcast=True, include_self=False)



if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
