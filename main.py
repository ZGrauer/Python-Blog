import os
import re
import string
import random
import hashlib
import hmac
import jinja2
import webapp2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

SECRET = "LVFuBg9EM8Bq3cd992Tb5g01Uh30GCV2"

def render_str(template, **params):
    '''Renders a jinja2 template with params to the browser.
        
    Args:
        template: String template name within the templates folder.  HTML
        params: name=value combos to send to the template

    Returns:
        rendered page
    '''
    t = jinja_env.get_template(template)
    return t.render(params)


class BlogHandler(webapp2.RequestHandler):
    '''Helper class for rendering all pages via handlers
    
    Attributes:
        None
    
    Methods:
        initialize: reads username cookie on all requests. sets self.user
        write: write out string to browser
        render_str: Gets jinja2 template for rendering.  Adds user param
        render: Primary method to render a template with params
        set_secure_cookie: Sets a HMAC secured cookie name value combo
        read_secure_cookie: Returns cookie value for name using HMAC
        login: Sets the username cookie for the current user
        logout: Sets the existing username cookie to nothing
    '''
    
    def initialize(self, *a, **kw):
        '''Checks for user cookie, if pressent set User object

        Called before every request in appengine
        '''
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie("username")
        self.user = uid and User.by_id(int(uid))

    def write(self, *a, **kw):
        '''Write out string/HTML to browser

        If user isn't logged in, set nav to "Login" via username
        Else set nav to "logout" and display "Welcome, {{username}}"
        
        Args:
            a: String template name
            kw: name=value combos to send to the template

        Returns:
            rendered page
        '''
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        '''Set jinja2 template

        Also insert user param on all requests
        
        Args:
            template: String template name
            params: name=value combos to send to the template

        Returns:
            rendered page
        '''
        params["user"] = self.user
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **params):
        ''' Primary method to render a template with params
        
        Args:
            template: String jinja2 template name
            params: name=value combos to send to the template

        Returns:
            rendered page
        '''
        self.write(self.render_str(template, **params))

    def set_secure_cookie(self, name, val):
        ''' Sets secured cookie with name=val.  Secured with HMAC

        Secured using HMAC and SECRET variable at top of file.
        Session cookie.  No expiration
        
        Args:
            name: String cookie name
            val: String value for name

        Returns:
            rendered page
        '''
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            "Set-Cookie",
            "%s=%s; Path=/" % (name, cookie_val))

    def read_secure_cookie(self, name):
        ''' Verifies cookie is valid and returns value by name 

        Secured using HMAC and SECRET variable at top of file.
        
        Args:
            name: String cookie name

        Returns:
            String cookie value, undoing HMAC
        '''
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        ''' Sets the username cookie for the current user

        Uses set_secure_cookie for HMAC
        
        Args:
            user: User instance from DB

        Returns:
            None
        '''
        self.set_secure_cookie("username", str(user.key().id()))

    def logout(self):
        ''' Sets the existing username cookie to nothing

        Logs the user out of site
        
        Args:
            None

        Returns:
            None
        '''
        self.response.headers.add_header("Set-Cookie", "username=; Path=/")


class BlogFront(BlogHandler):
    '''Handles the rendering of the main blog page

    inherits from BlogHandler
    
    Attributes:
        None
    
    Methods:
        get: GET request to render main blog page/template
    '''
    
    def get(self):
        '''Handles GET requests, render blog

        If user isn't logged in, set nav to "Login" via username
        Else set nav to "logout" and display "Welcome, {{username}}"
        
        Args:
            None

        Returns:
            rendered page
        '''
        posts = greetings = Post.all().order("-created")
        if self.user:
            self.render("blog.html", posts = posts,
                        username = self.user.username)
        else:
            self.render("blog.html", posts = posts, username = "Login")
        

class PostPage(BlogHandler):
    '''Handles the rendering of the full post via permalinks

    inherits from BlogHandler
    Allows users to like/dislike and comment on posts
    
    Attributes:
        None
    
    Methods:
        get: GET request to render full post page
        post: POST response from post. Perform actions from user, like
            edit post, delet post, add comment, like, dislike
    '''
    
    def get(self, post_id):
        '''Handles GET requests

        Render full post page.
        Replaces newline characters in post content with HTML breaks.
        Pulls all comments that have the post as an ancestor to display
        
        Args:
            None

        Returns:
            rendered full post page with all comments
        '''
        key = db.Key.from_path("Post", int(post_id), parent=blog_key())
        post = db.get(key)        
        if not post:
            self.error(404)
            return

        comments = Comment.all().ancestor(post)
        post._render_text = post.content.replace("\n", "<br>")  
        self.render_post(post, comments)

    def post(self, post_id):
        '''Handles POST requests for full post page

        Handles the "action" from the valid user.
            like: add 1 to the post like count in DB. Not user's post
            dislike: subtract 1 from the post like count in DB. Not user's post
            delete: deletes Post entity from DB, only for your own posts.
            edit: edits Post entity in DB, only for your own posts.
            add_comment: adds a Comment to DB for Post.  Any valid user

        If not a user, cannot add comment or like post
        
        Args:
            None

        Returns:
            rendered page
        '''
        
        key = db.Key.from_path("Post", int(post_id), parent=blog_key())
        post = db.get(key)
        if not post:
            self.error(404)
            return
        
        post._render_text = post.content.replace("\n", "<br>")
        comments = Comment.all().ancestor(post)
        
        post_action = self.request.get("action")
        if post_action=="like":
            post.add_like(self.user.key().id())
            post.put()
            self.render_post(post, comments)
        elif post_action=="delete":
            if User.by_id(post.user_id).username == self.user.username:
                post.delete()
                self.redirect("/blog")
        elif post_action=="edit":
            if User.by_id(post.user_id).username == self.user.username:
                post.title = self.request.get("title")
                post.content = self.request.get("content")
                post.put()
                self.redirect("/blog")
        elif post_action=="add_comment":
            c = Comment(parent = post.key(), user_id=self.user.key().id(),
                        content = self.request.get("comment_content"))
            c.put()
            self.render_post(post, comments)

    def render_post(self, post, comments):
        if self.user:
            self.render("permalink.html", post = post, comments = comments,
                        username = self.user.username,
                        post_username=User.by_id(post.user_id).username)
        else:
            self.render("permalink.html", post = post, comments = comments,
                        username = "Login", 
                        post_username=User.by_id(post.user_id).username)

        
class NewPost(BlogHandler):
    '''Handles the new post page of the blog

    inherits from BlogHandler
    Allows registered users to add new posst to the blog
    
    Attributes:
        None
    
    Methods:
        get: GET request to render new post page
        post: POST response from new post form. Create Post entity, then 
            redirect to permalink for new post on blog
    '''
    
    def get(self):
        '''Handles GET requests

        Render new post page only if logged in as valid user
        If not a user, redirect to logon
        
        Args:
            None

        Returns:
            rendered page
        '''
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/blog/login")

    def post(self):
        '''Handles POST requests for new post page

        If not a user, redirect to main blog
        Get values from user, create Post entity.
        If not valid title & content, render page again with error.
        Else redirect to post's permalink
        
        Args:
            None

        Returns:
            rendered page
        '''
        
        if not self.user:
            self.redirect("/blog/login")
            return
        
        title = self.request.get("title")
        content = self.request.get("content")

        if title and content:
            p = Post(parent = blog_key(), title = title, content = content,
                     likes=[self.user.key().id()],
                     user_id=self.user.key().id())
            p.put()
            self.redirect("/blog/%s" % str(p.key().id()))
        else:
            error = "Enter a title and content, please!"
            self.render("newpost.html", title=title, content=content,
                        error=error)


class Signup(BlogHandler):
    '''Handles user registration functions

    inherits from BlogHandler
    
    Attributes:
        None
    
    Methods:
        get: GET request to render signup page
        post: POST response from signup form. Validate info & create User
    '''
    
    def get(self):
        '''Handles GET requests

        Render signup page only if not logged in
        If a user is logged in, redirect to main blog
        
        Args:
            None

        Returns:
            rendered page
        '''
        if self.user:
            self.redirect("/blog")
        else:
            self.render("signup.html")

    def post(self):
        '''Handles POST requests for registration

        Verify username & passwords match regular expressions
        Verify both passwords match (confirm)
        Verify username doesn't already exist
        If good, create User entity and cookie. redirect to blog
        
        Args:
            None

        Returns:
            rendered page
        '''
        
        pwd_pattern = re.compile(
            "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$")
        name_pattern = re.compile("[A-Za-z]{3,20}")
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
            params["error"] = "Username already exists!"
            self.render("signup.html", **params)
        elif (not pwd_pattern.match(self.pwd1) or
              not pwd_pattern.match(self.pwd2)):
            params["error"] = "Passwords must be a min 8 characters at least 1 "
            "uppercase, 1 lowercase and 1 number "
            self.render("signup.html", **params)
        elif not name_pattern.match(self.username):
            params["error"] = "Name must 3 to 20 letters, upper or lowercase"
            self.render("signup.html", **params)
        elif (self.username and self.pwd1 and self.pwd2
              and (self.pwd1 == self.pwd2)):           
            u = User.register(self.username, self.pwd1, self.email)
            u.put()
            self.login(u)
            self.redirect("/blog")
        elif self.pwd1 != self.pwd2:
            params["error"] = "Passwords must match exactly!"
            self.render("signup.html", **params)
        else:
            params["error"] = "Enter a username & password, please!"
            self.render("signup.html", **params)


class Login(BlogHandler):
    '''Handles login functions for users on blog

    inherits from BlogHandler
    
    Attributes:
        None
    
    Methods:
        get: GET request to render login page
        post: POST response from login form. Verify user, set cookie
    '''
    
    def get(self):
        '''Handles GET requests for login

        Render login page based on template
        
        Args:
            None

        Returns:
            rendered page
        '''
        self.render("login.html")

    def post(self):
        '''Handles POST requests for login form

        Validate user ID & pass then set cookie
        
        Args:
            None

        Returns:
            rendered page
        '''
        
        username = self.request.get("username")
        pwd = self.request.get("pwd")

        u = User.login(username, pwd)
        if u:
            self.login(u)
            self.redirect("/blog")
        else:
            msg = "Invalid login"
            self.render("login.html", error = msg)


class Logout(BlogHandler):
    '''Handles logout functions for users on blog

    inherits from BlogHandler
    
    Attributes:
        None
    
    Methods:
        get: clears the username in the cookie.  Logout user
    '''
    
    def get(self):
        '''Handles GET requests for logout

        Clears the username on the cookie
        redirect to blog
        
        Args:
            None

        Returns:
            None
        '''
        self.logout()
        self.redirect("/blog")


class Post(db.Model):
    '''Defines a Post object for the datastore.
    
    Attributes:
        title: String for the title of a post
        content: Text content to be displayed. Not indexed. Can be text or HTML
        likes: Int count of the score/likes of the post
        created: DateTime of when the entity was created
        last_modified: DateTime of when the post was last modified
    
    Methods:
        render_overview: renders the shortend post for the main blog page
                        returns the rendered HTML for the template
    '''
    
    title = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    user_id = db.IntegerProperty(required = True)
    likes = db.ListProperty(int,indexed=True,default=[])
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def like_count(self):
        return len(self.likes)
        
    def user_like_count(self, uid):
        '''Checks if a user_id already liked a post

        Args:
            uid: Int user_id to find

        Returns:
            True if found in liked list
        '''
        return self.likes.count(uid)

    def add_like(self, uid):
        '''Checks if a user_id already liked a post

        Args:
            uid: Int user_id to find

        Returns:
            True if found in liked list
        '''
        if self.user_like_count(uid)==0:
            self.likes.append(uid)
    
    def render_overview(self):
        '''Generate HTML for post data.

        Replace user new lines with HTML breaks.
        HTML in data not escaped in template
        
        Args:
            None

        Returns:
            String HTML for post data. HTML in data not escaped in template
        '''
        self._render_text = self.content.replace("\n", "<br>")
        return render_str("postoverview.html", p = self,
                          post_username=User.by_id(self.user_id).username)


class Comment(db.Model):
    '''Defines a Comment object for the datastore.

    Comments are the child to a Post. Post is the ancestor for Comment.
    
    Attributes:
        user_id: Int the user who wrote the comment. ID matches a User object
        content: Text content to be displayed. Not indexed.
        created: DateTime of when the comment was created
    
    Methods:
        get_username: returns the username for the comment based on user_id
    '''
    
    user_id = db.IntegerProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    def get_username(self):
        '''Returns the username for a comment

        Args:
            None

        Returns:
            String username based on the ID from the comment
        '''
        return User.by_id(self.user_id).username


class User(db.Model):
    '''Defines a User object for the datastore.

    Users are created in the "default" group using users_key() function
    
    Attributes:
        username: String name for the user. 3 to 20 alpha
        password: Text content to be displayed. Not indexed.  8 alpha numeric
        email: Text of users optional email. Not indexed
        created: DateTime of when the account was created
        last_modified: DateTime of when the user last modified
    
    Class Methods:
        by_id: returns User object by entity ID
        by_name: returns User object by username
        register: returns User object with the password hashed.  SHA256 w/ salt
        login: returns User object after verifying password against hash
    '''
    
    username = db.StringProperty(required = True)
    password = db.TextProperty(required = True)
    email = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    @classmethod
    def by_id(cls, uid):
        '''Returns an existing User object based on ID

        Args:
            uid: ID for user entity in datastore

        Returns:
            User object. No password verified
        '''
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        '''Returns an existing User object based on username

        Args:
            name: String username to find

        Returns:
            User object. No password verified
        '''
        u = User.all().filter("username =", name).get()
        return u

    @classmethod
    def register(cls, name, pw, email = None):
        '''Returns a new User object

        Args:
            name: String username
            pw: String cleartext password
            email: String.  Default is None

        Returns:
            After hashing the password using SHA256 with random salt,
            a new User object is returned.
        '''
        
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    username = name,
                    password = pw_hash,
                    email = email)

    @classmethod
    def login(cls, name, pw):
        '''Returns an existing User object by name if password is correct

        Args:
            name: String username for existing account
            pw: String cleartext password

        Returns:
            After verifying the user exists and that the password is correct,
            a User object is returned for the named user account.
        '''
        
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.password):
            return u


def users_key(group = "default"):
    '''Gets parent in DB for all users

    Args:
        group: String group name for user seperation.  Default is default

    Returns:
        Parent key for all users.
    '''
    return db.Key.from_path("users", group)

def blog_key(name = "default"):
    '''Gets parent for blog in datastore

    Set name param for multiple blogs.

    Args:
        name: String name for blog seperation.  Default is default

    Returns:
        Parent key for blog.
    '''
    return db.Key.from_path("blogs", name)

def make_salt():
    '''Makes random string of letters for password salts

    Args:
        None

    Returns:
        String of 5 random letters
    '''
    return "".join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
    '''Hash password with SHA256 using name & salt

    Args:
        name: String username
        pw: String cleartext password
        salt: String, optional. If none one is generated.

    Returns:
        String of hashed password with salt, seperated by comma
    '''
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return "%s,%s" % (h, salt)

def valid_pw(name, pw, h):
    '''Checks if a password matches a hash

    Args:
        name: String username
        pw: String cleartext password
        h: String, hash of password

    Returns:
        True if cleartext password equals the hashed password
    '''
    salt = h.split(",")[1]
    if h==make_pw_hash(name, pw, salt):
        return True

def hash_str(s):
    '''Hash a string using HMAC

    Used for cookies.  Uses SECRET value at top

    Args:
        s: String to be hashed

    Returns:
        hash digest for HMAC on string
    '''
    return hmac.new(SECRET,s).hexdigest()

def make_secure_val(s):
    '''Add a HMAC hash digest to string

    Used for cookies

    Args:
        s: String to have hash added

    Returns:
        String with HMAC of string.  Seperated by pipe "|"
    '''
    return "%s|%s" % (s, hash_str(s))

def check_secure_val(h):
    '''Verifies cookie is valid using HMAC

    Used for cookies

    Args:
        h: String cookie value.  "string|hash"

    Returns:
        String cookie value without hash
    '''
    val = h.split("|")[0]
    if h == make_secure_val(val):
        return val


app = webapp2.WSGIApplication([("/", BlogFront),
                               ("/blog/?", BlogFront),
                               ("/blog/([0-9]+)", PostPage),
                               ("/blog/newpost", NewPost),
                               ("/blog/signup", Signup),
                               ("/blog/login", Login),
                               ("/blog/logout", Logout)],
                              debug=True)
