from unittest import mock

from django.db.utils import IntegrityError
from django.db.utils import DataError
from django.test import TestCase

from ranking import factory
from ranking.mock import response_data_mock
from ranking.models import Content
from ranking.models import ScrapingContent
from ranking.models import TwitterApi
from ranking.models import TwitterUser

# Create your tests here.


class ContentModelTests(TestCase):

    def test_name_unique(self):
        factory.ContentFactory(name='movie A')
        with self.assertRaises(IntegrityError):
            factory.ContentFactory(name='movie A')

    def test_screen_name_unique(self):
        factory.ContentFactory(screen_name='sample')
        with self.assertRaises(IntegrityError):
            factory.ContentFactory(screen_name='sample')

    def test_name_max_length(self):
        name = 'a' * 51
        with self.assertRaises(DataError):
            factory.ContentFactory(name=name)

    def test_screen_name_max_length(self):
        name = 'a' * 51
        with self.assertRaises(DataError):
            factory.ContentFactory(screen_name=name)

    def test_maker_max_length(self):
        maker = 'a' * 51
        with self.assertRaises(DataError):
            factory.ContentFactory(maker=maker)

    def test_has_tweets(self):
        content = factory.ContentFactory()
        twitter_user = factory.TwitterUserFactory(content=content)
        factory.TweetFactory(twitter_user=twitter_user, tweet_id='1')

        self.assertTrue(content.has_tweets())


class CategoryModelTests(TestCase):

    def test_name_unique(self):
        factory.CategoryFactory(name='Movie')
        with self.assertRaises(IntegrityError):
            factory.CategoryFactory(name='Movie')

    def test_name_max_length(self):
        name = 'a' * 51
        with self.assertRaises(DataError):
            factory.CategoryFactory(name=name)


class StaffModelTests(TestCase):

    def test_unique_fields(self):
        staff = factory.StaffFactory(name='tanaka', role='主人公', is_cast=True)
        with self.assertRaises(IntegrityError):
            factory.StaffFactory(name='tanaka', role='主人公', is_cast=True,
                                 content=staff.content)


class TwitterUserModelTests(TestCase):

    def setUp(self):
        self.twitter_user = factory.TwitterUserFactory()

    def test_retweets_avg(self):
        for num in range(10):
            factory.TweetFactory(tweet_id=str(num), retweet_count=10,
                                 favorite_count=5,
                                 twitter_user=self.twitter_user)
        self.assertEqual(self.twitter_user.retweets_avg(), 10)

    def test_favorite_avg(self):
        for num in range(10):
            factory.TweetFactory(tweet_id=str(num), retweet_count=10,
                                 favorite_count=5,
                                 twitter_user=self.twitter_user)
        self.assertEqual(self.twitter_user.favorite_avg(), 5)

    def test_favorite_avg_with_0(self):
        self.assertEqual(self.twitter_user.favorite_avg(), 0)

    def test_retweets_avg_with_0(self):
        self.assertEqual(self.twitter_user.retweets_avg(), 0)


class TwitterApiModelTests(TestCase):

    def setUp(self):
        self.timeline_patcher = mock.patch('ranking.models.TwitterApi.get_base')
        self.mock_get_base = self.timeline_patcher.start()
        self.screen_name = 'sample_screen_name'
        self.content = factory.ContentFactory(screen_name=self.screen_name)
        self.mock_get_base.side_effect = response_data_mock

    def tearDown(self):
        self.timeline_patcher.stop()

    def test_get_user(self):
        TwitterApi().get_user('test_screen_name')

        self.mock_get_base.assert_called_once()

    def test_get_most_timeline_call_three_times(self):
        TwitterApi().get_most_timeline('test name')

        self.assertEqual(self.mock_get_base.call_count, 3)

    def test_get_and_store_twitter_data(self):
        TwitterApi().get_and_store_twitter_data(self.content)

        twitter_user = Content.objects.get(
            screen_name=self.screen_name).twitteruser
        tweet_count = twitter_user.tweet_set.all().count()
        self.assertEqual(tweet_count, 100)
        self.assertEqual(self.mock_get_base.call_count, 4)

    def test_get_and_store_twitter_data_without_image_url(self):
        TwitterApi().get_and_store_twitter_data(self.content)

        twitter_user = Content.objects.get(
            screen_name=self.screen_name).twitteruser
        self.assertIsNone(twitter_user.icon_url, None)
        self.assertIsNone(twitter_user.banner_url, None)

    def test_update_twitter_data(self):
        twitter_user = factory.TwitterUserFactory(content=self.content)
        factory.TweetFactory(twitter_user=twitter_user, tweet_id='1')

        TwitterApi().update_data(self.content)

        updated_twitter_user = TwitterUser.objects.get(pk=twitter_user.pk)
        updated_tweet_count = updated_twitter_user.tweet_set.all().count()
        self.assertNotEqual(twitter_user.name, updated_twitter_user.name)
        self.assertGreater(updated_tweet_count, 1)


class WebScrapingModelTests(TestCase):

    @mock.patch('ranking.models.ScrapingContent.extra_data_from')
    def test_store_contents_data(self, mock_contents_data):
        test_data = [
            {'name': 'サンプルドラマ',
             'description': '詳細について',
             'cast': ['主人公：田中太郎', 'ヒロイン：はげ'],
             'official_url': 'http://sample.com/aniani/',
             'maker': 'A制作会社',
             'staff': ['【原作】ランキングコミック、鈴木次郎', '【監督】別所誠人'],
             'img_url': 'https://sample.com/image/2222',
             'screen_name': 'test_name'}]
        mock_contents_data.return_value = test_data

        scraping = ScrapingContent()
        scraping.contents_data = scraping.extra_data_from('test')
        category = factory.CategoryFactory(name='Movie')
        scraping.store_contents_data(category)

        content = Content.objects.get(name=test_data[0]['name'])
        self.assertEqual(content.description, test_data[0]['description'])
        self.assertEqual(content.maker, test_data[0]['maker'])
        self.assertEqual(content.screen_name, test_data[0]['screen_name'])
        self.assertEqual(content.category, category)
        self.assertEqual(content.staff_set.all().count(), 5)

    @mock.patch('ranking.models.ScrapingContent.extra_data_from')
    def test_store_contents_data_with_little_data(self, mock_contents_data):
        little_data = [
            {'name': 'サンプルドラマ'}]
        mock_contents_data.return_value = little_data

        scraping = ScrapingContent()
        scraping.contents_data = scraping.extra_data_from('test')
        category = factory.CategoryFactory(name='Movie')
        scraping.store_contents_data(category)

        content = Content.objects.get(name=little_data[0]['name'])
        self.assertEqual(content.description, None)
        self.assertEqual(content.maker, None)
        self.assertEqual(content.screen_name, None)
        self.assertEqual(content.category, category)
        self.assertEqual(content.staff_set.all().count(), 0)
