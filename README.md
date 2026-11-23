# djangotutorial (Django 공식 튜토리얼 polls 따라하기)

백엔드 수업 교재 `03 Django 기본 & 데이터베이스 구축` Django1~3을 따라 만든 연습 프로젝트입니다.

| 단계 | 내용 |
|---|---|
| 설치 | uv 프로젝트(Python 3.12), Django 6.1.3, django-extensions |
| Part1 | `polls` 앱, 첫 뷰와 URL 연결 / 실습: `movies` 앱 |
| Part2 | `Question`·`Choice` 모델, 마이그레이션, admin 등록, 한국어·서울 시간대 |
| Part3 | index·detail·results·vote 뷰, 템플릿 분리(`base`·`header`·`footer`), `static/polls/*.css` |

## 실행

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver 8002
```

- http://127.0.0.1:8002/polls/ , http://127.0.0.1:8002/movies/ , http://127.0.0.1:8002/admin/
- `db.sqlite3`는 올리지 않습니다. 질문 데이터는 admin에서 직접 넣으면 됩니다.
- 교재 `.gitignore`의 "migrations 제외" 줄은 뺐습니다. 마이그레이션 파일은 모델 변경 이력이라 함께 올립니다.
