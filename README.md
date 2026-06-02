# SecureBox

SecureBox 是一个本地密码管理器与加密工具，使用 Python、Flet、SQLite、Argon2id/PBKDF2 和 AES-GCM 实现。项目面向网络安全课程大作业，重点展示本地密码保险箱、密钥派生、认证加密、文件加密和跨端桌面/移动交付。

## 交付边界

SecureBox 只提供本地应用：

- Windows 桌面 exe
- Android apk

项目明确不支持 Web 版，不提供 PWA，不部署远程服务，也不把 Flet 作为 Web 服务运行。不要将以下命令作为交付方式：

```powershell
flet run --web
flet build web
flet publish
flet serve
```

这样做是为了避免把本地密码保险箱扩展成网络应用后引入服务端存储、远程认证、传输链路、浏览器缓存和网络暴露面等额外安全边界。

## 功能

- 主密码初始化和登录
- 密码记录新增、查看、修改、删除
- 随机密码生成
- 密码强度检测
- 文本加密与解密
- 文件分块加密与解密
- 加密导出与导入
- 自动锁定
- 登录失败延迟
- 复制密码后自动清理剪贴板
- 中英文界面切换
- 帮助弹窗
- Windows exe 与 Android apk 本地交付

## 安全设计

SecureBox 的主要威胁模型是：本地数据库或导出文件泄露后，攻击者无法直接获得明文密码，并且需要面对主密码 KDF 的离线破解成本。

核心机制：

- KDF：优先使用 Argon2id，保留 PBKDF2 兼容路径。
- 密钥结构：主密码派生 KEK，KEK 加密随机生成的 DEK，DEK 加密密码记录字段。
- 字段加密：敏感字段使用 AES-256-GCM 加密。
- 完整性：AES-GCM tag 用于发现密文篡改。
- AAD：绑定记录 ID、字段名、版本或文件 chunk index，降低密文字段替换风险。
- nonce：每次字段加密和文件 chunk 加密都使用独立随机 nonce。
- SQLite：只保存加密后的敏感字段，不保存明文密码。

安全限制：

- 不防护已完全失陷的本机系统。
- 不防护键盘记录器、屏幕录制、恶意剪贴板监听和运行时内存读取。
- SQLite 删除后的底层页残留不作为本项目主要防护目标。
- Android Debug 签名仅适合课程演示和本地验证，正式发布应使用 release keystore。

## 数据位置

Windows exe 默认数据目录：

```text
C:\Users\<用户名>\.securebox\securebox.sqlite3
```

Android apk 默认保存到应用私有数据目录，例如：

```text
/data/user/0/com.parlestargazer.securebox/app_flutter/securebox.sqlite3
```

Android 私有数据目录普通文件管理器通常不可直接访问。SecureBox 不会把数据库保存在 exe/apk 所在目录。

## 环境

项目使用 conda 管理 Python 环境，依赖安装优先使用 pip。

```powershell
conda env create -f environment.yml
conda activate securebox
python -m pip install -r requirements-dev.txt
```

如果环境已经存在：

```powershell
conda activate securebox
python -m pip install -r requirements-dev.txt
```

## 本地运行

```powershell
python -m securebox
```

也可以使用 Flet 本地模式：

```powershell
flet run -m securebox.main
```

不要添加 `--web`。

## 测试

```powershell
python -m pytest
python -m ruff check .
```

当前收尾验证：

```text
pytest: 60 passed
Android 模拟器安装: 通过
Android apkSigningVersion: 3
Android versionCode: 2
```

## 打包产物

本地产物目录：

```text
dist\SecureBox-windows-x64.zip
dist\SecureBox-android.apk
```

当前本地验证哈希：

```text
SecureBox-windows-x64.zip
SHA256: 55901EC41C00F7BBE4861248CE41AAFFBEC31242CCEFFBF08A29B27AFAB89F22

SecureBox-android.apk
SHA256: C7D5D61E90D8EE8E8C3391F80ADF8BA3570BCA4AA99E7168A907FFE0C1F91972
```

打包细节和 Android `libpython3.12.so` 修复流程见：

```text
docs\packaging.md
docs\build-verification.md
```

## 项目结构

```text
securebox/
  crypto/       KDF、AEAD、密钥包装、文件加密
  db/           SQLite schema 与 repository
  services/     认证、保险箱、导出、剪贴板、锁定等业务逻辑
  ui/           Flet 界面
  utils/        编码、时间和错误类型
tests/          单元测试与 UI smoke 测试
tools/          Android APK / ELF 修复工具
docs/           开发计划、打包说明、演示清单、验证记录
assets/         应用图标源文件和平台图标
```

## 文档

- `docs/development-plan.md`：按阶段和 commit 粒度划分的开发计划。
- `docs/packaging.md`：Windows exe 和 Android apk 打包说明。
- `docs/build-verification.md`：最终构建和验证结果。
- `docs/demo-checklist.md`：课堂演示流程和报告要点。

## 备注

Flet 0.85 的 `build` 命令要求入口文件位于应用根目录，因此仓库根目录提供了一个很薄的 `main.py`，实际逻辑仍在 `securebox.main` 和 `securebox.ui.app` 中。

当前 Windows/Flet/serious_python 组合对中文路径不稳定，正式打包时建议把源码复制或克隆到纯英文路径。
