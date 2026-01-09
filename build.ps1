Write-Host "Building PartyFish..." -ForegroundColor Green

# Define Python absolute path
$pythonPath = "C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe"

# Check if Python exists
if (-not (Test-Path $pythonPath)) {
    Write-Host "Error: Python not found. Please check the path." -ForegroundColor Red
    exit 1
}

# Install requirements.txt dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
try {
    & $pythonPath -m pip install -r requirements.txt
    Write-Host "Dependencies installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Error: Failed to install dependencies. Check network or requirements.txt." -ForegroundColor Red
    Write-Host "Details: $_" -ForegroundColor Red
    exit 1
}

# Copy config file to resources
Write-Host "Copying config file..." -ForegroundColor Yellow
try {
    $sourceConfig = "C:\Users\Admin\AppData\Local\Programs\Python\Python313\Lib\site-packages\rapidocr_onnxruntime\config.yaml"
    $targetConfig = "resources\config.yaml"
    Copy-Item -Path $sourceConfig -Destination $targetConfig -Force -ErrorAction Stop
    Write-Host "Config file copied successfully" -ForegroundColor Green
} catch {
    Write-Host "Warning: Failed to copy config file: $_" -ForegroundColor Yellow
}

# Copy model files if they exist
Write-Host "Checking and copying model files..." -ForegroundColor Yellow
try {
    $sourceModels = "C:\Users\Admin\AppData\Local\Programs\Python\Python313\Lib\site-packages\rapidocr_onnxruntime\models"
    $targetModels = "resources\models"
    if (Test-Path $sourceModels) {
        Copy-Item -Path $sourceModels -Destination $targetModels -Recurse -Force -ErrorAction Stop
        Write-Host "Model files copied successfully" -ForegroundColor Green
    } else {
        Write-Host "Info: Model files directory not found, skipping copy" -ForegroundColor Cyan
    }
} catch {
    Write-Host "Warning: Failed to copy model files: $_" -ForegroundColor Yellow
}

# Run PyInstaller to build the application
Write-Host "Running PyInstaller..." -ForegroundColor Yellow
try {
    & $pythonPath -m PyInstaller `
        --noconfirm `
        --name "PartyFish" `
        --onefile `
        --windowed `
        --icon "666.ico" `
        --add-data "resources;resources" `
        --add-data "666.ico;." `
        --uac-admin `
        --collect-data rapidocr_onnxruntime `
        --collect-all rapidocr_onnxruntime `
        --collect-all onnxruntime `
        --hidden-import=rapidocr_onnxruntime `
        --hidden-import=onnxruntime `
        --hidden-import=cv2 `
        --hidden-import=numpy `
        --hidden-import=PIL `
        --hidden-import=pynput `
        --hidden-import=ttkbootstrap `
        --hidden-import=mss `
        --hidden-import=yaml `
        --hidden-import=winsound `
        --hidden-import=time `
        --hidden-import=os `
        --hidden-import=webbrowser `
        --hidden-import=warnings `
        --hidden-import=threading `
        --hidden-import=ctypes `
        --hidden-import=datetime `
        --hidden-import=re `
        --hidden-import=queue `
        --hidden-import=random `
        --hidden-import=tkinter `
        --hidden-import=json `
        PartyFish.py

    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "Executable is located in dist/PartyFish/ directory" -ForegroundColor Cyan
} catch {
    Write-Host "Error: Build failed." -ForegroundColor Red
    Write-Host "Details: $_" -ForegroundColor Red
    exit 1
}