# RCST 前端功能增强设计

**日期:** 2026-04-19
**状态:** Approved
**类型:** 功能增强 + 重构

---

## 1. 概述

在现有 FunASR 语音翻译前端基础上，增加字幕导出、快捷键和会话管理功能，并采用模块化重构提升代码可维护性。

**新增功能:**
- 字幕历史导出（Markdown 格式）
- 键盘快捷键（Ctrl+S 导出、ESC 停止）
- 会话管理（时长显示、字幕计数、新建会话、暂停/恢复）

---

## 2. 文件结构

```
src/ui/
├── index.html              # 主页面（精简后）
├── js/
│   ├── app.js              # 主应用逻辑
│   ├── audio.js            # 音频捕获管理
│   ├── captions.js         # 字幕历史管理
│   ├── session.js          # 会话管理（时长、计数）
│   ├── export.js           # 导出功能
│   └── shortcuts.js        # 快捷键绑定
└── css/
    └── styles.css          # 样式文件
```

**重构原则:**
- 每个模块单一职责
- 模块间通过明确定义接口通信
- 主 HTML 只做布局和初始化

---

## 3. 新增功能详细设计

### 3.1 字幕导出（export.js）

**功能:**
- 导出会话字幕为 Markdown 文件
- 文件名格式: `RCST_{session_id}_{timestamp}.md`

**导出格式:**
```markdown
# RCST 会话导出

**会话ID:** 20260419_143000
**导出时间:** 2026-04-19 14:35:22
**字幕总数:** 42 条

| 时间 | English | 中文翻譯 |
|------|---------|----------|
| 14:30:01 | Welcome... | 歡迎... |
```

**接口:**
```javascript
// 导出当前会话为 Markdown
exportSessionAsMarkdown(sessionData: CaptionEntry[]): string

// 下载文件
downloadMarkdown(content: string, filename: string): void
```

### 3.2 快捷键（shortcuts.js）

**快捷键绑定:**

| 快捷键 | 功能 |
|--------|------|
| Ctrl + S | 导出会话为 Markdown |
| ESC | 停止当前会话 |

**实现:**
```javascript
interface ShortcutConfig {
    key: string;
    modifiers?: string[];  // ['ctrl', 'shift', 'alt']
    action: () => void;
    description: string;
}
```

### 3.3 会话管理（session.js）

**功能:**
1. **会话时长显示** — 格式 `HH:MM:SS`，每秒更新
2. **字幕计数** — 显示 "已翻 N 条"
3. **新建会话** — 调用 `/session/start` API
4. **暂停/恢复** — 暂停音频捕获，之后可继续

**接口:**
```javascript
interface SessionState {
    sessionId: string;
    startTime: Date;
    isPaused: boolean;
    captionCount: number;
}

startSession(): Promise<string>;
pauseSession(): void;
resumeSession(): void;
getSessionDuration(): string;
```

---

## 4. 模块通信

```
index.html
  ├── app.js (主控制器)
  │     ├── audio.js (音频捕获) → captions.js (字幕历史)
  │     ├── captions.js (字幕存储) → export.js (导出)
  │     ├── session.js (会话状态) → app.js (UI更新)
  │     └── shortcuts.js (快捷键) → 各模块响应
```

**事件通信:**
- 使用 CustomEvent 或简单回调
- 避免全局变量污染
- 事件命名: `session:start`, `session:pause`, `caption:new`, `export:trigger`

---

## 5. UI 变化

### 5.1 Header 区域

```
┌─────────────────────────────────────────────────────┐
│ RCST    [已翻 42 条] [00:05:32] [新建] [暂停]  Ready │
└─────────────────────────────────────────────────────┘
                          ↑新增
```

### 5.2 导出交互

- Ctrl+S 触发导出
- 浏览器自动下载 `.md` 文件
- 状态栏显示 "已导出: RCST_xxx.md"

---

## 6. 实现顺序

1. **重构基础结构** — 创建 js/css 目录，分离样式和脚本
2. **session.js** — 会话状态管理
3. **captions.js** — 字幕历史管理
4. **export.js** — 导出功能
5. **shortcuts.js** — 快捷键绑定
6. **audio.js** — 音频捕获（从 index.html 提取）
7. **app.js** — 主控制器，整合所有模块
8. **更新 index.html** — 使用新模块结构

---

## 7. 验证清单

- [ ] Ctrl+S 成功导出 Markdown 文件
- [ ] ESC 停止当前会话
- [ ] 会话时长实时更新
- [ ] 字幕计数正确
- [ ] 新建会话重置状态
- [ ] 暂停/恢复正常工作
- [ ] 各模块独立运行正常
