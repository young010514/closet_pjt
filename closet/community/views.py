from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from .models import Post, PostImage, PostVideo, ExperienceApplication, Comment
from .serializers import PostSerializer, ExperienceApplicationSerializer, CommentSerializer

ORDERING_MAP = {
    'popular': '-like_count',
    'viewed': '-view_count',
    'latest': '-created_at',
}


def check_experience_permission(request, category):
    if not request.user.is_authenticated:
        return Response({'detail': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        user_type = request.user.profile.user_type
    except Exception:
        return Response({'detail': '프로필 정보가 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    if category == 'recruit' and user_type != 'business':
        return Response({'detail': '사업자 회원만 체험단 모집 글을 작성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
    if category == 'review' and user_type != 'normal':
        return Response({'detail': '일반 회원만 체험단 후기 글을 작성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
    return None


def save_images(post, image_files):
    for idx, f in enumerate(image_files):
        PostImage.objects.create(post=post, image=f, order=idx)


def save_videos(post, video_files):
    for idx, f in enumerate(video_files):
        PostVideo.objects.create(post=post, video=f, order=idx)


class PostListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        from django.db.models import Q
        queryset = Post.objects.all()

        board = request.query_params.get('board')
        gender = request.query_params.get('gender')
        category = request.query_params.get('category')
        ordering = request.query_params.get('ordering', 'latest')
        search = request.query_params.get('search', '').strip()

        if board:
            queryset = queryset.filter(board=board)
        if gender:
            queryset = queryset.filter(gender=gender)
        if category:
            queryset = queryset.filter(category=category)
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))

        queryset = queryset.order_by(ORDERING_MAP.get(ordering, '-created_at'))

        serializer = PostSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        board = request.data.get('board', '')
        category = request.data.get('category', '')

        if board == 'experience':
            err = check_experience_permission(request, category)
            if err:
                return err

        serializer = PostSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            author = request.user if request.user.is_authenticated else None
            post = serializer.save(author=author)
            image_files = request.FILES.getlist('images')
            if image_files:
                save_images(post, image_files)
            video_files = request.FILES.getlist('videos')
            if video_files:
                save_videos(post, video_files)
            return Response(PostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        try:
            return (
                Post.objects.select_related('author', 'author__profile')
                .prefetch_related('images')
                .get(pk=pk)
            )
        except Post.DoesNotExist:
            return None

    def get(self, request, pk):
        post = self.get_object(pk)
        if not post:
            return Response(status=status.HTTP_404_NOT_FOUND)
        post.view_count += 1
        post.save(update_fields=['view_count'])
        serializer = PostSerializer(post, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        post = self.get_object(pk)
        if not post:
            return Response(status=status.HTTP_404_NOT_FOUND)

        board = request.data.get('board', post.board)
        category = request.data.get('category', post.category)

        if board == 'experience':
            err = check_experience_permission(request, category)
            if err:
                return err

        serializer = PostSerializer(post, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            post = serializer.save()
            new_images = request.FILES.getlist('images')
            if new_images:
                post.images.all().delete()
                save_images(post, new_images)
            new_videos = request.FILES.getlist('videos')
            if new_videos:
                post.videos.all().delete()
                save_videos(post, new_videos)
            return Response(PostSerializer(post, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        post = self.get_object(pk)
        if not post:
            return Response(status=status.HTTP_404_NOT_FOUND)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLikeView(APIView):
    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        post.like_count += 1
        post.save(update_fields=['like_count'])
        return Response({'like_count': post.like_count})


class CommentListCreateView(APIView):
    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(post.comments.all(), many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'detail': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(post=post, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailView(APIView):
    def _get_comment(self, comment_pk, user):
        try:
            comment = Comment.objects.get(pk=comment_pk)
        except Comment.DoesNotExist:
            return None, Response(status=status.HTTP_404_NOT_FOUND)
        if comment.author_id != user.pk:
            return None, Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        return comment, None

    def put(self, request, pk, comment_pk):
        if not request.user.is_authenticated:
            return Response({'detail': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        comment, err = self._get_comment(comment_pk, request.user)
        if err:
            return err
        serializer = CommentSerializer(comment, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, comment_pk):
        if not request.user.is_authenticated:
            return Response({'detail': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        comment, err = self._get_comment(comment_pk, request.user)
        if err:
            return err
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExperienceApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_recruit_post(self, pk):
        try:
            return Post.objects.get(pk=pk, board='experience', category='recruit')
        except Post.DoesNotExist:
            return None

    def get(self, request, pk):
        """신청 여부 확인"""
        post = self._get_recruit_post(pk)
        if not post:
            return Response(status=status.HTTP_404_NOT_FOUND)
        applied = ExperienceApplication.objects.filter(post=post, applicant=request.user).exists()
        return Response({'applied': applied})

    def post(self, request, pk):
        """신청 제출"""
        post = self._get_recruit_post(pk)
        if not post:
            return Response({'detail': '해당 체험단 모집 글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        if post.experience_status != 'recruiting':
            return Response({'detail': '모집 중인 체험단에만 신청할 수 있습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if request.user.profile.user_type != 'normal':
                return Response({'detail': '일반 회원만 체험단을 신청할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({'detail': '프로필 정보가 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        if ExperienceApplication.objects.filter(post=post, applicant=request.user).exists():
            return Response({'detail': '이미 신청하셨습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExperienceApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(post=post, applicant=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
