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
        tab_frame = tk.Frame(self.root)
        tab_frame.pack(fill='x', padx=5, pady=(5, 0))

        self.tab_buttons = {}
        self.active_tab = None
        self.tab_names = ['全部', '今日', '进行中', '已完成']
        self.tab_frame_ref = tab_frame

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

        main_paned = tk.PanedWindow(self.root, orient='horizontal', sashwidth=3)
        main_paned.pack(fill='both', expand=True, padx=5, pady=(0, 5))

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

        self.detail_frame = tk.Frame(main_paned, relief='groove', bd=1)
        self._build_detail_panel()
        main_paned.add(self.detail_frame, width=400)

    def _build_detail_panel(self):
        for w in self.detail_frame.winfo_children():
            w.destroy()

        pad = {'padx': 10, 'pady': 3}
        tk.Label(self.detail_frame, text='任务详情',
                 font=('Microsoft YaHei', 12, 'bold')).pack(anchor='w', **pad)

        self.detail_title = tk.Entry(self.detail_frame, font=('Microsoft YaHei', 11))
        self.detail_title.pack(fill='x', **pad)

        cat_frame = tk.Frame(self.detail_frame)
        cat_frame.pack(fill='x', **pad)
        tk.Label(cat_frame, text='分类:').pack(side='left')
        self.detail_category = ttk.Combobox(cat_frame, values=self.data.get_categories(),
                                            width=15, state='readonly')
        self.detail_category.pack(side='left', padx=5)

        tk.Label(cat_frame, text='优先级:').pack(side='left', padx=(10, 0))
        self.detail_priority = ttk.Combobox(cat_frame, values=['高', '中', '低'],
                                            width=5, state='readonly')
        self.detail_priority.pack(side='left', padx=5)

        date_frame = tk.Frame(self.detail_frame)
        date_frame.pack(fill='x', **pad)
        tk.Label(date_frame, text='截止日期:').pack(side='left')
        self.detail_date = tk.Entry(date_frame, width=15)
        self.detail_date.pack(side='left', padx=5)

        tk.Label(date_frame, text='状态:').pack(side='left', padx=(10, 0))
        self.detail_status = ttk.Combobox(date_frame, values=['待办', '进行中', '已完成'],
                                          width=8, state='readonly')
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
            tasks = [t for t in tasks if keyword.lower() in t['title'].lower()
                     or keyword.lower() in t['note'].lower()]
        if p_filter != '全部':
            tasks = [t for t in tasks if t['priority'] == p_filter]
        if s_filter != '全部':
            tasks = [t for t in tasks if t['status'] == s_filter]

        today_str = datetime.now().strftime('%Y-%m-%d')

        for t in tasks:
            icon = STATUS_ICON.get(t['status'], '○')
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
        self.detail_category['values'] = self.data.get_categories()
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
