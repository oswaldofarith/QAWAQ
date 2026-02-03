
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qawaq_project.settings')
import sys
sys.path.append(os.getcwd())
django.setup()

from django_q.tasks import async_task
from monitor.tasks import check_equipment_alerts_task

def test_task():
    print("Enqueuing check_equipment_alerts_task...")
    task_id = async_task('monitor.tasks.check_equipment_alerts_task')
    print(f"Task enqueued: {task_id}")

if __name__ == '__main__':
    test_task()
