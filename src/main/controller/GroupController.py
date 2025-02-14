from flask import request, jsonify, Blueprint
from src.main.db.models import Group, User, Post, Photo, Notification
from src.main.extensions import db
from src.main.utils.body_validator import check_data
from src.main.utils.authorization import check_group_permission
from flask_jwt_extended import (jwt_required,  get_jwt_identity)

group_bp = Blueprint("group_bp", __name__, url_prefix="/api/groups")

@group_bp.route("/", methods=["GET"])
@group_bp.route("/list", methods=["GET"])
@jwt_required()
def get_all_groups():
    groups = Group.query.all()
    groups_list = [group.to_dict() for group in groups]
    return jsonify(groups_list), 200


@group_bp.route("/my", methods=["GET"])
@jwt_required()
def get_user_groups():
    user_id = get_jwt_identity()
    user = User.query.filter_by(user_id=user_id).first()
    if user is None:
        return jsonify({"message": "No such user"}), 404
    user_groups = Group.query.join(Group.users).filter(User.user_id == user_id).all()
    groups_list = [group.to_dict() for group in user_groups]
    return jsonify(groups_list), 200

@group_bp.route("/<group_id>", methods=["GET"])
@jwt_required()
def get_group(group_id):
    group = Group.query.filter_by(group_id=group_id).first()
    if group == None:
        return jsonify({"message":"No such group"}), 404
    return jsonify(group.to_dict()), 200

@group_bp.route("/<group_id>/join", methods=["GET"])
@jwt_required()
def join_group(group_id):
    group = Group.query.filter_by(group_id=group_id).first()
    user_id = get_jwt_identity()
    if group == None:
        return jsonify({"message":"No such group"}), 404
    user = User.query.filter_by(user_id=user_id).first()
    if user == None:
        return jsonify({"message":"No such user"}), 404
    if user in group.users:
        return jsonify({"message":"User already in group"}), 400
    group.users.append(user)
    db.session.commit()
    return jsonify({"message":"User joined group"}), 200


@group_bp.route('/<group_id>/posts', methods=['GET'])
@jwt_required()
def get_posts(group_id):
    group = Group.query.filter_by(group_id=group_id).first()
    if group == None:
        return jsonify({"message":"No such group"}), 404
    posts = Post.query.filter_by(group_id=group_id).all()
    if posts == None:
        return jsonify({"message":"No posts"}), 404
    if not check_group_permission(get_jwt_identity(), group_id):
        return jsonify({"message":"No permission"}), 403
    posts_list = [post.to_dict() for post in posts]
    return jsonify(posts_list), 200

@group_bp.route('/<group_id>/posts', methods=['POST'])
@jwt_required()
def add_post(group_id):
    data = request.get_json()
    required_data = ['title', 'content', 'photos']
    response = check_data(data, required_data)
    if not response:
        return jsonify({"message":"Missing data"}), 400
    
    group = Group.query.filter_by(group_id=group_id).first()
    if not group:
        return jsonify({"message":"No such group"}), 404
    user_id = get_jwt_identity()
    if not check_group_permission(user_id, group_id):
        return jsonify({"message":"No permission"}), 403
    post = Post(title=data.get("title"), content=data.get("content"), group_id=group_id, user_id=user_id)
    db.session.add(post)
    db.session.commit()
    b64_photos = data.get('photos')
    if b64_photos:
        for b64_photo in b64_photos:
            photo = Photo(base64=b64_photo, post_id = post.post_id)
            db.session.add(photo)
            db.session.commit()
    # notify all users in group
    users = group.users
    for user in users:
        if user.user_id != user_id:
            notification = Notification(user_id=user.user_id, content=f"New post in group {group.name}", post_id=post.post_id)
            db.session.add(notification)
            db.session.commit()
    
    return jsonify({"message":"Post added"}), 200

@group_bp.route('/search/<phrase>', methods=['GET'])
@jwt_required()
def search_group_by_phrase(phrase):
    phrase = phrase.lower()
    groups = Group.query.all()
    valid = []
    for group in groups:
        if phrase in group.name.lower() or phrase in group.description.lower():
            valid.append(group.to_dict())
    if not valid:
        return jsonify({"message":"No such group"}), 404
    return jsonify(valid), 200
    