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
