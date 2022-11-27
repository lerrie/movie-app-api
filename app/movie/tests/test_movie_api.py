"""
Test for Movie APIs.
"""
from datetime import date
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Movie,
    Genre,
)
from movie.serializers import  (
    MovieSerializer,
    MovieDetailSerializer
)

MOVIES_URL = reverse('movie:movie-list')

def detail_url(movie_id):
    """Create and return a movie detail URL."""
    return reverse('movie:movie-detail',args=[movie_id])

def image_upload_url(movie_id):
    """Create and return an image upload URL."""
    return reverse('movie:movie-upload-image',args=[movie_id])

def create_movie(user, **params):
    """Create and return a sample movie."""
    defaults = {
        'title': 'Sample movie name',
        'description': 'Sample movie description.',
        'running_time_minutes': 120,
        'release_date': date(2022,10,15),
        'age_restriction': 'PG13',
        'link': 'https://example.com/movie.pdf'
    }
    defaults.update(params)

    movie = Movie.objects.create(user=user, **defaults)
    return movie

def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)

class PublicMovieAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(MOVIES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_movie(self):
        """Test retrieving a list of movies."""
        create_movie(user=self.user)
        create_movie(user=self.user)

        res = self.client.get(MOVIES_URL)

        movies = Movie.objects.all().order_by('title')
        serializer = MovieSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_list_limited_to_user(self):
        """Test list of movies is limited to authenticated user."""
        other_user = create_user(email='otheruser@example.com', password='test123')
        create_movie(user=other_user)
        create_movie(user=self.user)

        res = self.client.get(MOVIES_URL)

        movies = Movie.objects.filter(user=self.user)
        serializer = MovieSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_movie_detail(self):
        """Test get movie detail."""
        movie = create_movie(user=self.user)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.data, serializer.data)
    
    def test_create_movie(self):
        """Test creating a movie."""
        payload = {
            'title': 'Sample movie',
            'running_time_minutes': 120,
        }
        res = self.client.post(MOVIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(movie, k), v)
        self.assertEqual(movie.user, self.user)

    def test_partial_update(self):
        """Test partial update of a recipe."""
        original_link = 'https://example.com/movie.pdf'
        movie = create_movie(
            user=self.user,
            title='Sample movie title',
            link=original_link,
        )
        
        payload = {'title':'New movie title'}
        url = detail_url(movie.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertEqual(movie.title, payload['title'])
        self.assertEqual(movie.link, original_link)
        self.assertEqual(movie.user, self.user)
    
    def test_full_update(self):
        """Test full update of movie."""
        movie = create_movie(
            user=self.user,
            title='Sample movie title',
            link='https://example.com/movie.pdf',
            description='Sample movie description',
        )

        payload = {
            'title': 'New movie title',
            'link': 'https://example.com/movie-updated.pdf',
            'description': 'New movie description',
            'running_time_minutes': 180,
            'release_date': date(2022, 10,30),
            'age_restriction': 'G',
        }
        url = detail_url(movie.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(movie, k), v)
        self.assertEqual(movie.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the movie user results in an error."""
        new_user = create_user(email='user2@example.com', password='test123')
        movie = create_movie(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(movie.id)
        self.client.patch(url, payload)

        movie.refresh_from_db()
        self.assertEqual(movie.user, self.user)

    def test_delete_movie(self):
        """Test deleting a movie successfully."""
        movie = create_movie(user=self.user)

        url = detail_url(movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists()) 

    def test_delete_other_users_movie_error(self):
        """Test trying to delete another users movie gives error."""
        new_user = create_user(email='user2@example.com', password='test123')
        movie = create_movie(user=new_user)

        url = detail_url(movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Movie.objects.filter(id=movie.id).exists()) 
    
    def test_create_movie_with_new_genres(self):
        """Test creating a movie with new genres."""
        payload = {
            'title': 'New movie title',
            'link': 'https://example.com/movie-updated.pdf',
            'description': 'New movie description',
            'running_time_minutes': 180,
            'release_date': date(2022, 10, 10),
            'age_restriction': 'G',
            'genres': [{'name': 'Action'}, {'name': 'Romance'}],
        }
        res = self.client.post(MOVIES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movies = Movie.objects.filter(user=self.user)
        self.assertEqual(movies.count(), 1)
        movie = movies[0]
        self.assertEqual(movie.genres.count(), 2)
        for genre in payload['genres']:
            exists = movie.genres.filter(
                name=genre['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)
    
    def test_create_movie_with_existing_genre(self):
        """Test creating a recipe with existing genre."""
        genre_comedy = Genre.objects.create(user=self.user, name='Comedy')
        payload = {
            'title': 'New movie title',
            'link': 'https://example.com/movie-updated.pdf',
            'description': 'New movie description',
            'running_time_minutes': 180,
            'release_date': date(2022, 10, 10),
            'age_restriction': 'G',
            'genres': [{'name': 'Comedy'}, {'name': 'Romance'}],
        }
        res = self.client.post(MOVIES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movies = Movie.objects.filter(user=self.user)
        self.assertEqual(movies.count(), 1)
        movie = movies[0]
        self.assertEqual(movie.genres.count(), 2)
        for genre in payload['genres']:
            exists = movie.genres.filter(
                name=genre['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_genre_on_update(self):
        """Test creating genre when updating a movie,"""
        movie = create_movie(user=self.user)

        payload = {'genres': [{'name':'Adventure'}]}
        url = detail_url(movie.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_genre = Genre.objects.get(user=self.user, name='Adventure')
        self.assertIn(new_genre, movie.genres.all())

    def test_update_movie_assign_genre(self):
        """Test assigning an exsting genre when updating a movie."""
        genre_comedy = Genre.objects.create(user=self.user, name='Comedy')
        movie = create_movie(user=self.user)
        movie.genres.add(genre_comedy)

        genre_action = Genre.objects.create(user=self.user, name='Action')
        payload = {'genres': [{'name':'Action'}]}
        url = detail_url(movie.id)
        res = self.client.patch(url, payload, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(genre_action, movie.genres.all())
        self.assertNotIn(genre_comedy, movie.genres.all())
        
    def test_clear_movie_genres(self):
        """Test clearing a movie genres."""
        genre = Genre.objects.create(user=self.user, name='Sci-Fi')
        movie = create_movie(user=self.user)
        movie.genres.add(genre)

        payload = {'genres': []}
        url = detail_url(movie.id)
        res = self.client.patch(url, payload, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(movie.genres.count(), 0)

    def test_filter_by_genres(self):
        """Test filtering movies by tags."""
        m1 = create_movie(user=self.user, title='Black Adam')
        m2 = create_movie(user=self.user, title='Avengers')
        genre1 = Genre.objects.create(user=self.user, name='Adventure')
        genre2 = Genre.objects.create(user=self.user, name='Sci-Fi')
        m1.genres.add(genre1)
        m2.genres.add(genre2)
        m3 = create_movie(user=self.user, title='Holidays')

        params = {'genres': f'{genre1.id},{genre2.id}'}
        res = self.client.get(MOVIES_URL, params)

        s1 = MovieSerializer(m1)
        s2 = MovieSerializer(m2)
        s3 = MovieSerializer(m3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
        )
        self.client.force_authenticate(self.user)
        self.movie = create_movie(user=self.user)

    def tearDown(self):
        self.movie.image.delete()
    
    def test_upload_image(self):
        """Test uploading an image to a movie."""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10,10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image."""
        url = image_upload_url(self.movie.id)
        payload = {'image':'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
