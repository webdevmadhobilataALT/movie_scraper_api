

# scraper/urls.py
from django.urls import path
from .views import (
    CategoriesView,
    MoviesView,
    MovieDetailView,
    SearchView,
    ScrapeAllView,
)

urlpatterns = [
    path('categories/', CategoriesView.as_view(), name='categories'),
    path('movies/', MoviesView.as_view(), name='movies'),
    path('movie_details/', MovieDetailView.as_view(), name='movie-details'),
    path('search/', SearchView.as_view(), name='search'),
    path('scrape_all/', ScrapeAllView.as_view(), name='scrape-all'),
]


