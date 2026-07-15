# TodoTab 待办事项管理器 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 Windows 11 免安装单 EXE 待办事项管理器，Python + tkinter，CSV 存储

**Architecture:** DataManager 负责数据和 CSV 持久化；dialogs 提供弹出窗口；app.py 构建主窗口布局和事件绑定；main.py 为入口。PyInstaller 打包为单文件 EXE。

**Tech Stack:** Python 3.10+ (标准库), tkinter, csv, PyInstaller

## Global Constraints

- 零外部运行时依赖（打包时 PyInstaller 除外）
- CSV 文件 `todos.csv` 自动创建于 EXE 同级目录
- 所有字符串使用 UTF-8 编码
- 界面语言：中文
- 软删除（is_deleted 字段），不实际删除 CSV 行
- 分类预置：工作、个人、学习、其他

---

### Task 1: DataManager 数据层

**Files:**
- Create: `todotab/data.py`

**Interfaces:**
- Produces: `class DataManager` — 所有后续任务的数据依赖

- [ ] **Step 1: 创建 data.py，实现 DataManager 类骨架**

```python
import csv
import os
from datetime import datetime

CSV_FILE = 'todos.csv'
CSV_HEADERS = ['id', 'title', 'category', 'priority', 'due_date',
               'status', 'note', 'created_at', 'is_deleted']
DEFAULT_CATEGORIES = ['工作', '个人', '学习', '其他']

class DataManager:
    def __init__(self, csv_path=None):
        self.csv_path = csv_path or CSV_FILE
        self.tasks = []
        self._next_id = 1
        self.categories = DEFAULT_CATEGORIES.copy()
        self.load()

    def load(self):
        if not os.path.exists(self.csv_path):
            self.tasks = []
            self._next_id = 1
            return
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.tasks = []
                max_id = 0
                categories_set = set()
                for row in reader:
                    row['id'] = int(row['id'])
                    row['is_deleted'] = int(row.get('is_deleted', 0))
                    self.tasks.append(row)
                    max_id = max(max_id, row['id'])
                    categories_set.add(row.get('category', ''))
                self._next_id = max_id + 1
                extra = [c for c in categories_set if c and c not in self.categories]
                self.categories.extend(extra)
        except Exception:
            self.tasks = []
            self._next_id = 1

    def save(self):
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(self.tasks)

    def add_task(self, title, category='', priority='中',
                 due_date='', status='待办', note=''):
        task = {
            'id': self._next_id,
            'title': title,
            'category': category,
            'priority': priority,
            'due_date': due_date,
            'status': status,
            'note': note,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'is_deleted': 0,
        }
        self._next_id += 1
        self.tasks.append(task)
        if category and category not in self.categories:
            self.categories.append(category)
        self.save()
        return task['id']

    def update_task(self, task_id, **fields):
        for task in self.tasks:
            if task['id'] == task_id:
                task.update(fields)
                break
        self.save()

    def delete_task(self, task_id):
        for task in self.tasks:
            if task['id'] == task_id:
                task['is_deleted'] = 1
                break
        self.save()

    def get_task(self, task_id):
        for task in self.tasks:
            if task['id'] == task_id:
                return task
        return None

    def get_active_tasks(self):
        return [t for t in self.tasks if not t['is_deleted']]

    def search(self, keyword='', status=None, priority=None, category=None):
        results = self.get_active_tasks()
        if keyword:
            kw = keyword.lower()
            results = [t for t in results if kw in t['title'].lower() or kw in t['note'].lower()]
        if status:
            results = [t for t in results if t['status'] == status]
        if priority:
            results = [t for t in results if t['priority'] == priority]
        if category:
            results = [t for t in results if t['category'] == category]
        return results

    def get_today_tasks(self):
        today = datetime.now().strftime('%Y-%m-%d')
        return [t for t in self.get_active_tasks() if t['due_date'] == today]

    def add_category(self, name):
        if name and name not in self.categories:
            self.categories.append(name)
            self.save()

    def remove_category(self, name):
        if name in DEFAULT_CATEGORIES:
            return
        if name in self.categories:
            self.categories.remove(name)

    def get_categories(self):
        return self.categories.copy()
```

- [ ] **Step 2: 验证 data.py 可导入**

Run: `python -c "from data import DataManager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 创建 todotab/ 目录，放入 data.py**

```bash
New-Item -ItemType Directory -Path "todotab" -Force
Copy-Item data.py todotab/data.py
```

---

### Task 2: DataManager 单元测试

**Files:**
- Create: `todotab/tests/test_data.py`

**Interfaces:**
- Consumes: `DataManager` from `data.py`

- [ ] **Step 1: 创建 tests 目录和测试文件**

```bash
New-Item -ItemType Directory -Path "todotab/tests" -Force
```

```python
import os
import sys
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from data import DataManager

def test_add_and_get_task():
    dm = DataManager(csv_path=tempfile.mktemp(suffix='.csv'))
    tid = dm.add_task('测试任务', category='工作', priority='高')
    task = dm.get_task(tid)
    assert task['title'] == '测试任务'
    assert task['category'] == '工作'
    assert task['priority'] == '高'
    assert task['is_deleted'] == 0

def test_delete_soft():
    dm = DataManager(csv_path=tempfile.mktemp(suffix='.csv'))
    tid = dm.add_task('要删除的')
    dm.delete_task(tid)
    task = dm.get_task(tid)
    assert task['is_deleted'] == 1
    assert len(dm.get_active_tasks()) == 0

def test_update_task():
    dm = DataManager(csv_path=tempfile.mktemp(suffix='.csv'))
    tid = dm.add_task('原标题')
    dm.update_task(tid, title='新标题', status='已完成')
    task = dm.get_task(tid)
    assert task['title'] == '新标题'
    assert task['status'] == '已完成'

def test_search():
    dm = DataManager(csv_path=tempfile.mktemp(suffix='.csv'))
    dm.add_task('买咖啡', category='个人')
    dm.add_task('写报告', category='工作')
    results = dm.search(keyword='报告')
    assert len(results) == 1
    assert results[0]['title'] == '写报告'

def test_search_with_filters():
    dm = DataManager(csv_path=tempfile.mktemp(suffix='.csv'))
    dm.add_task('任务A', category='工作', priority='高', status='进行中')
    dm.add_task('任务B', category='个人', priority='低', status='待办')
    results = dm.search(priority='高')
    assert len(results) == 1
    assert results[0]['title'] == '任务A'

def test_today_tasks():
    dm = DataManager(csv_path=tempfile.mktemp(suffix='.csv'))
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    dm.add_task('今日任务', due_date=today)
    dm.add_task('明日任务', due_date='2099-01-01')
    assert len(dm.get_today_tasks()) == 1
    assert dm.get_today_tasks()[0]['title'] == '今日任务'

def test_categories():
    dm = DataManager(csv_path=tempfile.mktemp(suffix='.csv'))
    assert '工作' in dm.get_categories()
    dm.add_category('健身')
    assert '健身' in dm.get_categories()
    dm.remove_category('健身')
    assert '健身' not in dm.get_categories()

def test_csv_persistence():
    path = tempfile.mktemp(suffix='.csv')
    dm1 = DataManager(csv_path=path)
    dm1.add_task('持久化测试', category='工作')
    dm2 = DataManager(csv_path=path)
    assert len(dm2.get_active_tasks()) == 1
    assert dm2.get_active_tasks()[0]['title'] == '持久化测试'
```

- [ ] **Step 2: 运行测试验证全部通过**

Run: `cd todotab && python -m pytest tests/test_data.py -v`
Expected: 9/9 PASSED

---

### Task 3: 对话框模块 dialogs.py

**Files:**
- Create: `todotab/dialogs.py`
- Modify: `todotab/data.py` (no changes needed)

**Interfaces:**
- Produces: `add_task_dialog(parent, categories, on_save)` / `manage_categories_dialog(parent, categories, on_update)`

- [ ] **Step 1: 创建 dialogs.py**

```python
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class AddTaskDialog(tk.Toplevel):
    def __init__(self, parent, categories, on_save):
        super().__init__(parent)
        self.title('添加任务')
        self.geometry('400x350')
        self.resizable(False, False)
        self.on_save = on_save
        self.transient(parent)
        self.grab_set()

        row = 0
        tk.Label(self, text='标题 *').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.title_entry = tk.Entry(self, width=35)
        self.title_entry.grid(row=row, column=1, padx=10, pady=5)
        self.title_entry.focus()
        row += 1

        tk.Label(self, text='分类').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.category_combo = ttk.Combobox(self, values=categories, width=32, state='readonly')
        self.category_combo.set(categories[0] if categories else '')
        self.category_combo.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        tk.Label(self, text='优先级').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.priority_combo = ttk.Combobox(self, values=['高', '中', '低'], width=32, state='readonly')
        self.priority_combo.set('中')
        self.priority_combo.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        tk.Label(self, text='截止日期').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.date_entry = tk.Entry(self, width=35)
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        tk.Label(self, text='备注').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        self.note_text = tk.Text(self, width=35, height=4)
        self.note_text.grid(row=row, column=1, padx=10, pady=5)
        row += 1

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)
        tk.Button(btn_frame, text='确定', width=10, command=self._on_ok).pack(side='left', padx=5)
        tk.Button(btn_frame, text='取消', width=10, command=self.destroy).pack(side='left', padx=5)

        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self.destroy())

    def _on_ok(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning('提示', '标题不能为空', parent=self)
            self.title_entry.focus()
            return
        self.on_save({
            'title': title,
            'category': self.category_combo.get(),
            'priority': self.priority_combo.get(),
            'due_date': self.date_entry.get().strip(),
            'status': '待办',
            'note': self.note_text.get('1.0', 'end-1c').strip(),
        })
        self.destroy()


class ManageCategoriesDialog(tk.Toplevel):
    def __init__(self, parent, categories, on_update):
        super().__init__(parent)
        self.title('管理分类')
        self.geometry('350x300')
        self.resizable(False, False)
        self.on_update = on_update
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text='双击分类名可删除（预置分类不可删除）',
                 fg='gray', font=('Microsoft YaHei', 9)).pack(pady=5)

        list_frame = tk.Frame(self)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)

        for c in categories:
            self.listbox.insert('end', c)

        self.listbox.bind('<Double-Button-1>', self._on_delete)

        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill='x', padx=10, pady=5)

        self.new_entry = tk.Entry(bottom_frame, width=20)
        self.new_entry.pack(side='left', padx=(0, 5))
        tk.Button(bottom_frame, text='添加', command=self._on_add).pack(side='left')
        tk.Button(bottom_frame, text='关闭', command=self.destroy).pack(side='right')

        self.bind('<Escape>', lambda e: self.destroy())

    def _on_add(self):
        name = self.new_entry.get().strip()
        if name:
            self.on_update('add', name)
            self.listbox.insert('end', name)
            self.new_entry.delete(0, 'end')

    def _on_delete(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        name = self.listbox.get(sel[0])
        if name in ['工作', '个人', '学习', '其他']:
            messagebox.showinfo('提示', '预置分类不可删除', parent=self)
            return
        if messagebox.askyesno('确认', f'确定删除分类「{name}」？', parent=self):
            self.on_update('remove', name)
            self.listbox.delete(sel[0])
```

- [ ] **Step 2: 验证 dialogs.py 可导入**

Run: `python -c "from dialogs import AddTaskDialog, ManageCategoriesDialog; print('OK')"`
Expected: `OK`

---

### Task 4: 主窗口 app.py

**Files:**
- Create: `todotab/app.py`

**Interfaces:**
- Consumes: `DataManager` from `data.py`, dialogs from `dialogs.py`
- Produces: `class TodoApp`

- [ ] **Step 1: 创建 app.py — 主窗口类 TodoApp**

```python
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from data import DataManager
from dialogs import AddTaskDialog, ManageCategoriesDialog

PRIORITY_COLORS = {'高': '#E74C3C', '中': '#F39C12', '低': '#27AE60'}
STATUS_ICON = {'待办': '○', '进行中': '●', '已完成': '✓'}

class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title('TodoTab 待办事项管理器')
        self.root.geometry('1000x600')
        self.root.minsize(800, 450)

        self.data = DataManager()

        self._build_ui()
        self._bind_events()
        self._refresh_tabs()

    def _build_ui(self):
        # === Tab bar ===
        tab_frame = tk.Frame(self.root)
        tab_frame.pack(fill='x', padx=5, pady=(5, 0))

        self.tab_buttons = {}
        self.active_tab = None
        self.tab_names = ['全部', '今日', '进行中', '已完成']
        self.tab_frame_ref = tab_frame

        # === Toolbar ===
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill='x', padx=5, pady=5)

        tk.Button(toolbar, text='+ 添加任务', command=self._on_add_task,
                  bg='#3498DB', fg='white', relief='flat', padx=10).pack(side='left')

        tk.Label(toolbar, text='  搜索:').pack(side='left')
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *a: self._refresh_list())
        tk.Entry(toolbar, textvariable=self.search_var, width=25).pack(side='left', padx=5)

        tk.Label(toolbar, text='优先级:').pack(side='left', padx=(10, 0))
        self.filter_priority = ttk.Combobox(toolbar, values=['全部', '高', '中', '低'],
                                            width=6, state='readonly')
        self.filter_priority.set('全部')
        self.filter_priority.bind('<<ComboboxSelected>>', lambda e: self._refresh_list())
        self.filter_priority.pack(side='left', padx=2)

        tk.Label(toolbar, text='状态:').pack(side='left', padx=(5, 0))
        self.filter_status = ttk.Combobox(toolbar, values=['全部', '待办', '进行中', '已完成'],
                                          width=8, state='readonly')
        self.filter_status.set('全部')
        self.filter_status.bind('<<ComboboxSelected>>', lambda e: self._refresh_list())
        self.filter_status.pack(side='left', padx=2)

        # === Main area ===
        main_paned = tk.PanedWindow(self.root, orient='horizontal', sashwidth=3)
        main_paned.pack(fill='both', expand=True, padx=5, pady=(0, 5))

        # Left: task list
        left_frame = tk.Frame(main_paned)
        columns = ('status', 'title', 'priority', 'due_date', 'category')
        self.tree = ttk.Treeview(left_frame, columns=columns, show='tree',
                                 selectmode='browse')
        self.tree.heading('#0', text='')
        self.tree.column('#0', width=30, stretch=False)
        self.tree.heading('status', text='')
        self.tree.column('status', width=30, stretch=False, anchor='center')
        self.tree.heading('title', text='任务')
        self.tree.column('title', width=250)
        self.tree.heading('priority', text='优先级')
        self.tree.column('priority', width=70, anchor='center')
        self.tree.heading('due_date', text='截止日期')
        self.tree.column('due_date', width=100, anchor='center')
        self.tree.heading('category', text='分类')
        self.tree.column('category', width=80, anchor='center')

        vsb = tk.Scrollbar(left_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        main_paned.add(left_frame, width=550)

        # Right: detail panel
        self.detail_frame = tk.Frame(main_paned, relief='groove', bd=1)
        self._build_detail_panel()
        main_paned.add(self.detail_frame, width=400)

    def _build_detail_panel(self):
        for w in self.detail_frame.winfo_children():
            w.destroy()

        pad = {'padx': 10, 'pady': 3}
        tk.Label(self.detail_frame, text='任务详情', font=('Microsoft YaHei', 12, 'bold')).pack(anchor='w', **pad)

        self.detail_title = tk.Entry(self.detail_frame, font=('Microsoft YaHei', 11))
        self.detail_title.pack(fill='x', **pad)

        cat_frame = tk.Frame(self.detail_frame)
        cat_frame.pack(fill='x', **pad)
        tk.Label(cat_frame, text='分类:').pack(side='left')
        self.detail_category = ttk.Combobox(cat_frame, values=self.data.get_categories(), width=15, state='readonly')
        self.detail_category.pack(side='left', padx=5)

        tk.Label(cat_frame, text='优先级:').pack(side='left', padx=(10, 0))
        self.detail_priority = ttk.Combobox(cat_frame, values=['高', '中', '低'], width=5, state='readonly')
        self.detail_priority.pack(side='left', padx=5)

        date_frame = tk.Frame(self.detail_frame)
        date_frame.pack(fill='x', **pad)
        tk.Label(date_frame, text='截止日期:').pack(side='left')
        self.detail_date = tk.Entry(date_frame, width=15)
        self.detail_date.pack(side='left', padx=5)

        tk.Label(date_frame, text='状态:').pack(side='left', padx=(10, 0))
        self.detail_status = ttk.Combobox(date_frame, values=['待办', '进行中', '已完成'], width=8, state='readonly')
        self.detail_status.pack(side='left', padx=5)

        tk.Label(self.detail_frame, text='备注:').pack(anchor='w', **pad)
        self.detail_note = tk.Text(self.detail_frame, height=5)
        self.detail_note.pack(fill='x', **pad)

        btn_frame = tk.Frame(self.detail_frame)
        btn_frame.pack(fill='x', pady=10, padx=10)
        tk.Button(btn_frame, text='💾 保存', command=self._on_save_detail,
                  bg='#2ECC71', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        tk.Button(btn_frame, text='🗑 删除', command=self._on_delete_task,
                  bg='#E74C3C', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        tk.Button(btn_frame, text='✓ 切换完成', command=self._on_toggle_done,
                  bg='#3498DB', fg='white', relief='flat', padx=10).pack(side='left', padx=2)

        self.detail_id = None

    def _bind_events(self):
        self.tree.bind('<<TreeviewSelect>>', self._on_select_task)

    def _refresh_tabs(self):
        for w in self.tab_frame_ref.winfo_children():
            w.destroy()
        self.tab_buttons.clear()

        all_tabs = self.tab_names + self.data.get_categories()
        all_tabs.append('+')

        for name in all_tabs:
            if name == '+':
                btn = tk.Button(self.tab_frame_ref, text='+', width=3,
                                command=self._on_add_category_tab,
                                relief='flat', font=('Microsoft YaHei', 10, 'bold'))
            else:
                is_active = (self.active_tab is None and name == '全部') or (self.active_tab == name)
                bg = '#3498DB' if is_active else '#E0E0E0'
                fg = 'white' if is_active else 'black'
                btn = tk.Button(self.tab_frame_ref, text=name, bg=bg, fg=fg,
                                relief='flat', padx=10,
                                command=lambda n=name: self._switch_tab(n))
            btn.pack(side='left', padx=1)
            if name != '+':
                self.tab_buttons[name] = btn

        if self.active_tab is None:
            self.active_tab = '全部'
        self._refresh_list()

    def _switch_tab(self, name):
        for n, btn in self.tab_buttons.items():
            if n == name:
                btn.configure(bg='#3498DB', fg='white')
            else:
                btn.configure(bg='#E0E0E0', fg='black')
        self.active_tab = name
        self._refresh_list()

    def _on_add_category_tab(self):
        from dialogs import ManageCategoriesDialog
        def on_update(action, name):
            if action == 'add':
                self.data.add_category(name)
            elif action == 'remove':
                self.data.remove_category(name)
            self._refresh_tabs()
        ManageCategoriesDialog(self.root, self.data.get_categories(), on_update)

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        keyword = self.search_var.get().strip()
        p_filter = self.filter_priority.get()
        s_filter = self.filter_status.get()

        if self.active_tab == '今日':
            tasks = self.data.get_today_tasks()
        elif self.active_tab == '进行中':
            tasks = self.data.search(status='进行中')
        elif self.active_tab == '已完成':
            tasks = self.data.search(status='已完成')
        elif self.active_tab in self.data.get_categories():
            tasks = self.data.search(category=self.active_tab)
        else:
            tasks = self.data.get_active_tasks()

        if keyword:
            tasks = [t for t in tasks if keyword.lower() in t['title'].lower() or keyword.lower() in t['note'].lower()]
        if p_filter != '全部':
            tasks = [t for t in tasks if t['priority'] == p_filter]
        if s_filter != '全部':
            tasks = [t for t in tasks if t['status'] == s_filter]

        today_str = datetime.now().strftime('%Y-%m-%d')

        for t in tasks:
            icon = STATUS_ICON.get(t['status'], '○')
            priority_color = PRIORITY_COLORS.get(t['priority'], 'black')
            tags = []

            if t['due_date'] and t['due_date'] < today_str and t['status'] != '已完成':
                tags.append('overdue')
            elif t['due_date'] == today_str and t['status'] != '已完成':
                tags.append('today')

            self.tree.insert('', 'end',
                             iid=str(t['id']),
                             text=icon,
                             values=(icon, t['title'],
                                     f'  {t["priority"]}  ',
                                     t['due_date'] if t['due_date'] else '-',
                                     t['category']),
                             tags=tags)

        self.tree.tag_configure('overdue', foreground='#E74C3C')
        self.tree.tag_configure('today', foreground='#E67E22')

    def _on_select_task(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        task_id = int(sel[0])
        task = self.data.get_task(task_id)
        if not task:
            return
        self.detail_id = task['id']
        self.detail_title.delete(0, 'end')
        self.detail_title.insert(0, task['title'])
        self.detail_category.set(task['category'])
        self.detail_priority.set(task['priority'])
        self.detail_date.delete(0, 'end')
        self.detail_date.insert(0, task['due_date'])
        self.detail_status.set(task['status'])
        self.detail_note.delete('1.0', 'end')
        self.detail_note.insert('1.0', task['note'])

    def _on_save_detail(self):
        if self.detail_id is None:
            return
        title = self.detail_title.get().strip()
        if not title:
            messagebox.showwarning('提示', '标题不能为空')
            return
        self.data.update_task(
            self.detail_id,
            title=title,
            category=self.detail_category.get(),
            priority=self.detail_priority.get(),
            due_date=self.detail_date.get().strip(),
            status=self.detail_status.get(),
            note=self.detail_note.get('1.0', 'end-1c').strip(),
        )
        self._refresh_list()

    def _on_delete_task(self):
        if self.detail_id is None:
            return
        if messagebox.askyesno('确认删除', '确定要删除该任务吗？'):
            self.data.delete_task(self.detail_id)
            self.detail_id = None
            self._build_detail_panel()
            self._refresh_list()

    def _on_toggle_done(self):
        if self.detail_id is None:
            return
        task = self.data.get_task(self.detail_id)
        if not task:
            return
        new_status = '已完成' if task['status'] != '已完成' else '待办'
        self.data.update_task(self.detail_id, status=new_status)
        self.detail_status.set(new_status)
        self._refresh_list()

    def _on_add_task(self):
        def on_save(data):
            self.data.add_task(**data)
            self._refresh_tabs()
        AddTaskDialog(self.root, self.data.get_categories(), on_save)
```

- [ ] **Step 2: 验证 app.py 可导入**

Run: `python -c "from app import TodoApp; print('OK')"`
Expected: `OK`

---

### Task 5: 程序入口 main.py

**Files:**
- Create: `todotab/main.py`

- [ ] **Step 1: 创建 main.py**

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from app import TodoApp

def main():
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 验证程序可启动不报错（无 GUI 环境也可测试导入）**

Run: `python -c "import sys; sys.path.insert(0, 'todotab'); from app import TodoApp; print('OK')"`
Expected: `OK`

---

### Task 6: 集成测试与手动验证

**Files:** 无新建

- [ ] **Step 1: 从 todotab/ 目录启动程序**

Run: `cd todotab && python main.py`
Expected: 窗口弹出，显示"全部"标签页，空列表

- [ ] **Step 2: 手动验证功能清单**
  - 点击「+ 添加任务」→ 弹出对话框 → 填写标题"测试" → 确定 → 列表中出现
  - 点击任务 → 右侧详情面板显示内容
  - 修改标题 → 点保存 → 列表刷新
  - 点「✓ 切换完成」 → 状态变"已完成"，图标变 ✓
  - 点「🗑 删除」 → 确认 → 任务消失
  - 切换标签页：今日 / 进行中 / 已完成
  - 搜索框输入关键词 → 列表实时过滤
  - 优先级筛选 / 状态筛选
  - 点击「+」标签页 → 添加分类 → 新分类标签页出现
  - 关闭程序 → 重新打开 → 数据持久化

---

### Task 7: PyInstaller 打包

**Files:**
- Create: `todotab/TodoTab.spec` (可由 PyInstaller 自动生成)
- Output: `dist/TodoTab.exe`

- [ ] **Step 1: 安装 PyInstaller**

```bash
pip install pyinstaller
```

- [ ] **Step 2: 打包为单文件 EXE**

```bash
cd todotab
pyinstaller --onefile --windowed --name TodoTab --add-data "todos.csv;." main.py
```

说明：`--add-data` 将初始空 CSV 嵌入；首次运行时若 EXE 同目录无 CSV 则自动创建。

- [ ] **Step 3: 验证 EXE 可运行**

```bash
dist\TodoTab.exe
```
Expected: 程序正常启动，无控制台窗口，所有功能正常

- [ ] **Step 4: 复制 EXE 到独立目录，验证免安装**

```bash
mkdir final_dist
copy dist\TodoTab.exe final_dist\
```
双击 `final_dist\TodoTab.exe`，确认无需 Python 即可运行
