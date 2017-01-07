import main
import hashing

from google.appengine.ext import db

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
        return main.render_str("postoverview.html", p = self,
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
        
        pw_hash = hashing.make_pw_hash(name, pw)
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
        if u and hashing.valid_pw(name, pw, u.password):
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
