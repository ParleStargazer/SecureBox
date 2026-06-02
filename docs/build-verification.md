# 构建验证记录

## 2026-06-02

已验证：

```powershell
python -m pytest
python -m ruff check .
flet --version
```

结果：

```text
pytest: 46 passed
ruff: All checks passed
Flet: 0.85.2
Flutter target version reported by Flet CLI: 3.41.7
```

Windows exe 构建尝试：

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

构建状态：

```text
已完成 Windows bundle 验证。
```

关键过程：

```text
1. Flet 自动下载 Flutter SDK 时曾因网络/缓存得到无效 zip。
2. 已手动下载并解压 Flutter 3.41.7 到 C:\Users\Parle\flutter\3.41.7。
3. 原项目路径包含中文字符，serious_python 打包阶段会触发路径/编码问题。
4. 将源码复制到 C:\Users\Parle\SecureBox-build-20260602-170226 后，app/app.zip 成功生成。
5. Windows 原生构建生成 SecureBox.exe。
6. CMake install 阶段因本机 VS CMake 访问 C:\Windows\System32\vcruntime140_1.dll 失败而中断。
7. 仅在临时构建目录中将生成的 cmake_install.cmake 改为 C:/Windows/Sysnative/vcruntime140_1.dll 后，install 成功完成。
```

已验证 Windows 交付物：

```text
目录：C:\Users\Parle\SecureBox-windows-x64-20260602
压缩包：C:\Users\Parle\SecureBox-windows-x64-20260602.zip
短启动验证：SecureBox.exe 可启动并保持运行，随后测试进程已关闭。
压缩包大小：约 32 MiB
```

补充：

```text
Flet 0.85 的 build 入口不支持 dotted module，例如 securebox.main 会被解析为 securebox.py。
项目已提供根目录 main.py 作为 Flet build 入口，实际逻辑仍委托给 securebox.main。
当前 Windows/Flet/serious_python 组合对中文路径不稳，构建和运行交付物建议放在纯英文路径。
项目目录下 dist\SecureBox-windows-x64.zip 仅作本地归档副本；演示验收优先使用 C:\Users\Parle 下的英文路径交付物。
如果正式环境中仍遇到 vcruntime140_1.dll install 失败，应安装/修复 Microsoft Visual C++ Redistributable 或使用可正确访问 64 位 System32 的 CMake/VS 工具链。
项目不支持 Web 交付，未执行 flet build web / flet publish。
```

Android apk 构建尝试：

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

Android 状态：

```text
已完成 APK 构建和签名校验。
```

关键过程：

```text
1. Android SDK 位于 C:\Users\Parle\Android\sdk。
2. 已安装 cmdline-tools;latest、platform-tools、platforms;android-35、build-tools;34.0.0。
3. 已接受 Android SDK licenses。
4. Gradle/Flutter 构建需要 NDK 27.0.12077973；首次自动下载得到截断 zip，7-Zip 测试报 Unexpected end of archive。
5. 删除损坏的 ndk\27.0.12077973 半安装目录和 .temp\PackageOperation01 后，使用 sdkmanager 单独安装 ndk;27.0.12077973 成功。
6. Maven Central 依赖解析曾出现 TLS handshake 失败；本机 C:\Users\Parle\.gradle\init.gradle 增加阿里云 google / gradle-plugin / public 镜像后，Gradle 配置阶段可解析依赖。
7. 直接运行 gradlew help 会因缺少 SERIOUS_PYTHON_SITE_PACKAGES 失败，这是 Flet 未注入打包环境变量导致；完整 flet build apk 可正常注入并继续构建。
8. 构建日志：F:\实验课\网络安全原理与实践\大作业\build\logs\flet-apk-20260602-190242.out.log。
9. 日志显示：[19:10:41] Built .apk for Android OK。
```

已验证 Android 交付物：

```text
APK：C:\Users\Parle\SecureBox-android-20260602.apk
项目归档副本：dist\SecureBox-android.apk
大小：81,738,803 bytes
SHA256：24C4D5FA58F36B3CFFFAD8BB0C69C0713445490D3F074FD0E6E1B135BDEDDB39
apksigner verify --print-certs：通过，签名证书为 Android Debug 证书。
aapt dump badging：包名 com.parlestargazer.securebox，minSdk 24，targetSdk 36，native-code arm64-v8a / armeabi-v7a / x86_64。
```

Android 安全边界说明：

```text
APK 包含 Flet/Android 默认 INTERNET 和 ACCESS_NETWORK_STATE 权限。
SecureBox 仍按本地离线密码保险箱设计，不提供 Web 版本，不启动远程 Web 服务，不开放网络监听端口。
当前 APK 用于课程演示和本地安装验证；如要应用商店发布，需要替换为正式 release keystore 并重新签名。
```

运行时空白屏修复：

```text
现象：Windows exe 启动后只有空白窗口，Android apk 启动后黑屏。
原因：securebox/ui/app.py 使用了当前 Flet 0.85.2 中不存在的 ft.Icons.LOCK_SHIELD 和 ft.Icons.FOLDER_LOCK。
影响：Flet 原生壳可以启动，但 Python target 在首屏构建时抛 AttributeError，导致界面没有成功渲染。
修复：将首屏图标替换为 ft.Icons.SECURITY，将文件页图标替换为 ft.Icons.FOLDER。
回归测试：tests/test_ui_app.py 增加 Flet 图标/颜色常量存在性扫描，避免后续 Flet 版本变动再次造成空白屏。
源码短启动验证：python -m securebox 启动 10 秒后仍保持运行，stderr 无异常。
Windows bundle 验证：更新 data\flutter_assets\app\app.zip 和 app.zip.hash 后，SecureBox.exe 启动 10 秒后仍保持运行。
Windows zip 验证：C:\Users\Parle\SecureBox-windows-x64-20260602.zip 内部 app.zip 已确认包含 ft.Icons.SECURITY / ft.Icons.FOLDER。
Android APK 验证：重新执行 flet build apk，日志显示 [19:21:54] Built .apk for Android OK。
Android APK 内容验证：APK 内部 assets\flutter_assets\app\app.zip 已确认包含 ft.Icons.SECURITY / ft.Icons.FOLDER。
Android APK 签名验证：apksigner verify --print-certs 通过。
Android APK 新 SHA256：24C4D5FA58F36B3CFFFAD8BB0C69C0713445490D3F074FD0E6E1B135BDEDDB39。
真机/模拟器安装验证：当前 adb devices 无设备连接，尚未执行安装运行验收。
```
