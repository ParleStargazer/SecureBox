# 构建验证记录

## 最终状态

验证日期：2026-06-03

```text
pytest: 60 passed
Windows zip: 已生成
Android apk: 已生成
Android 模拟器安装: 通过
Android 真机图标刷新: 通过
```

## Windows

交付物：

```text
dist\SecureBox-windows-x64.zip
```

验证哈希：

```text
SHA256: 55901EC41C00F7BBE4861248CE41AAFFBEC31242CCEFFBF08A29B27AFAB89F22
```

已处理问题：

```text
- Flet 0.85 不支持 dotted module 作为 build 入口，已保留根目录 main.py 作为薄入口。
- 当前 Windows/Flet/serious_python 组合对中文路径不稳定，打包建议使用纯英文路径。
- EXE 图标已替换为 SecureBox 蓝盾锁图标。
- Windows bundle 内部 app.zip 已同步最新 UI Logo。
```

## Android

交付物：

```text
dist\SecureBox-android.apk
```

验证信息：

```text
package: com.parlestargazer.securebox
versionCode: 2
versionName: 1.0.0
minSdk: 24
targetSdk: 36
apkSigningVersion: 3
SHA256: C7D5D61E90D8EE8E8C3391F80ADF8BA3570BCA4AA99E7168A907FFE0C1F91972
```

已处理问题：

```text
- Android 黑屏：修复 APK 内 libpython3.12.so 的 ELF PT_LOAD 偏移对齐问题。
- APK 安装解析失败：确保 resources.arsc 不压缩并保持 4 字节对齐。
- APK v2+ 签名：使用 apksig 生成 v1/v2/v3 签名，设备侧显示 apkSigningVersion=3。
- Launcher 图标：替换 adaptive icon foreground、fallback mipmap、splash 和 Android 12 splash 图。
- 真机图标缓存：将 versionCode 提升到 2，强制手机桌面重新读取应用图标。
- 应用内 Logo：登录页改为使用 SecureBox 蓝盾锁图标资源。
```

模拟器验证：

```text
adb connect 127.0.0.1:5563
adb install -r dist\SecureBox-android.apk
```

结果：

```text
Success
versionCode=2
apkSigningVersion=3
```

## 测试

最终测试命令：

```powershell
python -m pytest
```

结果：

```text
60 passed
```
