const { ipcRenderer } = require('electron');

class ImageBackgroundRemover {
    constructor() {
        this.setupElements();
        this.setupEventListeners();
        this.setupIPC();
        this.colors = [];
        this.isWindowFocused = true;
        this.activeColorIndex = null;
        
        // Load saved settings
        this.loadSettings();
        
        // Handle clicking outside dropdowns
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.color-item')) {
                this.closeAllDropdowns();
            }
        });
    }

    setupElements() {
        // Image containers
        this.originalImageContainer = document.getElementById('original-image');
        this.processedImageContainer = document.getElementById('processed-image');
        this.processedPreviewContainer = document.getElementById('processed-preview-container');

        // Buttons
        this.loadButton = document.getElementById('load-image');
        this.pasteButton = document.getElementById('paste-image');
        this.saveButton = document.getElementById('save-image');
        this.copyButton = document.getElementById('copy-image');
        this.clearColorsButton = document.getElementById('clear-colors');
        this.settingsButton = document.getElementById('settings-button');

        // Settings elements
        this.settingsOverlay = document.getElementById('settings-overlay');
        this.closeSettingsButton = this.settingsOverlay.querySelector('.close-button');
        this.bgTypeSelect = document.getElementById('bg-type');
        this.bgColorInput = document.getElementById('bg-color');
        this.colorValue = document.querySelector('.color-value');

        // Color selection elements
        this.colorList = document.getElementById('color-list');
    }

    setupEventListeners() {
        // Image loading
        this.loadButton.addEventListener('click', () => this.loadImage());
        this.pasteButton.addEventListener('click', () => this.pasteImage());
        
        // Image saving/copying
        this.saveButton.addEventListener('click', () => this.saveImage());
        this.copyButton.addEventListener('click', () => this.copyImage());
        
        // Color management
        this.clearColorsButton.addEventListener('click', () => this.clearColors());

        // Settings
        this.settingsButton.addEventListener('click', () => this.openSettings());
        this.closeSettingsButton.addEventListener('click', () => this.closeSettings());
        this.settingsOverlay.addEventListener('click', (e) => {
            if (e.target === this.settingsOverlay) {
                this.closeSettings();
            }
        });

        // Background settings
        this.bgTypeSelect.addEventListener('change', () => this.updateBackground());
        this.bgColorInput.addEventListener('input', () => this.updateBackground());
        this.bgColorInput.addEventListener('change', () => {
            this.updateBackground();
            this.saveSettings();
        });
    }

    setupIPC() {
        // Listen for processed image updates
        ipcRenderer.on('image-processed', (event, data) => {
            console.log('Received processed image update:', data);
            if (data.status === 'success') {
                this.updateProcessedImage(data.path);
            } else {
                console.error('Image processing failed:', data.message);
            }
        });

        // Listen for Python errors
        ipcRenderer.on('python-error', (event, data) => {
            console.error('Python error:', data.message);
        });

        // Listen for shortcut triggers
        ipcRenderer.on('trigger-color-picker', () => {
            this.captureColor();
        });

        ipcRenderer.on('trigger-paste', () => {
            this.pasteImage();
        });

        ipcRenderer.on('trigger-copy', () => {
            this.copyImage();
        });

        // Handle native paste event
        document.addEventListener('paste', (e) => {
            e.preventDefault();
            this.pasteImage();
        });
    }

    async loadImage() {
        const result = await ipcRenderer.invoke('load-image');
        if (result.status === 'success') {
            this.updateOriginalImage(result.path);
            this.processImage(result.path);
        }
    }

    async pasteImage() {
        const result = await ipcRenderer.invoke('paste-image');
        if (result.status === 'success') {
            this.updateOriginalImage(result.path);
            this.processImage(result.path);
        }
    }

    async saveImage() {
        await ipcRenderer.invoke('save-image');
    }

    async copyImage() {
        try {
            const result = await ipcRenderer.invoke('copy-image');
            if (result.status === 'error') {
                console.error('Failed to copy image:', result.message);
                // You might want to show this error to the user in a more friendly way
            }
        } catch (error) {
            console.error('Copy operation failed:', error);
        }
    }

    async captureColor() {
        try {
            const result = await ipcRenderer.invoke('capture-color');
            if (result.status === 'success') {
                console.log('Captured color:', result.color);
                this.addColor(result.color);
            } else {
                console.error('Failed to capture color:', result.message);
            }
        } catch (error) {
            console.error('Color capture error:', error);
        }
    }

    addColor(color) {
        const colorData = {
            rgb: color,
            tolerance: 0  // Start with exact color match
        };
        
        this.colors.push(colorData);
        this.updateColorList();
        this.processImage();
    }

    updateColorList() {
        this.colorList.innerHTML = '';
        
        // Add headers
        const header = document.createElement('div');
        header.className = 'color-list-header';
        
        const colorHeader = document.createElement('div');
        colorHeader.className = 'header-color';
        colorHeader.textContent = 'color';
        
        const rgbHeader = document.createElement('div');
        rgbHeader.className = 'header-rgb';
        rgbHeader.textContent = 'rgb';
        
        const toleranceHeader = document.createElement('div');
        toleranceHeader.className = 'header-tolerance';
        toleranceHeader.textContent = 'tolerance';
        
        const actionsHeader = document.createElement('div');
        actionsHeader.className = 'header-actions';
        
        header.appendChild(colorHeader);
        header.appendChild(rgbHeader);
        header.appendChild(toleranceHeader);
        header.appendChild(actionsHeader);
        this.colorList.appendChild(header);
        
        // Add color items
        this.colors.forEach((color, index) => {
            const colorItem = document.createElement('div');
            colorItem.className = 'color-item';
            
            const preview = document.createElement('div');
            preview.className = 'color-preview';
            preview.style.backgroundColor = `rgb(${color.rgb.join(',')})`;
            
            const info = document.createElement('div');
            info.className = 'color-info';
            
            const rgbText = document.createElement('span');
            rgbText.className = 'color-rgb';
            rgbText.textContent = `(${color.rgb.join(', ')})`;

            // Create inline tolerance control
            const inlineTolerance = document.createElement('div');
            inlineTolerance.className = 'inline-tolerance';
            
            const toleranceSlider = document.createElement('input');
            toleranceSlider.type = 'range';
            toleranceSlider.min = 0;
            toleranceSlider.max = 255;
            toleranceSlider.value = color.tolerance;
            
            const toleranceInput = document.createElement('input');
            toleranceInput.type = 'number';
            toleranceInput.min = 0;
            toleranceInput.max = 255;
            toleranceInput.value = color.tolerance;
            
            // Sync slider and number input
            toleranceSlider.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                color.tolerance = value;
                toleranceInput.value = value;
                this.processImage();
            });
            
            toleranceInput.addEventListener('input', (e) => {
                let value = parseInt(e.target.value);
                // Clamp value between 0 and 255
                value = Math.max(0, Math.min(255, value));
                color.tolerance = value;
                toleranceSlider.value = value;
                this.processImage();
            });

            inlineTolerance.appendChild(toleranceSlider);
            inlineTolerance.appendChild(toleranceInput);
            
            const actions = document.createElement('div');
            actions.className = 'color-actions';

            // Delete button
            const deleteButton = document.createElement('button');
            deleteButton.className = 'delete-color';
            deleteButton.innerHTML = '🗑️';
            deleteButton.title = 'Delete Color';
            deleteButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.colors.splice(index, 1);
                this.updateColorList();
                this.processImage();
            });

            actions.appendChild(deleteButton);
            
            info.appendChild(rgbText);
            info.appendChild(inlineTolerance);
            colorItem.appendChild(preview);
            colorItem.appendChild(info);
            colorItem.appendChild(actions);
            
            this.colorList.appendChild(colorItem);
        });
    }

    closeAllDropdowns() {
        document.querySelectorAll('.color-settings-dropdown.active').forEach(dropdown => {
            dropdown.classList.remove('active');
        });
    }

    clearColors() {
        this.colors = [];
        this.updateColorList();
        ipcRenderer.invoke('clear-colors');
    }

    processImage(path = null) {
        if (path || this.currentImagePath) {
            ipcRenderer.invoke('process-image', {
                path: path || this.currentImagePath,
                colors: this.colors.map(color => ({
                    rgb: color.rgb,
                    tolerance: color.tolerance
                }))
            });
        }
    }

    updateOriginalImage(path) {
        this.currentImagePath = path;
        const normalizedPath = path.replace(/\\/g, '/');
        const fileUrl = `file:///${normalizedPath}`;
        const urlWithTimestamp = `${fileUrl}?t=${Date.now()}`;
        this.originalImageContainer.src = urlWithTimestamp;
    }

    updateProcessedImage(path) {
        const normalizedPath = path.replace(/\\/g, '/');
        const fileUrl = `file:///${normalizedPath}`;
        const urlWithTimestamp = `${fileUrl}?t=${Date.now()}`;
        this.processedImageContainer.src = urlWithTimestamp;
    }

    loadSettings() {
        const settings = JSON.parse(localStorage.getItem('displaySettings') || '{}');
        this.bgTypeSelect.value = settings.bgType || 'checkerboard';
        this.bgColorInput.value = settings.bgColor || '#ffffff';
        this.updateBackground();
    }

    saveSettings() {
        const settings = {
            bgType: this.bgTypeSelect.value,
            bgColor: this.bgColorInput.value
        };
        localStorage.setItem('displaySettings', JSON.stringify(settings));
    }

    updateBackground() {
        const type = this.bgTypeSelect.value;
        const color = this.bgColorInput.value;
        
        if (type === 'solid') {
            this.processedPreviewContainer.classList.add('solid-bg');
            this.processedPreviewContainer.style.backgroundColor = color;
        } else {
            this.processedPreviewContainer.classList.remove('solid-bg');
            this.processedPreviewContainer.style.backgroundColor = '';
        }

        // Update color value display
        this.colorValue.textContent = color.toUpperCase();
    }

    openSettings() {
        this.settingsOverlay.classList.add('active');
    }

    closeSettings() {
        this.settingsOverlay.classList.remove('active');
        this.saveSettings();
    }
}

// Initialize the application
window.addEventListener('DOMContentLoaded', () => {
    window.app = new ImageBackgroundRemover();
}); 