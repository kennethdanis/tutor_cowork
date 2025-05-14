import eventlet
eventlet.monkey_patch()

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
log_path = os.path.join(base_dir, 'change_log.txt')

# Load lines on startup
def load_lines():
    with open(master_path, 'r', encoding='utf-8') as file:
        return [line.strip().split('\t') for line in file if line.strip()]

lines = load_lines()
if not lines:
    print("\u26a0 WARNING: No lines loaded from master.txt!")

unused_lines = random.sample(lines, len(lines))
line_index = 0
current_line = unused_lines[line_index]
line_index += 1
layout_order = ['italian', 'spanish']
translations_visible = False

@app.route('/')
def index():
    return render_template('index.html', english=current_line[0])

@socketio.on('next_sentence')
def handle_next_sentence():
    global current_line, line_index, unused_lines, layout_order, translations_visible
    if line_index >= len(unused_lines):
        unused_lines = random.sample(lines, len(lines))
        line_index = 0
    current_line = unused_lines[line_index]
    line_index += 1

    layout_order = ['italian', 'spanish'] if random.random() > 0.5 else ['spanish', 'italian']

    emit('new_sentence', {
        'english': current_line[0],
        'layout_order': layout_order,
        'italian': '',
        'spanish': ''
    }, broadcast=True)

    emit('hide_both_translations', broadcast=True)
    translations_visible = False

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

@socketio.on('show_both_translations')
def handle_show_both_translations():
    global translations_visible
    with open(master_path, 'r', encoding='utf-8') as file:
        all_lines = [line.strip().split('\t') for line in file if line.strip()]

    italian_text = current_line[1]
    spanish_text = current_line[5]
    for fields in all_lines:
        if fields[0] == current_line[0]:
            italian_text = fields[1]
            spanish_text = fields[5]
            break

    current_line[1] = italian_text
    current_line[5] = spanish_text

    emit('update_translation', {'language': 'italian', 'text': italian_text}, broadcast=True)
    emit('update_translation', {'language': 'spanish', 'text': spanish_text}, broadcast=True)
    translations_visible = True
    emit('show_both_translations', broadcast=True)

@socketio.on('hide_both_translations')
def handle_hide_both_translations():
    global translations_visible
    emit('update_translation', {'language': 'italian', 'text': ''}, broadcast=True)
    emit('update_translation', {'language': 'spanish', 'text': ''}, broadcast=True)
    translations_visible = False
    emit('hide_both_translations', broadcast=True)

@socketio.on('restore_translation')
def handle_restore_translation(data):
    lang = data['language']
    index = 1 if lang == 'italian' else 5

    with open(master_path, 'r', encoding='utf-8') as file:
        all_lines = [line.strip().split('\t') for line in file if line.strip()]

    restored_text = current_line[index]
    for fields in all_lines:
        if fields[0] == current_line[0]:
            restored_text = fields[index]
            break

    current_line[index] = restored_text
    emit('update_translation', {'language': lang, 'text': restored_text}, broadcast=True)

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
        log_file.write('\t'.join(current_line) + '\n')

    emit('save_success', {'language': lang})

@socketio.on('play_audio')
def handle_play_audio(data):
    lang = data['language']
    filename_stem = current_line[2] if lang == 'italian' else current_line[6]
    file_path = f'/static/audio_files/{filename_stem}.mp3'
    emit('play_audio_file', {'file_path': file_path}, broadcast=True)

@socketio.on('edit_translation')
def handle_edit_translation(data):
    lang = data['language']
    text = data['text']
    index = 1 if lang == 'italian' else 5
    current_line[index] = text
    emit('update_translation_live', {'language': lang, 'text': text}, broadcast=True, include_self=False)

@socketio.on('scratchpad_update')
def handle_scratchpad_update(data):
    emit('scratchpad_update', data, broadcast=True, include_self=False)


@socketio.on('scratchpad_erase')
def handle_scratchpad_erase():
    emit('scratchpad_update', data, broadcast=True, include_self=False)


@socketio.on('save_notes')
def handle_save_notes(text):
    notes_path = os.path.join(base_dir, 'notes.txt')
    with open(notes_path, 'a', encoding='utf-8') as notes_file:
        notes_file.write(text.strip() + '\n\n')

@socketio.on('connect')
def on_connect():
    handle_next_sentence()
    emit('toggle_state_sync', {'visible': translations_visible})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
