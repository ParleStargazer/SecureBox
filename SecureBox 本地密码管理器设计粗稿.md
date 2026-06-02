# 网络安全原理与实践 期末大作业 SecureBox本地密码管理器

推荐设计：

```text
SecureBox 本地密码管理器 + 加密工具

技术栈：
Python + Flet
SQLite 本地数据库
cryptography 库
```

交付形式：

```text
仅支持本地应用形态：
- Windows 桌面 exe
- Android apk

不提供 Web 版，不部署远程服务，避免把本地密码保险箱扩展成网络应用后引入新的攻击面和安全边界问题。
```

整体架构：

```text
用户界面层
  ├─ 登录 / 初始化主密码
  ├─ 密码保险箱页面
  ├─ 随机密码生成页面
  ├─ 文本加密解密页面
  └─ 文件加密解密页面

业务逻辑层
  ├─ 主密码校验
  ├─ 密钥派生
  ├─ 密码记录管理
  ├─ 密码强度检测
  └─ 文件加密解密

数据安全层
  ├─ PBKDF2 / Argon2 派生密钥
  ├─ AES-GCM 加密数据
  ├─ salt / nonce / tag 管理
  └─ SQLite 加密字段存储
```

数据库可以简单设计成：

```text
config
- id
- salt
- verify_blob

password_entries
- id
- title
- username_enc
- password_enc
- url_enc
- note_enc
- created_at
- updated_at
```

核心流程：

```text
第一次打开：
设置主密码
↓
生成 salt
↓
派生 master_key
↓
保存 verify_blob

之后打开：
输入主密码
↓
用 salt 派生 master_key
↓
尝试解密 verify_blob
↓
成功则进入保险箱
```

功能优先级建议：

```text
第一优先级：
主密码初始化 / 登录
密码记录增删改查
随机密码生成
数据库字段加密保存

第二优先级：
密码强度检测
文本加密解密
文件加密解密

第三优先级：
导出报告
自动锁定
剪贴板自动清空
```

可补充的安全设计：

## 一、威胁模型与安全目标

建议在报告中先说明 SecureBox 主要防护的攻击场景：

```text
重点防护：
- 本地数据库文件被他人复制后离线破解
- 攻击者直接查看 SQLite 文件内容
- 备份文件或导出文件泄露
- 程序崩溃、误操作导致密文被篡改

不完全防护：
- 主机已经被木马完全控制
- 键盘记录器窃取主密码
- 用户主动输入弱主密码
- 程序运行时内存被高级攻击者读取
```

对应安全目标：

```text
- 不保存主密码明文，也不保存主密码的普通哈希值
- 数据库中敏感字段必须加密后再写入
- 每条记录使用独立随机 nonce，避免 nonce 重用
- 使用带认证的加密算法，保证密文被修改后能够检测
- 即使数据库泄露，也只能进行高成本的离线猜测
```

## 二、密钥派生方案

主密码不能直接作为 AES 密钥使用，需要通过 KDF 派生。

推荐优先级：

```text
首选：Argon2id
备选：PBKDF2-HMAC-SHA256
```

推荐设计：

```text
master_password
  ↓ KDF(salt, 参数)
key_encryption_key
  ↓ 解密 / 加密
data_encryption_key
  ↓ AES-GCM
具体加密每条密码记录
```

这样做的好处是：修改主密码时只需要重新加密 `data_encryption_key`，不需要重新加密所有密码记录。

`config` 表建议补充：

```text
config
- id
- kdf_name              # Argon2id / PBKDF2
- kdf_params            # iterations / memory_cost / time_cost / parallelism
- salt
- encrypted_dek         # 被主密码派生出的 KEK 加密的数据密钥
- verify_blob
- crypto_version
```

参数建议：

```text
Argon2id：
- salt：至少 16 字节随机数
- memory_cost：可设置 64MB 起步
- time_cost：2 或 3
- parallelism：1 或 2

PBKDF2-HMAC-SHA256：
- salt：至少 16 字节随机数
- iterations：至少 600000 次，可根据本机性能调整
```

参数需要保存在数据库中，因为之后登录时必须使用同一组参数重新派生密钥。

## 三、加密算法与数据格式

密码记录、备注、URL 等字段建议使用 AEAD 算法加密。

推荐：

```text
AES-256-GCM
```

每个加密字段单独保存：

```text
algorithm | nonce | ciphertext | tag
```

注意点：

```text
- AES-GCM 的 nonce 推荐 12 字节，由安全随机数生成
- 同一个 data_encryption_key 下 nonce 绝对不能重复
- tag 不要丢弃，解密时必须校验 tag
- 可以把 entry_id、字段名、crypto_version 作为 AAD，防止密文被移动到其他字段后仍然通过校验
```

`password_entries` 表可以补充：

```text
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

如果为了列表展示方便保留 `title` 明文，需要在报告中说明取舍：标题明文方便搜索和展示，但会泄露部分元数据；更安全的方案是标题也加密。

## 四、主密码校验

不要保存：

```text
hash(master_password)
```

建议保存一个固定明文加密后的 `verify_blob`，例如：

```text
verify_plaintext = "SecureBox verification v1"
verify_blob = AES-GCM(key_encryption_key, verify_plaintext)
```

登录时：

```text
输入主密码
↓
按 config 中保存的 salt 和 KDF 参数派生 key_encryption_key
↓
尝试解密 encrypted_dek 或 verify_blob
↓
tag 校验通过则说明主密码正确
```

## 五、随机数与密码生成

所有安全随机数必须使用密码学安全随机源。

Python 中建议：

```text
salt / nonce / data_encryption_key：os.urandom()
随机密码生成：secrets 模块
```

不要使用：

```text
random 模块
时间戳
用户名拼接
可预测计数器
```

随机密码生成器建议提供：

```text
- 长度选择，默认 16 或 20 位以上
- 大写字母 / 小写字母 / 数字 / 符号开关
- 避免每类字符固定位置，最后统一安全洗牌
- 给出强度或熵估计
```

## 六、文件加密功能补充

文件加密不要把大文件一次性全部读入内存。可以设计为分块加密：

```text
file_header:
- magic: SecureBoxFile
- version
- kdf_name
- kdf_params
- salt
- file_nonce_prefix

chunk:
- chunk_index
- nonce
- ciphertext
- tag
```

每个分块都用 AEAD 加密，并把 `chunk_index` 放入 AAD，防止分块被调换顺序。

文件加密密钥可以：

```text
方案 A：由用户输入的文件密码通过 KDF 派生
方案 B：使用保险箱中的 data_encryption_key 派生文件子密钥
```

如果项目演示重点是密码管理器，文件加密可以作为拓展功能，不必做得过大。

## 七、数据库与程序安全

SQLite 字段加密只能保护字段内容，不能隐藏数据库结构、记录数量、时间戳等元数据。

可以补充的安全措施：

```text
- 所有 SQL 操作使用参数化查询，防止 SQL 注入
- 数据库文件设置合理权限，避免普通用户随意读取
- 自动锁定：空闲一段时间后清空内存中的密钥并回到登录界面
- 剪贴板自动清空：复制密码后 30 秒自动清除
- 登录失败次数限制：连续失败后延迟重试，增加暴力破解成本
- 导出文件必须再次加密，禁止默认导出明文密码
- 删除记录时可以说明 SQLite 普通删除不等于安全擦除
```

Python 内存安全方面可以说明局限：

```text
Python 字符串不可变，主密码和密钥可能短暂留在内存中；
项目可以尽量减少敏感数据驻留时间，但不能保证完全内存清除。
```

## 八、异常处理与完整性

解密失败时要区分处理：

```text
- 主密码错误
- 密文被篡改
- 数据库损坏
- 加密版本不兼容
```

但界面提示不宜暴露过多细节，可以统一显示：

```text
主密码错误或数据已损坏
```

内部日志不要记录：

```text
- 主密码
- 派生密钥
- 明文密码
- 明文备注
- 完整密文和 nonce 组合
```

## 九、可写进报告的加分点

```text
1. 设计威胁模型，明确能防什么、不能防什么
2. 使用 Argon2id / PBKDF2 增加离线破解成本
3. 采用 AES-GCM 同时保证机密性和完整性
4. 每条记录独立 nonce，避免 GCM nonce 重用风险
5. 使用 DEK + KEK 的双层密钥结构，支持主密码更换
6. 使用 AAD 绑定记录 ID 和字段名，防止密文替换攻击
7. 剪贴板清理、自动锁定、登录失败延迟提升实际使用安全性
8. 说明 Python 内存清除和本机已被入侵情况下的安全局限
```
