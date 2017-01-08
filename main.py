import os
import re
import string
import jinja2
import webapp2
import data
import hashing
import logging

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

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
        '''Checks for user cookie, if pressent set data.User object

        Called before every request in appengine
        '''
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie("username")
        self.user = uid and data.User.by_id(int(uid))

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
        cookie_val = hashing.make_secure_val(val)
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
        return cookie_val and hashing.check_secure_val(cookie_val)

    def login(self, user):
        ''' Sets the username cookie for the current user

        Uses set_secure_cookie for HMAC
        
        Args:
            user: data.User instance from DB

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
        posts = greetings = data.Post.all().order("-created")
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
        post = data.Post.get_by_id(int(post_id), parent = data.blog_key())
        if not post:
            self.error(404)
            return

        comments = data.Comment.all().ancestor(post).order("-created")
        post._render_text = post.content.replace("\n", "<br>")  
        self.render_post(post, comments)

    def post(self, post_id):
        '''Handles POST requests for full post page

        Handles the "action" from the valid user.
            like: add 1 to the post like count in DB. Not user's post
            dislike: subtract 1 from the post like count in DB. Not user's post
            delete: deletes data.Post entity from DB, only for your own posts.
            edit: edits data.Post entity in DB, only for your own posts.
            add_comment: adds a Comment to DB for data.Post.  Any valid user
            edit_comment: edits a comment only by the author. Val is ID
            delete_comment: deletes a comment only by the author. Val is ID
        If not a user, cannot add/edit/delete comment or like post
        
        Args:
            None

        Returns:
            rendered page
        '''
        post = data.Post.get_by_id(int(post_id), parent = data.blog_key())
        if not post:
            self.error(404)
            return

        if not self.user:
            self.render_post(post, comments)
            return
        
        post._render_text = post.content.replace("\n", "<br>")
        comments = data.Comment.all().ancestor(post).order("-created")
        
        post_action = self.request.get("action")
        edit_comment = self.request.get("edit_comment")
        delete_comment = self.request.get("delete_comment")
        if post_action=="like":
            post.add_like(self.user.key().id())
            post.put()
            self.render_post(post, comments)
        elif post_action=="delete":
            if data.User.by_id(post.user_id).username == self.user.username:
                post.delete()
                self.redirect("/blog")
        elif post_action=="edit":
            if data.User.by_id(post.user_id).username == self.user.username:
                post.title = self.request.get("title")
                post.content = self.request.get("content")
                post.put()
                self.redirect("/blog")
        elif post_action=="add_comment":
            c = data.Comment(parent = post.key(), user_id=self.user.key().id(),
                        content = self.request.get("comment_content"))
            c.put()
            self.render_post(post, comments)
        elif edit_comment:
            # Get specific comment edited based on the ID in btn value
            comment = data.Comment.get_by_id(long(edit_comment),
                                             parent = post.key())
            if not comment:
                self.render_post(post, comments)
                return
            if data.User.by_id(comment.user_id).username == self.user.username:
                comment_content = self.request.get(str(comment.key().id()))
                comment.content = comment_content
                comment.put()
                comments = data.Comment.all().ancestor(post).order("-created")
                self.render_post(post, comments)
        elif delete_comment:
            # Get specific comment to delete based on the ID in btn value
            comment = data.Comment.get_by_id(long(delete_comment),
                                             parent = post.key())
            if not comment:
                self.render_post(post, comments)
                return
            if data.User.by_id(comment.user_id).username == self.user.username:
                comment.delete()
                comments = data.Comment.all().ancestor(post).order("-created")
                self.render_post(post, comments)

    def render_post(self, post, comments):
        if self.user:
            self.render("permalink.html", post = post, comments = comments,
                        username = self.user.username,
                        post_username=data.User.by_id(post.user_id).username)
        else:
            self.render("permalink.html", post = post, comments = comments,
                        username = "Login", 
                        post_username=data.User.by_id(post.user_id).username)

        
class NewPost(BlogHandler):
    '''Handles the new post page of the blog

    inherits from BlogHandler
    Allows registered users to add new posst to the blog
    
    Attributes:
        None
    
    Methods:
        get: GET request to render new post page
        post: POST response from new post form. Create data.Post entity, then 
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
        Get values from user, create data.Post entity.
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
            p = data.Post(parent = data.blog_key(), title = title, content = content,
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
        post: POST response from signup form. Validate info & create data.User
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
        If good, create data.User entity and cookie. redirect to blog
        
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

        u = data.User.by_name(self.username)
        
        if u:
            params["error"] = "data.Username already exists!"
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
            u = data.User.register(self.username, self.pwd1, self.email)
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

        u = data.User.login(username, pwd)
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



app = webapp2.WSGIApplication([("/", BlogFront),
                               ("/blog/?", BlogFront),
                               ("/blog/([0-9]+)", PostPage),
                               ("/blog/newpost", NewPost),
                               ("/blog/signup", Signup),
                               ("/blog/login", Login),
                               ("/blog/logout", Logout)],
                              debug=True)
