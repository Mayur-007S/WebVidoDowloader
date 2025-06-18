import os
import logging
import json
import requests
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file, session
from video_downloader import VideoDownloader
from social_media_downloader import SocialMediaDownloader
import validators

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the app
app = Flask(__name__)
# Set a fixed secret key for development - in production, use environment variable
app.secret_key = "dev_secret_key_make_this_random_and_unique"

# Create downloader instances
video_downloader = VideoDownloader()
social_media_downloader = SocialMediaDownloader()

# Global download progress tracker
download_progress = {
    'status': 'idle',  # idle, downloading, completed, error
    'progress': 0,     # 0-100
    'file_size': 0,    # total file size in bytes
    'downloaded': 0,   # bytes downloaded so far
    'speed': 0,        # download speed in bytes/sec
    'filename': '',    # name of the file being downloaded
    'platform': ''     # source platform
}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/download', methods=['GET', 'POST'])
def download_video():
    """Handle video download request"""
    global download_progress
    
    # Get URL from either POST form data or GET query parameter
    if request.method == 'POST':
        url = request.form.get('url', '')
    else:
        url = request.args.get('url', '')
    
    # Initialize download progress
    download_progress = {
        'status': 'idle',
        'progress': 0,
        'file_size': 0,
        'downloaded': 0,
        'speed': 0,
        'filename': '',
        'platform': ''
    }
    
    # Basic validation
    if not url:
        flash('Please enter a URL', 'danger')
        return redirect(url_for('index'))
    
    # Validate URL format
    if not validators.url(url):
        flash('Invalid URL format', 'danger')
        return redirect(url_for('index'))
    
    # Specify download location (default to downloads folder)
    download_path = request.form.get('download_path', 'downloads')
    
    # Create the downloads directory if it doesn't exist
    os.makedirs(download_path, exist_ok=True)
    
    try:
        # Update initial progress status
        update_download_progress(status='checking')
        
        # Check if it's a social media URL
        is_social_media, platform = social_media_downloader.is_social_media_url(url)
        
        # Set platform in progress tracker
        if is_social_media:
            update_download_progress(platform=platform)
        
        # Choose the appropriate downloader based on URL type
        if is_social_media:
            logger.info(f"Using social media downloader for {platform}: {url}")
            download_info = social_media_downloader.download_video(url, download_path)
        else:
            logger.info(f"Using general video downloader for: {url}")
            download_info = video_downloader.download_video(url, download_path)
        
        if download_info['success']:
            # Update final progress status
            update_download_progress(
                status='completed',
                progress=100,
                file_size=download_info.get('file_size', 0),
                downloaded=download_info.get('file_size', 0),
                filename=os.path.basename(download_info['filepath'])
            )
            
            flash(f'Video downloaded successfully to {download_info["filepath"]}', 'success')
            # Return the downloaded file
            return send_file(download_info['filepath'], as_attachment=True)
        else:
            # If social media downloader failed, try the generic downloader as fallback
            if is_social_media and not download_info['success']:
                logger.info(f"Social media downloader failed, trying generic downloader as fallback")
                update_download_progress(status='retrying', progress=0)
                
                download_info = video_downloader.download_video(url, download_path)
                
                if download_info['success']:
                    # Update final progress status
                    update_download_progress(
                        status='completed',
                        progress=100,
                        file_size=download_info.get('file_size', 0),
                        downloaded=download_info.get('file_size', 0),
                        filename=os.path.basename(download_info['filepath'])
                    )
                    
                    flash(f'Video downloaded successfully to {download_info["filepath"]}', 'success')
                    return send_file(download_info['filepath'], as_attachment=True)
            
            # Set error status in progress tracker
            update_download_progress(
                status='error',
                progress=0
            )
            
            flash(f'Failed to download video: {download_info.get("error", "Unknown error")}', 'danger')
    except Exception as e:
        logger.exception("Exception during video download")
        # Set error status in progress tracker
        update_download_progress(
            status='error',
            progress=0
        )
        flash(f'An error occurred: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/check-url', methods=['POST'])
def check_url():
    """Check if a URL contains downloadable video content"""
    url = request.json.get('url', '')
    
    if not url or not validators.url(url):
        return jsonify({'valid': False, 'message': 'Invalid URL format'})
    
    # Check if it's a social media URL
    is_social_media, platform = social_media_downloader.is_social_media_url(url)
    
    if is_social_media:
        return jsonify({
            'valid': True, 
            'message': f'Detected {platform.capitalize()} video that can be downloaded'
        })
    else:
        # For non-social media URLs, use the regular checker
        result = video_downloader.check_url(url)
        return jsonify(result)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Internal server error'), 500

@app.route('/download-progress', methods=['GET'])
def get_download_progress():
    """Return the current download progress as JSON"""
    global download_progress
    
    # Calculate human-readable sizes
    human_readable = {
        'file_size': format_size(download_progress['file_size']),
        'downloaded': format_size(download_progress['downloaded']),
        'speed': format_size(download_progress['speed']) + '/s',
    }
    
    # Add the human-readable values to the response
    response = download_progress.copy()
    response.update({'human_readable': human_readable})
    
    return jsonify(response)

@app.route('/get-direct-url', methods=['POST'])
def get_direct_url():
    """Get the direct URL for the video to enable browser-side downloading"""
    url = request.json.get('url', '')
    
    if not url or not validators.url(url):
        return jsonify({
            'success': False,
            'error': 'Invalid URL format'
        })
    
    try:
        # Check if it's a social media URL
        is_social_media, platform = social_media_downloader.is_social_media_url(url)
        
        # For social media, we need to extract the direct video URL
        if is_social_media:
            # This will get the actual video URL without downloading
            direct_url = social_media_downloader.get_direct_video_url(url, platform)
            if direct_url:
                return jsonify({
                    'success': True,
                    'direct_url': direct_url,
                    'platform': platform
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f"Could not extract direct video URL from {platform}"
                })
        else:
            # For non-social media URLs, check if it's a direct video URL
            head_response = requests.head(url, headers=video_downloader.headers, timeout=video_downloader.timeout)
            content_type = head_response.headers.get('Content-Type', '')
            
            if any(f'video/{ext.lstrip(".")}' in content_type for ext in video_downloader.video_extensions):
                # It's already a direct video URL
                return jsonify({
                    'success': True,
                    'direct_url': url,
                    'platform': 'direct'
                })
            else:
                # It's a webpage, we need to extract the video URL
                response = requests.get(url, headers=video_downloader.headers, timeout=video_downloader.timeout)
                if response.status_code == 200:
                    video_url = video_downloader.extract_video_url(url, response.text)
                    if video_url:
                        return jsonify({
                            'success': True,
                            'direct_url': video_url,
                            'platform': 'webpage'
                        })
                
                return jsonify({
                    'success': False,
                    'error': "Could not extract video URL from webpage"
                })
                
    except Exception as e:
        logger.exception(f"Error getting direct URL: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error: {str(e)}"
        })

def format_size(size_bytes):
    """Format bytes to human-readable size"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names)-1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def update_download_progress(status=None, progress=None, file_size=None, 
                          downloaded=None, speed=None, filename=None, platform=None):
    """Update the global download progress tracker"""
    global download_progress
    
    if status is not None:
        download_progress['status'] = status
    if progress is not None:
        download_progress['progress'] = progress
    if file_size is not None:
        download_progress['file_size'] = file_size
    if downloaded is not None:
        download_progress['downloaded'] = downloaded
    if speed is not None:
        download_progress['speed'] = speed
    if filename is not None:
        download_progress['filename'] = filename
    if platform is not None:
        download_progress['platform'] = platform
    
    return download_progress
