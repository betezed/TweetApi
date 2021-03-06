#! /usr/bin/python
# -*- coding:utf-8 -*-
from config import local_config


import hashlib
import os
import json
import datetime
from bson.objectid import ObjectId
from pymongo import MongoClient

client = MongoClient()
from operator import itemgetter
from flask import Flask, request, make_response

app = Flask(__name__)

db = client.tweetDB
users_collection = db.users
tweets_collection = db.tweets


#####################################################
#                   GET METHODS                     #
#####################################################


@app.route('/mongo/users/')
def mongo_get_users():
    followings = []
    logged_in = False
    handle = None
    if "Authorization" in request.headers.keys():
        for user in users_collection.find():
            if check_authen(user['handle'], request):
                handle = user['handle']
                logged_in = True
    if logged_in:
        user = find_user(handle)
        for following in user['followings']:
            followings.append(following['handle'])
    users = []
    for user in users_collection.find():
        remove_follow_attributes(user)
        user['_id'] = str(user['_id'])
        if not local_config['local']:
            user.pop('password', None)
            user.pop('token', None)
        if logged_in:
            if user['handle'] in followings:
                user['following'] = True
            else:
                user['following'] = False
        users.append(user)
    return get_response(users, 200)


@app.route('/mongo/tweets/')
def mongo_get_tweets():
    tweets = []
    for tweet in tweets_collection.find():
        tweet['_id'] = str(tweet['_id'])
        tweets.append(tweet)
    return get_response(tweets, 200)


@app.route('/mongo/<handle>/')
def mongo_get_user(handle):
    return get_response(find_user(handle), 200)


@app.route('/mongo/<handle>/tweets/')
def mongo_get_tweets_of_user(handle):
    tweets = []
    for tweet in tweets_collection.find({'handle': handle}):
        tweet['_id'] = str(tweet['_id'])
        tweets.append(tweet)
    return get_response(tweets, 200)


@app.route('/mongo/<handle>/followers/')
def mongo_get_followers_of_user(handle):
    followers = []
    user = find_user(handle)
    for follower in user['followers']:
        follower = remove_follow_attributes(find_user(follower['handle']))
        followers.append(follower)
    return get_response(followers, 200)


@app.route('/mongo/<handle>/followings/')
def mongo_get_followings_of_user(handle):
    followings = []
    user = find_user(handle)
    for following in user['followings']:
        following = remove_follow_attributes(find_user(following['handle']))
        following['following'] = True
        followings.append(following)
    return get_response(followings, 200)


@app.route('/mongo/<handle>/reading_list/')
def mongo_get_reading_list(handle):
    user = find_user(handle)
    tweets = []
    for follower in user['followers']:
        for tweet in tweets_collection.find({'handle': follower['handle']}):
            tweet['_id'] = str(tweet['_id'])
            tweets.append(tweet)
    tweets = sorted(tweets, key=itemgetter('date'), reverse=True)
    return get_response(tweets, 200)


#####################################################
#                   POST METHODS                    #
#####################################################


@app.route('/mongo/users/post/', methods=['POST', 'GET'])
def mongo_add_user():
    user = get_parameters(request)
    user['token'] = hashlib.sha1(os.urandom(128)).hexdigest()
    if 'password' not in user.keys():
        user['password'] = 'test'    
    if 'profilePicture' not in user.keys():
        user['profilePicture'] = 'http://www.cabb01.club/wp-content/uploads/2014/12/inconnu.jpg'    
    if 'status' not in user.keys():
        user['status'] = 'offline'
    users_collection.insert(user)
    status = {'result': True}
    return get_response(status, 201)


@app.route('/mongo/<handle>/tweets/post/', methods=['POST', 'GET'])
def mongo_add_tweet(handle):
    if not check_authen(handle, request):
        return get_response("", 401, True)
    tweet = get_parameters(request)
    tweet['handle'] = handle
    now = datetime.datetime.now()
    tweet['date'] = now.strftime("%Y/%m/%d")
    tweets_collection.insert(tweet)
    status = {'result': True}
    return get_response(status, 201)


@app.route('/mongo/<handle>/followers/post/', methods=['POST', 'GET'])
def mongo_add_follower(handle):
    if not check_authen(handle, request):
        return get_response("", 401, True)
    follower = get_parameters(request)
    follower = follower['handle']
    user = find_user(handle, None, True)
    if 'error' in find_user(follower, None, False).keys():
        status = {'result': False}
        return get_response(status, 400, True)
    user['_id'] = ObjectId(user['_id'])
    ref = {'_id': user['_id']}
    user['followers'].append({'handle': follower})
    users_collection.update(ref, user)
    status = {'result': True}
    return get_response(status, 201, True)


@app.route('/mongo/<handle>/followers/delete/', methods=['DELETE', 'GET'])
def mongo_del_follower(handle):
    if not check_authen(handle, request):
        return get_response("", 401, True)
    follower = get_parameters(request)
    follower = follower['handle']
    user = find_user(handle, None, True)
    if 'error' in find_user(follower, None, False).keys():
        status = {'result': False}
        return get_response(status, 400, True)
    user['_id'] = ObjectId(user['_id'])
    ref = {'_id': user['_id']}
    user['followers'].remove({'handle': follower})
    tweets_collection.update(ref, user)
    status = {'result': True}
    return get_response(status, 200, True)


@app.route('/mongo/<handle>/followings/post/', methods=['POST', 'GET'])
def mongo_add_following(handle):
    if not check_authen(handle, request):
        return get_response("", 401, True)
    following = get_parameters(request)
    following = following['handle']
    user = find_user(handle, None, True)
    if 'error' in find_user(following, None, False).keys():
        status = {'result': False}
        return get_response(status, 400, True)
    for c_following in user['followings']:
        if c_following['handle'] == following:
            status = {'result': False}
            return get_response(status, 409, True)
    user['_id'] = ObjectId(user['_id'])
    ref = {'_id': user['_id']}
    user['followings'].append({'handle': following})
    users_collection.update(ref, user)
    status = {'result': True}
    return get_response(status, 201, True)


@app.route('/mongo/<handle>/followings/delete/', methods=['DELETE', 'GET'])
def mongo_del_following(handle):
    if not check_authen(handle, request):
        return get_response("", 401, True)
    following = get_parameters(request)
    following = following['handle']
    user = find_user(handle, None, True)
    if 'error' in find_user(following, None, False).keys():
        status = {'result': False}
        return get_response(status, 400, True)
    user['_id'] = ObjectId(user['_id'])
    ref = {'_id': user['_id']}
    user['followings'].remove({'handle': following})
    users_collection.update(ref, user)
    status = {'result': True}
    return get_response(status, 200, True)


@app.route('/mongo/session/', methods=['POST', 'GET'])
def mongo_session():
    response = get_parameters(request)
    status = None
    if verify_password(response['handle'], response['password']):
        user = find_user(response['handle'], None, True)
        status = str(user['token'])
        return get_response(status, 200, False, True)
    else:
        return get_response(status, 401, True)

#####################################################
#                   UTILS METHODS                   #
#####################################################


def find_user(handle, password=None, get_token=False):
    users = []
    if password is not None:
        collection = users_collection.find({'handle': handle, 'password': password})
    else:
        collection = users_collection.find({'handle': handle})
    for user in collection:
        user['_id'] = str(user['_id'])
        users.append(user)
    if len(users) != 1:
        return {'error': 'Bad Request'}
    if not local_config['local'] and not get_token:
        users[0].pop('password', None)
        users[0].pop('token', None)
    return users[0]


def remove_follow_attributes(user):
    user.pop("followers", None)
    user.pop("followings", None)
    return user


def get_response(content, status_code, empty_content=False, text=False):
    if not isinstance(content, list) \
            and not isinstance(content, str) \
            and not isinstance(content, unicode) \
            and content is not None \
            and 'error' in content.keys():
        status_code = 400
    if not empty_content:
        if text:
            response = make_response(content)
            response.mimetype = "text/plain"
        else:
            response = make_response(json.dumps(content))
            response.mimetype = "application/json"
    else:
        response = make_response()
    response.status_code = status_code
    return response


def get_parameters(content):
    if "application/json" in content.headers['Content-Type']:
        return content.get_json()
    else:
        parameters = {}
        for key in content.args:
            parameters[key] = content.args[key]
        return parameters


def check_authen(handle, content):
    user = find_user(handle, None, True)
    if 'error' in user.keys() or 'Authorization' not in content.headers.keys():
        return False
    if content.headers["Authorization"] != "Bearer-" + user['token']:
        print(content.headers['Authorization'])
        print(user['token'])
        return False
    return True


def verify_password(handle, password):
    user = find_user(handle, password)
    if 'error' in user.keys():
        return False
    return True


#####################################################
#                       START                       #
#####################################################

if __name__ == '__main__':
    if local_config['local']:
        app.run(debug=True)
    else:
        app.run(host='0.0.0.0', port=5667, debug=True)
