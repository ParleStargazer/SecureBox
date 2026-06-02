# SecureBox 开发计划

## 1. 项目目标

SecureBox 是一个本地密码管理器与加密工具，核心目标是演示并实现网络安全课程中的常见安全机制：

- 使用主密码保护本地保险箱。
- 使用 KDF 抵抗数据库泄露后的离线暴力破解。
- 使用 AEAD 加密算法保护密码记录的机密性和完整性。
- 使用 SQLite 保存本地数据，但敏感字段必须加密后入库。
- 提供随机密码生成、密码强度检测、文本加解密、文件加解密等扩展功能。
- 在报告和演示中能够清楚说明安全边界、威胁模型与实现取舍。

## 2. 技术选型

建议 MVP 阶段使用以下技术：

```text
Python 3.12
Flet 跨端界面
SQLite 本地数据库
cryptography 加密库
argon2-cffi 密钥派生
zxcvbn 密码强度评估
pytest 单元测试
ruff 代码风格检查
```

说明：

- Flet 用 Python 编写界面，底层基于 Flutter，适合做比传统桌面界面更精美的跨端体验。
- 本项目只交付本地应用形态：Windows 桌面 exe 和 Android apk。
- 本项目明确不提供 Web 版，不部署远程 Web 服务，避免本地密码保险箱变成网络应用后引入新的攻击面、认证边界、传输安全和服务端存储风险。
- UI 层只负责展示和交互，`crypto`、`db`、`services` 保持纯 Python 业务模块，避免安全逻辑绑定在界面框架中。
- SQLite 不做整库加密，项目重点放在字段级加密与密钥管理。
- `requirements.txt` 只管理 pip 包，安装时使用 `python -m pip install -r requirements.txt`。

推荐 conda 开发环境：

```powershell
conda env create -f environment.yml
conda activate securebox
```

如果需要手动创建：

```powershell
conda create -n securebox python=3.12
conda activate securebox
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. 目录规划

```text
SecureBox/
  docs/
    development-plan.md
  securebox/
    __init__.py
    app.py
    main.py
    config.py
    crypto/
      __init__.py
      kdf.py
      aead.py
      keys.py
      file_crypto.py
    db/
      __init__.py
      connection.py
      schema.py
      repository.py
    services/
      __init__.py
      auth_service.py
      vault_service.py
      password_generator.py
      strength_service.py
      clipboard_service.py
      lock_service.py
    ui/
      __init__.py
      app.py
      routes.py
      theme.py
      login_view.py
      main_view.py
      vault_view.py
      generator_view.py
      text_crypto_view.py
      file_crypto_view.py
    utils/
      __init__.py
      encoding.py
      errors.py
      time.py
  tests/
    test_kdf.py
    test_aead.py
    test_auth_service.py
    test_vault_service.py
    test_password_generator.py
    test_file_crypto.py
  requirements.txt
  .gitignore
```

## 4. Commit 划分原则

每个 commit 尽量满足：

- 只做一个清晰目标。
- 能独立运行或至少不破坏已有测试。
- commit message 使用 `type(scope): summary` 格式。
- 涉及加密格式、数据库 schema、认证流程的 commit 必须配测试。
- 如果一个功能包含 UI 和底层逻辑，先提交底层逻辑，再提交 UI。

推荐类型：

```text
chore: 项目初始化、依赖、工具配置
docs: 文档
feat: 新功能
test: 测试
fix: 修复
refactor: 不改变行为的结构调整
```

## 5. 阶段 0：仓库与环境初始化

目标：创建可协作、可安装、可测试的项目基础。

建议 commits：

```text
docs(plan): add staged development plan
chore(repo): add gitignore and requirements
chore(project): add package skeleton and entry point
chore(test): add pytest smoke test
```

验收标准：

- 仓库已推送到 GitHub。
- `requirements.txt` 可被 pip 安装。
- 项目有明确目录结构。
- `python -m pytest` 至少能跑通一个 smoke test。

回滚边界：

- 这一阶段不包含业务功能，回滚风险低。
- 如果依赖选择不合适，可以只回滚依赖相关 commit。

## 6. 阶段 1：加密核心模块

目标：先实现安全底座，不急着写 GUI。

建议 commits：

```text
feat(crypto): add argon2id and pbkdf2 key derivation
test(crypto): cover kdf parameter persistence and verification
feat(crypto): add aes-gcm field encryption helpers
test(crypto): cover encrypt decrypt and tamper detection
feat(crypto): add dek and kek key wrapping helpers
test(crypto): cover master password change without re-encrypting entries
```

核心设计：

- `KDF` 输入主密码、salt、参数，输出 KEK。
- `DEK` 使用 `os.urandom(32)` 生成。
- `encrypted_dek` 使用 KEK + AES-GCM 加密保存。
- 具体密码字段使用 DEK + AES-GCM 加密。
- 每次加密生成 12 字节随机 nonce。
- AAD 绑定 `crypto_version`、`entry_id`、字段名。

验收标准：

- 相同主密码、salt、参数可以派生相同 KEK。
- 不同 salt 产生不同 KEK。
- 密文被篡改后解密失败。
- 字段名或 entry id 被替换后解密失败。
- 修改主密码时只重加密 `encrypted_dek`。

回滚边界：

- 如果 Argon2id 实现出问题，可以回滚到 PBKDF2 备选 commit。
- 如果 AAD 设计变更，只需回滚 AEAD helper 与对应测试。

## 7. 阶段 2：数据库与数据模型

目标：实现 SQLite schema、迁移和仓储层。

建议 commits：

```text
feat(db): add sqlite connection and schema initialization
feat(db): add config table for kdf and encrypted dek
feat(db): add password entries table with encrypted fields
test(db): cover schema creation and repository operations
feat(db): add schema version and migration guard
```

建议 schema：

```text
config
- id
- kdf_name
- kdf_params
- salt
- encrypted_dek
- verify_blob
- crypto_version
- created_at
- updated_at

password_entries
- id
- title_enc
- username_enc
- password_enc
- url_enc
- note_enc
- created_at
- updated_at
- crypto_version
```

验收标准：

- 首次启动能自动创建数据库。
- 重复启动不会破坏已有数据库。
- repository 层不暴露 SQL 细节给 service 层。
- 所有 SQL 使用参数化查询。

回滚边界：

- schema 相关 commit 独立，便于回滚迁移设计。
- 如果 title 需要改为明文展示，只影响 entries schema 和 vault service。

## 8. 阶段 3：初始化与登录认证

目标：完成主密码初始化、登录校验和会话状态。

建议 commits：

```text
feat(auth): add vault initialization flow
feat(auth): add master password verification flow
test(auth): cover login success wrong password and tampered config
feat(auth): add password change flow
test(auth): cover master password rotation
```

核心流程：

```text
初始化：
输入主密码
生成 salt
KDF 派生 KEK
生成 DEK
KEK 加密 DEK
KEK 加密 verify_blob
保存 config

登录：
读取 config
输入主密码
KDF 派生 KEK
尝试解密 encrypted_dek 或 verify_blob
成功后把 DEK 放入当前会话
```

验收标准：

- 未初始化时进入初始化流程。
- 已初始化时进入登录流程。
- 错误主密码不能进入保险箱。
- 篡改 `verify_blob` 或 `encrypted_dek` 会失败。
- 修改主密码后旧密码不能登录，新密码可以登录，已有记录可读。

回滚边界：

- 密码修改功能可单独回滚，不影响基础登录。
- 如果 verify_blob 方案调整，只回滚认证 service 和测试。

## 9. 阶段 4：密码记录管理

目标：完成保险箱核心 CRUD。

建议 commits：

```text
feat(vault): add encrypted entry creation
feat(vault): add entry list and detail read
feat(vault): add entry update and delete
test(vault): cover encrypted crud and tamper failures
feat(vault): add search strategy for encrypted titles
```

实现建议：

- MVP 中标题也加密，列表展示时登录后解密到内存。
- 搜索可以在登录后对解密标题做内存过滤。
- 数据库中不保存明文用户名、密码、URL、备注。
- 删除记录只做普通删除，并在报告中说明 SQLite 安全擦除限制。

验收标准：

- 新建记录后数据库中看不到明文密码。
- 记录更新后旧密文不能继续代表新值。
- 删除记录后 UI 不再显示。
- 篡改单个字段密文后，该字段解密失败并提示数据损坏。

回滚边界：

- 搜索功能晚于 CRUD，可以独立回滚。
- UI 未完成时也可以通过 service 测试验收。

## 10. 阶段 5：随机密码生成与强度检测

目标：实现可演示的密码安全辅助功能。

建议 commits：

```text
feat(password): add secure random password generator
test(password): cover generator options and required character sets
feat(password): add password strength scoring
feat(ui): add generator and strength views
```

实现建议：

- 使用 `secrets` 模块，不使用 `random`。
- 默认长度 20。
- 支持大小写、数字、符号选项。
- 每类字符至少出现一次后再统一安全洗牌。
- 使用 `zxcvbn` 给出强度评分和建议。

验收标准：

- 默认生成密码长度足够。
- 禁用某类字符后结果不包含该类字符。
- 多次生成结果不同。
- 弱密码能被识别为低分。

回滚边界：

- 强度检测可独立回滚，不影响随机生成。
- UI 可独立回滚，不影响 service。

## 11. 阶段 6：文本加密与解密

目标：提供独立的文本加密演示功能。

建议 commits：

```text
feat(text-crypto): add text encryption service
test(text-crypto): cover decrypt and tamper detection
feat(ui): add text encryption view
```

实现建议：

- 可以复用当前保险箱 DEK。
- 也可以支持用户输入一次性密码，通过 KDF 派生文本加密密钥。
- 输出格式使用 Base64 编码，包含版本、salt、nonce、ciphertext、tag。

验收标准：

- 明文加密后不会直接出现在输出中。
- 正确密钥可解密。
- 修改任意一位密文后解密失败。

回滚边界：

- 文本加密属于扩展功能，可整体回滚。

## 12. 阶段 7：文件加密与解密

目标：实现文件加密演示，并避免一次性读取大文件。

建议 commits：

```text
feat(file-crypto): add encrypted file format header
feat(file-crypto): add chunk encryption and decryption
test(file-crypto): cover roundtrip tamper and chunk ordering
feat(ui): add file encryption view
```

文件格式建议：

```text
header:
- magic
- version
- kdf_name
- kdf_params
- salt
- chunk_size

chunk:
- chunk_index
- nonce
- ciphertext
- tag
```

实现建议：

- 每个 chunk 独立 AES-GCM。
- AAD 绑定 header、chunk_index、chunk_size。
- 解密前检查 magic 和版本。
- 输出文件后缀可以使用 `.sbox`。

验收标准：

- 小文件和较大文件都能加密解密。
- 篡改 chunk 内容会解密失败。
- 调换 chunk 顺序会解密失败。
- 错误密码不能解密文件。

回滚边界：

- 文件加密功能独立于保险箱 CRUD，可以整体回滚。

## 13. 阶段 8：Flet 本地 GUI

目标：把已有 service 接入 Flet 界面，提供更精美的本地跨端体验。

建议 commits：

```text
feat(ui): add flet app shell and theme
feat(ui): add login and initialization views
feat(ui): add vault list and detail layout
feat(ui): wire create update delete entry actions
feat(ui): add password reveal and copy actions
feat(ui): add generator text crypto and file crypto tabs
test(ui): add minimal smoke tests for view construction
```

界面建议：

- 使用 Flet 的 `Page`、`Tabs`、`NavigationRail`、`Dialog` 等组件组织页面。
- 登录页只显示必要输入。
- 主界面用标签页区分保险箱、生成器、文本加密、文件加密。
- 密码默认隐藏，点击按钮临时显示。
- 复制密码后自动计时清空剪贴板。
- 解密失败统一提示“主密码错误或数据已损坏”。
- 不实现 Web 入口，不提供浏览器访问地址，不把保险箱暴露成 HTTP 服务。

验收标准：

- 可以通过 GUI 完成初始化、登录、CRUD。
- 错误主密码不能进入。
- 复制密码后定时清空剪贴板。
- 各页面操作不会把明文写入日志。
- Windows 桌面模式可运行。
- Android 界面布局在小屏幕下可正常操作。
- 浏览器 Web 模式不作为交付目标，不写入演示流程。

回滚边界：

- GUI commit 晚于 service commit，界面问题不影响核心逻辑。
- 单个 tab 可以单独回滚。

## 14. 阶段 9：自动锁定、剪贴板与运行安全

目标：补齐实际使用中的安全细节。

建议 commits：

```text
feat(security): add idle auto lock service
feat(security): add clipboard auto clear service
feat(security): add login failure delay
test(security): cover lock and retry timing logic
```

实现建议：

- 空闲 5 分钟自动锁定。
- 锁定时清空当前 session 中的 DEK 引用。
- 复制密码后 30 秒清空剪贴板。
- 登录连续失败后增加延迟，但不要把失败次数写成明文敏感日志。

验收标准：

- 空闲超时后需要重新输入主密码。
- 剪贴板在计时后被清空。
- 连续错误登录有延迟。

回滚边界：

- 自动锁定、剪贴板、失败延迟互相独立，可分别回滚。

## 15. 阶段 10：导出、报告与演示材料

目标：完成课程提交需要的辅助内容。

建议 commits：

```text
feat(export): add encrypted export and import
docs(report): add security design report draft
docs(demo): add demonstration checklist
chore(package): add flet windows exe packaging notes
chore(package): add flet android apk packaging notes
```

实现建议：

- 默认不允许明文导出。
- 导出文件继续使用 AES-GCM 保护。
- 报告中明确说明威胁模型、KDF、AEAD、nonce、AAD、SQLite 元数据限制。
- 报告中明确说明不支持 Web 版，避免网络服务端、传输链路、远程认证、浏览器缓存等额外安全边界。
- 打包目标只包括 Windows exe 和 Android apk。
- Android apk 构建需要额外验证 `cryptography`、`argon2-cffi` 等二进制依赖是否能被 Flet 打包链正确包含。
- 演示时准备数据库泄露但无法直接看到密码的截图。

验收标准：

- 导出文件中没有明文密码。
- 导入导出后记录一致。
- 报告能解释每个安全设计的原因。
- 演示清单覆盖初始化、登录、增删改查、篡改检测、文件加密。
- Windows exe 可以启动并完成核心流程。
- Android apk 可以安装并完成至少初始化、登录、查看保险箱的核心演示流程。
- 不提供 Web URL，不演示 Web 部署。

回滚边界：

- 导出导入为扩展功能，可以整体回滚。
- 报告文档独立于代码。

## 16. 阶段 11：测试、审计与收尾

目标：保证项目可运行、可解释、可验收。

建议 commits：

```text
test: add end-to-end vault workflow tests
test: add corrupted database and wrong password cases
chore: add ruff configuration
docs: add final usage guide
fix: address final test and demo issues
```

最终验收清单：

```text
环境：
- conda 环境可创建
- pip 依赖可安装
- pytest 全部通过
- Flet 桌面运行入口可启动

安全：
- 数据库中看不到明文密码
- 错误主密码不能登录
- 篡改密文会失败
- nonce 每次加密不同
- 主密码修改后原数据仍可解密

功能：
- 初始化保险箱
- 登录保险箱
- 新增密码记录
- 查看密码记录
- 修改密码记录
- 删除密码记录
- 生成随机密码
- 检测密码强度
- 文本加解密
- 文件加解密
- 自动锁定
- 剪贴板清空
- Windows exe 打包
- Android apk 打包
- 不支持 Web 版

文档：
- 开发计划
- 使用说明
- 安全设计说明
- 演示步骤
```

## 17. 建议开发顺序

实际开发时建议按这个顺序推进：

```text
1. 仓库初始化与依赖
2. 加密核心
3. 数据库 schema
4. 登录与初始化
5. 密码记录 CRUD
6. 密码生成与强度检测
7. Flet GUI 主流程
8. 文本加密
9. 文件加密
10. 自动锁定与剪贴板清理
11. 导出、报告、Windows exe 和 Android apk 打包
```

原因：

- 先写加密核心和测试，能避免 GUI 完成后再返工安全逻辑。
- 数据库和认证流程是保险箱的基础，应早于所有 UI。
- 文件加密和导出是扩展功能，可以留到核心功能稳定后再做。
- 每阶段都有独立 commit，可以按功能验收，也方便回滚。
