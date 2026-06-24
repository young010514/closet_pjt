from rest_framework import serializers

from accounts.serializers import PublicUserSerializer

from .models import Post, PostImage, PostVideo, ExperienceApplication, Comment


class PostImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    class Meta:
        model = PostImage
        fields = ['id', 'image_url', 'order']


class PostVideoSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()

    def get_video_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.video.url)
        return obj.video.url

    class Meta:
        model = PostVideo
        fields = ['id', 'video_url', 'order']


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    experience_status = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

    def get_author_name(self, obj):
        if obj.author is None:
            return '익명'
        try:
            return obj.author.profile.nickname
        except Exception:
            return obj.author.username

    def get_experience_status(self, obj):
        return obj.experience_status

    def get_images(self, obj):
        request = self.context.get('request')
        return PostImageSerializer(obj.images.all(), many=True, context={'request': request}).data

    def get_videos(self, obj):
        request = self.context.get('request')
        return PostVideoSerializer(obj.videos.all(), many=True, context={'request': request}).data

    def validate(self, attrs):
        board = attrs.get('board', '')
        category = attrs.get('category', '')

        if board == 'experience' and category == 'recruit':
            if not attrs.get('recruit_start'):
                raise serializers.ValidationError({'recruit_start': '모집 시작일을 입력해주세요.'})
            if not attrs.get('recruit_end'):
                raise serializers.ValidationError({'recruit_end': '모집 마감일을 입력해주세요.'})
            if not attrs.get('experience_end'):
                raise serializers.ValidationError({'experience_end': '체험단 종료일을 입력해주세요.'})
            if attrs.get('recruit_start') and attrs.get('recruit_end') and attrs['recruit_start'] > attrs['recruit_end']:
                raise serializers.ValidationError({'recruit_end': '모집 마감일은 시작일 이후여야 합니다.'})
            if attrs.get('recruit_end') and attrs.get('experience_end') and attrs['recruit_end'] > attrs['experience_end']:
                raise serializers.ValidationError({'experience_end': '체험단 종료일은 모집 마감일 이후여야 합니다.'})

        return attrs
    like_count=serializers.IntegerField(read_only=True)
    is_liked=serializers.SerializerMethodField()
    class Meta:
        model = Post
        fields = [
            'id', 'board', 'title', 'content', 'gender', 'category',
            'hashtags', 'author', 'author_name',
            'store_name', 'store_location', 'product_description', 'notice',
            'recruit_start', 'recruit_end', 'experience_end',
            'experience_participation_start', 'experience_participation_end',
            'experience_status', 'images', 'videos',
            'view_count', 'like_count','is_liked', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'author', 'author_name', 'experience_status', 'images', 'videos',
            'view_count', 'like_count', 'created_at', 'updated_at',
        ]
    def get_is_liked(self, obj):
        request = self.context.get('request')
 
        if not request or not request.user.is_authenticated:
            return False

        return obj.liked_users.filter(pk=request.user.pk).exists()


class ExperienceApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperienceApplication
        fields = ['id', 'name', 'phone', 'sns_account', 'motivation', 'status', 'rejection_reason', 'created_at']
        read_only_fields = ['status', 'rejection_reason', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_author = serializers.SerializerMethodField()

    def get_author_name(self, obj):
        if obj.author is None:
            return '익명'
        try:
            return obj.author.profile.nickname
        except Exception:
            return obj.author.username

    def get_is_author(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.author_id == request.user.pk
        return False

    class Meta:
        model = Comment
        fields = ['id', 'author_name', 'is_author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['author_name', 'is_author', 'created_at', 'updated_at']
