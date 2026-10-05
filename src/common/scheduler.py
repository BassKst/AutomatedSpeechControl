# Файл: utils/scheduler.py

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Union
import re

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.job import Job

# --- ИЗМЕНЕНИЕ: Импортируем классы триггеров напрямую ---
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from assistant_core.database.models import DATABASE_URL

logger = logging.getLogger(__name__)
logging.getLogger('apscheduler').setLevel(logging.INFO)


class TaskScheduler:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TaskScheduler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'scheduler'):
            SYNC_DATABASE_URL = re.sub(r"\+.+://", "://", DATABASE_URL)
            jobstores = {'default': SQLAlchemyJobStore(url=SYNC_DATABASE_URL)}
            executors = {'default': AsyncIOExecutor()}
            job_defaults = {
                'coalesce': True,
                'misfire_grace_time': (60 * 60 * 24 * 7), # неделя
                'max_instances': 1,
            }
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=ZoneInfo("Europe/Moscow")
            )

            self._pending_jobs = []
            self._lock = asyncio.Lock()

    async def start(self):
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logging.info("Планировщик запущен.")

            async with self._lock:
                if self._pending_jobs:
                    logging.info(f"Добавление {len(self._pending_jobs)} отложенных задач...")
                    for pending_job in self._pending_jobs:
                        # Мы сохраняем вызов метода и его аргументы, теперь вызываем его
                        schedule_func = getattr(self, pending_job["method_name"])
                        await schedule_func(**pending_job["params"])
                    self._pending_jobs.clear()
                    logging.info("Все отложенные задачи добавлены.")
        except Exception as e:
            logging.error(f"Ошибка при запуске планировщика: {e}")
            raise

    async def _schedule_wrapper(self, method_name: str, params: dict):
        """
        Проверяет, запущен ли планировщик. Если да - выполняет метод немедленно.
        Если нет - добавляет вызов в очередь отложенных задач.
        """
        if self.scheduler.running:
            # Если планировщик уже работает, вызываем нужный метод напрямую
            schedule_func = getattr(self, method_name)
            # Передаем только параметры, специфичные для этого метода
            return await schedule_func(**params)
        else:
            # Если планировщик не запущен, сохраняем вызов для будущего
            async with self._lock:
                logging.info(
                    f"Планировщик не запущен. Задача '{params.get('job_id')}' добавлена в очередь на отложенное планирование.")
                self._pending_jobs.append({"method_name": method_name, "params": params})
            return None  # Возвращаем None, так как объект Job еще не создан

    async def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logging.info("Планировщик остановлен.")

    # --- ИЗМЕНЕНИЕ: Внутренний метод теперь принимает ГОТОВЫЙ ОБЪЕКТ ТРИГГЕРА ---
    async def _add_job(self, job_id: str, func_ref: str, trigger: Union[DateTrigger, IntervalTrigger, CronTrigger],
                       args: Optional[List] = None, kwargs: Optional[Dict] = None) -> Optional[Job]:
        """Внутренний метод для добавления задачи с явным объектом триггера."""
        if not isinstance(func_ref, str) or ':' not in func_ref:
            raise ValueError(
                "Функция 'func_ref' должна быть строкой-ссылкой в формате 'module.submodule:function_name'")

        try:
            job = self.scheduler.add_job(
                func_ref,
                trigger=trigger,  # Передаем готовый объект
                args=args,
                kwargs=kwargs,
                id=job_id,
                replace_existing=True,
            )
            logging.info(f"Задача '{job_id}' успешно добавлена/обновлена. Триггер: {trigger}")
            return job
        except Exception as e:
            logging.error(f"Не удалось добавить задачу '{job_id}': {e}")
            return None

    # 1) Запустить задачу в определенную дату/время
    async def schedule_once(self, job_id: str, func_ref: str, run_date: datetime, args: Optional[List] = None,
                            kwargs: Optional[Dict] = None) -> Optional[Job]:
        if not self.scheduler.running:
            # Если планировщик не запущен, используем обертку для отложенного вызова
            params = locals()
            params.pop('self')
            return await self._schedule_wrapper('_schedule_once_internal', params)
        return await self._schedule_once_internal(job_id, func_ref, run_date, args, kwargs)

    async def _schedule_once_internal(self, job_id: str, func_ref: str, run_date: datetime, args: Optional[List] = None,
                                     kwargs: Optional[Dict] = None) -> Optional[Job]:
        trigger = DateTrigger(run_date=run_date)
        return await self._add_job(job_id, func_ref, trigger, args, kwargs)

    # 2) Запускать задачу каждые n секунд/минут/часов
    async def schedule_interval(self, job_id: str, func_ref: str, args: Optional[List] = None,
                                kwargs: Optional[Dict] = None, **interval_kwargs) -> Optional[Job]:
        if not self.scheduler.running:
            params = locals()
            params.pop('self')
            # kwargs из **interval_kwargs нужно смержить в основной словарь
            params.update(params.pop('interval_kwargs'))
            return await self._schedule_wrapper('_schedule_interval_internal', params)
        return await self._schedule_interval_internal(job_id, func_ref, args, kwargs, **interval_kwargs)

    async def _schedule_interval_internal(self, job_id: str, func_ref: str, args: Optional[List] = None,
                                         kwargs: Optional[Dict] = None, **interval_kwargs) -> Optional[Job]:
        trigger = IntervalTrigger(**interval_kwargs)
        return await self._add_job(job_id, func_ref, trigger, args, kwargs)

    # 3) Запускать задачу каждые n секунд на протяжении m секунд
    async def schedule_interval_for_duration(self, job_id: str, func_ref: str, duration: timedelta,
                                             args: Optional[List] = None, kwargs: Optional[Dict] = None,
                                             **interval_kwargs) -> Optional[Job]:
        """Обертка для отложенного планирования периодического запуска в течение определенного периода."""
        if not self.scheduler.running:
            params = locals()
            params.pop('self')
            # Объединяем именованные аргументы триггера в один словарь для передачи
            params.update(params.pop('interval_kwargs'))
            return await self._schedule_wrapper('_schedule_interval_for_duration_internal', params)
        return await self._schedule_interval_for_duration_internal(job_id, func_ref, duration, args, kwargs, **interval_kwargs)

    async def _schedule_interval_for_duration_internal(self, job_id: str, func_ref: str, duration: timedelta,
                                                      args: Optional[List] = None, kwargs: Optional[Dict] = None,
                                                      **interval_kwargs) -> Optional[Job]:
        """Внутренняя логика: планирует периодический запуск в течение определенного периода."""
        start_date = datetime.now(self.scheduler.timezone)
        end_date = start_date + duration
        trigger = IntervalTrigger(start_date=start_date, end_date=end_date, **interval_kwargs)
        return await self._add_job(job_id, func_ref, trigger, args, kwargs)

    # 6) Запускать задачу по cron-подобному расписанию
    async def schedule_cron(self, job_id: str, func_ref: str, args: Optional[List] = None,
                            kwargs: Optional[Dict] = None, **cron_kwargs) -> Optional[Job]:
        if not self.scheduler.running:
            params = locals()
            params.pop('self')
            params.update(params.pop('cron_kwargs'))
            return await self._schedule_wrapper('_schedule_cron_internal', params)
        return await self._schedule_cron_internal(job_id, func_ref, args, kwargs, **cron_kwargs)

    async def _schedule_cron_internal(self, job_id: str, func_ref: str, args: Optional[List] = None,
                                     kwargs: Optional[Dict] = None, **cron_kwargs) -> Optional[Job]:
        trigger = CronTrigger(**cron_kwargs, timezone=self.scheduler.timezone)
        return await self._add_job(job_id, func_ref, trigger, args, kwargs)

    # --- Вспомогательные функции (без изменений) ---

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.scheduler.get_job(job_id)

    def get_all_jobs(self) -> List[Job]:
        return self.scheduler.get_jobs()

    async def get_job_next_runs(self, job_id: str, limit: int = 5) -> List[datetime]:
        job = self.get_job(job_id)
        if not job:
            return []

        next_runs = []
        current_time = datetime.now(job.trigger.timezone)
        for _ in range(limit):
            next_run_time = job.trigger.get_next_fire_time(None, current_time)
            if next_run_time:
                next_runs.append(next_run_time)
                current_time = next_run_time
            else:
                break
        return next_runs

    async def remove_job(self, job_id: str):
        try:
            self.scheduler.remove_job(job_id)
            logging.info(f"Задача '{job_id}' успешно удалена.")
        except Exception as e:
            logging.warning(f"Не удалось удалить задачу '{job_id}': {e}")

    async def pause_job(self, job_id: str):
        self.scheduler.pause_job(job_id)
        logging.info(f"Задача '{job_id}' приостановлена.")

    async def resume_job(self, job_id: str):
        self.scheduler.resume_job(job_id)
        logging.info(f"Задача '{job_id}' возобновлена.")
