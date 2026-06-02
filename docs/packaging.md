# SecureBox 打包说明

## 交付目标

SecureBox 只交付本地应用：

```text
Windows 桌面 exe
Android apk
```

不交付 Web 版、PWA、远程 Web 服务或静态 Web 发布包。

## 通用准备

```powershell
conda activate securebox
python -m pip install -r requirements-dev.txt
python -m pytest
python -m ruff check .
```

当前 Flet/serious_python 构建链对中文路径不稳定，打包时建议使用纯英文路径，例如：

```text
C:\Users\Parle\SecureBox-build
```

## Windows exe

推荐构建命令：

```powershell
flet build windows . `
  --module-name main `
  --project securebox `
  --product SecureBox `
  --artifact SecureBox `
  --org com.parlestargazer `
  --description "SecureBox local password manager" `
  --skip-flutter-doctor `
  --no-rich-output `
  --yes
```

本地交付物：

```text
dist\SecureBox-windows-x64.zip
```

当前验证哈希：

```text
SHA256: 55901EC41C00F7BBE4861248CE41AAFFBEC31242CCEFFBF08A29B27AFAB89F22
```

验收要点：

```text
- SecureBox.exe 可以启动
- 可以初始化主密码
- 可以登录
- 可以新增、查看、修改、删除密码记录
- 数据库中看不到明文密码
- 登录页和系统图标使用 SecureBox 蓝盾锁图标
```

## Android apk

Android 构建需要：

```text
Android SDK command-line tools
Android platform / build-tools / platform-tools
ANDROID_HOME 环境变量
已接受 Android SDK licenses
NDK 27.0.12077973
```

推荐构建命令：

```powershell
flet build apk . `
  --module-name main `
  --project securebox `
  --product SecureBox `
  --artifact SecureBox `
  --org com.parlestargazer `
  --description "SecureBox local password manager" `
  --skip-flutter-doctor `
  --no-rich-output `
  --yes
```

当前 Flet/serious_python Android 运行时中的 `libpython3.12.so` 需要额外修复，否则部分 Android 链接器会在加载 CPython 前黑屏卡住。Flet 生成 APK 后执行：

```powershell
$builtApk = "build\flutter\build\app\outputs\apk\release\app-release.apk"
$unsignedApk = "build\apk-inspect\SecureBox-android-patched-unsigned.apk"
$alignedApk = "build\apk-inspect\SecureBox-android-patched-aligned.apk"
$finalApk = "dist\SecureBox-android.apk"

python tools\patch_android_apk_libpython.py $builtApk $unsignedApk
& "$env:ANDROID_HOME\build-tools\34.0.0\zipalign.exe" -p -f 4 $unsignedApk $alignedApk
& "$env:ANDROID_HOME\build-tools\34.0.0\apksigner.bat" sign `
  --ks "$env:USERPROFILE\.android\debug.keystore" `
  --ks-pass pass:android `
  --key-pass pass:android `
  --ks-key-alias androiddebugkey `
  --out $finalApk `
  $alignedApk
& "$env:ANDROID_HOME\build-tools\34.0.0\apksigner.bat" verify --print-certs $finalApk
```

当前本地 APK 还做了图标、splash、应用内 Logo 和 `versionCode=2` 的最终修正。最终交付物：

```text
dist\SecureBox-android.apk
SHA256: C7D5D61E90D8EE8E8C3391F80ADF8BA3570BCA4AA99E7168A907FFE0C1F91972
```

验收要点：

```text
- apk 可以安装
- apkSigningVersion 为 3
- versionCode 为 2
- 手机和模拟器 launcher 图标显示 SecureBox 蓝盾锁图标
- 启动页和登录页 Logo 显示 SecureBox 蓝盾锁图标
- 可以初始化主密码
- 可以登录
- 小屏幕布局不遮挡主要按钮和输入框
```

## Android 权限说明

`aapt dump badging` 显示 APK 包含 Flet/Android 默认的 `android.permission.INTERNET` 和 `android.permission.ACCESS_NETWORK_STATE` 权限。SecureBox 的功能边界仍为本地离线应用：不交付 Web 版，不启动远程 Web 服务，不开放网络监听端口，不把保险箱数据同步到网络。

课程演示可使用 Android Debug 证书；正式发布必须替换为 release keystore。
