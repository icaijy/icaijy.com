from django.shortcuts import render,get_object_or_404
from .models import Post
import markdown
from django.utils.safestring import mark_safe



def post_list(request):
    posts = Post.objects.all()
    return render(request, 'blog/post_list.html', {'posts': posts})

def post_detail(request, pk):

    post = get_object_or_404(Post, pk=pk)
    post.views+=1;
    post.save()
    post_content = markdown.markdown(post.content,extensions=['pymdownx.highlight','pymdownx.tilde','pymdownx.arithmatex','pymdownx.extra','pymdownx.emoji','codehilite'])
    # https://facelessuser.github.io/pymdown-extensions/extensions/arithmatex/
    return render(request, 'blog/post_detail.html', {'post': post, 'post_content': post_content})