from rest_framework import serializers
from .models import Post


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    def get_author_name(self, obj):
        return obj.author.username if obj.author else '익명'

    class Meta:
        model = Post
        fields = [
            'id', 'board', 'title', 'content', 'gender', 'category',
            'hashtags', 'author', 'author_name',
            'view_count', 'like_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['author', 'view_count', 'like_count', 'created_at', 'updated_at']
