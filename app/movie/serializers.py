"""
Serializers for movie APIs
"""
from rest_framework import serializers
from core.models import (
    Movie,
    Genre,
)


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for genres"""

    class Meta:
        model = Genre
        fields = ['id', 'name']
        read_only_fields = ['id']


class MovieSerializer(serializers.ModelSerializer):
    """Serializer for movie."""
    genres = GenreSerializer(many=True, required=False)

    class Meta:
        model = Movie
        fields = ['id', 'title', 'running_time_minutes', 'release_date', 'age_restriction','genres']
        read_only_fields = ['id']

    def _get_or_create_genres(self, genres, movie):
        """Handle getting or creating genres as needed."""
        auth_user = self.context['request'].user
        for genre in genres:
            genre_obj, created = Genre.objects.get_or_create(
                user=auth_user,
                **genre
            )
            movie.genres.add(genre_obj)

    def create(self, validated_data):
        """Create a movie."""
        genres = validated_data.pop('genres', [])
        movie = Movie.objects.create(**validated_data)
        self._get_or_create_genres(genres, movie)
        return movie

    def update(self, instance, validated_data):
        """Update movie."""
        genres = validated_data.pop('genres', None)
        if genres is not None:
            instance.genres.clear()
            self._get_or_create_genres(genres, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance        


class MovieDetailSerializer(MovieSerializer):
    """Serializer for movie detail view."""

    class Meta(MovieSerializer.Meta):
        fields = MovieSerializer.Meta.fields + ['description', 'link', 'image']


class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to movie."""

    class Meta:
        model = Movie
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}
        