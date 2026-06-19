from django.shortcuts import render

# Create your views here.


# scraper/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

from .serializers import (
    CategorySerializer,
    MovieSummarySerializer,
    MovieDetailSerializer,
    CategoriesInputSerializer,
    MoviesInputSerializer,
    MovieDetailInputSerializer,
    SearchInputSerializer,
    ScrapeAllInputSerializer,
)
from .utils import (
    get_categories,
    get_movie_list,
    get_movie_detail,
    search_movies,
    scrape_category_pages,
)

logger = logging.getLogger(__name__)


class CategoriesView(APIView):
    """
    POST /api/categories/
    Payload: { "base_url": "https://watchofree.website" } (optional)
    Returns a list of all categories.
    """
    def post(self, request):
        serializer = CategoriesInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        base_url = serializer.validated_data.get('base_url', settings.BASE_URL)

        try:
            categories = get_categories(base_url)
        except Exception as e:
            logger.exception("Error fetching categories")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        output_serializer = CategorySerializer(categories, many=True)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


class MoviesView(APIView):
    """
    POST /api/movies/
    Payload: { "category_url": "...", "page": 1, "limit": 10 }
    Returns movie summaries for a specific category page.
    """
    def post(self, request):
        serializer = MoviesInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        category_url = data['category_url']
        page = data.get('page', 1)
        limit = data.get('limit')

        try:
            movies = get_movie_list(category_url, page=page, max_items=limit)
        except Exception as e:
            logger.exception("Error fetching movies")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        output_serializer = MovieSummarySerializer(movies, many=True)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


class MovieDetailView(APIView):
    """
    POST /api/movie_details/
    Payload: { "url": "https://.../movie/123" }
    Returns full details of a single movie.
    """
    def post(self, request):
        serializer = MovieDetailInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        movie_url = serializer.validated_data['url']

        try:
            movie_data = get_movie_detail(movie_url)
        except Exception as e:
            logger.exception("Error fetching movie details")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not movie_data:
            return Response(
                {'error': 'Movie not found or could not be scraped'},
                status=status.HTTP_404_NOT_FOUND
            )

        output_serializer = MovieDetailSerializer(movie_data)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


class SearchView(APIView):
    """
    POST /api/search/
    Payload: { "q": "avengers", "base_url": "..." } (base_url optional)
    Returns search results as movie summaries.
    """
    def post(self, request):
        serializer = SearchInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data['q']
        base_url = serializer.validated_data.get('base_url', settings.BASE_URL)

        try:
            results = search_movies(query, base_url)
        except Exception as e:
            logger.exception("Error during search")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        output_serializer = MovieSummarySerializer(results, many=True)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


class ScrapeAllView(APIView):
    """
    POST /api/scrape_all/
    Payload: {
        "base_url": "https://watchofree.website",
        "start_path": "/director/netflix/",
        "max_pages": 517,
        "max_movies": null
    }
    Scrapes ALL pages and returns all movies in one JSON array.
    WARNING: This can take several minutes.
    """
    def post(self, request):
        serializer = ScrapeAllInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        base_url = data['base_url']
        start_path = data['start_path']
        max_pages = data.get('max_pages', 517)
        max_movies = data.get('max_movies')

        try:
            movies = scrape_category_pages(
                base_url=base_url,
                start_path=start_path,
                max_pages=max_pages,
                max_movies=max_movies
            )
        except Exception as e:
            logger.exception("Error in full scrape")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        output_serializer = MovieDetailSerializer(movies, many=True)
        return Response(output_serializer.data, status=status.HTTP_200_OK)
    
    