from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import User
from django.utils.html import strip_tags
import markdown


STATUS_CHOICES = (
    ('d', 'Черновик'),
    ('p', 'Опубликовано'),
    ('w', 'Скрыто'),
)


class Post(models.Model):
    """
    Модель Поста
    """
    title = models.CharField(max_length=300)
    content = models.TextField()
    meta_data = JSONField()
    is_active = models.BooleanField(default=False)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, null=True)
    tags = models.ManyToManyField('Tag')
    ribbon = models.ForeignKey('Ribbon', null=True, blank=True)

    def __str__(self):
        return str(self.id) + '. ' + str(self.title)

    def source_base_url(self):
        from urllib.parse import urlparse
        parts = urlparse(self.meta_data['source_url'])
        return parts.netloc

    def content2(self):
        return self.content\
            .replace("\n", '<br><br>')\
            .replace('<br><br> <br><br>', '<br><br>')\
            .replace('<br><br><br><br>', '<br><br>')

    def series(self):
        series_arr = []
        for rel in SeriesPost.objects.filter(post__exact=self).all():
            series = Series.objects.get(pk=rel.series_id)
            series.post_number = rel.number
            series_arr.append(series)
        return series_arr

    def previous_posts(self):
        return PostGroup.objects.get(pk=2).posts.filter(is_active__exact=True).all()

    def following_posts(self):
        return PostGroup.objects.get(pk=2).posts.filter(is_active__exact=True).all()

    def source_url(self):
        source_url = ''
        if 'source_url' in self.meta_data:
            source_url = self.meta_data['source_url']
        return source_url

    def image(self):
        if 'image_url' not in self.meta_data:
            return False
        return self.meta_data['image_url']

    def url(self):
        return '/post/' + str(self.id)

    def annotation(self):
        content_sections = self.content.split('<!--ANNOTATION_SPLITTER-->')
        if len(content_sections) == 1:
            return ''
        annotation = content_sections[0]
        #annotation = markdown.markdown(annotation)
        return annotation.strip()

    def len_without_sp(self):
        return len(self.content.replace(' ', ''))

    def len_with_sp(self):
        return len(str(self.content))

    def translation_to_posts(self):
        return self.posts_to

    def translations_posts(self):
        return self.posts_from


class PostRelation(models.Model):
    post_from = models.ForeignKey('Post', related_name='posts_from')
    post_to = models.ForeignKey('Post', related_name='posts_to')
    type = models.ForeignKey('PostRelationType')
    index_together = [
        ['post_from', 'type', 'post_to'],
    ]


class PostRelationType(models.Model):
    title = models.CharField(max_length=50)

    def __str__(self):
        return self.title


class PostLog(models.Model):
    post = models.ForeignKey('Post')
    created_at = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    """
    Модель комментария к Посту
    """
    post = models.ForeignKey('Post')
    user = models.ForeignKey(User)
    content = models.CharField(max_length=1200)
    created_at = models.DateTimeField(auto_now_add=True)


class PostGroup(models.Model):
    title = models.CharField(max_length=300)
    posts = models.ManyToManyField(Post)
    meta_data = JSONField()


class Tag(models.Model):
    title = models.CharField(max_length=50)
    color_class = models.CharField(max_length=16, null=True)

    def __str__(self):
        return self.title


class Series(models.Model):
    """
    Модель серии постов
    """
    title = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def posts(self, only_is_active=True):
        posts_arr = []
        for rel in SeriesPost.objects.filter(series__exact=self).order_by('number').all():
            post = Post.objects.get(pk=rel.post_id)
            if only_is_active is True and post.is_active is False:
                continue
            post.post_number = rel.number
            posts_arr.append(post)
        return posts_arr


class SeriesPost(models.Model):
    series = models.ForeignKey(Series)
    post = models.ForeignKey(Post)
    number = models.IntegerField()


class Ribbon(models.Model):
    """
    Лента
    """
    title = models.CharField(max_length=300)
    #logo_url = models.CharField(max_length=300)
    meta_data = JSONField(blank=True, null=True)

    def logo_url(self):
        try:
            return self.meta_data['logo_url']
        except:
            pass

    def __str__(self):
        return self.title
