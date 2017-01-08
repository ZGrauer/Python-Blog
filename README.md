# Personal Blog in Google Cloud
----

## What is it?
A personal blog for posting content with commenting and score system. Built using Python for the backend, and runs on  [Google App Engine](https://cloud.google.com/appengine/). The Python server uses [jinja2](http://jinja.pocoo.org/) for HTML templating and stores all site data in [Google Cloud Datastore](https://cloud.google.com/datastore/docs/concepts/overview).

## Installation
1. Download and install [Python 2.7](https://www.python.org/downloads/)
2. Download and install [Google App Engine SDK for Python](https://cloud.google.com/appengine/docs/python/download)
    * Optionally, see this [quickstart guide](https://cloud.google.com/appengine/docs/python/getting-started/python-standard-env)
3. Sign Up for a [Google App Engine Account](https://console.cloud.google.com/appengine/)
4. Create a new project in [Google’s Developer Console](https://console.cloud.google.com/) using a unique name
5. Follow the [App Engine Quickstart](https://cloud.google.com/appengine/docs/python/quickstart) to get an app up and running
6. Clone this repository into Google's repository using these [instructions](https://cloud.google.com/source-repositories/docs/quickstart)


## Development
Modify the site as needed. `front.html` in the `templates` directory is inherited/extended by all other HTML templates. Edit this file to change the page header and navigation.  

Styling can be changed using CSS in file `style.css` in the `css` folder.

**Be sure to change the value of SECRET, which is used for hashing.** This can be found on line 16 of `main.py`.
```python
SECRET = "LVFuBg9EM8Bq3cd992Tb5g01Uh30GCV2"
```

#### Running Locally
To run the site on your local machine, run this command from a Terminal within the application's directory.
```sh
$ dev_appserver.py .
```

The site will then be avialible at `http://localhost:8080/`.
The local Google Datastore can be viewed and edited using this address `http://localhost:8000/`.
All valid paths can be used and edited at the bottom of `main.py`:
```python
app = webapp2.WSGIApplication([("/", BlogFront),
                               ("/blog/?", BlogFront),
                               ("/blog/([0-9]+)", PostPage),
                               ("/blog/newpost", NewPost),
                               ("/blog/signup", Signup),
                               ("/blog/login", Login),
                               ("/blog/logout", Logout)],
                              debug=True)
```

#### Deploying to Cloud
Modified app files can be deployed to Google Cloud using:
```sh
$ gcloud app deploy
```

## Todos
- [ ] Add user roles so only some users can post articles
- [X] Add like/dislike tracking to block multiple likes/dislikes
- [ ] Add user administration functionality

## License
MIT
