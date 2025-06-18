document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const urlInput = document.getElementById('url');
    const checkUrlButton = document.getElementById('check-url');
    const urlCheckResult = document.getElementById('url-check-result');
    const downloadForm = document.getElementById('download-form');
    const downloadProgress = document.getElementById('download-progress');
    const progressBar = downloadProgress.querySelector('.progress-bar');
    
    // Check URL functionality
    checkUrlButton.addEventListener('click', function() {
        const url = urlInput.value.trim();
        
        if (!url) {
            showUrlCheckResult(false, 'Please enter a URL');
            return;
        }
        
        // Basic URL validation
        if (!isValidURL(url)) {
            showUrlCheckResult(false, 'Invalid URL format');
            return;
        }
        
        // Show loading state
        checkUrlButton.disabled = true;
        checkUrlButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Checking...';
        urlCheckResult.classList.add('d-none');
        
        // Send AJAX request to check URL
        fetch('/check-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url }),
        })
        .then(response => response.json())
        .then(data => {
            showUrlCheckResult(data.valid, data.message);
        })
        .catch(error => {
            console.error('Error:', error);
            showUrlCheckResult(false, 'Error checking URL');
        })
        .finally(() => {
            // Reset button state
            checkUrlButton.disabled = false;
            checkUrlButton.innerHTML = '<i class="fas fa-search me-1"></i> Check';
        });
    });
    
    // Handle form submission
    downloadForm.addEventListener('submit', function(event) {
        const url = urlInput.value.trim();
        
        if (!url || !isValidURL(url)) {
            event.preventDefault();
            showUrlCheckResult(false, 'Please enter a valid URL');
            return;
        }
        
        // Prevent the default form submission - we'll handle downloading in the browser
        event.preventDefault();
        
        // Show the URL check result as a loading message
        showUrlCheckResult(true, 'Preparing download, please wait...');
        
        // Show progress bar when downloading
        showProgressBar();
        
        // Get the direct video URL for client-side downloading
        getDirectVideoUrl(url);
    });
    
    // Helper function to show URL check result
    function showUrlCheckResult(isValid, message) {
        urlCheckResult.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-info', 'alert-warning');
        
        // Determine the type of alert based on the message
        let alertClass = 'alert-danger';
        let icon = '<i class="fas fa-exclamation-circle me-2"></i>';
        let platformClass = '';
        let platformName = '';
        let platformIconPath = '';
        
        if (isValid) {
            // Check if it's a social media platform
            if (message.toLowerCase().includes('youtube')) {
                alertClass = 'alert-info';
                platformClass = 'youtube';
                platformName = 'YouTube';
                platformIconPath = '/static/icons/youtube.svg';
            } else if (message.toLowerCase().includes('instagram')) {
                alertClass = 'alert-info';
                platformClass = 'instagram';
                platformName = 'Instagram';
                platformIconPath = '/static/icons/instagram.svg';
            } else if (message.toLowerCase().includes('twitter') || message.toLowerCase().includes('x')) {
                alertClass = 'alert-info';
                platformClass = 'twitter';
                platformName = 'Twitter';
                platformIconPath = '/static/icons/twitter.svg';
            } else if (message.toLowerCase().includes('facebook')) {
                alertClass = 'alert-info';
                platformClass = 'facebook';
                platformName = 'Facebook';
                platformIconPath = '/static/icons/facebook.svg';
            } else if (message.toLowerCase().includes('tiktok')) {
                alertClass = 'alert-info';
                platformClass = 'tiktok';
                platformName = 'TikTok';
                platformIconPath = '/static/icons/tiktok.svg';
            } else if (message.toLowerCase().includes('reddit')) {
                alertClass = 'alert-info';
                platformClass = 'general';
                platformName = 'Reddit';
                platformIconPath = '/static/icons/video.svg';
            } else if (message.toLowerCase().includes('vimeo')) {
                alertClass = 'alert-info';
                platformClass = 'general';
                platformName = 'Vimeo';
                platformIconPath = '/static/icons/video.svg';
            } else {
                alertClass = 'alert-success';
                platformClass = 'general';
                platformName = 'Video';
                platformIconPath = '/static/icons/video.svg';
            }
            
            // Store platform info in a data attribute for later use
            urlCheckResult.dataset.platform = platformClass;
        }
        
        urlCheckResult.classList.add(alertClass);
        
        // If we have a platform identified and it's not an error
        if (isValid && platformClass && platformName && alertClass === 'alert-info') {
            // Create badge with platform icon
            let platformBadge = `
                <div class="platform-badge ${platformClass} mb-2">
                    <img src="${platformIconPath}" alt="${platformName}" class="platform-icon">
                    ${platformName}
                </div>
            `;
            
            // If we're preparing a download, show loading indicator
            if (message.toLowerCase().includes('preparing') || message.toLowerCase().includes('starting')) {
                urlCheckResult.innerHTML = `
                    ${platformBadge}
                    ${message}
                    <div class="spinner-border spinner-border-sm ms-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="mt-2 small text-muted">Social media downloads may take longer. Please be patient.</div>
                `;
            } else {
                urlCheckResult.innerHTML = `
                    ${platformBadge}
                    ${message}
                    <div class="mt-2 small text-muted">Social media downloads may take longer. Please be patient.</div>
                `;
            }
        } else {
            // Regular message with icon
            urlCheckResult.innerHTML = icon + message;
        }
    }
    
    // Helper function to show progress bar
    function showProgressBar() {
        downloadProgress.classList.remove('d-none');
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressBar.innerHTML = 'Initializing...';
        
        // Create additional elements to display file size and speed
        if (!document.getElementById('download-stats')) {
            const statsContainer = document.createElement('div');
            statsContainer.id = 'download-stats';
            statsContainer.className = 'mt-2 small text-muted d-flex justify-content-between';
            
            const fileSize = document.createElement('div');
            fileSize.id = 'file-size';
            fileSize.innerHTML = 'File size: Calculating...';
            
            const downloadSpeed = document.createElement('div');
            downloadSpeed.id = 'download-speed';
            downloadSpeed.innerHTML = 'Speed: Calculating...';
            
            statsContainer.appendChild(fileSize);
            statsContainer.appendChild(downloadSpeed);
            
            // Insert the stats container after the progress bar
            downloadProgress.insertAdjacentElement('afterend', statsContainer);
        }
        
        // Start polling for progress updates
        startProgressPolling();
    }
    
    // Poll the server for download progress updates
    function startProgressPolling() {
        const fileSize = document.getElementById('file-size');
        const downloadSpeed = document.getElementById('download-speed');
        const statsContainer = document.getElementById('download-stats');
        
        // Show the stats container
        statsContainer.classList.remove('d-none');
        
        // Set up polling
        const poll = setInterval(function() {
            fetch('/download-progress')
                .then(response => response.json())
                .then(data => {
                    // Update progress bar
                    const progress = data.progress;
                    progressBar.style.width = progress + '%';
                    progressBar.setAttribute('aria-valuenow', progress);
                    
                    // Update status in progress bar text
                    switch(data.status) {
                        case 'idle':
                            progressBar.innerHTML = 'Waiting...';
                            break;
                        case 'checking':
                            progressBar.innerHTML = 'Checking URL...';
                            break;
                        case 'downloading':
                            let progressText = 'Downloading';
                            // Add platform info if available
                            if (data.platform) {
                                progressText += ` from ${data.platform.charAt(0).toUpperCase() + data.platform.slice(1)}`;
                            }
                            progressBar.innerHTML = `${progressText}: ${progress.toFixed(1)}%`;
                            break;
                        case 'processing':
                            progressBar.innerHTML = 'Processing video...';
                            break;
                        case 'completed':
                            progressBar.innerHTML = 'Download complete!';
                            break;
                        case 'retrying':
                            progressBar.innerHTML = 'Retrying with alternative method...';
                            break;
                        case 'error':
                            progressBar.innerHTML = 'Error during download';
                            break;
                        default:
                            progressBar.innerHTML = `${progress.toFixed(1)}%`;
                    }
                    
                    // Update file size and download speed
                    if (data.human_readable) {
                        fileSize.innerHTML = `File size: ${data.human_readable.file_size}`;
                        downloadSpeed.innerHTML = `Speed: ${data.human_readable.speed}`;
                        
                        // Add estimated time if we have enough data
                        if (data.file_size > 0 && data.downloaded > 0 && data.speed > 0) {
                            const remainingBytes = data.file_size - data.downloaded;
                            const remainingTimeSeconds = remainingBytes / data.speed;
                            
                            if (remainingTimeSeconds > 0 && remainingTimeSeconds < 3600) {
                                const minutes = Math.floor(remainingTimeSeconds / 60);
                                const seconds = Math.floor(remainingTimeSeconds % 60);
                                const timeStr = `${minutes}m ${seconds}s`;
                                downloadSpeed.innerHTML += ` • Est. time: ${timeStr}`;
                            }
                        }
                    }
                    
                    // If download is complete or there's an error, stop polling
                    if (data.status === 'completed' || data.status === 'error') {
                        clearInterval(poll);
                        
                        // If download is complete, show success message
                        if (data.status === 'completed') {
                            // Create a success message if it doesn't exist
                            if (!document.getElementById('download-success')) {
                                const successAlert = document.createElement('div');
                                successAlert.id = 'download-success';
                                successAlert.className = 'alert alert-success mt-3';
                                // Determine platform for icon display
                                let platformClass = 'general';
                                let platformName = 'Video';
                                let platformIconPath = '/static/icons/video.svg';
                                
                                if (data.platform) {
                                    const platform = data.platform.toLowerCase();
                                    if (platform === 'youtube') {
                                        platformClass = 'youtube';
                                        platformName = 'YouTube';
                                        platformIconPath = '/static/icons/youtube.svg';
                                    } else if (platform === 'instagram') {
                                        platformClass = 'instagram';
                                        platformName = 'Instagram';
                                        platformIconPath = '/static/icons/instagram.svg';
                                    } else if (platform === 'twitter') {
                                        platformClass = 'twitter';
                                        platformName = 'Twitter';
                                        platformIconPath = '/static/icons/twitter.svg';
                                    } else if (platform === 'facebook') {
                                        platformClass = 'facebook';
                                        platformName = 'Facebook';
                                        platformIconPath = '/static/icons/facebook.svg';
                                    } else if (platform === 'tiktok') {
                                        platformClass = 'tiktok';
                                        platformName = 'TikTok';
                                        platformIconPath = '/static/icons/tiktok.svg';
                                    }
                                }
                                
                                // Create platform badge with icon
                                const platformBadge = `
                                    <div class="platform-badge ${platformClass} mb-2">
                                        <img src="${platformIconPath}" alt="${platformName}" class="platform-icon">
                                        ${platformName}
                                    </div>
                                `;
                                
                                successAlert.innerHTML = `
                                    ${platformBadge}
                                    <div>Video downloaded successfully! File: <strong>${data.filename}</strong></div>
                                    <div class="mt-1 small">Size: ${data.human_readable.file_size}</div>
                                    <div class="mt-2">
                                        <a href="/download?url=${encodeURIComponent(urlInput.value)}" 
                                           class="btn btn-success btn-sm" download>
                                            <i class="fas fa-download me-1"></i> Save to Device
                                        </a>
                                    </div>
                                `;
                                
                                // Insert after stats container
                                statsContainer.insertAdjacentElement('afterend', successAlert);
                                
                                // Scroll to make the success message visible
                                successAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }
                        }
                        
                        // If there was an error, show it for a while then hide
                        if (data.status === 'error') {
                            // Create an error message
                            if (!document.getElementById('download-error')) {
                                const errorAlert = document.createElement('div');
                                errorAlert.id = 'download-error';
                                errorAlert.className = 'alert alert-danger mt-3';
                                errorAlert.innerHTML = `
                                    <i class="fas fa-exclamation-circle me-2"></i>
                                    Error during download. Please try again or use a different URL.
                                `;
                                
                                // Insert after stats container
                                statsContainer.insertAdjacentElement('afterend', errorAlert);
                            }
                            
                            setTimeout(function() {
                                downloadProgress.classList.add('d-none');
                                statsContainer.classList.add('d-none');
                                // Also hide error message
                                const errorAlert = document.getElementById('download-error');
                                if (errorAlert) errorAlert.classList.add('d-none');
                            }, 8000);
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching progress:', error);
                });
        }, 500); // Poll every 500ms
    }
    
    // Helper function to validate URL format
    function isValidURL(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
    
    // Add event listener for URL input to reset result when typing
    urlInput.addEventListener('input', function() {
        urlCheckResult.classList.add('d-none');
    });
    
    // Function to get the direct video URL and start browser-side download
    function getDirectVideoUrl(url) {
        // Show a loading message while we fetch the direct URL
        progressBar.innerHTML = 'Fetching video URL...';
        progressBar.style.width = '5%';
        progressBar.setAttribute('aria-valuenow', 5);
        
        console.log('Getting direct URL for:', url);
        
        // First, update the message to show we're working
        showUrlCheckResult(true, 'Getting video details, please wait...');
        
        // Send request to get direct URL
        fetch('/get-direct-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        })
        .then(response => {
            console.log('Got response:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Direct URL response:', data);
            
            if (data.success && data.direct_url) {
                // Update UI to show we're starting the browser download
                progressBar.innerHTML = 'Starting download...';
                progressBar.style.width = '10%';
                progressBar.setAttribute('aria-valuenow', 10);
                
                // Set up initial progress data
                const initialProgressData = {
                    status: 'downloading',
                    progress: 10,
                    platform: data.platform || 'general',
                    filename: 'video.mp4', // Default filename, will be updated
                    file_size: 0,
                    downloaded: 0,
                    speed: 0,
                    human_readable: {
                        file_size: '0 B',
                        downloaded: '0 B',
                        speed: '0 B/s'
                    }
                };
                
                // Show info to user that download is starting
                showUrlCheckResult(true, `Starting download from ${data.platform} - please wait...`);
                
                // Setup browser download with progress tracking
                console.log('Starting browser download with direct URL:', data.direct_url.substring(0, 100) + '...');
                startBrowserDownload(data.direct_url, initialProgressData);
            } else {
                // Show error and reset progress
                console.error('Failed to get direct URL:', data.error);
                showDownloadError(data.error || 'Could not get direct video URL');
            }
        })
        .catch(error => {
            console.error('Error getting direct URL:', error);
            showDownloadError('Network error while getting video URL');
            
            // Fallback to server-side download
            console.log('Falling back to server-side download...');
            document.getElementById('download-form').submit();
        });
    }
    
    // Function to start browser-side download with progress tracking
    function startBrowserDownload(url, initialProgressData) {
        console.log("Starting browser download for URL:", url);
        
        // Show download progress container
        downloadProgress.classList.remove('d-none');
        statsContainer.classList.remove('d-none');
        
        // First update the progress bar to show we're starting
        progressBar.innerHTML = 'Connecting to video server...';
        progressBar.style.width = '5%';
        progressBar.setAttribute('aria-valuenow', 5);
        
        const xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.responseType = 'blob';
        
        // Add timeout to detect stalled downloads
        xhr.timeout = 30000; // 30 seconds timeout
        
        // Extract filename from URL or use a default
        let filename = 'video.mp4';
        try {
            const urlObj = new URL(url);
            const pathParts = urlObj.pathname.split('/');
            if (pathParts.length > 0) {
                const lastPart = pathParts[pathParts.length - 1];
                if (lastPart && lastPart.includes('.')) {
                    filename = lastPart;
                }
            }
        } catch (e) {
            console.error('Error parsing URL:', e);
        }
        
        console.log("Will save as filename:", filename);
        
        // Setup progress tracking
        let lastLoaded = 0;
        let startTime = Date.now();
        let lastUpdateTime = startTime;
        let speedSamples = [];
        
        xhr.onprogress = function(event) {
            if (event.lengthComputable) {
                const total = event.total;
                const loaded = event.loaded;
                const progress = Math.min((loaded / total) * 100, 99.9);
                
                // Calculate download speed
                const now = Date.now();
                const timeDiff = (now - lastUpdateTime) / 1000; // in seconds
                
                if (timeDiff > 0.5) { // Update every 0.5 seconds
                    const loadDiff = loaded - lastLoaded;
                    const speed = loadDiff / timeDiff; // bytes per second
                    
                    // Keep a rolling average of speed
                    speedSamples.push(speed);
                    if (speedSamples.length > 5) {
                        speedSamples.shift(); // Keep only last 5 samples
                    }
                    
                    // Calculate average speed
                    const avgSpeed = speedSamples.reduce((a, b) => a + b, 0) / speedSamples.length;
                    
                    // Update progress data
                    const progressData = {
                        status: 'downloading',
                        progress: progress,
                        file_size: total,
                        downloaded: loaded,
                        speed: avgSpeed,
                        filename: filename,
                        platform: initialProgressData.platform || 'general',
                        human_readable: {
                            file_size: formatBytes(total),
                            downloaded: formatBytes(loaded),
                            speed: formatBytes(avgSpeed) + '/s'
                        }
                    };
                    
                    // Update local UI
                    updateDownloadProgress(progressData);
                    
                    // Save values for next calculation
                    lastLoaded = loaded;
                    lastUpdateTime = now;
                }
            }
        };
        
        xhr.onload = function() {
            console.log('Download completed with status:', this.status);
            if (this.status === 200) {
                // Download completed
                const blob = new Blob([this.response], { type: 'video/mp4' });
                const link = document.createElement('a');
                
                // Create download link
                link.href = window.URL.createObjectURL(blob);
                link.download = filename;
                document.body.appendChild(link);
                
                // Update progress to 100%
                const progressData = {
                    status: 'completed',
                    progress: 100,
                    file_size: this.response.size,
                    downloaded: this.response.size,
                    speed: 0,
                    filename: filename,
                    platform: initialProgressData.platform || 'general',
                    human_readable: {
                        file_size: formatBytes(this.response.size),
                        downloaded: formatBytes(this.response.size),
                        speed: '0 B/s'
                    }
                };
                
                // Update the progress display
                updateDownloadProgress(progressData);
                
                // Set progress bar to success state
                progressBar.classList.remove('bg-primary');
                progressBar.classList.add('bg-success');
                progressBar.innerHTML = 'Download complete! 100%';
                
                // Get or create the stats container
                let statsContainer = document.getElementById('download-stats');
                if (!statsContainer) {
                    statsContainer = document.createElement('div');
                    statsContainer.id = 'download-stats';
                    statsContainer.className = 'mt-2 small text-muted d-flex justify-content-between';
                    downloadProgress.insertAdjacentElement('afterend', statsContainer);
                }
                
                // Create a success message
                console.log('Creating success message');
                const successAlert = document.createElement('div');
                successAlert.id = 'download-success';
                successAlert.className = 'alert alert-success mt-3';
                
                // Determine platform for icon display
                let platformClass = 'general';
                let platformName = 'Video';
                let platformIconPath = '/static/icons/video.svg';
                
                if (initialProgressData && initialProgressData.platform) {
                    const platform = initialProgressData.platform.toLowerCase();
                    if (platform === 'youtube') {
                        platformClass = 'youtube';
                        platformName = 'YouTube';
                        platformIconPath = '/static/icons/youtube.svg';
                    } else if (platform === 'instagram') {
                        platformClass = 'instagram';
                        platformName = 'Instagram';
                        platformIconPath = '/static/icons/instagram.svg';
                    } else if (platform === 'twitter') {
                        platformClass = 'twitter';
                        platformName = 'Twitter';
                        platformIconPath = '/static/icons/twitter.svg';
                    } else if (platform === 'facebook') {
                        platformClass = 'facebook';
                        platformName = 'Facebook';
                        platformIconPath = '/static/icons/facebook.svg';
                    } else if (platform === 'tiktok') {
                        platformClass = 'tiktok';
                        platformName = 'TikTok';
                        platformIconPath = '/static/icons/tiktok.svg';
                    }
                }
                
                // Create platform badge with icon
                const platformBadge = `
                    <div class="platform-badge ${platformClass} mb-2">
                        <img src="${platformIconPath}" alt="${platformName}" class="platform-icon">
                        ${platformName}
                    </div>
                `;
                
                successAlert.innerHTML = `
                    ${platformBadge}
                    <div>Video downloaded successfully! File: <strong>${filename}</strong></div>
                    <div class="mt-1 small">Size: ${formatBytes(this.response.size)}</div>
                    <button id="save-video-btn" class="btn btn-success btn-sm mt-2">
                        <i class="fas fa-download me-1"></i> Save to Device
                    </button>
                `;
                
                // Remove any existing success message
                const existingSuccess = document.getElementById('download-success');
                if (existingSuccess) {
                    existingSuccess.remove();
                }
                
                // Insert the new success message
                statsContainer.insertAdjacentElement('afterend', successAlert);
                
                // Attach click event to the save button
                document.getElementById('save-video-btn').addEventListener('click', function() {
                    link.click();
                    window.URL.revokeObjectURL(link.href);
                    this.disabled = true;
                    this.innerHTML = '<i class="fas fa-check me-1"></i> Saved';
                    this.classList.replace('btn-success', 'btn-secondary');
                });
                
                // Scroll to make the success message visible
                successAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                // Show error message
                console.error('Error downloading video, status:', this.status);
                showDownloadError('Error downloading video. Server returned status: ' + this.status);
            }
        };
        
        xhr.onerror = function() {
            console.error('Network error during download, could be a CORS issue');
            showDownloadError('Network error during download. This might be due to CORS restrictions. Trying server-side download...');
            
            // After a brief pause, fall back to server-side download
            setTimeout(function() {
                console.log('Falling back to server-side download...');
                // Create a form submission to download via the server
                document.getElementById('url-input').value = url;
                document.getElementById('download-form').submit();
            }, 2000);
        };
        
        xhr.ontimeout = function() {
            console.error('Download timed out');
            showDownloadError('Download timed out. Trying server-side download...');
            
            // After a brief pause, fall back to server-side download
            setTimeout(function() {
                console.log('Falling back to server-side download...');
                // Create a form submission to download via the server
                document.getElementById('url-input').value = url;
                document.getElementById('download-form').submit();
            }, 2000);
        };
        
        // Start the download
        xhr.send();
    }
    
    // Helper function to format bytes to human readable format
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    // Function to update UI with download progress
    function updateDownloadProgress(data) {
        // Update progress bar
        progressBar.style.width = data.progress + '%';
        progressBar.setAttribute('aria-valuenow', data.progress);
        
        // Update progress text based on status
        let progressText = 'Downloading';
        
        // Add platform-specific icon to progress bar
        let platformIcon = '';
        if (data.platform) {
            const platform = data.platform.toLowerCase();
            const platformName = data.platform.charAt(0).toUpperCase() + data.platform.slice(1);
            
            // Determine which icon to use
            let iconPath = '/static/icons/video.svg';
            if (platform === 'youtube') {
                iconPath = '/static/icons/youtube.svg';
            } else if (platform === 'instagram') {
                iconPath = '/static/icons/instagram.svg';
            } else if (platform === 'twitter') {
                iconPath = '/static/icons/twitter.svg';
            } else if (platform === 'facebook') {
                iconPath = '/static/icons/facebook.svg';
            } else if (platform === 'tiktok') {
                iconPath = '/static/icons/tiktok.svg';
            }
            
            // Create inline icon
            platformIcon = `<img src="${iconPath}" alt="${platformName}" width="16" height="16" style="margin-right: 4px; vertical-align: text-bottom;">`;
            progressText += ` from ${platformName}`;
        }
        
        progressBar.innerHTML = `${platformIcon}${progressText}: ${data.progress.toFixed(1)}%`;
        
        // Update file size and download speed
        const fileSize = document.getElementById('file-size');
        const downloadSpeed = document.getElementById('download-speed');
        
        if (fileSize && downloadSpeed && data.human_readable) {
            fileSize.innerHTML = `File size: ${data.human_readable.file_size}`;
            downloadSpeed.innerHTML = `Speed: ${data.human_readable.speed}`;
            
            // Add estimated time if we have enough data
            if (data.file_size > 0 && data.downloaded > 0 && data.speed > 0) {
                const remainingBytes = data.file_size - data.downloaded;
                const remainingTimeSeconds = remainingBytes / data.speed;
                
                if (remainingTimeSeconds > 0 && remainingTimeSeconds < 3600) {
                    const minutes = Math.floor(remainingTimeSeconds / 60);
                    const seconds = Math.floor(remainingTimeSeconds % 60);
                    const timeStr = `${minutes}m ${seconds}s`;
                    downloadSpeed.innerHTML += ` • Est. time: ${timeStr}`;
                }
            }
        }
    }
    
    // Show error message and reset progress
    function showDownloadError(message) {
        const statsContainer = document.getElementById('download-stats');
        
        // Create an error message if it doesn't exist
        if (!document.getElementById('download-error')) {
            const errorAlert = document.createElement('div');
            errorAlert.id = 'download-error';
            errorAlert.className = 'alert alert-danger mt-3';
            errorAlert.innerHTML = `
                <i class="fas fa-exclamation-circle me-2"></i>
                ${message || 'Error during download. Please try again or use a different URL.'}
            `;
            
            // Insert after stats container
            statsContainer.insertAdjacentElement('afterend', errorAlert);
        }
        
        // Update progress bar to show error
        progressBar.style.width = '100%';
        progressBar.classList.remove('bg-primary', 'bg-success');
        progressBar.classList.add('bg-danger');
        progressBar.innerHTML = 'Download failed';
        
        // Hide progress after a delay
        setTimeout(function() {
            const downloadProgress = document.getElementById('download-progress');
            if (downloadProgress) downloadProgress.classList.add('d-none');
            if (statsContainer) statsContainer.classList.add('d-none');
            
            // Also hide error message
            const errorAlert = document.getElementById('download-error');
            if (errorAlert) errorAlert.classList.add('d-none');
            
            // Reset progress bar
            progressBar.classList.remove('bg-danger');
            progressBar.classList.add('bg-primary');
        }, 8000);
    }
});
