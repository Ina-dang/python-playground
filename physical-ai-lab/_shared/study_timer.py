"""공통 선택 학습 타이머. 표준 라이브러리만 사용하며 import/로드만으로 기록하지 않습니다."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

KST = timezone(timedelta(hours=9))


class TimerError(RuntimeError):
    """원본을 바꾸지 않고 사용자에게 알려야 하는 타이머 오류."""


def _metadata(lesson_id, lesson_date, notebook_name):
    if not isinstance(lesson_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", lesson_id):
        raise TimerError("교재 ID가 올바르지 않아요.")
    if not isinstance(notebook_name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.ipynb", notebook_name):
        raise TimerError("노트북 이름이 올바르지 않아요.")
    try:
        if date.fromisoformat(lesson_date).isoformat() != lesson_date:
            raise ValueError()
    except (TypeError, ValueError):
        raise TimerError("고정 교재 날짜를 YYYY-MM-DD로 지정해 주세요.")


def _checked(path, *, directory=False, file=False, missing=False):
    """resolve()로 링크를 따라가기 전에 모든 기존 경로 구성요소를 lstat 검사합니다."""
    path = Path(path)
    if ".." in path.parts:
        raise TimerError("상위 폴더로 이동하는 경로는 사용하지 않아요.")
    if not path.is_absolute():
        path = Path.cwd() / path
    for item in [*reversed(path.parents), path]:
        try:
            info = item.lstat()
        except FileNotFoundError:
            if missing:
                return path
            raise TimerError("교재 또는 공통 도구 파일을 확인할 수 없어요.")
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise TimerError("바로가기·junction·reparse 경로는 사용하지 않아요.")
    if directory and not stat.S_ISDIR(info.st_mode):
        raise TimerError("예상한 폴더가 아니에요.")
    if file and not stat.S_ISREG(info.st_mode):
        raise TimerError("예상한 일반 파일이 아니에요.")
    return path


def _find_notebook(lesson_id, notebook_name, cwd):
    cwd = _checked(cwd, directory=True)
    candidates = []
    for folder in (cwd, cwd / lesson_id):
        if folder.name == lesson_id and (folder / notebook_name).is_file():
            _checked(folder, directory=True)
            candidates.append(_checked(folder / notebook_name, file=True))
    if len(candidates) != 1:
        raise TimerError("교재 폴더가 없거나 모호해요. 루트 또는 해당 교재 폴더에서 열어 주세요.")
    return candidates[0]


def create_timer(lesson_id, lesson_date, notebook_name, *, notebook_path=None, cwd=None):
    """명시한 교재 메타데이터에 결합합니다. 생성만으로 기록/폴더를 만들지 않습니다."""
    _metadata(lesson_id, lesson_date, notebook_name)
    if notebook_path is None:
        path = _find_notebook(lesson_id, notebook_name, Path.cwd() if cwd is None else cwd)
    else:
        path = _checked(notebook_path, file=True)
        if path.name != notebook_name or path.parent.name != lesson_id:
            raise TimerError("교재 ID와 노트북 경로가 맞지 않아요.")
    return StudyTimer(lesson_id, lesson_date, notebook_name, path)


class StudyTimer:
    def __init__(self, lesson_id, lesson_date, notebook_name, notebook_path):
        _metadata(lesson_id, lesson_date, notebook_name)
        notebook_path = _checked(notebook_path, file=True)
        if notebook_path.name != notebook_name or notebook_path.parent.name != lesson_id:
            raise TimerError("교재 ID와 노트북 경로가 맞지 않아요.")
        self.LESSON = lesson_id
        self.DATE = lesson_date
        self.NOTEBOOK = notebook_name
        self.notebook_path = notebook_path
        self.lesson_path = notebook_path.parent
        self.NAME = lesson_date + "-" + lesson_id + ".json"

    def paths(self, create=False):
        # 매 동작 때 다시 검사하여 생성 후 바뀐 junction도 거절합니다.
        _metadata(self.LESSON, self.DATE, self.NOTEBOOK)
        if (self.NAME != self.DATE + "-" + self.LESSON + ".json"
                or self.notebook_path.parent != self.lesson_path
                or self.notebook_path.name != self.NOTEBOOK
                or self.lesson_path.name != self.LESSON):
            raise TimerError("결합된 교재 경로가 바뀌어 기록하지 않았어요.")
        _checked(self.lesson_path, directory=True)
        _checked(self.notebook_path, file=True)
        folder = _checked(self.lesson_path / ".study_timer", directory=True, missing=True)
        if create:
            folder.mkdir(exist_ok=True)
            _checked(folder, directory=True)
        record = _checked(folder / self.NAME, file=True, missing=True)
        return folder, record

    def parse(self, raw):
        try:
            def unique(pairs):
                obj = {}
                for key, value in pairs:
                    if key in obj:
                        raise ValueError()
                    obj[key] = value
                return obj
            obj = json.loads(raw, object_pairs_hook=unique)
            if not isinstance(obj, dict) or set(obj) != {"version", "lesson", "date", "start", "end"}:
                raise ValueError()
            if type(obj["version"]) is not int or obj["version"] != 1:
                raise ValueError()
            if obj["lesson"] != self.LESSON or obj["date"] != self.DATE:
                raise ValueError()
            def timestamp(value):
                if not isinstance(value, str):
                    raise ValueError()
                result = datetime.fromisoformat(value)
                if result.utcoffset() != timedelta(hours=9):
                    raise ValueError()
                return result
            start = timestamp(obj["start"])
            end = timestamp(obj["end"]) if obj["end"] is not None else None
            if end is not None and end < start:
                raise ValueError()
            return obj, start, end
        except (ValueError, TypeError, KeyError, UnicodeDecodeError):
            raise TimerError("기록의 형식·교재 정보·시간이 올바르지 않아요. 원본을 보존했어요.")

    @staticmethod
    def encode(obj):
        return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    @staticmethod
    def _identity(info):
        return (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns, info.st_size)

    def _snapshot(self):
        _, record = self.paths()
        before = record.lstat()
        raw = record.read_bytes()
        after = record.lstat()
        if self._identity(before) != self._identity(after):
            raise TimerError("읽는 동안 기록이 바뀌었어요. 다시 확인해 주세요.")
        return self.parse(raw), (self._identity(after), hashlib.sha256(raw).digest()), raw

    def read(self):
        return self._snapshot()[0]

    @staticmethod
    def show(obj, start, end):
        print("시작 시각:", start.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST"))
        if end is not None:
            print("종료 시각:", end.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST"))
            seconds = int((end - start).total_seconds())
            print(f"경과 시간: {seconds // 3600}시간 {(seconds % 3600) // 60}분 {seconds % 60}초")
        else:
            print("아직 종료하지 않았어요.")
        print("벽시계 시간으로 쉬거나 노트북을 닫은 시간도 포함해요. 저장·채팅 시각과는 별개예요.")

    @staticmethod
    def _error(exc):
        # OS 예외의 절대 개인경로는 출력하지 않습니다.
        detail = str(exc) if isinstance(exc, TimerError) else "파일을 읽거나 쓸 수 없어 멈췄어요."
        print("타이머 확인:", detail, "\n기록을 지우지 말고 함께 확인해 주세요.")

    def finish_interactive(self):
        try:
            _, record = self.paths()
            if not record.exists():
                print("시작 기록이 없어요. 먼저 맨 위 시작 셀을 실행해 주세요.")
                return
            (obj, start, end), token, _ = self._snapshot()
            if end is not None:
                self.show(obj, start, end)
                return  # 파일 쓰기와 input 모두 하지 않습니다.
        except (OSError, TimerError) as exc:
            self._error(exc)
            return
        try:
            answer = input("끝내려면 종료 입력 (취소는 Enter): ")
        except (EOFError, KeyboardInterrupt):
            answer = ""
        self.action("finish", answer, expected_start=obj["start"], expected_token=token)

    def action(self, kind, answer=None, enabled=False, expected_start=None, expected_token=None):
        if kind not in {"start", "finish", "reset"}:
            print("지원하지 않는 타이머 동작이에요.")
            return
        if kind == "finish" and answer != "종료":
            print("취소했어요. 기록을 바꾸지 않았어요.")
            return
        if kind == "reset" and (not enabled or answer != "초기화"):
            print("초기화하지 않았어요.")
            return
        try:
            folder, record = self.paths()
            if record.exists():
                prior, _, _ = self._snapshot()
                if kind == "start" or (kind == "finish" and prior[2] is not None):
                    self.show(*prior)
                    return
            elif kind != "start":
                print("시작 기록이 없어요. 먼저 맨 위 시작 셀을 실행해 주세요.")
                return
            if kind == "start":
                folder, record = self.paths(create=True)
            lock = _checked(folder / (self.NAME + ".lock"), file=True, missing=True)
            nonce = os.urandom(16)
            with lock.open("xb") as handle:
                handle.write(nonce)
            try:
                folder, record = self.paths()
                if record.exists():
                    (obj, start, end), token, raw = self._snapshot()
                    if kind == "finish":
                        if expected_start is not None and obj["start"] != expected_start:
                            raise TimerError("입력 중 새 측정이 시작되어 종료하지 않았어요.")
                        if expected_token is not None and token != expected_token:
                            raise TimerError("입력 중 기록이 바뀌어 종료하지 않았어요.")
                    if kind == "start" or (kind == "finish" and end is not None):
                        self.show(obj, start, end)
                        return
                    if kind == "finish":
                        now = datetime.now(KST)
                        if now < start:
                            raise TimerError("시계가 시작보다 이전이에요. 시스템 시간을 확인해 주세요.")
                        obj["end"] = now.isoformat()
                        temp = _checked(folder / (self.NAME + "." + uuid.uuid4().hex + ".tmp"),
                                        file=True, missing=True)
                        created = False
                        try:
                            with temp.open("xb") as handle:
                                created = True
                                handle.write(self.encode(obj))
                                handle.flush()
                                os.fsync(handle.fileno())
                            for attempt in range(6):
                                _, current_token, current_raw = self._snapshot()
                                if current_token != token or current_raw != raw:
                                    raise TimerError("동시에 기록이 바뀌어 종료하지 않았어요.")
                                self.paths()
                                _checked(temp, file=True)
                                try:
                                    os.replace(temp, record)
                                    break
                                except PermissionError as exc:
                                    # Windows의 짧은 읽기 핸들 충돌만 제한 재시도해요.
                                    # 잠금과 원본 token 확인을 유지하며 계속 실패하면 보존해요.
                                    if (os.name != "nt"
                                            or getattr(exc, "winerror", None) not in {5, 32}
                                            or attempt == 5):
                                        raise
                                    time.sleep(0.02)
                        finally:
                            if created and temp.exists():
                                _checked(temp, file=True)
                                temp.unlink()
                        self.show(*self.read())
                        return
                    if kind == "reset":
                        backup = _checked(folder / (self.NAME + "." + uuid.uuid4().hex + ".backup"),
                                          file=True, missing=True)
                        with backup.open("xb") as handle:
                            handle.write(raw)
                            handle.flush()
                            os.fsync(handle.fileno())
                        _checked(backup, file=True)
                        _, current_token, current_raw = self._snapshot()
                        if backup.read_bytes() != raw or current_token != token or current_raw != raw:
                            raise TimerError("백업 또는 원본 확인에 실패해 초기화를 멈췄어요.")
                        record.unlink()
                        print("기존 기록을 백업했어요. 새 측정은 맨 위 시작 셀을 다시 실행해 주세요.")
                        return
                elif kind == "start":
                    obj = {"version": 1, "lesson": self.LESSON, "date": self.DATE,
                           "start": datetime.now(KST).isoformat(), "end": None}
                    with record.open("xb") as handle:
                        handle.write(self.encode(obj))
                        handle.flush()
                        os.fsync(handle.fileno())
                    self.show(*self.read())
            finally:
                _checked(lock, file=True)
                if lock.read_bytes() != nonce:
                    raise TimerError("잠금 소유권이 바뀌어 다른 잠금을 보존했어요.")
                lock.unlink()
        except (OSError, TimerError) as exc:
            self._error(exc)


# 실행 전에 공통 helper와 모든 경로 구성요소를 검사하는 셀 템플릿입니다.
# 실제 기록 동작은 마지막 start/finish/reset 명령에서만 일어납니다.
_BOOTSTRAP = r'''
from pathlib import Path as _Path
import stat as _stat

def _load_shared_timer():
    # 교재 ID·날짜·노트북 이름은 제작 때 고정한 값이에요.
    _lesson_id = __LESSON__
    _lesson_date = __DATE__
    _notebook_name = __NOTEBOOK__

    def _safe(path, directory=False):
        if ".." in path.parts:
            raise RuntimeError("상위 폴더 경로는 사용하지 않아요.")
        for item in [*reversed(path.parents), path]:
            info = item.lstat()
            if (_stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400):
                raise RuntimeError("바로가기·junction·reparse 경로는 사용하지 않아요.")
        if directory and not _stat.S_ISDIR(info.st_mode):
            raise RuntimeError("예상한 폴더가 아니에요.")
        if not directory and not _stat.S_ISREG(info.st_mode):
            raise RuntimeError("예상한 일반 파일이 아니에요.")
        return path

    _cwd = _safe(_Path.cwd(), directory=True)
    _candidates = []
    for _folder in (_cwd, _cwd / _lesson_id):
        if _folder.name == _lesson_id and (_folder / _notebook_name).is_file():
            _safe(_folder, directory=True)
            _candidates.append(_safe(_folder / _notebook_name))
    if len(_candidates) != 1:
        raise RuntimeError("교재 폴더가 없거나 모호해요.")
    _notebook_path = _candidates[0]
    _shared_dir = _safe(_notebook_path.parent.parent / "_shared", directory=True)
    _helper = _safe(_shared_dir / "study_timer.py")
    # 검사한 파일을 메모리에서 로드해 __pycache__를 만들지 않아요.
    _before = _helper.lstat()
    _source = _helper.read_bytes()
    _after = _safe(_helper).lstat()
    _identity = lambda info: (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size)
    if _identity(_before) != _identity(_after):
        raise RuntimeError("읽는 동안 공통 도구 파일이 바뀌었어요.")
    _module = {"__name__": "physical_ai_shared_timer"}
    exec(compile(_source, str(_helper), "exec"), _module)
    return _module["create_timer"](
        _lesson_id, _lesson_date, _notebook_name,
        notebook_path=_notebook_path)

try:
    _study_timer = _load_shared_timer()
except (OSError, RuntimeError, SyntaxError):
    print("타이머 경로를 확인하지 못했어요. 루트 또는 교재 폴더에서 열고 _shared 폴더를 함께 보관해 주세요. 기록은 바꾸지 않았어요.")
else:
__ACTION__
'''


def notebook_cells(lesson_id, lesson_date, notebook_name):
    """새 교재 제작 시 이 생성기만 호출합니다. 경로 검증까지 포함한 세 셀을 반환합니다."""
    _metadata(lesson_id, lesson_date, notebook_name)
    prefix = (_BOOTSTRAP.replace("__LESSON__", repr(lesson_id))
              .replace("__DATE__", repr(lesson_date)).replace("__NOTEBOOK__", repr(notebook_name)))
    actions = {
        "start": '    _study_timer.action("start")',
        "finish": '    _study_timer.finish_interactive()',
        "reset": ('    enabled = False  # 정말 다시 잴 때만 True로 바꾸세요.\n'
                  '    if enabled:\n'
                  '        _study_timer.action("reset", input("초기화하려면 초기화 입력: "), enabled=True)\n'
                  '    else:\n'
                  '        print("초기화는 비활성화되어 있어요.")'),
    }
    return {key: prefix.replace("__ACTION__", action).lstrip() for key, action in actions.items()}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="새 교재의 공통 타이머 셀만 생성합니다. 타이머는 실행하지 않습니다.")
    parser.add_argument("--lesson", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--notebook", required=True)
    args = parser.parse_args()
    print(json.dumps(notebook_cells(args.lesson, args.date, args.notebook), ensure_ascii=False, indent=2))

