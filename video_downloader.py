import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import urllib.parse
import json
from datetime import datetime

class VideoDownloader:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Common video file extensions
        self.video_extensions = ['.mp4', '.avi', '.mov', '.flv', '.wmv', '.mkv', '.webm', '.m4v', '.mpeg', '.3gp']
        # Default headers to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
        }
        # Maximum number of retries for HTTP requests
        self.max_retries = 3
        # Timeout in seconds for HTTP requests
        self.timeout = 30
        # Session to maintain cookies across requests
        self.session = requests.Session()

    def check_url(self, url):
        """
        Check if a URL contains downloadable video content
        
        Args:
            url (str): The URL to check
            
        Returns:
            dict: Result containing valid status and message
        """
        try:
            # Send a HEAD request first to check content type and save bandwidth
            head_response = requests.head(url, headers=self.headers, timeout=self.timeout)
            content_type = head_response.headers.get('Content-Type', '')
            
            # Direct video file
            if any(f'video/{ext.lstrip(".")}' in content_type for ext in self.video_extensions):
                return {'valid': True, 'message': 'Direct video link detected'}
                
            # If not a direct video file, make a GET request to analyze the page
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code != 200:
                return {'valid': False, 'message': f'Failed to access the URL (Status code: {response.status_code})'}
                
            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for video tags
            video_tags = soup.find_all('video')
            if video_tags:
                return {'valid': True, 'message': f'Found {len(video_tags)} video elements on the page'}
                
            # Check for source tags
            source_tags = soup.find_all('source')
            video_sources = [s for s in source_tags if s.get('type', '').startswith('video/')]
            if video_sources:
                return {'valid': True, 'message': f'Found {len(video_sources)} video sources on the page'}
                
            # Check for iframe embeds (like YouTube, Vimeo, etc.)
            iframes = soup.find_all('iframe')
            video_platforms = ['youtube.com', 'vimeo.com', 'dailymotion.com', 'twitch.tv']
            video_iframes = [i for i in iframes if any(platform in i.get('src', '') for platform in video_platforms)]
            if video_iframes:
                return {'valid': True, 'message': f'Found {len(video_iframes)} embedded video players'}
                
            # Look for video URLs in the page source
            video_urls = []
            for ext in self.video_extensions:
                pattern = f'https?://[^\\s/$.?#].[^\\s]*\\{ext}'
                matches = re.findall(pattern, response.text)
                video_urls.extend(matches)
                
            if video_urls:
                return {'valid': True, 'message': f'Found {len(video_urls)} video URLs in page source'}
                
            # Check for common JavaScript video players
            video_players = ['videojs', 'jwplayer', 'flowplayer', 'mediaelement', 'plyr']
            for player in video_players:
                if player in response.text.lower():
                    return {'valid': True, 'message': f'Found {player} video player on the page'}
            
            # If we made it here, we couldn't find any obvious video content
            return {'valid': False, 'message': 'No obvious video content detected on this page'}
            
        except Exception as e:
            self.logger.exception(f"Error checking URL: {url}")
            return {'valid': False, 'message': f'Error checking URL: {str(e)}'}

    def extract_video_url(self, page_url, page_content):
        """
        Extract the video URL from a page's HTML content
        
        Args:
            page_url (str): The URL of the page
            page_content (str): The HTML content of the page
            
        Returns:
            str or None: The video URL if found, None otherwise
        """
        try:
            soup = BeautifulSoup(page_content, 'html.parser')
            video_url = None
            
            # Strategy 1: Check for video tags with src attribute
            for video_tag in soup.find_all('video'):
                if video_tag.get('src'):
                    video_url = video_tag['src']
                    self.logger.info(f"Found video tag with src: {video_url}")
                    return self._ensure_absolute_url(video_url, page_url)
                
                # Check for source tags inside video tags
                for source in video_tag.find_all('source'):
                    if source.get('src'):
                        video_url = source['src']
                        self.logger.info(f"Found source tag inside video: {video_url}")
                        return self._ensure_absolute_url(video_url, page_url)
            
            # Strategy 2: Check for standalone source tags
            for source in soup.find_all('source'):
                if source.get('src'):
                    video_url = source['src']
                    self.logger.info(f"Found standalone source tag: {video_url}")
                    return self._ensure_absolute_url(video_url, page_url)
            
            # Strategy 3: Check for video URLs in the page source
            for ext in self.video_extensions:
                pattern = f'https?://[^\\s/$.?#].[^\\s]*\\{ext}'
                matches = re.findall(pattern, page_content)
                if matches:
                    video_url = matches[0]  # Return the first match
                    self.logger.info(f"Found video URL in page source: {video_url}")
                    return video_url
            
            # Strategy 4: Look for data attributes which might contain video info
            video_attrs = ['data-src', 'data-source', 'data-video']
            for tag in soup.find_all():
                for attr in video_attrs:
                    if tag.has_attr(attr):
                        video_url = tag[attr]
                        self.logger.info(f"Found video in data attribute {attr}: {video_url}")
                        return self._ensure_absolute_url(video_url, page_url)
            
            # Strategy 5: Check for iframe embeds (YouTube, Vimeo)
            for iframe in soup.find_all('iframe'):
                src = iframe.get('src')
                if src:
                    # Check for YouTube
                    if 'youtube.com/embed/' in src:
                        video_id = src.split('/')[-1].split('?')[0]
                        self.logger.info(f"YouTube video detected, ID: {video_id}")
                        return f"https://www.youtube.com/watch?v={video_id}"
                    
                    # Check for Vimeo
                    elif 'vimeo.com' in src:
                        video_id = src.split('/')[-1].split('?')[0]
                        self.logger.info(f"Vimeo video detected, ID: {video_id}")
                        return f"https://vimeo.com/{video_id}"
            
            # If all strategies fail, return None
            self.logger.warning("Could not extract video URL using any strategy")
            return None
            
        except Exception as e:
            self.logger.exception(f"Error extracting video URL: {str(e)}")
            return None

    def _ensure_absolute_url(self, url, base_url):
        """Convert relative URLs to absolute URLs"""
        if url.startswith('//'):  # Protocol-relative URL
            return 'https:' + url
        elif url.startswith('/'):  # Absolute path
            parsed_base = urllib.parse.urlparse(base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
        elif not url.startswith(('http://', 'https://')):  # Relative path
            # Join the URL with the base URL
            return urllib.parse.urljoin(base_url, url)
        return url

    def download_video(self, url, download_path='downloads'):
        """
        Download a video from a URL
        
        Args:
            url (str): The URL of the video or page containing the video
            download_path (str): The path to save the downloaded video
            
        Returns:
            dict: Information about the download including success status
        """
        self.logger.info(f"Starting download from: {url}")
        
        # Create the download directory if it doesn't exist
        os.makedirs(download_path, exist_ok=True)
        
        # Initialize retry counter
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                # Set headers to mimic a browser request
                # Use the session for all requests to maintain cookies
                session = self.session
                
                # Check if the URL is a direct video file
                try:
                    head_response = session.head(url, headers=self.headers, timeout=self.timeout)
                    content_type = head_response.headers.get('Content-Type', '')
                    
                    # Direct video file
                    if any(f'video/{ext.lstrip(".")}' in content_type for ext in self.video_extensions):
                        video_url = url
                        self.logger.info("Direct video link detected")
                    else:
                        # Get the page content
                        response = session.get(url, headers=self.headers, timeout=self.timeout)
                        
                        if response.status_code != 200:
                            self.logger.warning(f"Failed to access the URL. Status code: {response.status_code}")
                            return {
                                'success': False,
                                'error': f"Failed to access the URL. Status code: {response.status_code}"
                            }
                        
                        # Parse the HTML content
                        self.logger.info("Parsing HTML content to find video source")
                        video_url = self.extract_video_url(url, response.text)
                        
                        if not video_url:
                            self.logger.warning("No video source found on the page")
                            return {
                                'success': False,
                                'error': "No video source found on the page"
                            }
                except Exception as e:
                    self.logger.warning(f"Error during initial URL check: {str(e)}")
                    # Fall back to direct request without head check
                    response = session.get(url, headers=self.headers, timeout=self.timeout)
                    
                    if response.status_code != 200:
                        self.logger.warning(f"Failed to access the URL. Status code: {response.status_code}")
                        return {
                            'success': False,
                            'error': f"Failed to access the URL. Status code: {response.status_code}"
                        }
                    
                    # Extract the video URL from the page
                    video_url = self.extract_video_url(url, response.text)
                    
                    if not video_url:
                        self.logger.warning("No video source found on the page")
                        return {
                            'success': False,
                            'error': "No video source found on the page"
                        }
                
                # If the video URL is a relative URL, convert it to an absolute URL
                video_url = self._ensure_absolute_url(video_url, url)
                self.logger.info(f"Video URL identified: {video_url}")
                
                try:
                    # Check content type of the video URL
                    video_head = session.head(video_url, headers=self.headers, timeout=self.timeout)
                    content_type = video_head.headers.get('Content-Type', '')
                except Exception as e:
                    self.logger.warning(f"Error checking video URL headers: {str(e)}")
                    # If head request fails, assume a generic content type
                    content_type = ""
                
                # Determine file extension
                file_ext = self._get_file_extension(video_url, content_type)
                
                # Generate a unique filename
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"video_{timestamp}{file_ext}"
                filepath = os.path.join(download_path, filename)
                
                # Download the video with progress bar
                self.logger.info(f"Downloading video from: {video_url}")
                
                # Custom headers for video download
                download_headers = self.headers.copy()
                download_headers.update({
                    'Referer': url,  # Set the referrer to the original page URL
                    'Range': 'bytes=0-',  # Support for partial content
                })
                
                # Download the video with progress tracking
                try:
                    self._download_file_with_progress(video_url, filepath, headers=download_headers)
                    
                    # Verify the file was actually downloaded and has content
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        self.logger.info(f"Video downloaded successfully to: {filepath}")
                        return {
                            'success': True,
                            'filepath': filepath,
                            'original_url': url,
                            'video_url': video_url,
                            'file_size': os.path.getsize(filepath)
                        }
                    else:
                        self.logger.warning("Downloaded file is empty or does not exist")
                        return {
                            'success': False,
                            'error': "Download failed - empty file or file does not exist"
                        }
                except Exception as download_error:
                    self.logger.exception(f"Error during download: {str(download_error)}")
                    return {
                        'success': False,
                        'error': f"Download error: {str(download_error)}"
                    }
                
            except requests.exceptions.Timeout:
                retry_count += 1
                self.logger.warning(f"Timeout error, retrying ({retry_count}/{self.max_retries})...")
                time.sleep(2)  # Wait before retrying
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error: {str(e)}")
                return {
                    'success': False,
                    'error': f"Request error: {str(e)}"
                }
                
            except Exception as e:
                self.logger.exception(f"Unexpected error: {str(e)}")
                return {
                    'success': False,
                    'error': f"Unexpected error: {str(e)}"
                }
        
        return {
            'success': False,
            'error': "Maximum retry attempts reached"
        }

    def _get_file_extension(self, url, content_type):
        """
        Determine the file extension based on URL or content type
        
        Args:
            url (str): The URL of the video
            content_type (str): The content type header
            
        Returns:
            str: The file extension including the dot
        """
        # First try to get the extension from the URL
        path = urllib.parse.urlparse(url).path
        ext = os.path.splitext(path)[1].lower()
        
        if ext and ext in self.video_extensions:
            return ext
            
        # If not found or not valid, try to determine from content type
        if 'video/' in content_type:
            video_format = content_type.split('/')[-1].split(';')[0]
            if video_format == 'quicktime':
                return '.mov'
            elif video_format == 'x-msvideo':
                return '.avi'
            elif video_format == 'x-ms-wmv':
                return '.wmv'
            elif video_format == 'x-flv':
                return '.flv'
            elif video_format == 'x-matroska':
                return '.mkv'
            elif video_format == 'webm':
                return '.webm'
            else:
                return f".{video_format}"
                
        # Default to .mp4 if we couldn't determine the extension
        return '.mp4'

    def _download_file_with_progress(self, url, filepath, headers=None):
        """
        Download a file with progress indication
        
        Args:
            url (str): The URL of the file to download
            filepath (str): The path to save the file
            headers (dict, optional): Custom headers for the download request
        """
        from app import update_download_progress
        import time
        
        # Use provided headers or default headers
        download_headers = headers if headers else self.headers
        
        # Reset and initialize download progress
        filename = os.path.basename(filepath)
        update_download_progress(
            status='downloading',
            progress=0,
            file_size=0,
            downloaded=0,
            speed=0,
            filename=filename,
            platform='generic'
        )
        
        # Use session for consistent cookies and connection pooling
        response = self.session.get(url, headers=download_headers, stream=True, timeout=self.timeout)
        
        # Get the total file size if available
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 8  # 8 KB for faster downloads
        
        # Update file size in progress tracker
        update_download_progress(file_size=total_size)
        
        # Variables to track download speed
        start_time = time.time()
        downloaded = 0
        last_update_time = start_time
        update_interval = 0.2  # Update progress every 0.2 seconds for smoother UI
        
        with open(filepath, 'wb') as file, tqdm(
                desc=filename,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(block_size):
                if data:  # Filter out keep-alive chunks
                    file.write(data)
                    data_len = len(data)
                    downloaded += data_len
                    bar.update(data_len)
                    
                    # Calculate progress percentage
                    progress = (downloaded / total_size * 100) if total_size > 0 else 0
                    
                    # Update download speed calculation periodically
                    current_time = time.time()
                    elapsed = current_time - last_update_time
                    
                    if elapsed >= update_interval:
                        # Calculate download speed (bytes per second)
                        speed = downloaded / (current_time - start_time) if (current_time - start_time) > 0 else 0
                        
                        # Update progress tracker
                        update_download_progress(
                            progress=min(progress, 99.9),  # Cap at 99.9% until fully complete
                            downloaded=downloaded,
                            speed=speed
                        )
                        
                        last_update_time = current_time
        
        # Final update to mark as complete
        update_download_progress(
            status='completed',
            progress=100,
            downloaded=downloaded,
            speed=downloaded / (time.time() - start_time) if (time.time() - start_time) > 0 else 0
        )
        
        # Ensure the file is completely written to disk
        # (Important for some systems where writing might be cached)
        os.fsync(file.fileno())
