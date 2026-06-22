import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from community.models import Post

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test experience posts for all status types'

    def handle(self, *args, **options):
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not user:
            user = User.objects.create_superuser(
                username='testadmin',
                email='testadmin@test.com',
                password='testpass123!',
            )
            self.stdout.write('Created test superuser: testadmin / testpass123!')

        today = timezone.localdate()
        self.stdout.write(f'User: {user.username}')
        self.stdout.write(f'Today (KST): {today}')
        self.stdout.write('')

        Post.objects.filter(title__startswith='[TEST]').delete()
        self.stdout.write('Deleted previous [TEST] posts.')
        self.stdout.write('')

        cases = [
            {
                'title': '[TEST] Recruiting - recruit_start=today-3, recruit_end=today+7, exp_end=today+30',
                'recruit_start': today - datetime.timedelta(days=3),
                'recruit_end': today + datetime.timedelta(days=7),
                'experience_end': today + datetime.timedelta(days=30),
            },
            {
                'title': '[TEST] Closed (boundary) - recruit_end=today, exp_end=today+20',
                'recruit_start': today - datetime.timedelta(days=10),
                'recruit_end': today,
                'experience_end': today + datetime.timedelta(days=20),
            },
            {
                'title': '[TEST] Closed (past) - recruit_end=today-5, exp_end=today+10',
                'recruit_start': today - datetime.timedelta(days=15),
                'recruit_end': today - datetime.timedelta(days=5),
                'experience_end': today + datetime.timedelta(days=10),
            },
            {
                'title': '[TEST] Ended - exp_end=today-5',
                'recruit_start': today - datetime.timedelta(days=30),
                'recruit_end': today - datetime.timedelta(days=20),
                'experience_end': today - datetime.timedelta(days=5),
            },
            {
                'title': '[TEST] Not started - recruit_start=today+5',
                'recruit_start': today + datetime.timedelta(days=5),
                'recruit_end': today + datetime.timedelta(days=15),
                'experience_end': today + datetime.timedelta(days=30),
            },
        ]

        for c in cases:
            p = Post.objects.create(
                board='experience',
                category='recruit',
                author=user,
                title=c['title'],
                recruit_start=c['recruit_start'],
                recruit_end=c['recruit_end'],
                experience_end=c['experience_end'],
            )
            status = p.experience_status
            self.stdout.write(
                f'  recruit_start={p.recruit_start} | recruit_end={p.recruit_end} | exp_end={p.experience_end}'
            )
            self.stdout.write(f'  => status: "{status}"')
            self.stdout.write('')
