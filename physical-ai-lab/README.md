# Physical AI Lab

피지컬 AI의 개념을 Python 실습으로 익히고, 단계별 교재와 학습 기록을 정리하는 공간입니다.

## 학습 목록

| 날짜       | 단계                 | Markdown 교재                              | PDF                                                                                |
| ---------- | -------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------- |
| 2026-10-17 | Day 01 · 센서와 필터 | [교재 보기](day01-sensor-filter/README.md) | [PDF 보기](https://drive.google.com/file/d/1ZHcYnh1BMP7-ub1c5LRG7SJ-uH7xFNqW/view) |
| 2026-10-18 | Day 02 · NumPy 마스크 | [교재 보기](day02-numpy-mask/README.md) | [PDF 보기](https://drive.google.com/file/d/1KAGzsTku40bNxZVhgro7cVw9okCphE52/view?usp=drivesdk) |
| 2026-10-19 | Day 03 · NumPy 행 선택과 shape | [교재 보기](day03-numpy-row-selection/README.md) | [PDF 보기](https://drive.google.com/file/d/1mfK3mN6NeWmtggCqmdJuQAMxsw0Ro_pe/view?usp=drivesdk) |
| 2026-10-20 | Day 4 NumPy 온도 보정 | [교재 보기](day04-numpy-calibration/README.md) | [PDF 보기](https://drive.google.com/file/d/1E7ylfdYdE_jzPRmbsZouLfdTfbagfPWV/view) |
| 2026-10-21 | Day05 센서별 NumPy 온도 보정 | [교재 보기](day05-numpy-sensor-offsets/README.md) | [PDF 보기](https://drive.google.com/file/d/1x8IbgzXcSb7YfhfKP6auNvt7JdCEXylW/view) |
| 2026-10-23 | Day06 조건에 맞는 센서만 고르기 | [교재 보기](day06-numpy-boolean-mask/README.md) | [PDF 보기](https://drive.google.com/file/d/1fzQoNkrwuY9QgLYI3O85xyNmLTyWKVVN/view?usp=drivesdk) |

## 자료 구성

각 단계의 교재는 해당 하위 폴더의 `README.md`에, 교재에 필요한 이미지는 같은 폴더의 `assets/`에 보관합니다. 이미지 링크는 상대경로를 사용합니다.

---

# 첫 실행 (환경 세팅)

## 왜 `uv` + `Python 3.12`를 사용하나요?

- **Python 3.12 선택 이유:** 피지컬 AI / 로보틱스 / 데이터 과학 분야의 핵심 라이브러리(`PyTorch`, `NumPy`, `SciPy`, `OpenCV` 등)는 너무 최신 파이썬 버전에서 호환성 문제나 빌드 오류가 발생할 수 있습니다. 속도와 생태계 안정성이 모두 검증된 **3.12의 최신 패치 버전**을 사용하는 것이 가장 안정적입니다.
- **`uv` 도입 이유:** Rust 기반의 초고속 파이썬 패키지·버전 관리 도구로, 시스템에 설치된 파이썬 버전에 의존하지 않고 원하는 파이썬 패치 버전을 독립적으로 받아 관리할 수 있으며, 기존 `venv` 및 `pip` 대비 가상환경 생성과 패키지 설치 속도가 압도적으로 빠릅니다.

## Git Bash 기준 (Windows)

```bash
# 1. uv 설치 (최초 1회)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. uv 관리용 최신 Python 3.12 패치 버전 설치
uv python install 3.12 --managed-python

# 3. 최신 3.12 패치판으로 가상환경(.venv) 생성
uv venv .venv --python 3.12 --managed-python

# 4. 가상환경 활성화
source .venv/Scripts/activate

# 5. 연결된 파이썬 경로 및 버전 확인
which python
python --version

# 6. 패키지 설치 (pip 대신 uv pip 사용)
uv pip install numpy matplotlib ipykernel

# 7. 가상환경 비활성화 (종료 시)
deactivate
```

## 커리큘럼

[피지컬 AI 맞춤 학습 로드맵](curriculum/README.md) · [커리큘럼 PDF](https://drive.google.com/file/d/1ikdB95IZTMFIYb0LmbeQfK1HR2F-eeHP/view?usp=drivesdk)
