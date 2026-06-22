from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Post
from .serializers import PostSerializer

ORDERING_MAP = {
    'popular': '-like_count',
    'viewed': '-view_count',
    'latest': '-created_at',
}


class PostListCreateView(APIView):
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

        serializer = PostSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            author = request.user if request.user.is_authenticated else None
            serializer.save(author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
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
        serializer = PostSerializer(post)
        return Response(serializer.data)

    def put(self, request, pk):
        post = self.get_object(pk)
        if not post:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
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
