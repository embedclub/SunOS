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
