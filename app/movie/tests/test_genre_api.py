"""
Tests for the genre APIs.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Genre
from movie.serializers import GenreSerializer

GENRE_URL = reverse('movie:genre-list')

def detail_url(genre_id):
    """Create and return a tag detail url."""
    return reverse('movie:genre-detail', args=[genre_id])

def create_user(email='user@example', password='testpass123'):
    """Create and return a user."""
    return get_user_model().objects.create_user(email=email, password=password)

class PublicGenresApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving genres"""
        res = self.client.get(GENRE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PublicGenresApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_genres(self):
        """Test retirieving a list of genres."""
        Genre.objects.create(user=self.user, name='Action')
        Genre.objects.create(user=self.user, name='Drama')

        res = self.client.get(GENRE_URL)

        genres = Genre.objects.all().order_by('-name')
        serializer = GenreSerializer(genres, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_genres_limited_to_user(self):
        """Test list of genres is limited to authoricated user."""
        user2 = create_user(email='user2@example.com')
        Genre.objects.create(user=user2, name='Romance')
        genre = Genre.objects.create(user=self.user, name='Adventure')

        res = self.client.get(GENRE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], genre.name)
        self.assertEqual(res.data[0]['id'], genre.id)

    def test_update_genre(self):
        """Test updating a genre."""
        genre = Genre.objects.create(user=self.user, name='Sci-Fi')

        payload = {'name':'Comedy'}
        url = detail_url(genre.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        genre.refresh_from_db()
        self.assertEqual(genre.name, payload['name'])

    def test_delete_genre(self):
        """Test deleting a genre."""
        genre = Genre.objects.create(user=self.user, name='Romantic')

        url = detail_url(genre.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        genres = Genre.objects.filter(user=self.user)
        self.assertFalse(genres.exists())
