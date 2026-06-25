from django.db.models import Count
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from community.models import ExperienceApplication, Post, PostImage, PostVideo
from community.serializers import PostSerializer
from community.views import save_images, save_videos

from .authentication import SessionAuthentication401
from .permissions import IsBusinessUser

ORDERING_MAP = {
    'popular': '-like_count',
    'viewed': '-view_count',
    'latest': '-created_at',
}


class BusinessAPIView(APIView):
    authentication_classes = [SessionAuthentication401]
    permission_classes = [IsAuthenticated, IsBusinessUser]


class DashboardView(BusinessAPIView):
    def get(self, request):
        user = request.user

        try:
            bp = user.business_profile
            store_name = bp.business_name
            store_address = bp.address
        except Exception:
            store_name = ''
            store_address = ''
        local_shop_post_count = Post.objects.filter(author=user, board='local_shop').count()

        experience_posts = Post.objects.filter(author=user, board='experience', category='recruit')
        recruiting = sum(1 for p in experience_posts if p.experience_status == 'recruiting')
        closed = sum(1 for p in experience_posts if p.experience_status == 'closed')
        ended = sum(1 for p in experience_posts if p.experience_status == 'ended')
        total = experience_posts.count()

        applicant_qs = (
            ExperienceApplication.objects
            .filter(post__author=user)
            .values('post_id', 'post__title')
            .annotate(applicant_count=Count('id'))
        )
        applicant_summary = [
            {
                'post_id': r['post_id'],
                'title': r['post__title'],
                'applicant_count': r['applicant_count'],
            }
            for r in applicant_qs
        ]

        recent_qs = Post.objects.filter(author=user).order_by('-created_at')[:5]
        recent_posts = [
            {
                'id': p.id,
                'title': p.title,
                'board': p.board,
                'created_at': p.created_at,
            }
            for p in recent_qs
        ]

        data = {
            'store_summary': {
                'store_name': store_name,
                'store_address': store_address,
                'local_shop_post_count': local_shop_post_count,
            },
            'experience_summary': {
                'recruiting': recruiting,
                'closed': closed,
                'ended': ended,
                'total': total,
            },
            'applicant_summary': applicant_summary,
            'recent_posts': recent_posts,
        }

        return Response(data)


class StorePostListCreateView(BusinessAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        ordering = request.query_params.get('ordering', 'latest')
        qs = Post.objects.filter(author=request.user, board='local_shop').order_by(
            ORDERING_MAP.get(ordering, '-created_at')
        )
        serializer = PostSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['board'] = 'local_shop'
        serializer = PostSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            try:
                store_location = ' '.join(request.user.business_profile.address.split())
            except Exception:
                store_location = ''
            post = serializer.save(author=request.user, board='local_shop', store_location=store_location)
            images = request.FILES.getlist('images')
            if images:
                save_images(post, images)
            videos = request.FILES.getlist('videos')
            if videos:
                save_videos(post, videos)
            return Response(
                PostSerializer(post, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StorePostDetailView(BusinessAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_own_post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk, board='local_shop')
        except Post.DoesNotExist:
            return None, Response(status=status.HTTP_404_NOT_FOUND)
        if post.author_id != request.user.pk:
            return None, Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        return post, None

    def get(self, request, pk):
        post, err = self._get_own_post(request, pk)
        if err:
            return err
        return Response(PostSerializer(post, context={'request': request}).data)

    def put(self, request, pk):
        post, err = self._get_own_post(request, pk)
        if err:
            return err
        data = request.data.copy()
        data['board'] = 'local_shop'
        serializer = PostSerializer(post, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            try:
                store_location = ' '.join(request.user.business_profile.address.split())
            except Exception:
                store_location = ''
            updated_post = serializer.save(board='local_shop', store_location=store_location)
            delete_image_ids = request.data.getlist('delete_image_ids')
            if delete_image_ids:
                PostImage.objects.filter(post=updated_post, pk__in=delete_image_ids).delete()
            delete_video_ids = request.data.getlist('delete_video_ids')
            if delete_video_ids:
                PostVideo.objects.filter(post=updated_post, pk__in=delete_video_ids).delete()
            new_images = request.FILES.getlist('images')
            if new_images:
                save_images(updated_post, new_images)
            new_videos = request.FILES.getlist('videos')
            if new_videos:
                save_videos(updated_post, new_videos)
            return Response(PostSerializer(updated_post, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        post, err = self._get_own_post(request, pk)
        if err:
            return err
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExperiencePostListCreateView(BusinessAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        ordering = request.query_params.get('ordering', 'latest')
        qs = Post.objects.filter(author=request.user, board='experience', category='recruit').order_by(
            ORDERING_MAP.get(ordering, '-created_at')
        )
        serializer = PostSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['board'] = 'experience'
        data['category'] = 'recruit'
        serializer = PostSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            try:
                store_location = ' '.join(request.user.business_profile.address.split())
            except Exception:
                store_location = ''
            post = serializer.save(
                author=request.user,
                board='experience',
                category='recruit',
                store_location=store_location,
            )
            images = request.FILES.getlist('images')
            if images:
                save_images(post, images)
            return Response(
                PostSerializer(post, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExperiencePostDetailView(BusinessAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_own_post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk, board='experience', category='recruit')
        except Post.DoesNotExist:
            return None, Response(status=status.HTTP_404_NOT_FOUND)
        if post.author_id != request.user.pk:
            return None, Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        return post, None

    def get(self, request, pk):
        post, err = self._get_own_post(request, pk)
        if err:
            return err
        return Response(PostSerializer(post, context={'request': request}).data)

    def put(self, request, pk):
        post, err = self._get_own_post(request, pk)
        if err:
            return err
        data = request.data.copy()
        data['board'] = 'experience'
        data['category'] = 'recruit'
        serializer = PostSerializer(post, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            updated_post = serializer.save(board='experience', category='recruit')
            new_images = request.FILES.getlist('images')
            if new_images:
                updated_post.images.all().delete()
                save_images(updated_post, new_images)
            return Response(PostSerializer(updated_post, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        post, err = self._get_own_post(request, pk)
        if err:
            return err
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExperienceApplicantListView(BusinessAPIView):
    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk, board='experience', category='recruit')
        except Post.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if post.author_id != request.user.pk:
            return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        applications = post.applications.select_related('applicant').order_by('created_at')
        data = [
            {
                'id': a.id,
                'applicant_id': a.applicant_id,
                'name': a.name,
                'phone': a.phone,
                'sns_account': a.sns_account,
                'motivation': a.motivation,
                'status': a.status,
                'rejection_reason': a.rejection_reason,
                'created_at': a.created_at,
            }
            for a in applications
        ]
        return Response(data)


class ExperienceApplicantDecisionView(BusinessAPIView):
    def patch(self, request, pk, application_id):
        try:
            post = Post.objects.get(pk=pk, board='experience', category='recruit')
        except Post.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if post.author_id != request.user.pk:
            return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            application = ExperienceApplication.objects.get(pk=application_id, post=post)
        except ExperienceApplication.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        decision = request.data.get('status')
        if decision not in (ExperienceApplication.STATUS_APPROVED, ExperienceApplication.STATUS_REJECTED):
            return Response({'detail': '유효하지 않은 상태값입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if decision == ExperienceApplication.STATUS_REJECTED:
            rejection_reason = request.data.get('rejection_reason', '').strip()
            if not rejection_reason:
                return Response({'detail': '거절 사유를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
            application.rejection_reason = rejection_reason

        application.status = decision
        application.save(update_fields=['status', 'rejection_reason'])

        return Response({
            'id': application.id,
            'status': application.status,
            'rejection_reason': application.rejection_reason,
        })
