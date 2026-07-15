# TodoTab — 标签页式待办事项管理器 设计文档

## 1. 概述

Windows 11 桌面待办事项程序，使用 Python 3 + tkinter 开发，CSV 文件存储数据。采用标签页式布局，支持任务的增删改查、分类管理、优先级标记、截止日期和搜索过滤。

## 2. 技术栈

| 项 | 选择 |
|---|---|
| 语言 | Python 3.10+ |
| GUI 框架 | tkinter（标准库） |
| 数据存储 | CSV 文件 (`todos.csv`) |
| 外部依赖 | 零（仅标准库） |

## 3. 功能规格

### 3.1 核心功能

- **添加任务**：弹出对话框输入标题、分类、优先级、截止日期、备注
- **编辑任务**：双击或右键任务，在详情面板中修改
- **删除任务**：确认后从列表和数据文件中移除
- **标记完成/未完成**：点击复选框切换状态
- **查看详情**：点击任务在右侧面板显示完整信息

### 3.2 分类管理

- 预置分类：工作、个人、学习、其他
- 支持新增/编辑/删除自定义分类
- 标签页栏按分类显示对应任务

### 3.3 优先级

- 三级：高（🔴 红色）、中（🟡 黄色）、低（🟢 绿色）
- 列表中用颜色标签直观显示

### 3.4 截止日期

- 日期输入格式 `YYYY-MM-DD`
- 逾期任务自动红色高亮
- 今日到期任务橙色高亮

### 3.5 搜索与过滤

- 关键词实时搜索（匹配标题和备注）
- 组合过滤：按状态 + 优先级 + 分类

### 3.6 标签页

| 标签页 | 内容 |
|---|---|
| 全部 | 所有未删除任务 |
| 今日 | 截止日期为今天的任务 |
| 进行中 | status=进行中的任务 |
| 已完成 | status=已完成的任务 |
| [分类名] | 动态生成，每个分类一个标签页 |

## 4. 数据结构

### CSV Schema

```csv
id,title,category,priority,due_date,status,note,created_at,is_deleted
1,完成季度报告,工作,高,2026-07-20,进行中,需要汇总数据,2026-07-15 09:00,0
```

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int | 自增唯一 ID |
| title | str | 任务标题（必填） |
| category | str | 分类名称 |
| priority | str | 高/中/低 |
| due_date | str | 截止日期 YYYY-MM-DD 或空 |
| status | str | 待办 / 进行中 / 已完成 |
| note | str | 备注文字 |
| created_at | str | 创建时间 YYYY-MM-DD HH:MM |
| is_deleted | int | 0=正常, 1=已删除（软删除） |

## 5. 界面布局

```
┌──────────────────────────────────────────────────┐
│  TodoTab  待办事项管理器                    — □ × │
├──────────────────────────────────────────────────┤
│  [全部] [今日] [进行中] [已完成] [工作] [个人] + │  ← 标签页栏（含添加分类按钮）
├──────────────────────────────────────────────────┤
│  [+] 添加任务   搜索: [______________]  [筛选▼]  │  ← 工具栏
├───────────────────────┬──────────────────────────┤
│  任务列表 (Treeview)   │  详情面板                │
│                       │                          │
│  🔴 完成项目报告  高  │  标题: [___________]     │
│     📅 2026-07-20     │  分类: [工作▼]           │
│  🟡 去健身房      中  │  优先级: [高▼]           │
│     📅 2026-07-16     │  截止: [2026-07-20] [📅] │
│  🟢 读一本书      低  │  备注: [___________]     │
│     📅 -              │  状态: [进行中▼]         │
│                       │                          │
│                       │  [💾 保存] [🗑 删除]     │
│                       │  [✓ 标记完成]            │
└───────────────────────┴──────────────────────────┘
```

## 6. 模块设计

### 6.1 文件结构

```
todotab/
├── main.py          # 程序入口，启动主循环
├── app.py           # 主窗口类 TodoApp，构建布局和事件绑定
├── data.py          # DataManager：CSV 读写、CRUD 操作、搜索过滤
├── dialogs.py       # 对话框：添加任务、编辑分类、关于等
└── todos.csv        # 数据文件（首次运行时自动创建）
```

### 6.2 模块职责

| 模块 | 类/函数 | 职责 |
|---|---|---|
| `main.py` | `main()` | 创建 TodoApp 实例，启动 mainloop |
| `app.py` | `class TodoApp` | 构建整个窗口布局、标签页、工具栏、列表、详情面板；绑定事件 |
| `data.py` | `class DataManager` | CSV 加载/保存；任务 CRUD；分类 CRUD；搜索过滤逻辑 |
| `dialogs.py` | `add_task_dialog()` | 添加任务弹出窗口 |
| | `manage_categories_dialog()` | 管理分类弹出窗口 |

### 6.3 数据流

```
DataManager (内存: list[dict])
    ↕ CSV 文件读写
    ↕ CRUD 接口供 TodoApp 调用
        ↓
TodoApp 收到用户操作 → 调用 DataManager 方法 → 刷新界面
```

### 6.4 关键接口

```python
class DataManager:
    def load(self) -> list[dict]
    def save(self)
    def add_task(self, task: dict) -> int
    def update_task(self, task_id: int, fields: dict)
    def delete_task(self, task_id: int)
    def get_task(self, task_id: int) -> dict
    def search(self, keyword: str, **filters) -> list[dict]
    def get_categories(self) -> list[str]
    def add_category(self, name: str)
    def remove_category(self, name: str)
```

## 7. 错误处理

- CSV 文件损坏 → 自动备份原文件，创建空数据集
- 空标题添加 → 弹出提示，不允许保存
- 日期格式错误 → 显示红色边框提示
- 文件读写失败 → 弹出错误对话框，不丢失内存数据

## 8. 交付物

单个免安装 EXE 文件 `TodoTab.exe`，双击即可启动，无需安装 Python 或任何依赖。

### 打包方案

使用 PyInstaller 将 Python 脚本打包为单文件 EXE：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name TodoTab main.py
```

- `--onefile`：单文件输出，所有依赖内嵌
- `--windowed`：不显示控制台窗口
- 输出文件 `dist/TodoTab.exe`，约 8-15 MB
- CSV 数据文件 (`todos.csv`) 在首次运行时自动创建在 EXE 同级目录
