"""
스케줄러 - 매일 오후 6시~11:59 사이 랜덤 시간에 실행
"""
import random
import logging
from datetime import datetime, time, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.date import DateTrigger
from typing import Callable

logger = logging.getLogger(__name__)


class RandomScheduler:
    """랜덤 시간 스케줄러"""
    
    def __init__(self, start_hour: int = 18, end_hour: int = 23, end_minute: int = 59):
        """
        Args:
            start_hour: 시작 시간 (18 = 오후 6시)
            end_hour: 종료 시간 (23 = 오후 11시)
            end_minute: 종료 분 (59)
        """
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.end_minute = end_minute
        self.scheduler = BlockingScheduler()
    
    def _generate_random_time_for_date(self, target_date) -> datetime:
        """특정 날짜의 랜덤 시간 생성"""
        random_hour = random.randint(self.start_hour, self.end_hour)
        
        if random_hour == self.end_hour:
            random_minute = random.randint(0, self.end_minute)
        else:
            random_minute = random.randint(0, 59)
        
        random_second = random.randint(0, 59)
        
        return datetime.combine(target_date, time(random_hour, random_minute, random_second))
    
    def schedule_daily_random(self, job_func: Callable):
        """
        매일 랜덤 시간에 작업 스케줄링
        
        Args:
            job_func: 실행할 함수
        """
        def schedule_next_day():
            """다음날 랜덤 시간 스케줄링"""
            tomorrow = datetime.now().date() + timedelta(days=1)
            run_time = self._generate_random_time_for_date(tomorrow)
            logger.info(f"다음 실행 예정: {run_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 기존 job이 있으면 제거
            try:
                self.scheduler.remove_job('daily_post_job')
            except:
                pass
            
            self.scheduler.add_job(
                job_with_reschedule,
                trigger=DateTrigger(run_date=run_time),
                id='daily_post_job'
            )
        
        def job_with_reschedule():
            """작업 실행 후 다음날 스케줄링"""
            job_func()
            schedule_next_day()
        
        # 오늘 실행할지 내일 실행할지 결정
        now = datetime.now()
        today = now.date()
        today_run_time = self._generate_random_time_for_date(today)
        
        if today_run_time > now:
            # 오늘 실행 가능
            logger.info(f"오늘 실행 예정: {today_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.scheduler.add_job(
                job_with_reschedule,
                trigger=DateTrigger(run_date=today_run_time),
                id='daily_post_job'
            )
        else:
            # 오늘 시간이 지났으므로 내일 실행
            schedule_next_day()
        
        logger.info("스케줄러를 시작합니다...")
        self.scheduler.start()
    
    def schedule_single_random(self, job_func: Callable):
        """오늘 또는 내일 랜덤 시간에 한 번만 실행 (테스트용)"""
        now = datetime.now()
        today = now.date()
        
        run_time = self._generate_random_time_for_date(today)
        
        # 이미 지난 시간이면 내일로
        if run_time < now:
            tomorrow = today + timedelta(days=1)
            run_time = self._generate_random_time_for_date(tomorrow)
        
        logger.info(f"실행 예정 시간: {run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.scheduler.add_job(
            job_func,
            trigger=DateTrigger(run_date=run_time),
            id='single_post_job'
        )
        self.scheduler.start()

