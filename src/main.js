const { app, BrowserWindow, ipcMain, dialog, clipboard, nativeImage, globalShortcut, screen, desktopCapturer } = require('electron');
const path = require('path');
const { PythonShell } = require('python-shell');
const fs = require('fs');
let pythonProcess = null;
let mainWindow = null;

// Get the application root directory
function getAppRoot() {
    const isDev = !app.isPackaged;
    return isDev ? path.join(__dirname, '..') : process.resourcesPath;
}

// Get the correct temp directory path
function getTempPath() {
    const appRoot = getAppRoot();
    return path.join(appRoot, 'temp');
}

// Get the correct backend directory path
function getBackendPath() {
    const appRoot = getAppRoot();
    return path.join(appRoot, 'src', 'backend');
}

// Ensure temp directory exists
function ensureTempDir() {
    const tempDir = getTempPath();
    if (!fs.existsSync(tempDir)) {
        console.log('Creating temp directory:', tempDir);
        fs.mkdirSync(tempDir, { recursive: true });
    }
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    mainWindow.loadFile('src/ui/index.html');
    
    // Register global shortcuts only when window is focused
    mainWindow.on('focus', () => {
        // Color picker shortcut
        globalShortcut.register('W', () => {
            if (mainWindow.isFocused()) {
                mainWindow.webContents.send('trigger-color-picker');
            }
        });
        
        // Paste shortcut (already handled by the OS, just need to forward it)
        globalShortcut.register('CommandOrControl+V', () => {
            if (mainWindow.isFocused()) {
                mainWindow.webContents.send('trigger-paste');
            }
        });
        
        // Copy shortcut
        globalShortcut.register('CommandOrControl+C', () => {
            if (mainWindow.isFocused()) {
                mainWindow.webContents.send('trigger-copy');
            }
        });
    });
    
    // Unregister shortcuts when window loses focus
    mainWindow.on('blur', () => {
        globalShortcut.unregisterAll();
    });
    
    // Open DevTools in development
    if (process.argv.includes('--debug')) {
        mainWindow.webContents.openDevTools();
    }
}

// Start Python backend service
function startPythonService() {
    // Determine if we're in development or production
    const isDev = !app.isPackaged;
    
    // Set up paths based on environment
    let pythonPath;
    let scriptPath;
    
    if (isDev) {
        // Development environment
        pythonPath = path.join('venv', 'Scripts', 'python');
        scriptPath = getBackendPath();
        console.log('Development environment detected');
    } else {
        // Production environment
        console.log('Production environment detected');
        scriptPath = path.join(process.resourcesPath, 'app.asar.unpacked', 'backend');
        console.log('Script path:', scriptPath);
        
        try {
            // First check if Python is available
            require('child_process').execSync('python --version');
            console.log('Python is available');
            
            // Install requirements directly using system Python
            const requirementsPath = path.join(getAppRoot(), 'requirements.txt');
            console.log('Installing requirements from:', requirementsPath);
            
            if (!fs.existsSync(requirementsPath)) {
                console.error('requirements.txt not found at:', requirementsPath);
                throw new Error('requirements.txt not found');
            }
            
            const installCommand = `python -m pip install -r "${requirementsPath}"`;
            console.log('Running command:', installCommand);
            require('child_process').execSync(installCommand);
            
            console.log('Dependencies installed successfully');
            pythonPath = 'python';
        } catch (error) {
            console.error('Error setting up Python environment:', error);
            mainWindow.webContents.send('python-error', {
                status: 'error',
                message: 'Failed to set up Python environment: ' + error.message
            });
            return;
        }
    }

    // Verify all required files exist
    console.log('Verifying required files...');
    const servicePath = path.join(scriptPath, 'service.py');
    if (!fs.existsSync(servicePath)) {
        console.error('service.py not found at:', servicePath);
        mainWindow.webContents.send('python-error', {
            status: 'error',
            message: 'service.py not found'
        });
        return;
    }

    const options = {
        mode: 'json',
        pythonPath: pythonPath,
        pythonOptions: ['-u'], // unbuffered output
        scriptPath: scriptPath,
        args: []
    };

    console.log('Starting Python service with options:', options);

    pythonProcess = new PythonShell('service.py', options);
    
    pythonProcess.on('message', function (message) {
        console.log('Python message received:', message);
        try {
            // Handle messages from Python
            if (message.type === 'image-processed') {
                // Normalize path before sending to renderer
                const normalizedPath = message.path.replace(/\\/g, '/');
                mainWindow.webContents.send('image-processed', {
                    status: 'success',
                    path: normalizedPath
                });
            }
        } catch (error) {
            console.error('Error handling Python message:', error);
            mainWindow.webContents.send('python-error', {
                status: 'error',
                message: error.message
            });
        }
    });
    
    pythonProcess.on('stderr', function (stderr) {
        console.error('Python stderr:', stderr);
        mainWindow.webContents.send('python-error', {
            status: 'error',
            message: stderr
        });
    });
    
    pythonProcess.on('error', function (err) {
        console.error('Python Error:', err);
        mainWindow.webContents.send('python-error', {
            status: 'error',
            message: err.message
        });
    });

    pythonProcess.on('close', function (code) {
        console.log('Python process closed with code:', code);
        if (code !== 0) {
            mainWindow.webContents.send('python-error', {
                status: 'error',
                message: `Python process exited with code ${code}`
            });
        }
    });
}

app.whenReady().then(() => {
    ensureTempDir();
    createWindow();
    startPythonService();

    app.on('activate', function () {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        if (pythonProcess) {
            pythonProcess.end();
        }
        app.quit();
    }
});

// IPC Communication handlers
ipcMain.handle('load-image', async () => {
    const result = await dialog.showOpenDialog({
        properties: ['openFile'],
        filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg'] }]
    });

    if (!result.canceled && result.filePaths.length > 0) {
        const imagePath = result.filePaths[0];
        pythonProcess.send({ command: 'process-image', path: imagePath });
        return { status: 'success', path: imagePath };
    }
    return { status: 'cancelled' };
});

ipcMain.handle('paste-image', async () => {
    try {
        // Get image from clipboard
        const image = clipboard.readImage();
        
        if (image.isEmpty()) {
            return { status: 'error', message: 'No image in clipboard' };
        }

        // Get temp directory path
        const tempDir = getTempPath();
        
        // Convert to PNG with alpha channel
        const pngBuffer = image.toPNG();
        
        // Save clipboard image to temp file
        const tempPath = path.join(tempDir, 'clipboard_image.png');
        fs.writeFileSync(tempPath, pngBuffer);

        // Send to Python for processing
        pythonProcess.send({ command: 'process-image', path: tempPath });
        
        return { status: 'success', path: tempPath };
    } catch (error) {
        console.error('Paste error:', error);
        return { status: 'error', message: error.message };
    }
});

ipcMain.handle('save-image', async () => {
    const result = await dialog.showSaveDialog({
        filters: [{ name: 'PNG Image', extensions: ['png'] }]
    });

    if (!result.canceled) {
        // Copy processed image to selected location
        const tempDir = getTempPath();
        fs.copyFileSync(
            path.join(tempDir, 'processed_image.png'),
            result.filePath
        );
        return { status: 'success' };
    }
    return { status: 'cancelled' };
});

ipcMain.handle('copy-image', async () => {
    try {
        // Read the processed image
        const tempDir = getTempPath();
        const processedImagePath = path.join(tempDir, 'processed_image.png');
        if (!fs.existsSync(processedImagePath)) {
            return { status: 'error', message: 'No processed image available' };
        }

        // Create native image from file
        const image = nativeImage.createFromPath(processedImagePath);
        
        // Copy to clipboard
        clipboard.writeImage(image);
        
        return { status: 'success' };
    } catch (error) {
        console.error('Copy error:', error);
        return { status: 'error', message: error.message };
    }
});

ipcMain.handle('capture-color', async () => {
    try {
        const mousePos = screen.getCursorScreenPoint();
        const displays = screen.getAllDisplays();
        const display = displays.find(d => {
            return mousePos.x >= d.bounds.x && 
                   mousePos.x <= d.bounds.x + d.bounds.width &&
                   mousePos.y >= d.bounds.y && 
                   mousePos.y <= d.bounds.y + d.bounds.height;
        });

        if (!display) {
            throw new Error('Could not determine display for color picking');
        }

        const sources = await desktopCapturer.getSources({
            types: ['screen'],
            thumbnailSize: {
                width: display.bounds.width,
                height: display.bounds.height
            }
        });

        const source = sources.find(s => s.display_id === display.id.toString());
        if (!source) {
            throw new Error('Could not capture screen content');
        }

        // Get the color from the thumbnail at mouse position
        const img = nativeImage.createFromDataURL(source.thumbnail.toDataURL());
        const relativeX = mousePos.x - display.bounds.x;
        const relativeY = mousePos.y - display.bounds.y;
        
        // Scale coordinates to thumbnail size
        const scaleX = img.getSize().width / display.bounds.width;
        const scaleY = img.getSize().height / display.bounds.height;
        const pixelX = Math.floor(relativeX * scaleX);
        const pixelY = Math.floor(relativeY * scaleY);

        // Get pixel color from the image
        const bitmap = img.toBitmap();
        const pixelIndex = (pixelY * img.getSize().width + pixelX) * 4;
        const color = [
            bitmap[pixelIndex + 2],  // R
            bitmap[pixelIndex + 1],  // G
            bitmap[pixelIndex + 0]   // B
        ];

        return { status: 'success', color: color };
    } catch (error) {
        console.error('Color capture error:', error);
        return { status: 'error', message: error.message };
    }
});

ipcMain.handle('clear-colors', async () => {
    pythonProcess.send({ command: 'clear-colors' });
    return { status: 'success' };
});

ipcMain.handle('update-tolerance', async (event, data) => {
    pythonProcess.send({ 
        command: 'update-tolerance',
        tolerance: data.tolerance,
        index: data.index
    });
    return { status: 'success' };
});

ipcMain.handle('update-edge-settings', async (event, data) => {
    pythonProcess.send({
        command: 'update-edge-settings',
        enabled: data.enabled,
        sensitivity: data.sensitivity
    });
    return { status: 'success' };
});

ipcMain.handle('process-image', async (event, data) => {
    pythonProcess.send({
        command: 'process-image',
        path: data.path,
        colors: data.colors || []
    });
    return { status: 'success' };
}); 