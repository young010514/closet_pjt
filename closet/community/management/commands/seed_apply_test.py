import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from community.models import Post, ExperienceApplication

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed test data for experience application feature'

    def handle(self, *args, **options):
        today = timezone.localdate()

        # 비즈니스 유저 (모집글 작성자)
        biz_user, created = User.objects.get_or_create(
            username='biz_test',
            defaults={'email': 'biz@test.com'},
        )
        if created or not biz_user.check_password('test1234!'):
            biz_user.set_password('test1234!')
            biz_user.save()

        if not hasattr(biz_user, 'profile'):
            from accounts.models import UserProfile, TermsAgreement
            UserProfile.objects.create(
                user=biz_user,
                user_type='business',
                real_name='사업자테스트',
                nickname='비즈니스유저',
                phone='010-1111-2222',
            )
            TermsAgreement.objects.create(
                user=biz_user,
                service_terms_agreed=True,
                privacy_agreed=True,
            )
        else:
            biz_user.profile.user_type = 'business'
            biz_user.profile.save()

        # 일반 유저 (신청자)
        normal_user, created = User.objects.get_or_create(
            username='normal_test',
            defaults={'email': 'normal@test.com'},
        )
        if created or not normal_user.check_password('test1234!'):
            normal_user.set_password('test1234!')
            normal_user.save()

        if not hasattr(normal_user, 'profile'):
            from accounts.models import UserProfile, TermsAgreement
            UserProfile.objects.create(
                user=normal_user,
                user_type='normal',
                real_name='일반테스트',
                nickname='일반유저',
                phone='010-3333-4444',
            )
            TermsAgreement.objects.create(
                user=normal_user,
                service_terms_agreed=True,
                privacy_agreed=True,
            )
        else:
            normal_user.profile.user_type = 'normal'
            normal_user.profile.save()

        # 모집중 체험단 게시물
        Post.objects.filter(title='[TEST] 체험단 신청 테스트 - 모집중').delete()
        post = Post.objects.create(
            board='experience',
            category='recruit',
            author=biz_user,
            title='[TEST] 체험단 신청 테스트 - 모집중',
            store_name='클로젯 패션샵',
            store_location='서울시 강남구 역삼동 123-4',
            product_description='신상 여름 린넨 셔츠 체험단을 모집합니다.\n편안한 소재와 세련된 디자인으로 이번 여름을 시원하게!',
            notice='''■ 체험단 인원: 5명
■ 신청 방법: 아래 신청 폼 작성
■ 제공 혜택: 린넨 셔츠 1장 (5만원 상당) 무상 제공
■ 후기 작성 기간: 체험 후 2주 이내
■ 주의 사항:
  - 체험 후 SNS 또는 블로그에 솔직한 후기를 작성해 주세요.
  - 제공된 제품은 반납하지 않아도 됩니다.''',
            recruit_start=today - datetime.timedelta(days=3),
            recruit_end=today + datetime.timedelta(days=7),
            experience_end=today + datetime.timedelta(days=30),
        )

        # 기존 신청 삭제 후 재생성
        ExperienceApplication.objects.filter(post=post).delete()
        ExperienceApplication.objects.create(
            post=post,
            applicant=normal_user,
            name='김일반',
            phone='010-3333-4444',
            sns_account='@normal_insta',
            motivation='패션에 관심이 많아 체험단에 참여하고 싶습니다. 인스타그램 팔로워 2,000명 보유 중입니다.',
        )

        self.stdout.write('')
        self.stdout.write('=== 테스트 계정 ===')
        self.stdout.write(f'  비즈니스 유저: biz_test / test1234!')
        self.stdout.write(f'  일반 유저:     normal_test / test1234!  (이미 신청 완료 상태)')
        self.stdout.write('')
        self.stdout.write(f'=== 테스트 게시물 ===')
        self.stdout.write(f'  ID: {post.id}  |  {post.title}')
        self.stdout.write(f'  status: {post.experience_status}')
        self.stdout.write(f'  recruit_end: {post.recruit_end}  /  experience_end: {post.experience_end}')
        self.stdout.write('')
        self.stdout.write('  접속: http://localhost:5173/community 에서 체험단 탭 확인')
        self.stdout.write(f'  상세: http://localhost:5173/community/{post.id}')
