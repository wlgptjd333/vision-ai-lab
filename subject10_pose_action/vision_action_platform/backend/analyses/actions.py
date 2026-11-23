"""모델이 예측하는 교과10 기본 6개 Action (subject10_pose_action configs/action_classes.csv 와 같은 번호).

AI 서버의 models/action_classes.csv 와 같은 목록이다. Django 는 화면 표시·예상 동작 선택·대시보드 집계에만 쓴다.
"""
ACTIONS = [
    ("A001", "bend_return", "허리 굽혔다 펴기"),
    ("A002", "leg_raise_lower", "한쪽 다리 들었다 내리기"),
    ("A003", "walk_turn_walk", "걷다가 돌아서 다시 걷기"),
    ("A004", "drink_return", "음료 마시고 정면 보기"),
    ("A005", "sit_stand", "의자에 앉았다 일어서기"),
    ("A006", "wave", "한 손 흔들어 인사하기"),
]
ACTION_IDS = [a[0] for a in ACTIONS]
ACTION_CHOICES = [(a[0], f"{a[0]} {a[2]}") for a in ACTIONS]
ACTION_BY_ID = {a[0]: {"id": a[0], "label": a[1], "name_ko": a[2]} for a in ACTIONS}
