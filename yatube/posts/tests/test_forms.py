import tempfile
import shutil

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from django.urls import reverse

from ..models import Post, Comment, Follow
from .utils import Utils

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase, Utils):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user, user_name = cls.new_user()
        cls.user_2, user_name_2 = cls.new_user()
        cls.group, *_ = cls.new_group()
        cls.new_post(cls.user, group=cls.group)

        cls.urls = {
            'create': reverse('posts:post_create'),
            'posts/1': reverse('posts:post_detail', kwargs={'post_id': 1}),
            'posts/1/edit': reverse('posts:post_edit', kwargs={'post_id': 1}),
            'posts/1/comment': reverse(
                'posts:add_comment', kwargs={'post_id': 1}),
            'profile': reverse(
                'posts:profile', kwargs={'username': user_name}),
            'follow': reverse(
                'posts:profile_follow', kwargs={'username': user_name_2}),
            'follow-redirect': reverse(
                'posts:profile', kwargs={'username': user_name_2}),
            'unfollow': reverse(
                'posts:profile_unfollow', kwargs={'username': user_name_2})
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        count = Post.objects.count()

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif')

        form_data = {
            'text': 'Добавлен пост 2',
            'group': '',
            'image': uploaded,
        }

        response = self.authorized_client.post(
            self.urls['create'],
            data=form_data,
            follow=True)

        self.assertRedirects(response, self.urls['profile'])
        self.assertEqual(Post.objects.count(), count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Добавлен пост 2',
                image='posts/small.gif'
            ).exists()
        )

    def test_create_post_error_message(self):
        invalid_text = 'abc'
        response = self.authorized_client.post(
            self.urls['create'],
            data={'text': invalid_text, 'group': ''},
            follow=True)

        expected = 'Пост должен содержать не менее 5 символов'
        self.assertFormError(response, 'form', 'text', expected)
        self.assertEqual(response.status_code, 200,
                         'is_valid == false & страница продолжает работать')

    def test_edit_post(self):
        response = self.authorized_client.post(
            self.urls['posts/1/edit'],
            data={'text': 'Пост pk=1 изменен', 'group': 1},
            follow=True)
        self.assertRedirects(response, self.urls['posts/1'])
        self.assertTrue(
            Post.objects.filter(
                text='Пост pk=1 изменен',
                group=self.group).exists())

    def test_comment(self):
        count = Comment.objects.count()
        form_data = {'text': 'Комментарий добавлен в бд'}

        response = self.authorized_client.post(
            self.urls['posts/1/comment'],
            data=form_data,
            follow=True)

        self.assertRedirects(response, self.urls['posts/1'])
        self.assertEqual(Comment.objects.count(), count + 1)
        self.assertTrue(
            Comment.objects.filter(text='Комментарий добавлен в бд').exists()
        )

    def test_follow(self):
        count = Follow.objects.count()
        response = self.authorized_client.get(
            self.urls['follow'],
            follow=True)

        self.assertRedirects(response, self.urls['follow-redirect'])
        self.assertEqual(Follow.objects.count(), count + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user,
                author=self.user_2
            ).exists()
        )

    def test_unfollow(self):
        response = self.authorized_client.get(
            self.urls['unfollow'],
            follow=True)

        self.assertRedirects(response, self.urls['follow-redirect'])
        self.assertEqual(Follow.objects.count(), 0)
