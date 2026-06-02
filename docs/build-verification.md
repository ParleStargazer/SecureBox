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
未生成 APK。
JDK 安装完成，Python app 打包完成，图标和 splash 生成完成。
Flutter Android 构建阶段报错：[!] No Android SDK found. Try setting the ANDROID_HOME environment variable.
```

后续条件：

```text
1. 安装 Android SDK command-line tools、platforms、build-tools、platform-tools。
2. 设置 ANDROID_HOME 指向 Android SDK 目录。
3. 接受 Android SDK licenses。
4. 在纯英文路径下重新执行 flet build apk。
5. APK 仍需额外验证 cryptography 和 argon2-cffi 的 Android 二进制依赖兼容性。
```
