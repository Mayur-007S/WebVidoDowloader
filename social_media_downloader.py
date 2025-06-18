import os
import re
import logging
import tempfile
import shutil
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Import specialized downloader libraries
try:
    import pytube
except ImportError:
    pytube = None

try:
    import instaloader
except ImportError:
    instaloader = None

try:
    from yt_dlp import YoutubeDL
except ImportError:
    YoutubeDL = None


class SocialMediaDownloader:
    """
    A class to download videos from various social media platforms.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = tempfile.mkdtemp()
        
        # Check if required libraries are available
        self.has_pytube = pytube is not None
        self.has_instaloader = instaloader is not None
        self.has_yt_dlp = YoutubeDL is not None
        
        # Initialize instaloader if available
        if self.has_instaloader:
            self.insta = instaloader.Instaloader(
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                post_metadata_txt_pattern=''
            )
    
    def is_social_media_url(self, url):
        """
        Check if URL is from a supported social media platform.
        
        Args:
            url (str): The URL to check
            
        Returns:
            tuple: (is_supported, platform_name)
        """
        domain = urlparse(url).netloc.lower()
        
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return True, 'youtube'
        elif 'instagram.com' in domain:
            return True, 'instagram'
        elif 'twitter.com' in domain or 'x.com' in domain:
            return True, 'twitter'
        elif 'facebook.com' in domain or 'fb.com' in domain:
            return True, 'facebook'
        elif 'tiktok.com' in domain:
            return True, 'tiktok'
        elif 'reddit.com' in domain:
            return True, 'reddit'
        elif 'linkedin.com' in domain:
            return True, 'linkedin'
        elif 'vimeo.com' in domain:
            return True, 'vimeo'
        elif 'dailymotion.com' in domain:
            return True, 'dailymotion'
        elif 'twitch.tv' in domain:
            return True, 'twitch'
            
        return False, None
    
    def download_video(self, url, download_path='downloads'):
        """
        Download a video from a social media platform.
        
        Args:
            url (str): The URL of the social media post containing a video
            download_path (str): The path to save the downloaded video
            
        Returns:
            dict: Information about the download including success status
        """
        # Create the download directory if it doesn't exist
        os.makedirs(download_path, exist_ok=True)
        
        # Check if URL is from a supported platform
        is_supported, platform = self.is_social_media_url(url)
        
        if not is_supported:
            self.logger.warning(f"URL {url} is not from a supported social media platform")
            return {
                'success': False, 
                'error': 'URL is not from a supported social media platform'
            }
        
        self.logger.info(f"Detected social media platform: {platform}")
        
        # Call the appropriate platform-specific downloader
        try:
            if platform == 'youtube':
                return self._download_youtube(url, download_path)
            elif platform == 'instagram':
                return self._download_instagram(url, download_path)
            elif platform in ['twitter', 'x']:
                return self._download_twitter(url, download_path)
            else:
                # Use yt-dlp for other platforms - it supports many sites
                return self._download_with_yt_dlp(url, download_path, platform)
                
        except Exception as e:
            self.logger.exception(f"Error downloading from {platform}: {str(e)}")
            return {
                'success': False,
                'error': f"Error downloading from {platform}: {str(e)}"
            }
    
    def _download_youtube(self, url, download_path):
        """Download a video from YouTube."""
        # Try first with pytube
        if self.has_pytube:
            try:
                self.logger.info(f"Downloading YouTube video with pytube: {url}")
                yt = pytube.YouTube(url)
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                
                if not stream:
                    # Try getting any video stream if progressive not available
                    stream = yt.streams.filter(file_extension='mp4').order_by('resolution').desc().first()
                
                if stream:
                    # Generate a unique filename
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    filename = f"youtube_{timestamp}.mp4"
                    filepath = os.path.join(download_path, filename)
                    
                    # Download the video
                    stream.download(output_path=download_path, filename=filename)
                    
                    return {
                        'success': True,
                        'filepath': filepath,
                        'original_url': url,
                        'title': yt.title,
                        'channel': yt.author,
                        'file_size': os.path.getsize(filepath)
                    }
            except Exception as e:
                self.logger.warning(f"Pytube failed, trying yt-dlp: {str(e)}")
                
        # Fall back to yt-dlp
        return self._download_with_yt_dlp(url, download_path, 'youtube')
    
    def _download_instagram(self, url, download_path):
        """Download a video from Instagram."""
        if not self.has_instaloader:
            self.logger.warning("Instaloader not available, falling back to yt-dlp")
            return self._download_with_yt_dlp(url, download_path, 'instagram')
        
        try:
            self.logger.info(f"Downloading Instagram video with instaloader: {url}")
            
            # Extract shortcode from URL
            shortcode = None
            if '/p/' in url:
                shortcode = url.split('/p/')[1].split('/')[0]
            elif '/reel/' in url:
                shortcode = url.split('/reel/')[1].split('/')[0]
                
            if not shortcode:
                raise ValueError("Could not extract Instagram post shortcode from URL")
                
            self.logger.info(f"Extracted Instagram shortcode: {shortcode}")
            
            # Create a temporary directory for downloading
            temp_download_dir = os.path.join(self.temp_dir, shortcode)
            os.makedirs(temp_download_dir, exist_ok=True)
            
            # Get the post and download it
            post = instaloader.Post.from_shortcode(self.insta.context, shortcode)
            
            if not post.is_video:
                raise ValueError("Instagram post does not contain a video")
                
            # Download video to temp directory
            self.insta.download_post(post, temp_download_dir)
            
            # Find the downloaded video file (should be the only .mp4 file)
            video_files = [f for f in os.listdir(temp_download_dir) if f.endswith('.mp4')]
            
            if not video_files:
                raise FileNotFoundError("Downloaded video file not found")
                
            # Generate a unique filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"instagram_{timestamp}.mp4"
            final_path = os.path.join(download_path, filename)
            
            # Move the file to the target directory
            shutil.copy2(os.path.join(temp_download_dir, video_files[0]), final_path)
            
            # Clean up temp files
            shutil.rmtree(temp_download_dir)
            
            return {
                'success': True,
                'filepath': final_path,
                'original_url': url,
                'title': post.caption if post.caption else "Instagram Video",
                'file_size': os.path.getsize(final_path)
            }
            
        except Exception as e:
            self.logger.warning(f"Instaloader failed, trying yt-dlp: {str(e)}")
            return self._download_with_yt_dlp(url, download_path, 'instagram')
    
    def _download_twitter(self, url, download_path):
        """Download a video from Twitter/X."""
        # Twitter API requires auth, so we'll use yt-dlp directly
        return self._download_with_yt_dlp(url, download_path, 'twitter')
    
    def get_direct_video_url(self, url, platform):
        """
        Extract the direct video URL without downloading it.
        
        Args:
            url (str): The URL of the social media post
            platform (str): The platform name (youtube, instagram, etc.)
            
        Returns:
            str or None: The direct video URL if found, None otherwise
        """
        if not self.has_yt_dlp:
            self.logger.error("yt-dlp not available for URL extraction")
            return None
        
        self.logger.info(f"Extracting direct URL from {platform}: {url}")
        
        try:
            # Try platform-specific extraction for YouTube first if pytube is available
            if platform == 'youtube' and self.has_pytube:
                try:
                    self.logger.info(f"Attempting to extract YouTube URL with pytube: {url}")
                    yt = pytube.YouTube(url)
                    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                    
                    if stream and stream.url:
                        self.logger.info(f"Successfully extracted YouTube URL with pytube")
                        return stream.url
                except Exception as pytube_err:
                    self.logger.warning(f"Failed to extract with pytube: {str(pytube_err)}")
            
            # Configure yt-dlp options for URL extraction only
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'nocheckcertificate': True,
                'skip_download': True,  # Skip download, just get the info
                'geo_bypass': True,     # Try to bypass geo restrictions
                'cookiefile': None,     # Don't use cookies
                'socket_timeout': 10,   # 10 seconds timeout
                'retries': 3            # Retry 3 times
            }
            
            self.logger.info(f"Extracting URL with yt-dlp for {platform}")
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Check if we have direct URL info
                if info.get('url'):
                    self.logger.info(f"Found direct URL in info['url']")
                    return info['url']
                elif info.get('requested_formats') and len(info['requested_formats']) > 0:
                    # Get the best format
                    best_url = info['requested_formats'][0]['url']
                    self.logger.info(f"Found URL in requested_formats")
                    return best_url
                elif info.get('formats') and len(info['formats']) > 0:
                    # Find the best video format (giving preference to formats with both audio and video)
                    best_format = None
                    max_width = 0
                    
                    # First try to get formats with both audio and video
                    for fmt in info['formats']:
                        if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                            width = fmt.get('width', 0)
                            if width > max_width:
                                max_width = width
                                best_format = fmt
                    
                    # If no combined format found, just get the best video format
                    if not best_format:
                        for fmt in info['formats']:
                            if fmt.get('vcodec') != 'none':
                                width = fmt.get('width', 0)
                                if width > max_width:
                                    max_width = width
                                    best_format = fmt
                    
                    if best_format and best_format.get('url'):
                        self.logger.info(f"Found best format with width {max_width}")
                        return best_format['url']
            
            self.logger.warning(f"Could not extract direct URL from {platform}")
            return None
            
        except Exception as e:
            self.logger.exception(f"Error extracting direct URL from {platform}: {str(e)}")
            # Print full traceback for debugging
            import traceback
            traceback.print_exc()
            return None

    def _download_with_yt_dlp(self, url, download_path, platform):
        """Use yt-dlp to download videos from various platforms."""
        from app import update_download_progress
        import time
        
        if not self.has_yt_dlp:
            self.logger.error("yt-dlp not available")
            return {
                'success': False,
                'error': "yt-dlp library not available"
            }
            
        self.logger.info(f"Downloading {platform} video with yt-dlp: {url}")
        
        # Generate a unique filename
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{platform}_{timestamp}.%(ext)s"
        filepath_template = os.path.join(download_path, filename)
        
        # Initialize download progress tracking
        update_download_progress(
            status='downloading',
            progress=0,
            file_size=0,
            downloaded=0,
            speed=0,
            filename=f"{platform}_{timestamp}",
            platform=platform
        )
        
        # Start time for speed calculation
        start_time = time.time()
        
        # Custom progress hook to update download progress
        def yt_dlp_progress_hook(d):
            if d['status'] == 'downloading':
                # Get file size if available
                if d.get('total_bytes'):
                    total_bytes = d['total_bytes']
                    update_download_progress(file_size=total_bytes)
                elif d.get('total_bytes_estimate'):
                    total_bytes = d['total_bytes_estimate']
                    update_download_progress(file_size=total_bytes)
                
                # Get downloaded bytes and calculate progress
                if d.get('downloaded_bytes'):
                    downloaded_bytes = d['downloaded_bytes']
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    
                    # Calculate progress percentage
                    if total > 0:
                        progress = min(downloaded_bytes / total * 100, 99.9)
                    else:
                        progress = 0
                    
                    # Calculate speed
                    elapsed = time.time() - start_time
                    speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                    
                    # Update the progress tracker
                    update_download_progress(
                        progress=progress,
                        downloaded=downloaded_bytes,
                        speed=speed
                    )
            
            elif d['status'] == 'finished':
                # Download is complete
                update_download_progress(
                    status='processing',
                    progress=99.9  # Allow room for post-processing
                )
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Prefer MP4 if available
            'outtmpl': filepath_template,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'nooverwrites': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'prefer_ffmpeg': True,
            'progress_hooks': [yt_dlp_progress_hook],
        }
        
        try:
            # Download the video
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                
                # Some videos may have a different extension than mp4
                if not os.path.exists(downloaded_file):
                    possible_files = [
                        os.path.join(download_path, f) 
                        for f in os.listdir(download_path) 
                        if f.startswith(f"{platform}_{timestamp}")
                    ]
                    if possible_files:
                        downloaded_file = possible_files[0]
                
                # Final update to mark as complete
                filesize = os.path.getsize(downloaded_file)
                update_download_progress(
                    status='completed',
                    progress=100,
                    file_size=filesize,
                    downloaded=filesize,
                    filename=os.path.basename(downloaded_file)
                )
                
                return {
                    'success': True,
                    'filepath': downloaded_file,
                    'original_url': url,
                    'title': info.get('title', f"{platform.capitalize()} Video"),
                    'uploader': info.get('uploader', 'Unknown'),
                    'file_size': filesize
                }
                
        except Exception as e:
            self.logger.exception(f"Error using yt-dlp for {platform}: {str(e)}")
            return {
                'success': False,
                'error': f"Error downloading from {platform}: {str(e)}"
            }
    
    def cleanup(self):
        """Clean up temporary files."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            self.logger.warning(f"Error cleaning up temporary files: {str(e)}")