"""하루 분석 횟수 제한.

Gemini 무료 등급은 하루 호출 수가 프로젝트 단위로 정해져 있어서, 사이트를 여러 사람이 쓰면
한 사람이 한도를 다 써 버릴 수 있다. 그래서 하루 전체 횟수와 IP당 횟수를 센다.
같은 레포를 다시 분석하면 캐시를 쓰므로 AI 호출은 거의 없지만, 단순하게 '새 분석 요청'을 센다.
서버를 재시작하면 숫자가 0으로 돌아가지만, 무료 서버의 재시작은 드물어 이 정도로 충분하다.
"""

import threading
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")  # 한국 사용자 기준으로 자정에 초기화


class LimitExceeded(Exception):
    pass


class DailyLimiter:
    def __init__(self, total: int, per_ip: int):
        self.total_limit = total  # 0이면 제한 없음
        self.per_ip_limit = per_ip
        self._day = ""
        self._total = 0
        self._per_ip: Counter[str] = Counter()
        self._lock = threading.Lock()

    def check(self, ip: str) -> None:
        """한도를 넘었으면 LimitExceeded. 아직 세지는 않는다 (중복 요청은 세지 않기 위해)."""
        with self._lock:
            self._roll_day()
            if self.total_limit and self._total >= self.total_limit:
                raise LimitExceeded(f"오늘 사이트 전체 분석 횟수({self.total_limit}회)를 다 썼습니다. 한국 시간 자정에 초기화됩니다.")
            if self.per_ip_limit and self._per_ip[ip] >= self.per_ip_limit:
                raise LimitExceeded(f"오늘 분석 가능 횟수({self.per_ip_limit}회)를 다 썼습니다. 한국 시간 자정에 초기화됩니다.")

    def count(self, ip: str) -> None:
        with self._lock:
            self._roll_day()
            self._total += 1
            self._per_ip[ip] += 1

    def _roll_day(self) -> None:
        today = datetime.now(_KST).date().isoformat()
        if today != self._day:
            self._day, self._total, self._per_ip = today, 0, Counter()
