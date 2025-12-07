from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Profile, Post, Comment, FriendRequest
from .forms import UserUpdateForm, ProfileUpdateForm, PostForm
from django.contrib import messages
from .models import Message
from django.db.models import Max, Exists, OuterRef

# ... (omitted previous functions until profile_view)

@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    is_owner = request.user == profile_user
    
    # Handle Post Creation
    if is_owner and request.method == 'POST' and 'create_post' in request.POST:
        content = request.POST.get('content', '')
        visibility = request.POST.get('visibility', 'public')
        
        post = Post(user=request.user, content=content, visibility=visibility)
        
        if 'image' in request.FILES:
            post.image = request.FILES['image']
        if 'video' in request.FILES:
            post.video = request.FILES['video']
                
        post.save()
        messages.success(request, 'Post created on your profile!')
        return redirect('profile', username=username)
    
    # Friendship Logic
    is_friend = False
    request_sent = False
    request_received = False
    request_received_id = None
    
    if not is_owner:
        print(f"Checking friendship between {request.user.username} (ID: {request.user.id}) and {profile_user.username} (ID: {profile_user.id})")
        # Explicit refresh of friends list to be sure
        my_friends = request.user.profile.friends.all()
        print(f"My friends: {[f.username for f in my_friends]}")
        
        if profile_user in my_friends:
            print("is_friend is TRUE (found in list)")
            is_friend = True
        else:
            print("is_friend is FALSE (not in list)")
            
        if FriendRequest.objects.filter(from_user=request.user, to_user=profile_user).exists():
            request_sent = True
        else:
            incoming_req = FriendRequest.objects.filter(from_user=profile_user, to_user=request.user).first()
            if incoming_req:
                request_received = True
                request_received_id = incoming_req.id

    posts = profile_user.posts.select_related('user', 'user__profile').prefetch_related('likes', 'comments').all().order_by('-created_at')
    if not is_owner and not is_friend:
        # Only show public posts if not owner and not friend?
        # Requirement: "other user can ... also implement this feature in other user profile"
        # Assuming typical logic: Friends might see friends-only posts if we implemented that visibility.
        # But for now, we only have 'public' and 'private'. 'private' usually means ONLY ME.
        # Let's keep logic: if not owner, only public.
        posts = posts.filter(visibility='public')
    elif is_friend:
        # If friend, maybe see more? For now, let's show public only unless visibility 'friends' exists (it doesn't yet).
        # Actually in models.py: ('public', 'Public'), ('private', 'Private').
        # So 'private' is strictly private. Friends see public.
        posts = posts.filter(visibility='public')
        
    photos = posts.exclude(image='')
    videos = posts.exclude(video='')
    
    context = {
        'profile_user': profile_user,
        'posts': posts,
        'photos': photos,
        'videos': videos,
        'is_owner': is_owner,
        'is_friend': is_friend,
        'request_sent': request_sent,
        'request_received': request_received,
        'request_received_id': request_received_id,
        'debug_info': f"Me:{request.user.username}({request.user.id}) Viewing:{profile_user.username}({profile_user.id}) IsFriend:{is_friend}"
    }
    return render(request, 'core/profile.html', context)

@login_required
def search_view(request):
    query = request.GET.get('q', '')
    filter_type = request.GET.get('type', 'all') # Default to all
    
    users = []
    posts = []
    
    if query:
        # Base Queries
        user_query = Q(username__icontains=query) | Q(profile__bio__icontains=query)
        post_query = Q(content__icontains=query, visibility='public')
        
        if filter_type == 'all':
            users = User.objects.filter(user_query).exclude(id=request.user.id)[:5] # Limit for overview
            posts = Post.objects.filter(post_query)[:10]
            
        elif filter_type == 'people':
            users = User.objects.filter(user_query).exclude(id=request.user.id)
        
        elif filter_type == 'posts':
            posts = Post.objects.filter(post_query)
            
        elif filter_type == 'photos':
            posts = Post.objects.filter(post_query).exclude(image='')
            
        elif filter_type == 'videos':
            posts = Post.objects.filter(post_query).exclude(video='')
            
    context = {
        'query': query,
        'filter_type': filter_type,
        'users': users,
        'posts': posts,
    }
    return render(request, 'core/search.html', context)

@login_required
def chat_view(request, username=None):
    # Get all users who have exchanged messages with current user, ordered by latest message
    # This involves a bit of complex query logic, so we'll simplify for MVP:
    # Get all friends + anyone we have messages with
    
    # 1. Get querysets of people I sent to or received from
    sent_to = Message.objects.filter(sender=request.user).values_list('receiver', flat=True)
    received_from = Message.objects.filter(receiver=request.user).values_list('sender', flat=True)
    
    # Combined set of user IDs
    chat_user_ids = set(list(sent_to) + list(received_from))
    
    chat_users = User.objects.filter(id__in=chat_user_ids).exclude(id=request.user.id)
    
    # Annotate with unread status
    unread_subquery = Message.objects.filter(
        sender=OuterRef('pk'),
        receiver=request.user,
        is_read=False
    )
    chat_users = chat_users.annotate(has_unread=Exists(unread_subquery))
    
    # If a specific user is selected (e.g. clicked 'Message' on profile)
    active_user = None
    chat_messages = []
    
    if username:
        active_user = get_object_or_404(User, username=username)
        # Mark as read
        Message.objects.filter(sender=active_user, receiver=request.user, is_read=False).update(is_read=True)
        # Get history
        chat_messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=active_user)) | 
        (Q(sender=active_user) & Q(receiver=request.user))
    ).select_related('sender', 'sender__profile', 'receiver', 'receiver__profile').order_by('timestamp')
        
        # If this implies a new chat with someone not in list, add them temporarily for UI
        if active_user not in chat_users:
            pass 

    context = {
        'chat_users': chat_users,
        'active_user': active_user,
        'chat_messages': chat_messages,
        'is_active_user_online': active_user.profile.is_online if active_user else False
    }
    return render(request, 'core/chat.html', context)

@login_required
def send_message_ajax(request):
    if request.method == 'POST':
        to_username = request.POST.get('to_user')
        content = request.POST.get('content', '')
        
        # Check files in request.FILES
        file = request.FILES.get('file')
        
        if not to_username or (not content and not file):
            return JsonResponse({'status': 'error', 'message': 'Missing data'})
            
        try:
            to_user = User.objects.get(username=to_username)
            msg = Message.objects.create(sender=request.user, receiver=to_user, content=content, file=file)
            
            response_data = {
                'status': 'success',
                'timestamp': msg.timestamp.strftime('%H:%M'),
                'content': msg.content
            }
            if msg.file:
                response_data['file_url'] = msg.file.url
                response_data['is_image'] = msg.file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
                response_data['file_name'] = msg.file.name.split('/')[-1]

            return JsonResponse(response_data)
        except User.DoesNotExist:
             return JsonResponse({'status': 'error', 'message': 'User not found'})
             
    return JsonResponse({'status': 'error'})

@login_required
def get_messages_ajax(request, username):
    other_user = get_object_or_404(User, username=username)
    
    # Get unread messages
    new_msgs = Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).order_by('timestamp')
    
    data = []
    for m in new_msgs:
        item = {
            'sender': m.sender.username,
            'content': m.content,
            'timestamp': m.timestamp.strftime('%H:%M'),
            'type': 'received'
        }
        if m.file:
            item['file_url'] = m.file.url
            item['is_image'] = m.file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
            item['file_name'] = m.file.name.split('/')[-1]
            
        data.append(item)
        m.is_read = True
        m.save()
        
    return JsonResponse({'status': 'success', 'messages': data})

# ... (Previous Auth Views: signup, login_view, logout_view stay same) ...

def dashboard_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'core/dashboard.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f'Welcome back, {username}!')
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

@login_required
def create_post_view(request):
    # For now, redirect to home where the post form exists.
    return redirect('home')

@login_required
def home(request):
    if request.method == 'POST' and 'create_post' in request.POST:
        content = request.POST.get('content', '')
        visibility = request.POST.get('visibility', 'public')
        
        post = Post(user=request.user, content=content, visibility=visibility)
        
        if 'image' in request.FILES:
            print(f"DEBUG: Image found in request.FILES: {request.FILES['image']}")
            post.image = request.FILES['image']
        else:
            print("DEBUG: No image in request.FILES")

        if 'video' in request.FILES:
            post.video = request.FILES['video']
                
        post.save()
        if post.image:
             print(f"DEBUG: Post saved with image URL: {post.image.url}")
        else:
             print("DEBUG: Post saved WITHOUT image")

        messages.success(request, 'Post created!')
        return redirect('home')


    # Handle Comment
    if request.method == 'POST' and 'create_comment' in request.POST:

        content = request.POST.get('content')
        post_id = request.POST.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        if content:
            Comment.objects.create(user=request.user, post=post, content=content)
        return redirect('home')

    posts = Post.objects.filter(visibility='public') 
    own_posts = Post.objects.filter(user=request.user, visibility='private')
    all_posts = (posts | own_posts).distinct().order_by('-created_at')
    
    return render(request, 'core/feed.html', {'posts': all_posts})

@login_required
def like_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'liked': liked, 'count': post.likes.count()})
        
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def add_comment_ajax(request):
    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        content = request.POST.get('content')
        post = get_object_or_404(Post, id=post_id)
        if content:
            comment = Comment.objects.create(user=request.user, post=post, content=content)
            return JsonResponse({
                'status': 'success',
                'username': request.user.username,
                'profile_url': request.user.profile.profile_picture.url,
                'content': comment.content,
                'count': post.comments.count()
            })
    return JsonResponse({'status': 'error'})

@login_required
def edit_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.user:
        return redirect('home')
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated!')
            return redirect('home')
    else:
        form = PostForm(instance=post)
    
    return render(request, 'core/edit_post.html', {'form': form})

@login_required
def delete_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.user:
        return redirect('home')
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully.')
        return redirect('home')
        
    return render(request, 'core/delete_post_confirm.html', {'post': post})

@login_required
def share_post_view(request, post_id):
    original_post = get_object_or_404(Post, id=post_id)
    
    # If the post being shared is itself a share, share the original source content instead
    target_post = original_post.shared_post if original_post.shared_post else original_post
    
    # Prevent sharing own post (either direct or indirect)
    if target_post.user == request.user:
         return JsonResponse({'status': 'error', 'message': 'You cannot share your own post.'}, status=403)
        
    if request.method == 'POST':
        # Create a new post that references the target one
        Post.objects.create(
            user=request.user,
            shared_post=target_post,
            visibility='public' 
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def friends_view(request):
    # Incoming Requests
    friend_requests = FriendRequest.objects.filter(to_user=request.user)
    
    # Current Friends
    friends = request.user.profile.friends.all()
    
    # Simple Suggestion Logic: Users who are NOT me, NOT my friends, and NOT in pending requests
    # 1. Get all users excluding self
    all_users = User.objects.exclude(id=request.user.id)
    
    # 2. Exclude current friends
    # Note: friends is a queryset of Users
    all_users = all_users.exclude(id__in=friends.values_list('id', flat=True))
    
    # 3. Exclude users I've sent requests to OR received from
    sent_to_ids = FriendRequest.objects.filter(from_user=request.user).values_list('to_user_id', flat=True)
    received_from_ids = FriendRequest.objects.filter(to_user=request.user).values_list('from_user_id', flat=True)
    
    suggestions = all_users.exclude(id__in=sent_to_ids).exclude(id__in=received_from_ids)
    
    return render(request, 'core/friends.html', {
        'friend_requests': friend_requests,
        'friends': friends,
        'suggestions': suggestions
    })

@login_required
def send_friend_request(request, username):
    to_user = get_object_or_404(User, username=username)
    if request.user == to_user:
        return JsonResponse({'status': 'error', 'message': 'Cannot add yourself'})
        
    # Check if already friends
    if to_user in request.user.profile.friends.all():
        return JsonResponse({'status': 'error', 'message': 'Already friends'})
        
    # Check if request already sent
    if FriendRequest.objects.filter(from_user=request.user, to_user=to_user).exists():
        return JsonResponse({'status': 'error', 'message': 'Request already sent'})
    
    # Create request
    FriendRequest.objects.create(from_user=request.user, to_user=to_user)
    return JsonResponse({'status': 'success', 'message': 'Friend request sent'})

@login_required
def accept_friend_request(request, request_id):
    freq = get_object_or_404(FriendRequest, id=request_id)
    if freq.to_user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    # Add to friends (Both ways)
    request.user.profile.friends.add(freq.from_user)
    freq.from_user.profile.friends.add(request.user)
    
    freq.delete()
    return JsonResponse({'status': 'success', 'message': 'Friend request accepted'})

@login_required
def reject_friend_request(request, request_id):
    freq = get_object_or_404(FriendRequest, id=request_id)
    if freq.to_user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    freq.delete()
    return JsonResponse({'status': 'success', 'message': 'Friend request rejected'})

@login_required
def remove_friend(request, username):
    other_user = get_object_or_404(User, username=username)
    
    if other_user in request.user.profile.friends.all():
        request.user.profile.friends.remove(other_user)
        other_user.profile.friends.remove(request.user)
        return JsonResponse({'status': 'success', 'message': 'Friend removed'})
        
    return JsonResponse({'status': 'error', 'message': 'Not friends'})




# ... (Previous Edit Profile and granular update views stay same) ...

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile', username=request.user.username)
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'core/edit_profile.html', context)

@login_required
def update_cover_view(request):
    if request.method == 'POST' and request.FILES.get('cover_photo'):
        profile = request.user.profile
        profile.cover_photo = request.FILES['cover_photo']
        profile.save()
        messages.success(request, 'Cover photo updated!')
    return redirect('profile', username=request.user.username)

@login_required
def update_avatar_view(request):
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        profile = request.user.profile
        profile.profile_picture = request.FILES['profile_picture']
        profile.save()
        messages.success(request, 'Profile picture updated!')
    return redirect('profile', username=request.user.username)

@login_required
def update_bio_view(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.bio = request.POST.get('bio', '')
        profile.location = request.POST.get('location', '')
        profile.save()
        messages.success(request, 'Profile info updated!')
    return redirect('profile', username=request.user.username)
@login_required
def get_unread_count(request):
    # Count unique users who sent unread messages
    count = Message.objects.filter(receiver=request.user, is_read=False).values('sender').distinct().count()
    return JsonResponse({'count': count})

@login_required
def get_friend_request_count(request):
    count = FriendRequest.objects.filter(to_user=request.user).count()
    return JsonResponse({'count': count})

import os
import re
import mimetypes
from django.http import StreamingHttpResponse, Http404, HttpResponse
from django.conf import settings

def stream_video(request, path):
    """
    Stream video file supporting Range header for partial content (206).
    """
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    if not os.path.exists(file_path):
        raise Http404("Video not found")

    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'

    range_header = request.headers.get('Range', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)

    if range_match:
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte) if last_byte else file_size - 1
        
        if last_byte >= file_size:
            last_byte = file_size - 1
        
        length = last_byte - first_byte + 1
        
        def file_iterator(file_path, offset=0, length=None, chunk_size=8192):
            with open(file_path, 'rb') as f:
                f.seek(offset, os.SEEK_SET)
                remaining = length
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        response = StreamingHttpResponse(
            file_iterator(file_path, offset=first_byte, length=length),
            status=206,
            content_type=content_type
        )
        response['Content-Range'] = f'bytes {first_byte}-{last_byte}/{file_size}'
        response['Content-Length'] = str(length)
        response['Accept-Ranges'] = 'bytes'
    else:
        # If no range header, return the full file (or maybe just a standard serve?)
        # For simplicity in this 'stream' view, we return full content but setup accept-ranges
        response = HttpResponse(open(file_path, 'rb'), content_type=content_type)
        response['Content-Length'] = str(file_size)
        response['Accept-Ranges'] = 'bytes'
        
    return response
