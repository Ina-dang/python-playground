"""Day21 선택 타이머. Python 표준 라이브러리만 사용합니다."""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid

LESSON = 'day21-xy-coordinates'
DATE = '2026-11-09'
NAME = DATE + '-' + LESSON + '.json'
KST = timezone(timedelta(hours=9))

class TimerError(Exception):
    pass

def lesson_dir():
    # 작업 폴더 또는 그 바로 아래에 정확한 교재 폴더가 하나 있어야 해요.
    cwd = Path.cwd()
    candidates = [p for p in (cwd, cwd / LESSON) if p.name == LESSON and p.is_dir() and (p / 'day21.ipynb').is_file() and (p / 'study_timer.py').is_file()]
    if len(candidates) != 1 or any(p.is_symlink() or (p / 'study_timer.py').is_symlink() or (p / 'day21.ipynb').is_symlink() for p in candidates):
        raise TimerError('교재 폴더를 하나로 확인할 수 없어요. day21 폴더에서 노트북을 열어 주세요.')
    return candidates[0]

def paths(create=False):
    root = lesson_dir()
    folder = root / '.study_timer'
    if folder.is_symlink():
        raise TimerError('타이머 폴더가 바로가기여서 기록하지 않았어요.')
    if create:
        folder.mkdir(exist_ok=True)
    if folder.exists() and not folder.is_dir():
        raise TimerError('타이머 폴더를 사용할 수 없어요.')
    record = folder / NAME
    if record.is_symlink():
        raise TimerError('기록 파일이 바로가기여서 읽거나 바꾸지 않았어요.')
    return folder, record

def parse(raw):
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result: raise ValueError('duplicate key')
                result[key] = value
            return result
        obj = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(obj, dict) or set(obj) != {'version','lesson','date','start','end'}:
            raise ValueError()
        if type(obj['version']) is not int or obj['version'] != 1 or obj['lesson'] != LESSON or obj['date'] != DATE:
            raise ValueError()
        def dt(value):
            if not isinstance(value, str): raise ValueError()
            d = datetime.fromisoformat(value)
            if d.utcoffset() != timedelta(hours=9): raise ValueError()
            return d
        start = dt(obj['start'])
        end = dt(obj['end']) if obj['end'] is not None else None
        if end is not None and end < start: raise ValueError()
        return obj, start, end
    except (ValueError, TypeError, KeyError, UnicodeDecodeError):
        raise TimerError('기록의 형식, 교재 정보 또는 시간이 올바르지 않아요. 원본을 보존했어요.')

def read(record):
    if record.is_symlink(): raise TimerError('바로가기 기록은 사용하지 않아요.')
    return parse(record.read_bytes())

def show(obj, start, end):
    print('시작 시각:', start.astimezone(KST).strftime('%Y-%m-%d %H:%M:%S KST'))
    if end is not None:
        print('종료 시각:', end.astimezone(KST).strftime('%Y-%m-%d %H:%M:%S KST'))
        seconds = int((end-start).total_seconds())
        print(f'경과 시간: {seconds//3600}시간 {(seconds%3600)//60}분 {seconds%60}초')
        print('쉬거나 노트북을 닫은 시간도 포함해요. 저장·채팅 시각은 별개예요.')
    else:
        print('아직 종료하지 않았어요.')

def encode(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def finish_interactive():
    # 이미 종료된 경우 최초 결과를 그대로 보여줘요. 이 확인은 파일을 쓰지 않아요.
    try:
        _, record = paths(False)
        if not record.exists():
            print('시작 기록이 없어요. 먼저 맨 위 학습 시작 셀을 실행해 주세요.'); return
        obj, start, end = read(record)
        if end is not None:
            show(obj, start, end); return
    except (OSError, TimerError) as exc:
        print('기록을 확인하지 못했어요:', exc, '\n기록을 지우지 말고 함께 확인해 주세요.'); return
    answer = input('끝내려면 종료 입력 (취소는 Enter): ')
    # 입력을 기다리는 동안 다른 측정이 시작됐을 수 있어요.
    action('finish', answer, expected_start=obj['start'])

def action(kind, answer=None, enabled=False, expected_start=None):
    # 취소는 폴더 생성과 잠금보다 먼저 처리해요.
    if kind == 'finish' and answer != '종료':
        print('취소했어요. 기록을 바꾸지 않았어요.'); return
    if kind == 'reset' and (not enabled or answer != '초기화'):
        print('초기화하지 않았어요.'); return
    try:
        folder, record = paths(False)
        if kind in ('finish', 'reset') and not record.exists():
            print('시작 기록이 없어요. 먼저 맨 위 학습 시작 셀을 실행해 주세요.'); return
        if kind == 'start': folder, record = paths(True)
        lock = folder / (NAME + '.lock')
        # 시작·종료·초기화가 같은 잠금 파일을 사용해 동시 변경을 막아요.
        with lock.open('xb') as lock_file:
            lock_file.write(b'locked\n')
        try:
            folder, record = paths(False)
            if record.exists():
                obj, start, end = read(record)
                # 잠금 안에서 확인할 때만 방금 승인한 시작 기록을 종료해요.
                if kind == 'finish' and expected_start is not None and obj['start'] != expected_start:
                    raise TimerError('입력하는 동안 새 측정이 시작되어 종료하지 않았어요. 다시 확인해 주세요.')
                if kind == 'start' or (kind == 'finish' and end is not None):
                    show(obj, start, end); return
                if kind == 'finish':
                    now = datetime.now(KST)
                    if now < start: raise TimerError('시계가 시작보다 이전이에요. 시스템 시간을 확인해 주세요.')
                    obj['end'] = now.isoformat()
                    # 같은 폴더의 고유 임시 파일을 완성한 뒤 교체해요.
                    temp = folder / (NAME + '.' + uuid.uuid4().hex + '.tmp')
                    created = False
                    try:
                        with temp.open('xb') as f:
                            created = True  # 이 실행에서 만든 파일만 정리할 수 있어요.
                            f.write(encode(obj)); f.flush(); os.fsync(f.fileno())
                        # 잠금 중에도 외부 수정이 있었다면 교체하지 않아요.
                        current, _, _ = read(record)
                        if current['start'] != obj['start'] or current['end'] is not None:
                            raise TimerError('기록이 동시에 바뀌어 종료하지 않았어요.')
                        os.replace(temp, record)
                    finally:
                        if created and temp.exists(): temp.unlink()
                    show(*read(record)); return
                if kind == 'reset':
                    raw = record.read_bytes(); parse(raw)
                    backup = folder / (NAME + '.' + uuid.uuid4().hex + '.backup')
                    with backup.open('xb') as f:
                        f.write(raw); f.flush(); os.fsync(f.fileno())
                    if backup.read_bytes() != raw or record.read_bytes() != raw:
                        raise TimerError('백업 또는 원본이 달라져 초기화를 멈췄어요.')
                    record.unlink()
                    print('기존 기록을 백업했어요. 새 측정은 맨 위 시작 셀을 다시 실행해 주세요.'); return
            elif kind == 'start':
                obj = {'version': 1, 'lesson': LESSON, 'date': DATE, 'start': datetime.now(KST).isoformat(), 'end': None}
                # x 모드는 기존 파일을 덮어쓰지 않아요.
                with record.open('xb') as f:
                    f.write(encode(obj)); f.flush(); os.fsync(f.fileno())
                show(*read(record)); return
            else:
                print('시작 기록이 없어요. 먼저 시작 셀을 실행해 주세요.')
        finally:
            lock.unlink()
    except (OSError, TimerError) as exc:
        print('타이머를 바꾸지 못했어요:', exc, '\n기록을 지우지 말고 함께 확인해 주세요.')
