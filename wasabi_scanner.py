import os
import time
import json
import threading
import boto3
from botocore.config import Config
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import tempfile

# Wasabi configuration
WASABI_ACCESS_KEY = "W7X9U7PACFCWQZHRJBRH"
WASABI_SECRET_KEY = "Xc3tkWt1W0tGSMhEN3w6WTPJNsOlWYuhtirgV9Dc"
WASABI_ENDPOINT = "https://s3.us-west-1.wasabisys.com"  # Adjust this based on your region

# File to store the processed files and their status
PROCESSED_FILES_DB = "processed_files.json"
LOG_FILE = "processing_log.json"

# Number of parallel worker threads for processing files
# Since we can handle up to 4000 requests per minute, 
# we'll use a much higher concurrency while staying under that limit
MAX_WORKERS = 50  # Process 50 files concurrently

# Maximum batch size when processing files
MAX_BATCH_SIZE = 200

# Retry parameters for failed API requests
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds between retries

class WasabiScanner:
    def __init__(self):
        # Configure S3 client for Wasabi
        self.s3 = boto3.client(
            's3',
            endpoint_url=WASABI_ENDPOINT,
            aws_access_key_id=WASABI_ACCESS_KEY,
            aws_secret_access_key=WASABI_SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
        
        # Load processed files from disk
        self.processed_files = self._load_processed_files()
        
        # Initialize processing log
        self.processing_log = self._load_processing_log()
        
        # Flag to control the scan thread
        self.keep_running = False
        self.scan_thread = None
        self.is_scanning = False
        
        # Thread pool for processing files in parallel
        self.thread_pool = None
        
        # Lock for thread-safe operations
        self.log_lock = threading.Lock()
        self.processed_files_lock = threading.Lock()
    
    def _load_processed_files(self):
        """Load the database of processed files from disk"""
        if os.path.exists(PROCESSED_FILES_DB):
            try:
                with open(PROCESSED_FILES_DB, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_processed_files(self):
        """Save the current state of processed files to disk"""
        with open(PROCESSED_FILES_DB, 'w') as f:
            json.dump(self.processed_files, f)
    
    def _load_processing_log(self):
        """Load the processing log from disk"""
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"current": [], "completed": []}
        return {"current": [], "completed": []}
    
    def _save_processing_log(self):
        """Save the processing log to disk"""
        with open(LOG_FILE, 'w') as f:
            json.dump(self.processing_log, f)
    
    def add_to_processing_log(self, file_info, status="processing", error_msg=None):
        """Add a file to the processing log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            "bucket": file_info["bucket"],
            "key": file_info["key"],
            "path": file_info["path"],
            "timestamp": timestamp,
            "status": status
        }
        
        # Add error message if provided
        if error_msg:
            log_entry["error"] = error_msg
        
        # Use a lock to avoid race conditions when updating the log
        with self.log_lock:
            # If file is being processed, add to current list
            if status == "processing":
                # Check if already in current list
                for i, entry in enumerate(self.processing_log["current"]):
                    if entry["path"] == file_info["path"]:
                        # Update the entry
                        self.processing_log["current"][i] = log_entry
                        self._save_processing_log()
                        return
                
                # Add to current list
                self.processing_log["current"].append(log_entry)
            
            # If file is completed, move from current to completed list
            elif status == "completed":
                # Find entry in current list
                current_entry = None
                for i, entry in enumerate(self.processing_log["current"]):
                    if entry["path"] == file_info["path"]:
                        current_entry = entry
                        break
                
                # Copy any upload_locations from current entry
                if current_entry and "upload_locations" in current_entry:
                    log_entry["upload_locations"] = current_entry["upload_locations"]
                
                # Remove from current list
                self.processing_log["current"] = [
                    entry for entry in self.processing_log["current"] 
                    if entry["path"] != file_info["path"]
                ]
                
                # Add to completed list (limit to most recent 100)
                self.processing_log["completed"].insert(0, log_entry)
                self.processing_log["completed"] = self.processing_log["completed"][:100]
            
            # If file failed, mark as failed but keep in current list for reference
            elif status == "failed":
                for i, entry in enumerate(self.processing_log["current"]):
                    if entry["path"] == file_info["path"]:
                        # Update the entry
                        self.processing_log["current"][i]["status"] = "failed"
                        if error_msg:
                            self.processing_log["current"][i]["error"] = error_msg
                        self._save_processing_log()
                        return
                
                # If not found in current list, add it
                self.processing_log["current"].append(log_entry)
            
            self._save_processing_log()
    
    def update_upload_locations(self, bucket, key, upload_locations):
        """Update upload locations in the processing log for a file"""
        file_path = f"{bucket}/{key}"
        
        with self.log_lock:
            # First check current processing list
            for i, entry in enumerate(self.processing_log["current"]):
                if entry["path"] == file_path:
                    self.processing_log["current"][i]["upload_locations"] = upload_locations
                    self._save_processing_log()
                    return
            
            # Also check completed list, in case it moved there during processing
            for i, entry in enumerate(self.processing_log["completed"]):
                if entry["path"] == file_path:
                    self.processing_log["completed"][i]["upload_locations"] = upload_locations
                    self._save_processing_log()
                    return
    
    def get_processing_log(self):
        """Get the current processing log"""
        with self.log_lock:
            return self.processing_log
    
    def clear_current_processing(self):
        """Clear the current processing list"""
        with self.log_lock:
            self.processing_log["current"] = []
            self._save_processing_log()
    
    def is_audio_file(self, key):
        """Check if a file is an audio file based on extension"""
        audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
        return any(key.lower().endswith(ext) for ext in audio_extensions)
    
    def mark_as_transcribed(self, bucket, key):
        """Mark a file as transcribed"""
        with self.processed_files_lock:
            if bucket not in self.processed_files:
                self.processed_files[bucket] = {}
            
            self.processed_files[bucket][key] = {"transcribed": True, "summarized": False}
            self._save_processed_files()
    
    def mark_as_summarized(self, bucket, key):
        """Mark a file as summarized"""
        with self.processed_files_lock:
            if bucket in self.processed_files and key in self.processed_files[bucket]:
                self.processed_files[bucket][key]["summarized"] = True
                self._save_processed_files()
    
    def get_unprocessed_files(self):
        """Scan Wasabi and get a list of all unprocessed audio files"""
        pending = []
        
        try:
            # List all buckets
            buckets = self.s3.list_buckets()
            
            for bucket in buckets['Buckets']:
                bucket_name = bucket['Name']
                
                # Initialize this bucket in our processed files if it doesn't exist
                with self.processed_files_lock:
                    if bucket_name not in self.processed_files:
                        self.processed_files[bucket_name] = {}
                
                # Process this bucket recursively
                self._scan_bucket_recursively(bucket_name, "", pending)
                
                # If we've found MAX_BATCH_SIZE files, stop scanning more
                if len(pending) >= MAX_BATCH_SIZE:
                    print(f"Reached maximum batch size of {MAX_BATCH_SIZE} files, stopping scan")
                    break
                
            print(f"Found {len(pending)} unprocessed audio files")
            
        except Exception as e:
            print(f"Error scanning Wasabi: {str(e)}")
        
        # Save the processed files database after scanning
        with self.processed_files_lock:
            self._save_processed_files()
        
        return pending
    
    def _scan_bucket_recursively(self, bucket, prefix, pending):
        """Recursively scan a bucket for audio files"""
        try:
            # Stop scanning if we've reached MAX_BATCH_SIZE
            if len(pending) >= MAX_BATCH_SIZE:
                return
            
            # List objects in the current prefix
            paginator = self.s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/')
            
            # Check each object
            for page in pages:
                # Process files in current directory
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        
                        # Skip if not an audio file
                        if not self.is_audio_file(key):
                            continue
                            
                        # Check if we need to process this file
                        with self.processed_files_lock:
                            # Skip files that are already in the current processing list
                            already_processing = False
                            with self.log_lock:
                                for entry in self.processing_log["current"]:
                                    if entry["bucket"] == bucket and entry["key"] == key:
                                        already_processing = True
                                        break
                            
                            if already_processing:
                                continue
                            
                            if key not in self.processed_files[bucket] or (
                                not self.processed_files[bucket][key].get("transcribed", False)
                            ):
                                pending.append({
                                    "bucket": bucket,
                                    "key": key,
                                    "path": f"{bucket}/{key}"
                                })
                                
                                # Stop scanning if we've reached MAX_BATCH_SIZE
                                if len(pending) >= MAX_BATCH_SIZE:
                                    return
                
                # Recursively process subdirectories
                if 'CommonPrefixes' in page:
                    for prefix_obj in page['CommonPrefixes']:
                        subdir_prefix = prefix_obj['Prefix']
                        self._scan_bucket_recursively(bucket, subdir_prefix, pending)
                        
                        # Stop scanning if we've reached MAX_BATCH_SIZE
                        if len(pending) >= MAX_BATCH_SIZE:
                            return
        
        except Exception as e:
            print(f"Error scanning prefix {prefix} in bucket {bucket}: {str(e)}")
    
    def download_file(self, bucket, key, local_path):
        """Download a file from Wasabi to a local path"""
        try:
            self.s3.download_file(bucket, key, local_path)
            return True
        except Exception as e:
            print(f"Error downloading file {bucket}/{key}: {str(e)}")
            return False
    
    def upload_summary(self, bucket, key, content):
        """Upload a summary file to Wasabi"""
        try:
            # Determine the path for the summary
            dir_path = os.path.dirname(key)
            summary_dir = os.path.join(dir_path, "summaries")
            filename = os.path.basename(key)
            summary_key = os.path.join(summary_dir, filename.rsplit(".", 1)[0] + "_summary.txt")
            
            # Create a temporary file to upload from
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
                f.write(content)
                temp_path = f.name
            
            # Upload the file
            try:
                # First, try to create the summaries folder if it doesn't exist
                try:
                    self.s3.put_object(Bucket=bucket, Key=summary_dir + "/")
                except Exception:
                    # Ignore errors, the folder might already exist
                    pass
                
                # Upload the summary file
                self.s3.upload_file(temp_path, bucket, summary_key)
                return summary_key
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception as e:
            print(f"Error uploading summary for {bucket}/{key}: {str(e)}")
            return None
    
    def upload_transcript(self, bucket, key, content):
        """Upload a transcript file to Wasabi"""
        try:
            # Determine the path for the transcript
            dir_path = os.path.dirname(key)
            transcript_dir = os.path.join(dir_path, "transcripts")
            filename = os.path.basename(key)
            transcript_key = os.path.join(transcript_dir, filename.rsplit(".", 1)[0] + "_transcript.txt")
            
            # Create a temporary file to upload from
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
                f.write(content)
                temp_path = f.name
            
            # Upload the file
            try:
                # First, try to create the transcripts folder if it doesn't exist
                try:
                    self.s3.put_object(Bucket=bucket, Key=transcript_dir + "/")
                except Exception:
                    # Ignore errors, the folder might already exist
                    pass
                
                # Upload the transcript file
                self.s3.upload_file(temp_path, bucket, transcript_key)
                return transcript_key
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception as e:
            print(f"Error uploading transcript for {bucket}/{key}: {str(e)}")
            return None

    def process_file_worker(self, file_info, callback):
        """Worker function that processes a single file"""
        retry_count = 0
        while retry_count <= MAX_RETRIES:
            try:
                # Add to processing log (only on first attempt)
                if retry_count == 0:
                    self.add_to_processing_log(file_info, "processing")
                elif retry_count > 0:
                    self.add_to_processing_log(file_info, "retrying", f"Retry {retry_count}/{MAX_RETRIES}")
                
                # Process the file
                callback(file_info)
                
                # Mark as completed in log
                self.add_to_processing_log(file_info, "completed")
                return
            except Exception as e:
                error_msg = str(e)
                retry_count += 1
                
                # Check if error is retryable
                retryable_errors = [
                    "Server disconnected",
                    "timeout",
                    "connection error",
                    "rate limit"
                ]
                
                is_retryable = any(err in error_msg.lower() for err in retryable_errors)
                
                if is_retryable and retry_count <= MAX_RETRIES:
                    print(f"Retryable error for {file_info['path']}: {error_msg}")
                    print(f"Retry {retry_count}/{MAX_RETRIES} in {RETRY_DELAY} seconds...")
                    self.add_to_processing_log(file_info, "retrying", f"Retry {retry_count}/{MAX_RETRIES}: {error_msg}")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"Error processing {file_info['path']}: {error_msg}")
                    # Mark as failed in log with error message
                    self.add_to_processing_log(file_info, "failed", error_msg)
                    raise

    def start_scanning(self, callback):
        """Start processing files in parallel"""
        if self.is_scanning:
            return False  # Already running
        
        # Start the processing thread with high concurrency
        self.keep_running = True
        self.thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self.scan_thread = threading.Thread(target=self._scan_and_process, args=(callback,), daemon=True)
        self.scan_thread.start()
        
        return True
    
    def _scan_and_process(self, callback):
        """Internal method that scans and processes files in parallel"""
        self.is_scanning = True
        
        try:
            while self.keep_running:
                # First, get all unprocessed files (up to MAX_BATCH_SIZE)
                pending_files = self.get_unprocessed_files()
                
                if not pending_files:
                    print("No files to process, waiting before next scan...")
                    # Wait before next scan if no files were found
                    for _ in range(60):  # Check every minute, but can interrupt
                        if not self.keep_running:
                            break
                        time.sleep(1)
                    continue
                
                print(f"Submitting {len(pending_files)} files for parallel processing")
                
                # Process files in parallel - submit all at once to maximize throughput
                futures = []
                for file_info in pending_files:
                    if not self.keep_running:
                        break
                    
                    # Submit file for processing in thread pool
                    future = self.thread_pool.submit(
                        self.process_file_worker, file_info, callback
                    )
                    futures.append(future)
                
                # Wait for all submissions to complete before next scan
                for future in futures:
                    if not self.keep_running:
                        break
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error in worker thread: {str(e)}")
                
                # If we've processed less than MAX_BATCH_SIZE files, wait before next scan
                if len(pending_files) < MAX_BATCH_SIZE:
                    print(f"Processed {len(pending_files)} files, waiting before next scan...")
                    for _ in range(60):  # Check every minute, but can interrupt
                        if not self.keep_running:
                            break
                        time.sleep(1)
        
        except Exception as e:
            print(f"Error in scanning thread: {str(e)}")
        
        # Clean up
        self.is_scanning = False
    
    def stop_scanning(self):
        """Stop the scanning thread and shutdown the thread pool"""
        self.keep_running = False
        
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5)
        
        # Shutdown the thread pool
        if self.thread_pool:
            self.thread_pool.shutdown(wait=False)
            self.thread_pool = None
            
        self.scan_thread = None
        self.is_scanning = False
        
        # Clear current processing list
        self.clear_current_processing()
        
        return True
    
    def get_scanning_status(self):
        """Get the current scanning status"""
        return self.is_scanning 