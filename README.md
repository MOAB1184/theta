# ThetaSummary Transcriber

A tool for automatically generating transcripts and summaries from audio files. This application can scan Wasabi cloud storage for audio files, transcribe them, and generate summaries automatically.

## Features

- Upload audio files through the web interface for transcription and summarization
- Automatically scan Wasabi cloud storage for new audio files
- Process multiple files in parallel for maximum efficiency (up to 50 concurrent files)
- Generate transcripts using Google's Gemini AI
- Create summaries using Deepseek's AI model
- Maintain a database of processed files to avoid duplicates
- Save summaries back to Wasabi in the appropriate directory structure

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python app.py
   ```

3. Access the web interface at http://localhost:5000

## How It Works

The application has two main modes:

1. **Manual Mode**: Upload audio files through the web interface
2. **High-Throughput Automatic Mode**: Scan Wasabi storage and process files in parallel

### Automatic Processing

When you click "Start Processing":

1. The app scans Wasabi storage looking recursively through all folders for audio files
2. When it finds unprocessed audio files, it:
   - Processes up to 50 files simultaneously (configurable)
   - Downloads each file
   - Transcribes it using Gemini AI
   - Summarizes the transcript using Deepseek AI 
   - Saves the summary back to Wasabi in a "summaries" folder at the same path
   - Marks the file as processed in the local database

### High-Performance Processing

The application has been optimized for high-throughput processing:

- Processes up to 50 files simultaneously (configurable)
- Loads up to 200 files at once in each processing batch
- Uses efficient thread pooling to maximize resource utilization
- Provides real-time status tracking of each file

### Settings

You can configure:

- The summary prompt used for generating summaries (supports complex prompts)
- Start and stop processing with dedicated control buttons

## Files

- `app.py`: Main application file
- `wasabi_scanner.py`: Logic for scanning and interacting with Wasabi storage
- `settings.json`: Configuration settings
- `processed_files.json`: Database of processed files (created automatically)
- `processing_log.json`: Log of processing activity (created automatically)

## Wasabi Integration

The application automatically uses the path structure in Wasabi for organization. When a file is found at `bucket/folder1/folder2/audio.mp3`, the summary will be saved at `bucket/folder1/folder2/summaries/audio_summary.txt`.

## Notes

- The application stores a local database of processed files in `processed_files.json`
- A log of processing activity is maintained in `processing_log.json`
- If you stop the application, it will remember which files it has already processed
- You can control processing through the web interface with Start/Stop buttons 