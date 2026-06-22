from django.contrib.auth import get_user_model
from community.models import Post
from django.utils import timezone
import datetime

User = get_user_model()

user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()
print(f'사용 유저: {user}')

today = timezone.localdate()
print(f'오늘 날짜(KST): {today}')

Post.objects.filter(title__startswith='[TEST]').delete()

p1 = Post.objects.create(
    board='experience', category='recruit', author=user,
    title='[TEST] 모집중 테스트',
    recruit_start=today - datetime.timedelta(days=3),
    recruit_end=today + datetime.timedelta(days=7),
    experience_end=today + datetime.timedelta(days=30),
)

p2 = Post.objects.create(
    board='experience', category='recruit', author=user,
    title='[TEST] 마감 테스트',
    recruit_start=today - datetime.timedelta(days=10),
    recruit_end=today,
    experience_end=today + datetime.timedelta(days=20),
)

p3 = Post.objects.create(
    board='experience', category='recruit', author=user,
    title='[TEST] 종료 테스트',
    recruit_start=today - datetime.timedelta(days=30),
    recruit_end=today - datetime.timedelta(days=20),
    experience_end=today - datetime.timedelta(days=5),
)

p4 = Post.objects.create(
    board='experience', category='recruit', author=user,
    title='[TEST] 미시작 테스트',
    recruit_start=today + datetime.timedelta(days=5),
    recruit_end=today + datetime.timedelta(days=15),
    experience_end=today + datetime.timedelta(days=30),
)

print()
print('=== experience_status 결과 ===')
for p in [p1, p2, p3, p4]:
    print(f'{p.title}')
    print(f'  recruit_start={p.recruit_start}, recruit_end={p.recruit_end}, experience_end={p.experience_end}')
    print(f'  status = "{p.experience_status}"')
    print()
