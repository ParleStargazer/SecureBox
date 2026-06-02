# SecureBox 打包说明

## 交付目标

只交付：

```text
Windows 桌面 exe
Android apk
```

不交付：

```text
Web 版
PWA
远程 Web 服务
静态 Web 发布包
```

禁止将以下命令作为项目交付方式：

```powershell
flet run --web
flet build web
flet publish
flet serve
```

## Windows exe

在 `securebox` conda 环境中执行：

```powershell
python -m pip install -r requirements-dev.txt
```

Windows/Flet/serious_python 在当前环境下对中文路径不稳定，建议将源码复制或克隆到纯英文路径再构建，例如：

```text
C:\Users\Parle\SecureBox-build
```

```powershell
flet build windows . `
  --module-name main `
  --project securebox `
  --product SecureBox `
  --artifact SecureBox `
  --org com.parlestargazer `
  --description "SecureBox local password manager"
```

输出目录默认为：

```text
build/windows
```

打包时会读取 `pyproject.toml` 中的 `tool.flet.app.exclude`，自动排除 `.git`、测试缓存、测试目录、文档目录和本地数据目录，避免把开发文件或本地明文/密文运行数据放进交付包。

如果 Windows install 阶段报 `vcruntime140_1.dll` 找不到，应优先安装或修复 Microsoft Visual C++ Redistributable，并确保 CMake/VS 工具链能访问 64 位 VC++ runtime。当前本机验证中，生成脚本对 `C:\Windows\System32\vcruntime140_1.dll` 的访问受工具链位数影响，使用英文临时目录并改为 `C:\Windows\Sysnative\vcruntime140_1.dll` 后完成了本地 bundle 验证。

验收：

```text
- exe 可以启动
- 可以初始化主密码
- 可以登录
- 可以新增、查看、修改、删除密码记录
- 数据库中看不到明文密码
```

## Android apk

在 `securebox` conda 环境中执行：

```powershell
python -m pip install -r requirements-dev.txt
```

Android 构建必须预先准备：

```text
Android SDK command-line tools
Android platform / build-tools / platform-tools
ANDROID_HOME 环境变量
已接受 Android SDK licenses
```

```powershell
flet build apk . `
  --module-name main `
  --project securebox `
  --product SecureBox `
  --artifact SecureBox `
  --org com.parlestargazer `
  --description "SecureBox local password manager"
```

输出目录默认为：

```text
build/apk
```

验收：

```text
- apk 可以安装
- 可以初始化主密码
- 可以登录
- 至少可以查看保险箱页面
- 小屏幕布局不遮挡主要按钮和输入框
```

## Android 风险说明

Android APK 构建需要额外验证：

```text
- cryptography 二进制 wheel 是否能被打包链正确包含
- argon2-cffi / argon2-cffi-bindings 是否能在 Android 目标运行
- 本地 SQLite 数据目录是否可写
- 文件加解密页面的路径选择是否需要改成平台文件选择器
```

如果 Android 打包因为二进制依赖失败，优先保留 Windows exe 作为主交付，并在报告中说明 APK 是跨端扩展目标及其依赖限制。

## 构建故障记录

构建验证过程记录在：

```text
docs/build-verification.md
```

如果 Windows 构建在 Flutter SDK 下载阶段出现 `zipfile.BadZipFile: File is not a zip file`，说明下载到的 Flutter 归档不完整或不是有效 zip。可以清理 Flet 构建缓存后重试，或手动安装 Flet CLI 要求的 Flutter SDK 版本后再执行构建命令。
