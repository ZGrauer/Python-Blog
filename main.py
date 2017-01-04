import os
import jinja2
import webapp2
import random
import string
import hashlib
import hmac

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

SECRET = "LVFuBg9EM8Bq3cd992Tb5g01Uh30GCV2"

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def blog_key(name = 'default'):
    '''
    Sets parent for items in datastore. Set name param for multiple blogs.
    '''
    return db.Key.from_path('blogs', name)

class BlogHandler(webapp2.RequestHandler):
    def initialize(self, *a, **kw):
        '''
        Called before every request in appengine
        Checks for user cookie, if pressent set User object
        '''
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('username')
        self.user = uid and User.by_id(int(uid))

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **params):
        self.write(self.render_str(template, **params))

    def set_secure_cookie(self, name, val):
        '''
        params: name (str) - cookie name
                val (str) - cookie value

        Sets secured cookie with name=val.  Secured with HMAC
        '''
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        '''
        params: name (str) - cookie name

        return: cookie value, if valid
        '''
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('username', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'username=; Path=/')

class BlogFront(BlogHandler):
    def get(self):
        posts = greetings = Post.all().order('-created')
        if self.user:
            self.render('blog.html', posts = posts, username = self.user.username)
        else:
            self.render('blog.html', posts = posts, username = "Login")
        

class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        post._render_text = post.content.replace('\n', '<br>')
                   
        if not post:
            self.error(404)
            return

        self.render_post(post)

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        post._render_text = post.content.replace('\n', '<br>')
        post_action = self.request.get("action")
        if post_action=="like":
            post.likes += 1
            post.put()
            self.render_post(post)
        elif post_action=="dislike":
            post.likes -= 1
            post.put()
            self.render_post(post)
        elif post_action=="delete":
            if User.by_id(post.user_id).username == self.user.username:
                post.delete()
                self.redirect('/blog')
        elif post_action=="edit":
            if User.by_id(post.user_id).username == self.user.username:
                post.title = self.request.get('title')
                post.content = self.request.get('content')
                post.put()
                self.redirect('/blog')

    def render_post(self, post):
        if self.user:
            self.render("permalink.html", post = post,
                        username = self.user.username,
                        post_username=User.by_id(post.user_id).username)
        else:
            self.render("permalink.html", post = post, username = "Login",
                        post_username=User.by_id(post.user_id).username)
        
class NewPost(BlogHandler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/blog/login")

    def post(self):
        if not self.user:
            self.redirect('/blog')
            
        title = self.request.get('title')
        content = self.request.get('content')

        if title and content:
            p = Post(parent = blog_key(), title = title, content = content,
                     user_id=self.user.key().id())
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))
        else:
            error = "Enter a title and content, please!"
            self.render("newpost.html", title=title, content=content, error=error)

class Signup(BlogHandler):
    def get(self):
        if self.user:
            self.redirect("/blog")
        else:
            self.render("signup.html")

    def post(self):
        self.username = self.request.get("username")
        self.pwd1 = self.request.get("pwd1")
        self.pwd2 = self.request.get("pwd2")
        self.email = self.request.get("email")
        
        params = dict(username = self.username,
                      email = self.email,
                      pwd1 = self.pwd1,
                      pwd2 = self.pwd2)

        u = User.by_name(self.username)
        
        if u:
            params['error'] = "Username already exists!"
            self.render("signup.html", **params)
        elif self.username and self.pwd1 and self.pwd2 and (self.pwd1 == self.pwd2):           
            u = User.register(self.username, self.pwd1, self.email)
            u.put()
            self.login(u)
            self.redirect("/blog")
        elif self.pwd1 != self.pwd2:
            params['error'] = "Passwords must match exactly!"
            self.render("signup.html", **params)
        else:
            params['error'] = "Enter a username & password, please!"
            self.render("signup.html", **params)

class Login(BlogHandler):
    def get(self):
        self.render("login.html")

    def post(self):
        username = self.request.get('username')
        pwd = self.request.get('pwd')

        u = User.login(username, pwd)
        if u:
            self.login(u)
            self.redirect('/blog')
        else:
            msg = 'Invalid login'
            self.render('login.html', error = msg)

class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/blog')

class Post(db.Model):
    '''
    Defines post for datastore.
    render method creates HTML to display post data
    '''
    title = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    user_id = db.IntegerProperty(required = True)
    likes = db.IntegerProperty(default=1)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)
    
    def render_overview(self):
        '''
        Replace user new lines with HTML breaks.
        Generate HTML for post data. HTML in data not escaped
        '''
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("postoverview.html", p = self,
                          post_username=User.by_id(self.user_id).username)

class User(db.Model):
    '''
    Defines a user for datastore.

    Includes 4 static methods
    '''
    username = db.StringProperty(required = True)
    password = db.TextProperty(required = True)
    email = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    @classmethod
    def by_id(cls, uid):
        '''
        Static method

        param: user ID
        returns: user for ID
        '''
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        '''
        Static method

        param: username
        returns: user for name
        '''
        u = User.all().filter("username =", name).get()
        return u

    @classmethod
    def register(cls, name, pw, email = None):
        '''
        Static method

        param: username (str)
                password (str)
                email (str) - default is None
        returns: new user object
        '''
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    username = name,
                    password = pw_hash,
                    email = email)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.password):
            return u

def users_key(group = 'default'):
    '''
    Sets parent in DB for all users
    '''
    return db.Key.from_path('users', group)

def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (h, salt)

def valid_pw(name, pw, h):
    salt = h.split(",")[1]
    if h==make_pw_hash(name, pw, salt):
        return True

def hash_str(s):
    return hmac.new(SECRET,s).hexdigest()

def make_secure_val(s):
    return "%s|%s" % (s, hash_str(s))

def check_secure_val(h):
    val = h.split("|")[0]
    if h == make_secure_val(val):
        return val


app = webapp2.WSGIApplication([('/blog/?', BlogFront),
                               ('/blog/([0-9]+)', PostPage),
                               ('/blog/newpost', NewPost),
                               ('/blog/signup', Signup),
                               ('/blog/login', Login),
                               ('/blog/logout', Logout)],
                              debug=True)
