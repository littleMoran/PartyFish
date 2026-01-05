Write-Host "正在打包 PartyFish..." -ForegroundColor Green

# Execute packaging command
pyinstaller `
    --noconfirm `
    --name "PartyFish" `
    --windowed `
    --icon "666.ico" `
    --add-data "resources;resources" `
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
    PartyFish.py

Write-Host "打包完成！" -ForegroundColor Green
Read-Host "按任意键继续..."