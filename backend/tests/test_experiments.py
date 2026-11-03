import pytest

from experiments.metrics import ari, cohen_kappa, nmi


def test_ari():
    assert ari([0, 0, 1, 1], [5, 5, 9, 9]) == 1.0  # 이름만 다르고 나누기는 같음
    assert ari([0, 0, 1, 1], [0, 1, 0, 1]) == pytest.approx(-0.5)  # 완전히 엇갈림
    # 손 계산: 같은 쌍 2개, 기대값 6·3/15=1.2, 최대 4.5 → (2-1.2)/(4.5-1.2)
    assert ari([0, 0, 0, 1, 1, 1], [0, 0, 1, 1, 2, 2]) == pytest.approx(0.8 / 3.3)


def test_nmi():
    assert nmi([0, 0, 1, 1], [1, 1, 0, 0]) == pytest.approx(1.0)
    assert nmi([0, 0, 1, 1], [0, 1, 0, 1]) == pytest.approx(0.0)
    # 손 계산: 상호정보량 = (2/3)·ln2, 엔트로피 ln2·ln3 → (2/3·ln2) / ((ln2+ln3)/2)
    import math

    assert nmi([0, 0, 0, 1, 1, 1], [0, 0, 1, 1, 2, 2]) == pytest.approx((2 / 3 * math.log(2)) / ((math.log(2) + math.log(3)) / 2))


def test_cohen_kappa():
    assert cohen_kappa(["y", "n", "y"], ["y", "n", "y"]) == 1.0
    # 일치 4/6, 우연 일치 기대값 0.5 → (0.667-0.5)/(1-0.5)
    assert cohen_kappa(list("yyynnn"), list("yynnny")) == pytest.approx(1 / 3)


def test_faithfulness_judging_and_summary():
    from datetime import datetime, timezone

    from app.models import Commit, FileChange
    from experiments.faithfulness import Item, JudgeBatch, RepoRun, Verdict, judge_repo, summarize_condition

    c1 = Commit(sha="a" * 40, url="u1", message="제품 19종 추가", authored_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                author_login="u", files=[FileChange(path="data/catalog.ts", patch="+19 items")])
    run = RepoRun("o/r", {c1.sha: c1}, [
        Item("A", "카탈로그 19종 추가", [c1.sha]),
        Item("A", "성능 3배 개선", [c1.sha]),       # 숫자 3이 근거에 없음
        Item("A", "근거 없는 주장", [], bad_ids=1),  # 없는 ID만 달았음 → 판정 없이 unsupported
        Item("C", "카탈로그 19종 추가", [c1.sha]),   # A와 같은 문장 → 판정은 한 번만
    ])

    class FakeJudge:
        calls = 0

        def parse(self, *, system, prompt, schema):
            FakeJudge.calls += 1
            assert "카탈로그 19종 추가" in prompt and prompt.count("카탈로그 19종 추가") == 1  # 중복 제거
            lines = [l for l in prompt.splitlines() if l.startswith("[")]
            return JudgeBatch(verdicts=[
                Verdict(id=int(l[1]), verdict="supported" if "19종" in l else "unsupported", reason="")
                for l in lines
            ])

    judge_repo(run, FakeJudge())
    assert FakeJudge.calls == 1
    a = summarize_condition([run], "A")
    assert a["statements"] == 3 and a["supported"] == pytest.approx(1 / 3)
    assert a["bad_id_rate"] == pytest.approx(1 / 3)
    assert a["number_ok_rate"] == pytest.approx(1 / 2)  # 19는 확인, 3은 확인 안 됨
    assert summarize_condition([run], "C")["supported"] == 1.0
