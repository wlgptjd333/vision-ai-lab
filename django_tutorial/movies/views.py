from django.http import HttpResponse

# 실습해보기_Part1: DB 없이 파이썬 코드에 영화 데이터를 직접 쓰고, HttpResponse 로 HTML 을 돌려준다
MOVIES = [
    {"title": "인터스텔라", "genre": "SF, 드라마",
     "description": "우주를 배경으로 한 아버지의 위대한 사랑과 모험 이야기."},
    {"title": "기생충", "genre": "드라마, 스릴러",
     "description": "상류층과 하류층의 현실을 꼬집는 블랙코미디 영화."},
    {"title": "토이 스토리", "genre": "애니메이션, 가족",
     "description": "장난감들의 유쾌한 우정과 모험 이야기."},
]


def index(request):
    cards = "".join(
        f"""
        <div class="movie">
            <div class="title">{m['title']}</div>
            <div class="genre">장르: {m['genre']}</div>
            <div class="description">{m['description']}</div>
            <a href="#" class="btn">추천하기</a>
        </div>"""
        for m in MOVIES
    )
    html = f"""
    <html>
    <head>
        <title>🎬 영화 추천</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 2em; }}
            .movie {{ border: 1px solid #ccc; padding: 1em; margin-bottom: 1em; border-radius: 10px; }}
            .title {{ font-size: 1.5em; font-weight: bold; }}
            .genre {{ color: gray; }}
            .description {{ margin-top: 0.5em; }}
            .btn {{ margin-top: 1em; display: inline-block; padding: 0.5em 1em; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>🎬 오늘의 영화 추천</h1>
        {cards}
    </body>
    </html>
    """
    return HttpResponse(html)
