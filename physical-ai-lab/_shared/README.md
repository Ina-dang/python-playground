# 공통 선택 학습 타이머

Day22와 이후 교재는 이 폴더의 구현과 중앙 테스트 한 벌을 재사용합니다.
Day19~21은 기존 방식과 기록을 그대로 보존합니다.

## 공부할 때

1. 교재의 맨 위 시작 셀을 실행합니다.
2. 문제를 풉니다.
3. 맨 아래 종료 셀에서 직접 **종료**를 입력합니다.
4. Ctrl+S로 노트북을 저장하고 대화에 완료를 알립니다.

루트 physical-ai-lab 또는 해당 교재 폴더에서 노트북을 실행하세요.
교재 폴더와 이 _shared 폴더를 같은 부모 아래에 두어야 합니다.
타이머를 쓰지 않아도 학습 셀은 독립적으로 풀 수 있습니다.

## 파일과 기록

- study_timer.py: 공통 구현과 세 타이머 셀 생성기.
- test_study_timer.py: 중앙 테스트. 실제 기록 대신 임시 복제 교재만 사용.
- 기록: 각 교재의 .study_timer/교재날짜-교재ID.json.
- 공통 _shared 폴더에 교재 기록을 모으지 않습니다.
- 교재 ID, 날짜, notebook 이름은 교재를 만들 때 고정합니다. 실행일이 바뀌어도 기록 이름이 바뀌지 않습니다.
- JSON version=1 및 lesson/date/start/end 키와 KST ISO 시각을 유지합니다.
- 시작 재실행과 커널 재시작은 기록을 복원합니다.
- 이미 종료된 기록 재표시는 입력 요청이나 파일 쓰기를 하지 않습니다.
- 빈 종료 입력과 비활성 초기화는 기록을 바꾸지 않습니다.
- 초기화는 enabled=True와 직접 초기화 입력이 모두 필요하고, 검증된 고유 백업을 만든 뒤에만 기존 기록을 제거합니다.
- 경과 시간은 쉬거나 노트북을 닫은 시간까지 포함한 벽시계 시간입니다. 저장·채팅 시각이나 순수 집중 시간과 다릅니다.
- 링크·junction·reparse 경로, 모호한 교재 위치, 손상 기록, 시계 역행과 잠금 충돌은 자동 수정하지 않고 멈춥니다.

## 다음 교재를 만들 때

study_timer.py/test_study_timer.py를 날짜별 폴더에 다시 복사하지 마세요.
공통 모듈의 notebook_cells(lesson_id, lesson_date, notebook_name)를 호출하면
검증된 로더를 포함한 start/reset/finish 세 소스 문자열을 반환합니다.

예를 들어 루트에서 다음 명령은 셀 JSON만 출력하며 타이머를 시작하지 않습니다.

~~~powershell
.\.venv\Scripts\python.exe -B _shared\study_timer.py --lesson day23-next-lesson --date 2026-11-11 --notebook day23.ipynb
~~~

- start를 맨 위 시작 안내 아래의 코드 셀에 넣습니다.
- reset은 모든 학습 과제 뒤의 선택 초기화 안내 아래에 넣습니다. 기본 enabled=False를 유지합니다.
- finish는 맨 아래 종료 안내 아래의 마지막 코드 셀에 넣습니다.
- 새 교재의 .study_timer 폴더에 한정된 gitignore 규칙을 기존 규칙을 보존하며 추가합니다.
- 사용자 교재에서 타이머를 검수 실행하지 않습니다. 중앙 테스트를 사용합니다.
- 출력·시각·개인 기록은 배포 노트북에 담지 않습니다.

직접 사용하는 API는 create_timer(lesson_id, lesson_date, notebook_name,
notebook_path=...)입니다. 경로가 없으면 cwd=... 또는 현재 작업 폴더에서
루트/교재 위치를 확인합니다. 생성만으로 폴더나 기록을 만들지 않습니다.

## 중앙 테스트

루트에서 다음 명령을 실행합니다. 외부 패키지 설치가 필요 없습니다.

~~~powershell
.\.venv\Scripts\python.exe -I -B _shared\test_study_timer.py -v
~~~

Windows에서 일반 심볼릭 링크 생성 권한이 없으면 해당 실링크 테스트만 skip될 수 있습니다.
reparse 모의 검사와 별도의 실제 Windows junction 검사는 계속 실행됩니다.

## 독립적으로 ZIP을 풀어 사용할 때

압축 안 physical-ai-lab 아래의 _shared와 day22-goal-distance를 함께 유지하세요.
Day22 폴더만 떼어 옮기면 학습 문제는 남지만 공통 타이머는 경로 안내 후 멈춥니다.
기존 2026-11-10_Day22_MD_assets_notebook.zip은 날짜별 타이머가 포함된 구버전입니다.
수정된 공유 타이머 패키지는 2026-11-10_Day22_shared_timer_package.zip이며 새 업로드는 자동으로 하지 않습니다.

