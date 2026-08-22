import os
import sys
from pathlib import Path
import pytest

# Set up paths
root_dir = Path(__file__).resolve().parent.parent.parent.parent
backend_dir = root_dir / "backend"

for p in [str(root_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.conf import settings
import apps.knowledge_base.tasks as kb_tasks


def test_celery_beat_schedule_structure():
    """Verify CELERY_BEAT_SCHEDULE contains 10m (HN/RSS), 1h (GitHub), and 6h (arXiv) tasks."""
    schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
    assert isinstance(schedule, dict), "CELERY_BEAT_SCHEDULE must be a dictionary"
    
    # 1. Verify 10m Tasks (HN, RSS feeds, background scraping)
    ten_min_tasks = [
        k for k, v in schedule.items()
        if (isinstance(v.get('schedule'), (int, float)) and v.get('schedule') == 600.0)
        or "*/10" in str(v.get('schedule'))
    ]
    assert len(ten_min_tasks) >= 1, "Must contain at least one 10-minute recurring ingestion task"
    
    # 2. Verify 1h Task (GitHub Releases)
    one_hour_tasks = [
        k for k, v in schedule.items()
        if (isinstance(v.get('schedule'), (int, float)) and v.get('schedule') == 3600.0)
        or (hasattr(v.get('schedule'), 'hour') and str(v.get('schedule').hour) == '*')
    ]
    assert len(one_hour_tasks) >= 1, "Must contain a 1-hour recurring GitHub Releases ingestion task"
    
    # 3. Verify 6h Task (arXiv Research Papers)
    six_hour_tasks = [
        k for k, v in schedule.items()
        if (isinstance(v.get('schedule'), (int, float)) and v.get('schedule') == 21600.0)
        or "*/6" in str(v.get('schedule'))
    ]
    assert len(six_hour_tasks) >= 1, "Must contain a 6-hour recurring arXiv papers ingestion task"


def test_celery_task_bindings_exist():
    """Verify all task functions referenced in the Beat schedule exist and are callable in kb_tasks."""
    schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
    for schedule_name, schedule_config in schedule.items():
        task_path = schedule_config.get('task')
        assert task_path is not None, f"Schedule '{schedule_name}' must specify a 'task' string"
        
        task_func_name = task_path.split('.')[-1]
        assert hasattr(kb_tasks, task_func_name), f"Task function '{task_func_name}' must exist in apps.knowledge_base.tasks"
        task_obj = getattr(kb_tasks, task_func_name)
        assert callable(task_obj), f"Task '{task_func_name}' must be callable"
