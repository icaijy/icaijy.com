from django.db import models
from django.utils import timezone

class Post(models.Model):
    title = models.CharField(max_length=20)  # 标题
    content = models.TextField()  # 正文
    summary = models.CharField(max_length=20,default="No Summary")
    created = models.DateTimeField(auto_now_add=True,editable=False)  # 创建时间
    modified = models.DateTimeField(auto_now=True,editable=False)
    views = models.PositiveIntegerField(default=0,editable=False)
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # 每次保存时更新 modified 字段
        self.modified = timezone.now()
        super().save(*args, **kwargs)  # 调用父类的 save 方法
