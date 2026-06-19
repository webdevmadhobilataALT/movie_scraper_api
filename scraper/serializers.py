

# scraper/serializers.py
from rest_framework import serializers

# ---------- Output Serializers (for API responses) ----------
class CategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    url = serializers.URLField()


class MovieSummarySerializer(serializers.Serializer):
    title = serializers.CharField()
    url = serializers.URLField()
    thumbnail = serializers.URLField(required=False, allow_null=True)


class MovieDetailSerializer(serializers.Serializer):
    title = serializers.CharField()
    genre = serializers.CharField()
    director = serializers.CharField()
    actors = serializers.CharField()
    country = serializers.CharField()
    duration = serializers.CharField()
    quality = serializers.CharField()
    release = serializers.CharField()
    imdb = serializers.CharField()
    description = serializers.CharField()


# ---------- Input Serializers (for POST payload validation) ----------
class CategoriesInputSerializer(serializers.Serializer):
    base_url = serializers.URLField(required=False)


class MoviesInputSerializer(serializers.Serializer):
    category_url = serializers.URLField(required=True)
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    limit = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class MovieDetailInputSerializer(serializers.Serializer):
    url = serializers.URLField(required=True)


class SearchInputSerializer(serializers.Serializer):
    q = serializers.CharField(required=True, max_length=200)
    base_url = serializers.URLField(required=False)


class ScrapeAllInputSerializer(serializers.Serializer):
    base_url = serializers.URLField(required=True)
    start_path = serializers.CharField(required=True)
    max_pages = serializers.IntegerField(required=False, default=517, min_value=1)
    max_movies = serializers.IntegerField(required=False, allow_null=True, min_value=1)