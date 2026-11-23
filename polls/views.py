from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Choice, Question


# index(최신글 list) — Part1 의 HttpResponse("Hello, world...") 를 Part3 에서 템플릿으로 바꿈
def index(request):
    latest_question_list = Question.objects.order_by("-pub_date")[:5]
    # - 내림차순 + 오름차순
    context = {"latest_question_list": latest_question_list}
    return render(request, "polls/index.html", context)


# detail(상세조회)
def detail(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    # Question 테이블에서 pk가 question_id인 데이터 1개를 조회하되, 없으면
    # 서버 에러(500)가 아니라 404 Not Found 페이지를 띄워라
    return render(request, "polls/detail.html", {"question": question})


# results(결과보기)
def results(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    return render(request, "polls/results.html", {"question": question})


# vote(투표하기) — Part3 에서는 아직 더미 텍스트
def vote(request, question_id):
    return HttpResponse(f"You're voting on question {question_id}.")
