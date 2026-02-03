
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qawaq_project.settings')
import sys
sys.path.append(os.getcwd())
django.setup()

from django_q.models import Task

def check_results():
    print("Checking recent task results for 'monitor.tasks.check_equipment_alerts_task':")
    tasks = Task.objects.filter(func='monitor.tasks.check_equipment_alerts_task').order_by('-started')[:5]
    
    if not tasks:
        print("No executed tasks found.")
    
    for t in tasks:
        print(f"ID: {t.id} | Func: {t.func} | Success: {t.success}")
        if not t.success:
            print(f"Result: {t.result}")

if __name__ == '__main__':
    check_results()
