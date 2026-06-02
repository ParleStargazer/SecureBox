# SecureBox

SecureBox 是一个本地密码管理器与加密工具，使用 Python、Flet、SQLite、Argon2id/PBKDF2 和 AES-GCM 实现。

## 安全边界

SecureBox 只作为本地应用交付：

- Windows 桌面 exe
- Android apk

项目不提供 Web 版，不部署远程服务，不使用 `flet run --web`、`flet build web`、`flet publish` 或 `flet serve` 作为交付方式。这样可以避免把本地密码保险箱扩展成网络应用后引入服务端存储、远程认证、传输链路、浏览器缓存等额外安全边界。

## 环境

```powershell
conda env create -f environment.yml
conda activate securebox
```

如果环境已存在：

```powershell
conda activate securebox
python -m pip install -r requirements-dev.txt
```

## 运行

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

## 当前功能

- 主密码初始化和登录
- Argon2id / PBKDF2 密钥派生
- DEK + KEK 双层密钥结构
- AES-256-GCM 字段加密
- SQLite 加密字段存储
- 密码记录增删改查
- 随机密码生成
- 密码强度检测
- 文本加解密
- 分块文件加解密
- 自动锁定、剪贴板清理、登录失败延迟服务
- Flet 本地桌面界面

## Flet 构建入口

Flet 0.85 的 `build` 命令要求入口文件位于应用根目录，因此仓库根目录提供了一个很薄的 `main.py`，实际逻辑仍在 `securebox.main` 和 `securebox.ui.app` 中。

打包命令、Windows/Android 验证状态和本地交付物位置见 `docs/packaging.md` 与 `docs/build-verification.md`。当前 Windows/Flet/serious_python 组合对中文路径不稳定，构建和运行交付物建议放在纯英文路径。
