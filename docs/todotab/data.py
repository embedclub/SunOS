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
