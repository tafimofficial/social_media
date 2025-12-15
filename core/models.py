from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from django.templatetags.static import static

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, max_length=500)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='default_profile.png', blank=True)
    cover_photo = models.ImageField(upload_to='cover_photos/', default='default_cover.png', blank=True)
    location = models.CharField(max_length=100, blank=True)
    friends = models.ManyToManyField(User, blank=True, related_name='friends')
    last_activity = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    @property
    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            if 'default_profile.png' in self.profile_picture.name:
                return static('img/default_profile.png')
            return self.profile_picture.url
        return static('img/default_profile.png')

    @property
    def get_cover_photo_url(self):
        if self.cover_photo and hasattr(self.cover_photo, 'url'):
            if 'default_cover.png' in self.cover_photo.name:
                return static('img/default_cover.png')
            return self.cover_photo.url
        return static('img/default_cover.png')

    @property
    def is_online(self):
        if self.last_activity:
            return timezone.now() < self.last_activity + timedelta(minutes=5)
        return False

class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.from_user.username} -> {self.to_user.username}'

class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.sender.username} -> {self.receiver.username}: {self.content[:20]}'

    class Meta:
        ordering = ['timestamp']

class Post(models.Model):
    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    video = models.FileField(upload_to='post_videos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    shared_post = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='shares')

    def __str__(self):
        return f'{self.user.username} - {self.created_at}'
    
    def total_likes(self):
        return self.likes.count()

    class Meta:
        ordering = ['-created_at']

class Comment(models.Model):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.content[:20]}'

# Signals moved to signals.py

# Trigger a reload to be safe
