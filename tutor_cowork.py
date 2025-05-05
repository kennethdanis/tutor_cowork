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
lines = []

# Get absolute paths
base_dir = os.path.dirname(os.path.abspath(__file__))
master_path = os.path.join(base_dir, 'master.txt')
log_path = os.path.join(base_dir, 'translation_log.txt')

# Load lines on startup
def load_lines():
    with open(master_path, 'r', encoding='utf-8') as file:
        return [line.strip().split('\t') for line in file if line.strip()]

lines = load_lines()
if not lines:
    print("⚠ WARNING: No lines loaded from master.txt!")

# Initialize shared current_line
current_line = random.choice(lines)

@app.route('/')
def index():
    return render_template('index.html', english=current_line[0])

@socketio.on('request_current_state')
def handle_request_current_state():
    emit('sync_current_state', {
        'english': current_line[0],
        'italian': '',   # clear translation box on initial load
        'spanish': ''    # clear translation box on initial load
    })

@socketio.on('show_translation')
def handle_show_translation(data):
    lang = data['language']
    if lang == 'italian':
        emit('update_translation', {'language': 'italian', 'text': current_line[1]}, broadcast=True)
        filename_stem = current_line[2]
    elif lang == 'spanish':
        emit('update_translation', {'language': 'spanish', 'text': current_line[5]}, broadcast=True)
        filename_stem = current_line[6]
    else:
        return
    file_path = f'/static/audio_files/{filename_stem}.mp3'
    emit('play_audio_file', {'file_path': file_path}, broadcast=True)

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

    with open(log_path, 'a', encoding='utf-8') as log_file:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"{timestamp}\t{current_line[4]}\t{current_line[0]}\t{lang}\t{new_text}\n")
    emit('save_success', {'language': lang})

@socketio.on('play_audio')
def handle_play_audio(data):
    lang = data['language']
    filename_stem = current_line[2] if lang == 'italian' else current_line[6]
    file_path = f'/static/audio_files/{filename_stem}.mp3'
    emit('play_audio_file', {'file_path': file_path}, broadcast=True)

@socketio.on('next_sentence')
def handle_next_sentence():
    global current_line
    current_line = random.choice(lines)
    emit('new_sentence', {
        'english': current_line[0],
        'italian': '',  # clear translation box on next sentence
        'spanish': ''   # clear translation box on next sentence
    }, broadcast=True)

@socketio.on('edit_translation')
def handle_edit_translation(data):
    lang = data['language']
    text = data['text']
    index = 1 if lang == 'italian' else 5

    # Update the shared in-memory line
    current_line[index] = text

    # Broadcast the change to all other clients
    emit('update_translation_live', {'language': lang, 'text': text}, broadcast=True, include_self=False)

# ✅ NEW: Scratchpad handlers
@socketio.on('scratchpad_update')
def handle_scratchpad_update(data):
    emit('scratchpad_update', data, broadcast=True)

@socketio.on('scratchpad_erase')
def handle_scratchpad_erase():
    emit('scratchpad_update', '', broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
