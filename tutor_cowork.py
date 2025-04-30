from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

audio_folder = 'audio_files'
current_line = {}
lines = []

def load_lines():
    with open('master.txt', 'r', encoding='utf-8') as file:
        return [line.strip().split('\t') for line in file if line.strip()]

def select_random_line():
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
    elif lang == 'spanish':
        emit('update_translation', {'language': 'spanish', 'text': current_line[5]})

@socketio.on('save_translation')
def handle_save_translation(data):
    lang = data['language']
    new_text = data['text']
    index = 1 if lang == 'italian' else 5
    current_line[index] = new_text

    with open('master.txt', 'r', encoding='utf-8') as file:
        all_lines = file.readlines()

    for i, line in enumerate(all_lines):
        fields = line.strip().split('\t')
        if fields[0] == current_line[0]:
            fields[index] = new_text
            all_lines[i] = '\t'.join(fields) + '\n'
            break

    with open('master.txt', 'w', encoding='utf-8') as file:
        file.writelines(all_lines)

    emit('save_success', {'language': lang})

@socketio.on('play_audio')
def handle_play_audio(data):
    lang = data['language']
    filename_stem = current_line[2] if lang == 'italian' else current_line[6]
    file_path = f'/static/audio_files/{filename_stem}.mp3'
    emit('play_audio_file', {'file_path': file_path})  # 🔁 back to file_path

@socketio.on('next_sentence')
def handle_next_sentence():
    global current_line
    current_line = select_random_line()
    emit('new_sentence', {'english': current_line[0]}, broadcast=True)

if __name__ == '__main__':
    lines = load_lines()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
