from django.db.models import Count
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from community.models import ExperienceApplication, Post
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
            new_images = request.FILES.getlist('images')
            if new_images:
                updated_post.images.all().delete()
                save_images(updated_post, new_images)
            new_videos = request.FILES.getlist('videos')
            if new_videos:
                updated_post.videos.all().delete()
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
    def get(self, request):
        return Response({"message": "ok"})

    def post(self, request):
        return Response({"message": "ok"})


class ExperiencePostDetailView(BusinessAPIView):
    def get(self, request, pk):
        return Response({"message": "ok"})

    def put(self, request, pk):
        return Response({"message": "ok"})

    def delete(self, request, pk):
        return Response({"message": "ok"})


class ExperienceApplicantListView(BusinessAPIView):
    def get(self, request, pk):
        return Response({"message": "ok"})
