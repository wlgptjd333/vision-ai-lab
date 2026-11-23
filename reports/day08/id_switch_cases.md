# Day 08 Tracking Cases

> 47번(YOLO Pose + ByteTrack, `bytetrack.yaml`) → 48번 → 51번 실행 결과. 수치는 교재 실행 결과와 모두 같음.
> 결과영상은 `reports/day08/tracking/*_tracked.mp4` (Git 제외). 아래 "결과영상 확인"은 해당 Frame을 직접 캡처해서 본 내용.

## 1. Shaking Hands

- 전체 Frame: 30
- Unique Track IDs: 2
- Two-ID Frame Ratio: 1.0000
- Extra ID: 0
- ID 1: 30 / 30 Frame (평균 box_conf 0.931, keypoint_conf 0.701)
- ID 2: 30 / 30 Frame (평균 box_conf 0.937, keypoint_conf 0.698)
- Log 해석: 두 Track이 전체 영상에서 유지됨
- 결과영상 확인: Frame 0·15·29에서 오른쪽 사람이 계속 ID 1, 왼쪽 사람이 계속 ID 2. 악수로 손이 닿는 Frame 15에서도 상자가 따로 잡힘
- 최종 판단: Track Lost·ID Switch 없음

## 2. Hugging

- 전체 Frame: 33
- Unique Track IDs: 4
- Two-ID Frame Ratio: 0.6364 (33 Frame 중 21 Frame만 정확히 ID 2개)
- Extra ID: 2
- ID 1: 24 / 33 Frame
- ID 2: 33 / 33 Frame
- ID 4: 4 Frame (6·7·8·11)
- ID 5: 3 Frame (20·21·23)
- Log 해석: Occlusion 구간에서 Tracking이 불안정해짐
- ID 4 / ID 5가 나타난 장면: 두 사람이 팔을 감아 겹치는 순간. 두 상자는 모두 x 약 237~306px의 폭 55~60px짜리 좁은 상자로, 두 사람 사이 겹친 부분에 생김. box_conf 0.25~0.48, keypoint_conf 0.27~0.36으로 낮음
- 결과영상에서 본 현상:
  - Frame 7·21: ID 1·ID 2 상자 사이에 좁은 상자(ID 4·5)가 하나 더 겹쳐 그려짐. 사람이 셋으로 보이는 게 아니라 두 사람이 겹친 부분을 한 번 더 잡은 것
  - Frame 13: 두 사람이 완전히 껴안아 ID 2 상자 하나가 두 사람을 다 덮음. 이때 ID 1이 사라짐(Frame 9, 12~15, 22, 24)
  - ID 1은 사라졌다가 Frame 16·25에 **같은 번호 1로 돌아옴** → ByteTrack이 잠깐 잃은 Track을 기억하고 있다가 다시 연결함
- 최종 판단:
  - Track Lost + New ID → 아님 (ID 1은 같은 번호로 복귀, 새 번호를 받지 않음)
  - ID Switch 의심 → 아님 (ID 1·2가 서로 바뀐 장면 없음)
  - **중복 Track → 맞음** (ID 4·5는 겹친 부분을 잡은 짧고 낮은 신뢰도의 추가 상자)
  - **짧은 Track Lost → 맞음** (ID 1이 9 Frame 동안 ID 2 상자에 가려짐)

## 3. Kicking

- 전체 Frame: 18
- Unique Track IDs: 2
- Two-ID Frame Ratio: 1.0000
- Extra ID: 0
- ID 1: 18 / 18 Frame (평균 keypoint_conf 0.778)
- ID 2: 18 / 18 Frame (평균 keypoint_conf 0.739)
- Log 해석: 빠른 움직임에서도 두 Track 유지
- 결과영상 확인: Frame 0·9·17에서 왼쪽(차는 사람) ID 1, 오른쪽 ID 2 유지. 다리를 뻗은 Frame 9에서 상자가 커지지만 번호는 그대로
- 최종 판단: Track Lost·ID Switch 없음. 다만 영상이 1.16초(18 Frame)로 짧아 "빠른 움직임에 강하다"고 일반화하기는 어려움

## 4. 세 영상 비교

- 기본 Tracking: Shaking Hands → 안정적
- Occlusion: Hugging → 가장 큰 Tracking 변화 발생
- 빠른 움직임: Kicking → 이번 영상에서는 안정적
- 가장 눈에 띈 문제: Hugging에서 ID 4와 ID 5가 추가로 발생
- 배운 점: Unique ID 수(4)만 보면 ID Switch처럼 보이지만, Frame별 ID 목록과 결과영상을 같이 보면 "중복 상자 + 잠깐 가려짐"이었음. 49번처럼 사람별 Action Buffer를 붙이면 ID 4·5는 3~4 Frame만 쌓이다 사라지므로 Window(기본 5초)가 차지 않아 예측까지 가지 못할 것으로 보이고, ID 1은 가려진 동안 Feature가 빠져 Window가 덜 채워질 것으로 보임 (SBU 영상에는 Action 예측을 붙이지 않아 직접 확인은 안 함)
