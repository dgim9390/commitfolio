"""환경변수 설정.

프로젝트 루트(backend/의 상위 폴더)의 .env 파일을 읽는다.
CLI와 FastAPI가 같은 설정을 쓰도록 get_settings()로만 접근한다.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    github_token: str = ""  # 비어 있으면 비인증 호출 (시간당 60회)

    llm_provider: str = "gemini"  # gemini(무료 등급) | claude(유료)
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = ""  # 비우면 제공자별 기본 모델 (llm.DEFAULT_MODELS)
    llm_effort: str = "medium"  # Claude 전용: low | medium | high | xhigh | max
    # 한 번의 LLM 호출에 넣을 그룹 요약 입력 상한. 무료 등급은 하루 호출 수가 적어서
    # 여러 그룹을 한 번에 요약한다 (DeskBoard 기준 2회)
    max_chars_per_summary_call: int = 150000

    # GitHub API 응답(SQLite)과 클론한 레포가 저장되는 곳
    cache_dir: Path = ROOT_DIR / ".cache"

    # LLM 비용 제한용 diff 길이 상한 (문자 수)
    # 24000자 ≈ 8천 토큰 정도. 커밋 40개 레포 전체 요약에 입력 약 30만 토큰 이내
    max_patch_chars_per_file: int = 6000
    max_patch_chars_per_commit: int = 24000
    # 한 파일에서 이보다 많은 줄이 바뀌면 자동 생성/데이터 파일로 보고 제외
    max_file_lines_changed: int = 3000
    # 그룹 하나를 요약할 때 LLM에 보낼 diff 총량 상한
    max_patch_chars_per_group: int = 30000
    # 포트폴리오 소개글 생성 시 참고할 README 앞부분 길이
    max_readme_chars: int = 6000


@lru_cache
def get_settings() -> Settings:
    return Settings()
