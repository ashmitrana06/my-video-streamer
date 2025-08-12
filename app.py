# app.py
import os
from flask import Flask, render_template, Response, request, send_from_directory, redirect, url_for, flash
import re # Make sure 're' is imported for regex operations
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Set a secret key for Flash messages (important for Flask apps)
app.config['SECRET_KEY'] = 'your_secret_key_here' # IMPORTANT: Change this to a strong, random key!

# Define the directory where video files are stored
VIDEO_DIR = 'videos'
# Define the directory where thumbnail files are stored
THUMBNAIL_STATIC_PATH = 'thumbnails' # This is the path Flask will serve from 'static/'
THUMBNAIL_FULL_DIR = os.path.join('static', THUMBNAIL_STATIC_PATH)

# Allowed video extensions for upload
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Create necessary directories if they don't exist
if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)
    print(f"Created video directory: {VIDEO_DIR}")
if not os.path.exists(THUMBNAIL_FULL_DIR):
    os.makedirs(THUMBNAIL_FULL_DIR)
    print(f"Created thumbnail directory: {THUMBNAIL_FULL_DIR}")

def allowed_file(filename):
    """Checks if a filename has an allowed video extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """
    Renders the main page with the video player, a list of available videos,
    and the upload form.
    """
    video_data = []
    # Get all video files (case-insensitive for common video extensions)
    video_files = [f for f in os.listdir(VIDEO_DIR) if os.path.isfile(os.path.join(VIDEO_DIR, f)) and f.lower().endswith(tuple(ALLOWED_EXTENSIONS))]

    if not video_files:
        print(f"DEBUG: No video files found in '{VIDEO_DIR}'.")
        # Render the template even if no videos, so user sees the "No videos" message
        return render_template('index.html', video_data=[])

    print(f"DEBUG: Found {len(video_files)} video(s) in '{VIDEO_DIR}'.")
    for video_file in video_files:
        # We assume a thumbnail exists with the same name as the video, but with .jpg extension
        thumbnail_base_name = os.path.splitext(video_file)[0] + '.jpg'
        
        # This is the URL path for the HTML to request the thumbnail from Flask's static folder
        thumbnail_url_for_html = os.path.join(THUMBNAIL_STATIC_PATH, thumbnail_base_name).replace('\\', '/') # Use '/' for web paths

        full_thumbnail_path_on_disk = os.path.join(THUMBNAIL_FULL_DIR, thumbnail_base_name)
        if not os.path.exists(full_thumbnail_path_on_disk):
            print(f"WARNING: Thumbnail expected at '{full_thumbnail_path_on_disk}' was NOT found. Using placeholder.")
            truncated_video_name = (video_file[:15] + '...') if len(video_file) > 15 else video_file
            thumbnail_url_for_html = f'https://placehold.co/160x90/D1D5DB/1F2937?text=No+Thumb-{truncated_video_name}'
        else:
            print(f"DEBUG: Thumbnail found for '{video_file}' at '{full_thumbnail_path_on_disk}'.")

        video_data.append({
            'filename': video_file,
            'thumbnail_url': thumbnail_url_for_html
        })
    
    print(f"DEBUG: Sending {len(video_data)} video entries to index.html template.")
    return render_template('index.html', video_data=video_data)

@app.route('/video_feed/<filename>')
def video_feed(filename):
    """
    Streams the video file in chunks.
    This function handles HTTP Range requests for seeking and partial content.
    """
    full_video_path_on_disk = os.path.join(VIDEO_DIR, filename)
    print(f"DEBUG: Attempting to serve video: '{filename}' from full path: '{full_video_path_on_disk}'")

    if not os.path.exists(full_video_path_on_disk):
        print(f"ERROR: Video file NOT FOUND on disk at '{full_video_path_on_disk}' (returned 404).")
        return "Video not found", 404

    # Get file size
    file_size = os.path.getsize(full_video_path_on_disk)
    range_header = request.headers.get('Range', None)
    print(f"DEBUG: Received Range header: '{range_header}' for file size {file_size} bytes.")

    if range_header:
        byte1, byte2 = 0, None
        m = re.match('bytes=(\d+)-(\d*)', range_header)
        if m:
            byte1 = int(m.group(1))
            if m.group(2):
                byte2 = int(m.group(2))

        length = file_size - byte1
        if byte2 is not None:
            length = byte2 - byte1 + 1

        print(f"DEBUG: Serving bytes {byte1}-{byte1 + length - 1}/{file_size} for '{filename}'.")
        with open(full_video_path_on_disk, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        rv = Response(data, 206, mimetype="video/mp4",
                      headers={'Content-Range': f'bytes {byte1}-{byte1 + len(data) - 1}/{file_size}',
                               'Accept-Ranges': 'bytes'})
        return rv
    else:
        print(f"DEBUG: Serving entire video: '{filename}'.")
        return send_from_directory(VIDEO_DIR, filename, mimetype="video/mp4")

@app.route('/upload_video', methods=['POST'])
def upload_video():
    """Handles video file uploads."""
    print("DEBUG: Received upload request.")
    if 'file' not in request.files:
        flash('No file part')
        print("ERROR: No file part in request.")
        return redirect(request.url) # Redirect back to the page if no file part
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        print("ERROR: No file selected for upload.")
        return redirect(request.url) # Redirect if no file was selected
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename) # Secure the filename to prevent malicious paths
        file_path = os.path.join(VIDEO_DIR, filename)
        file.save(file_path)
        print(f"DEBUG: File '{filename}' uploaded successfully to '{file_path}'.")
        
        # IMPORTANT: After upload, you'll want to generate a thumbnail for this new video.
        # This part is still manual or requires an external script execution.
        # For a fully automated solution, you'd integrate thumbnail generation here,
        # potentially in a background task for large videos.
        
        flash(f'Video "{filename}" uploaded successfully!')
        return redirect(url_for('index')) # Redirect back to the home page to refresh video list
    else:
        flash('Allowed video types are MP4, AVI, MOV, MKV, WEBM.')
        print(f"ERROR: Invalid file type uploaded: '{file.filename}'.")
        return redirect(request.url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

