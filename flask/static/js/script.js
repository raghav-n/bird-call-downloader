document.addEventListener('DOMContentLoaded', function() {
    // Tab navigation
    const tabs = document.querySelectorAll('.tab');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Hide all tab panes
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Show the corresponding pane
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Configuration form submission
    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const messageDiv = document.getElementById('config-message');
            
            // Send AJAX request
            fetch('/save_config', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Show success or error message
                messageDiv.textContent = data.message;
                messageDiv.classList.remove('hidden', 'success', 'error');
                messageDiv.classList.add(data.status);
                
                // Hide message after 5 seconds
                setTimeout(() => {
                    messageDiv.classList.add('hidden');
                }, 5000);
            })
            .catch(error => {
                console.error('Error saving configuration:', error);
                messageDiv.textContent = 'An error occurred while saving the configuration.';
                messageDiv.classList.remove('hidden', 'success');
                messageDiv.classList.add('error');
            });
        });
    }
    
    // Handle enable/disable toggles for sections
    const xenoEnabled = document.getElementById('xeno_enabled');
    const ebirdEnabled = document.getElementById('ebird_enabled');
    const xenoSettings = document.getElementById('xeno-settings');
    const ebirdSettings = document.getElementById('ebird-settings');
    
    // Toggle section content when checkbox changes
    xenoEnabled.addEventListener('change', function() {
        xenoSettings.style.opacity = this.checked ? '1' : '0.5';
        xenoSettings.querySelectorAll('input, select').forEach(input => {
            input.disabled = !this.checked;
        });
    });
    
    ebirdEnabled.addEventListener('change', function() {
        ebirdSettings.style.opacity = this.checked ? '1' : '0.5';
        ebirdSettings.querySelectorAll('input, select').forEach(input => {
            input.disabled = !this.checked;
        });
    });
    
    // Download form submission
    const downloadForm = document.getElementById('download-form');
    const progressSection = document.getElementById('progress-section');
    const messageDiv = document.getElementById('message');
    
    if (downloadForm) {
        downloadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const downloadBtn = document.getElementById('download-btn');
            
            // Disable button to prevent multiple submissions
            downloadBtn.disabled = true;
            downloadBtn.textContent = 'Starting...';
            
            // Get form data
            const formData = new FormData(this);
            
            // Send AJAX request
            fetch('/start_download', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show progress section
                    downloadForm.style.display = 'none';
                    progressSection.classList.remove('hidden');
                    
                    // Start checking progress
                    checkProgress();
                } else {
                    // Show error message
                    messageDiv.textContent = data.message;
                    messageDiv.classList.remove('hidden', 'success');
                    messageDiv.classList.add('error');
                    
                    // Re-enable button
                    downloadBtn.disabled = false;
                    downloadBtn.textContent = 'Start Downloads';
                }
            })
            .catch(error => {
                console.error('Error starting download:', error);
                messageDiv.textContent = 'An error occurred while starting the download.';
                messageDiv.classList.remove('hidden', 'success');
                messageDiv.classList.add('error');
                
                // Re-enable button
                downloadBtn.disabled = false;
                downloadBtn.textContent = 'Start Downloads';
            });
        });
    }
    
    // New download button
    const newDownloadBtn = document.getElementById('new-download-btn');
    if (newDownloadBtn) {
        newDownloadBtn.addEventListener('click', function() {
            // Show form and hide progress
            downloadForm.style.display = 'block';
            progressSection.classList.add('hidden');
            
            // Reset form
            downloadForm.reset();
            
            // Reset message
            messageDiv.classList.add('hidden');
        });
    }
    
    // Track if we should keep checking progress
    let continueChecking = false;
    
    // Function to check download progress
    function checkProgress() {
        continueChecking = true;
        
        function checkUpdate() {
            if (!continueChecking) return;
            
            fetch('/progress')
                .then(response => response.json())
                .then(data => {
                    // Update progress bars
                    updateProgressBar('xeno', data.xeno);
                    updateProgressBar('ebird', data.ebird);
                    
                    // Update status message
                    document.getElementById('status-message').textContent = data.status;
                    
                    // Check if download is complete
                    if (data.xeno_complete && data.ebird_complete) {
                        document.getElementById('download-complete').classList.remove('hidden');
                        continueChecking = false;
                    }
                    
                    // If download is still running, check again in 1 second
                    if (data.download_running && continueChecking) {
                        setTimeout(checkUpdate, 1000);
                    }
                })
                .catch(error => {
                    console.error('Error checking progress:', error);
                    if (continueChecking) {
                        setTimeout(checkUpdate, 5000);  // Retry after 5 seconds if error
                    }
                });
        }
        
        // Start checking
        checkUpdate();
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'visible' && continueChecking) {
                checkUpdate();
            }
        });
    }
    
    // Function to update progress bar
    function updateProgressBar(id, progress) {
        const progressPercent = Math.round(progress * 100);
        const progressBar = document.getElementById(`${id}-progress`);
        progressBar.style.width = `${progressPercent}%`;
        progressBar.textContent = `${progressPercent}%`;
    }

    // Directory browser functionality
    const browseBtn = document.getElementById('browse-btn');
    const downloadDirInput = document.getElementById('download_dir');
    
    if (browseBtn) {
        browseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get current path from input
            const currentPath = downloadDirInput.value || '/';
            
            // Create and show the directory browser modal
            showDirectoryBrowser(currentPath);
        });
    }

    function showDirectoryBrowser(initialPath) {
        // Create modal HTML
        const modalHTML = `
            <div class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Select Download Directory</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="current-path">
                            <input type="text" id="current-path" value="${initialPath}" readonly>
                        </div>
                        <div class="directory-actions">
                            <button class="btn" id="new-folder-btn">New Folder</button>
                        </div>
                        <div class="new-folder-form hidden">
                            <div class="input-with-button">
                                <input type="text" id="new-folder-name" placeholder="Folder name">
                                <button class="btn" id="create-folder-btn">Create</button>
                                <button class="btn" id="cancel-folder-btn">Cancel</button>
                            </div>
                        </div>
                        <div class="directory-list-container">
                            <div class="directory-list" id="directory-list">
                                <p class="loading">Loading directories...</p>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn" id="select-dir-btn">Select This Directory</button>
                        <button class="btn" id="cancel-browse-btn">Cancel</button>
                    </div>
                </div>
            </div>
        `;
        
        // Insert modal into DOM
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHTML;
        document.body.appendChild(modalContainer);
        
        // Add event listeners
        const modal = document.querySelector('.modal-overlay');
        const closeBtn = modal.querySelector('.modal-close');
        const cancelBtn = modal.querySelector('#cancel-browse-btn');
        const selectBtn = modal.querySelector('#select-dir-btn');
        const currentPathDisplay = modal.querySelector('#current-path');
        
        // Close modal functionality
        function closeModal() {
            document.body.removeChild(modalContainer);
        }
        
        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        
        // Select current directory
        selectBtn.addEventListener('click', function() {
            downloadDirInput.value = currentPathDisplay.value;
            closeModal();
        });
        
        // Load initial directory listing
        loadDirectories(initialPath);
        
        // Function to load directories from server
        function loadDirectories(path) {
            const directoryList = document.getElementById('directory-list');
            directoryList.innerHTML = '<p class="loading">Loading directories...</p>';
            
            fetch('/browse_directories', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    path: path
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Update current path display
                    currentPathDisplay.value = data.current_path;
                    
                    // Clear and populate directory list
                    directoryList.innerHTML = '';
                    
                    // Add parent directory link if available
                    if (data.parent_path) {
                        const parentItem = document.createElement('div');
                        parentItem.className = 'directory-item parent';
                        parentItem.innerHTML = '<span class="dir-icon">📁</span> ..';
                        parentItem.addEventListener('click', function() {
                            loadDirectories(data.parent_path);
                        });
                        directoryList.appendChild(parentItem);
                    }
                    
                    // Add each directory
                    if (data.directories.length === 0) {
                        directoryList.innerHTML += '<p>No subdirectories found</p>';
                    } else {
                        data.directories.forEach(dir => {
                            const dirItem = document.createElement('div');
                            dirItem.className = 'directory-item';
                            dirItem.innerHTML = `<span class="dir-icon">📁</span> ${dir.name}`;
                            dirItem.addEventListener('click', function() {
                                loadDirectories(dir.path);
                            });
                            directoryList.appendChild(dirItem);
                        });
                    }
                } else {
                    directoryList.innerHTML = `<p class="error">${data.message}</p>`;
                }
            })
            .catch(error => {
                directoryList.innerHTML = `<p class="error">Error loading directories: ${error.message}</p>`;
            });
        }

        // Add event listeners for new folder functionality
        const newFolderBtn = modal.querySelector('#new-folder-btn');
        const newFolderForm = modal.querySelector('.new-folder-form');
        const newFolderInput = modal.querySelector('#new-folder-name');
        const createFolderBtn = modal.querySelector('#create-folder-btn');
        const cancelFolderBtn = modal.querySelector('#cancel-folder-btn');
        
        // Show new folder form
        newFolderBtn.addEventListener('click', function() {
            newFolderForm.classList.remove('hidden');
            newFolderInput.focus();
        });
        
        // Hide new folder form
        cancelFolderBtn.addEventListener('click', function() {
            newFolderForm.classList.add('hidden');
            newFolderInput.value = '';
        });
        
        // Create new folder
        createFolderBtn.addEventListener('click', function() {
            const folderName = newFolderInput.value.trim();
            if (!folderName) {
                alert('Please enter a folder name');
                return;
            }
            
            const currentPath = currentPathDisplay.value;
            
            fetch('/create_folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    path: currentPath,
                    folder_name: folderName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Reset form and hide it
                    newFolderForm.classList.add('hidden');
                    newFolderInput.value = '';
                    
                    // Reload the directory listing
                    loadDirectories(currentPath);
                } else {
                    alert('Error creating folder: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error creating folder: ' + error.message);
            });
        });
        
        // Handle Enter key in new folder input
        newFolderInput.addEventListener('keyup', function(event) {
            if (event.key === 'Enter') {
                createFolderBtn.click();
            } else if (event.key === 'Escape') {
                cancelFolderBtn.click();
            }
        });
    }
});
