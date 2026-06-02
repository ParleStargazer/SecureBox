# SecureBox 演示清单

## 准备

```powershell
conda activate securebox
python -m pytest
python -m ruff check .
python -m securebox
```

演示时强调：

```text
- SecureBox 是本地应用
- 不提供 Web 版
- 不部署远程服务
- 交付目标是 Windows exe 和 Android apk
```

## 核心流程

```text
1. 第一次启动，设置主密码
2. 进入保险箱页面
3. 新增一条密码记录
4. 关闭或锁定后重新登录
5. 查看、修改、删除密码记录
6. 打开 SQLite 数据库，证明没有明文密码
7. 使用随机密码生成器
8. 展示弱密码和强密码评分
9. 使用文本加密和解密
10. 使用文件加密和解密
```

## 安全演示

```text
- 错误主密码无法登录
- 篡改密文后解密失败
- 每次加密 nonce 不同
- 修改主密码后已有记录仍可解密
- 复制密码后触发剪贴板清理逻辑
- 空闲后触发自动锁定逻辑
```

## 报告要点

```text
- 威胁模型：主要防本地数据库泄露后的离线破解
- KDF：Argon2id 优先，PBKDF2 作为备选
- 加密：AES-256-GCM 同时提供机密性和完整性
- nonce：每个字段、每个文件 chunk 独立随机 nonce
- AAD：绑定记录 ID、字段名、版本或 chunk index，防止替换攻击
- 密钥结构：主密码派生 KEK，KEK 加密 DEK，DEK 加密记录
- 安全边界：本机完全失陷、键盘记录器、运行时内存读取不在主要防护范围内
- 交付边界：只提供本地 exe/apk，不做 Web 版
```

