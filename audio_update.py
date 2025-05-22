import os
from gtts import gTTS
from datetime import datetime

DUB_LIST_PATH = 'dub_list.txt'
AUDIO_FOLDER = 'static/audio_files'
LOG_FILE_PATH = 'tts_log.txt'

# Mapping input languages to gTTS language codes
LANGUAGE_CODES = {
    'English': 'en',
    'Spanish': 'es',
    'Italian': 'it'
}

def read_lines(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def write_lines(filepath, lines):
    with open(filepath, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

def log_message(log_file, message):
    timestamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(timestamped)
    log_file.write(timestamped + '\n')

def generate_mp3(language, filename, text, log_file):
    lang_code = LANGUAGE_CODES.get(language)
    if not lang_code:
        log_message(log_file, f"Unsupported language: {language}")
        return False

    try:
        tts = gTTS(text=text, lang=lang_code)
        output_path = os.path.join(AUDIO_FOLDER, filename + '.mp3')
        tts.save(output_path)
        log_message(log_file, f"Created: {output_path}")
        return True
    except Exception as e:
        log_message(log_file, f"Error creating audio for '{filename}': {e}")
        return False

def main():
    lines = read_lines(DUB_LIST_PATH)
    remaining_lines = []

    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as log_file:
        log_message(log_file, "--- Starting TTS update session ---")
        for line in lines:
            try:
                language, filename, text = line.split('\t', 2)
            except ValueError:
                log_message(log_file, f"Skipping malformed line: {line}")
                continue

            success = generate_mp3(language, filename, text, log_file)
            if not success:
                remaining_lines.append(line)

        log_message(log_file, "--- Session complete ---\n")

    write_lines(DUB_LIST_PATH, remaining_lines)

if __name__ == '__main__':
    main()
