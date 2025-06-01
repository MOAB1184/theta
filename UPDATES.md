# ThetaSummary Updates

We've updated the ThetaSummary application to add the following features:

## Enhanced Wasabi Integration

1. **Manual Processing Control**
   - Added "Start Processing" and "Stop Processing" buttons
   - The application no longer starts processing automatically
   - Processing can be explicitly started and stopped by the user

2. **Processing Log**
   - Added a processing log display showing:
     - Currently processing files
     - Completed files
   - The log updates automatically every 5 seconds while processing is active
   - The log can be manually refreshed using the refresh button

3. **Status Tracking**
   - Each file's processing status is tracked (processing, completed, failed)
   - Status information is preserved even if the application is restarted
   - Files that have already been processed won't be processed again

4. **Parallel Processing**
   - Added multi-threaded processing capability (processes 5 files simultaneously)
   - The system first scans Wasabi to find all unprocessed audio files
   - Then processes multiple files in parallel for much faster throughput
   - Progress statistics show count of in-progress, completed, and failed files

## Usage

1. Open the ThetaSummary web application
2. Update the summary prompt in the Settings (⚙️) if desired
3. Click "Start Processing" to begin scanning Wasabi for audio files
4. Monitor the processing log and statistics to see which files are being processed
5. Click "Stop Processing" when you're done

The application saves processing history to disk, so even if you stop the application and restart it later, it will remember which files have already been processed.

## Technical Details

- Processing log is saved in `processing_log.json`
- Processed files database is stored in `processed_files.json` 
- The scanner recursively searches through all Wasabi buckets and folders
- Summaries are saved in a "summaries" subfolder at the same path as the original audio file
- Uses a thread pool with 5 workers to process files in parallel (can be adjusted in wasabi_scanner.py) 