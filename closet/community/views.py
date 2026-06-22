from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Post, PostImage
from .serializers import PostSerializer

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


class PostListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        queryset = Post.objects.all()

        board = request.query_params.get('board')
        gender = request.query_params.get('gender')
        category = request.query_params.get('category')
        ordering = request.query_params.get('ordering', 'latest')

        if board:
            queryset = queryset.filter(board=board)
        if gender:
            queryset = queryset.filter(gender=gender)
        if category:
            queryset = queryset.filter(category=category)

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
            return Response(PostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        try:
            return Post.objects.get(pk=pk)
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
